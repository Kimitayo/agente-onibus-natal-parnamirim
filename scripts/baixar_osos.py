"""
Arquivo destinado ao download dos pdfs do site https://natal.rn.gov.br/sttu/oso, que constam todas as informações mais recentes sobre cada linha de onibus de Natal.
"""


from pathlib import Path
from urllib.parse import urljoin, urlparse
import csv

import requests
from bs4 import BeautifulSoup


# CAMINHOS
RAIZ_PROJETO = Path(__file__).resolve().parent.parent

URL_OSO = "https://natal.rn.gov.br/sttu/oso"

PASTA_OSO = RAIZ_PROJETO / "dados" / "oso"
PASTA_ORIGINAIS = PASTA_OSO / "originais"

PASTA_ORIGINAIS.mkdir(parents=True, exist_ok=True)


def encontrar_pdfs(session):
    """Identifica os links de PDFs na página oficial da STTU."""

    resposta = session.get(URL_OSO, timeout=30)
    resposta.raise_for_status()

    soup = BeautifulSoup(resposta.text, "html.parser")

    documentos = []

    for link in soup.find_all("a", href=True):
        url = urljoin(URL_OSO, link["href"])

        caminho = urlparse(url).path.lower()

        if (
            "/storage/app/media/sttu/oso/linhas/" in caminho
            and caminho.endswith(".pdf")
        ):
            documentos.append({
                "linha": link.get_text(" ", strip=True),
                "url": url,
                "arquivo": Path(urlparse(url).path).name,
            })

    # Remove URLs repetidas
    unicos = {
        documento["url"]: documento
        for documento in documentos
    }

    return list(unicos.values())


def baixar_documentos(session, documentos):
    """Baixa os PDFs e registra os resultados."""

    resultados = []

    for i, documento in enumerate(documentos, start=1):

        nome = documento["arquivo"]
        destino = PASTA_ORIGINAIS / nome

        print(f"\n[{i}/{len(documentos)}] {documento['linha']}")
        print(f"Arquivo: {nome}")

        try:
            resposta = session.get(
                documento["url"],
                timeout=60
            )

            resposta.raise_for_status()

            # Verifica se realmente recebemos um PDF
            if not resposta.content.startswith(b"%PDF"):
                raise ValueError("O conteúdo recebido não é um PDF.")

            destino.write_bytes(resposta.content)

            status = "BAIXADO"

            print(f"Download concluído: {destino}")

        except Exception as erro:

            status = "ERRO"

            print(f"Falha no download: {erro}")

        resultados.append({
            "linha": documento["linha"],
            "arquivo": nome,
            "url": documento["url"],
            "status": status,
            "tamanho_bytes": (
                destino.stat().st_size
                if status == "BAIXADO"
                else 0
            ),
        })

    return resultados


def salvar_manifesto(resultados):
    """Salva o inventário dos documentos encontrados."""

    destino = PASTA_OSO / "manifesto_osos.csv"

    with open(
        destino,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as arquivo:

        campos = [
            "linha",
            "arquivo",
            "url",
            "status",
            "tamanho_bytes",
        ]

        escritor = csv.DictWriter(
            arquivo,
            fieldnames=campos
        )

        escritor.writeheader()
        escritor.writerows(resultados)

    print(f"\nManifesto salvo em: {destino}")


def main():

    session = requests.Session()

    session.headers.update({
        "User-Agent": "Mozilla/5.0"
    })

    print("Acessando página oficial da STTU...")

    documentos = encontrar_pdfs(session)

    print(f"\nPDFs encontrados: {len(documentos)}")

    resultados = baixar_documentos(
        session,
        documentos
    )

    salvar_manifesto(resultados)

    baixados = sum(
        r["status"] == "BAIXADO"
        for r in resultados
    )

    erros = len(resultados) - baixados

    print("\nRESUMO")
    print(f"Documentos encontrados: {len(documentos)}")
    print(f"Documentos baixados: {baixados}")
    print(f"Falhas: {erros}")


if __name__ == "__main__":
    main()
