"""Indexa os PDFs originais das OSOs em Chroma.

Segue a sequência do notebook 11 - RAG:
PDFPlumberLoader -> RecursiveCharacterTextSplitter -> Chroma.

A indexação usa lotes pequenos, pausa entre chamadas e repetição com
backoff quando a API Gemini responde com limite 429. Também retoma uma
indexação interrompida, ignorando os chunks que já foram persistidos.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
import os
import re
import shutil
import time
from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.document_loaders import PDFPlumberLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag.indice import (
    NOME_COLECAO,
    PASTA_INDICE,
    RAIZ_PROJETO,
    criar_embeddings,
)

PASTA_PDFS = RAIZ_PROJETO / "dados" / "oso" / "originais"
CSV_METADADOS = RAIZ_PROJETO / "dados" / "oso" / "tratados" / "osos_metadados.csv"

# Valores conservadores para a cota gratuita de embeddings.
TAMANHO_LOTE_PADRAO = 5
INTERVALO_LOTES_PADRAO = 12.0
MAX_TENTATIVAS_429 = 5


def carregar_metadados() -> dict[str, dict[str, str]]:
    """Relaciona o nome de cada PDF aos metadados extraídos da OSO."""
    resultado: dict[str, dict[str, str]] = {}
    with CSV_METADADOS.open("r", encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo, delimiter=";")
        for registro in leitor:
            nome = (registro.get("arquivo_origem") or "").strip()
            if nome:
                resultado[nome] = registro
    return resultado


def metadados_validos(registro: dict[str, str], nome_pdf: str, pagina: int) -> dict:
    """Mantém somente tipos aceitos pelo Chroma e preserva a proveniência."""
    campos = {
        "source": nome_pdf,
        "arquivo_origem": nome_pdf,
        "page": pagina,
        "fonte": registro.get("fonte") or "STTU - OSO",
        "prioridade_fonte": registro.get("prioridade_fonte") or "ALTA",
        "linha": registro.get("linha") or "",
        "nome_linha": registro.get("nome_linha") or "",
        "numero_oso": registro.get("numero_oso") or "",
        "empresa": registro.get("empresa") or "",
        "periodo_operacao": registro.get("periodo_operacao") or "",
        "vigencia": registro.get("vigencia") or "",
    }
    return {chave: valor for chave, valor in campos.items() if valor is not None}


def carregar_documentos():
    """Carrega páginas dos PDFs originais e anexa metadados da OSO."""
    if not PASTA_PDFS.is_dir():
        raise FileNotFoundError(f"Pasta de PDFs não encontrada: {PASTA_PDFS}")
    if not CSV_METADADOS.is_file():
        raise FileNotFoundError(f"CSV de metadados não encontrado: {CSV_METADADOS}")

    metadados = carregar_metadados()
    arquivos = sorted(PASTA_PDFS.rglob("*.pdf"))
    if not arquivos:
        raise RuntimeError(f"Nenhum PDF encontrado em {PASTA_PDFS}")

    documentos = []
    erros = []

    for caminho in arquivos:
        try:
            paginas = PDFPlumberLoader(str(caminho)).load()
            registro = metadados.get(caminho.name, {})
            for documento in paginas:
                # O PDFPlumberLoader usa página indexada a partir de zero.
                pagina = int(documento.metadata.get("page", 0)) + 1
                documento.metadata = metadados_validos(registro, caminho.name, pagina)
                if documento.page_content.strip():
                    documentos.append(documento)
        except Exception as erro:
            erros.append((caminho.name, str(erro)))

    return arquivos, documentos, erros


def _eh_erro_de_limite(erro: Exception) -> bool:
    """Identifica erros de cota/rate limit que podem ser tentados novamente."""
    mensagem = str(erro).lower()
    return any(
        termo in mensagem
        for termo in ("429", "resource_exhausted", "quota exceeded", "rate limit")
    )


def _calcular_tempo_espera(erro: Exception, tentativa: int) -> int:
    """Usa o tempo recomendado pelo Google ou backoff exponencial."""
    mensagem = str(erro)
    padroes = (
        r"retry in\s+([\d.]+)\s*s",
        r"retryDelay['\"]?\s*:\s*['\"]?([\d.]+)\s*s",
    )

    for padrao in padroes:
        encontrado = re.search(padrao, mensagem, flags=re.IGNORECASE)
        if encontrado:
            return max(1, math.ceil(float(encontrado.group(1))) + 1)

    # 15, 30, 60, 120 segundos, no máximo.
    return min(15 * (2 ** (tentativa - 1)), 120)


def adicionar_lote_com_retentativa(
    vector_store: Chroma,
    documentos: list,
    ids: list[str],
) -> None:
    """Envia um lote ao Chroma e repete somente falhas temporárias 429."""
    for tentativa in range(1, MAX_TENTATIVAS_429 + 1):
        try:
            vector_store.add_documents(documents=documentos, ids=ids)
            return
        except Exception as erro:
            if not _eh_erro_de_limite(erro) or tentativa == MAX_TENTATIVAS_429:
                raise

            espera = _calcular_tempo_espera(erro, tentativa)
            print(
                f"Limite 429 do Gemini. Tentativa {tentativa}/"
                f"{MAX_TENTATIVAS_429 - 1} esgotada; aguardando {espera}s."
            )
            time.sleep(espera)


def indexar(recriar: bool = False) -> None:
    """Divide as páginas em chunks e persiste os embeddings no Chroma."""
    if recriar and PASTA_INDICE.exists():
        shutil.rmtree(PASTA_INDICE)
        print("Índice anterior removido por solicitação (--recriar).")

    PASTA_INDICE.parent.mkdir(parents=True, exist_ok=True)

    vector_store = Chroma(
        collection_name=NOME_COLECAO,
        embedding_function=criar_embeddings(),
        persist_directory=str(PASTA_INDICE),
        collection_metadata={"hnsw:space": "cosine"},
    )

    arquivos, documentos, erros = carregar_documentos()
    if not documentos:
        raise RuntimeError("Nenhuma página com texto foi extraída dos PDFs.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
    )
    chunks = splitter.split_documents(documentos)

    ids = []
    for indice, chunk in enumerate(chunks):
        chave = (
            f"{chunk.metadata.get('arquivo_origem')}|"
            f"{chunk.metadata.get('page')}|{indice}|{chunk.page_content}"
        )
        ids.append(hashlib.sha256(chave.encode("utf-8")).hexdigest())

    # Retoma a execução: chunks persistidos antes de uma interrupção são pulados.
    ids_existentes = set(vector_store.get().get("ids", []))
    indices_pendentes = [
        indice for indice, identificador in enumerate(ids)
        if identificador not in ids_existentes
    ]

    if not indices_pendentes:
        print("Todos os chunks deste conjunto de PDFs já estão indexados.")
        print(f"Chunks persistidos: {len(ids_existentes)}")
        print(f"Índice: {PASTA_INDICE}")
        return

    try:
        tamanho_lote = int(os.getenv("GEMINI_EMBEDDING_BATCH_SIZE", str(TAMANHO_LOTE_PADRAO)))
        intervalo_lotes = float(
            os.getenv("GEMINI_EMBEDDING_DELAY_SECONDS", str(INTERVALO_LOTES_PADRAO))
        )
    except ValueError as erro:
        raise ValueError(
            "GEMINI_EMBEDDING_BATCH_SIZE deve ser inteiro e "
            "GEMINI_EMBEDDING_DELAY_SECONDS deve ser numérico."
        ) from erro

    if tamanho_lote < 1:
        raise ValueError("GEMINI_EMBEDDING_BATCH_SIZE deve ser maior que zero.")
    if intervalo_lotes < 0:
        raise ValueError("GEMINI_EMBEDDING_DELAY_SECONDS não pode ser negativo.")

    print("\n=== INÍCIO DA INDEXAÇÃO RAG ===")
    print(f"PDFs encontrados: {len(arquivos)}")
    print(f"Páginas com texto: {len(documentos)}")
    print(f"Chunks criados: {len(chunks)}")
    print(f"Chunks já indexados: {len(ids_existentes)}")
    print(f"Chunks pendentes: {len(indices_pendentes)}")
    print(f"Tamanho do lote: {tamanho_lote}")
    print(f"Pausa entre lotes: {intervalo_lotes}s")

    enviados = 0
    total_lotes = math.ceil(len(indices_pendentes) / tamanho_lote)

    for numero_lote, inicio in enumerate(range(0, len(indices_pendentes), tamanho_lote), start=1):
        indices_lote = indices_pendentes[inicio:inicio + tamanho_lote]
        documentos_lote = [chunks[indice] for indice in indices_lote]
        ids_lote = [ids[indice] for indice in indices_lote]

        adicionar_lote_com_retentativa(
            vector_store=vector_store,
            documentos=documentos_lote,
            ids=ids_lote,
        )

        enviados += len(indices_lote)
        print(
            f"Lote {numero_lote}/{total_lotes} concluído. "
            f"Enviados nesta execução: {enviados}/{len(indices_pendentes)}."
        )

        if numero_lote < total_lotes and intervalo_lotes > 0:
            time.sleep(intervalo_lotes)

    ids_persistidos = set(vector_store.get().get("ids", []))
    ids_faltantes = set(ids) - ids_persistidos

    print("\n=== RESULTADO DA INDEXAÇÃO RAG ===")
    print(f"PDFs encontrados: {len(arquivos)}")
    print(f"Páginas com texto: {len(documentos)}")
    print(f"Chunks criados: {len(chunks)}")
    print(f"Chunks persistidos nesta coleção: {len(ids_persistidos)}")
    print(f"Chunks deste conjunto ainda ausentes: {len(ids_faltantes)}")
    print(f"Índice: {PASTA_INDICE}")

    if ids_faltantes:
        print("ATENÇÃO: a indexação ficou incompleta. Execute novamente sem --recriar para retomar.")
    else:
        print("INDEXAÇÃO CONCLUÍDA COM SUCESSO.")

    if erros:
        print(f"\nPDFs com erro de leitura: {len(erros)}")
        for nome, erro in erros:
            print(f"- {nome}: {erro}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Indexar PDFs das OSOs para o RAG")
    parser.add_argument(
        "--recriar",
        action="store_true",
        help="Apaga e recria o índice vetorial. Use somente se quiser descartar o índice atual.",
    )
    argumentos = parser.parse_args()
    indexar(recriar=argumentos.recriar)
