
"""
OBJETIVO: Ferramenta de consulta de linhas de ônibus.
Consulta o arquivo osos_metadados.csv, gerado a partir da extração
das OSOs da STTU de Natal/RN.

Permite listar as linhas cadastradas na base ou buscar uma linha
específica pelo seu código, retornando informações como nome da
linha, empresa responsável, período de operação, data de vigência,
número da OSO e documento de origem.

Realiza a normalização dos códigos para facilitar a busca e
preserva registros diferentes de uma mesma linha, pois podem
existir OSOs para períodos de operação distintos.

Esta ferramenta será integrada ao servidor MCP próprio do
projeto, permitindo que o agente consulte informações oficiais
sobre as linhas de transporte público.

Observação: a consulta utiliza os documentos disponíveis na
base local. A data de vigência não garante que a programação
continua em operação atualmente.
"""




import argparse
import csv
import json
import re
from pathlib import Path


# Pasta principal do projeto
RAIZ_PROJETO = Path(__file__).resolve().parents[1]

# CSV oficial de metadados das OSOs
CAMINHO_CSV = (
    RAIZ_PROJETO
    / "dados"
    / "oso"
    / "tratados"
    / "osos_metadados.csv"
)


def normalizar_codigo(codigo):
    """
    Padroniza o código de uma linha para comparação.

    Exemplos:
        L-54 -> L54
        l54  -> L54
        309  -> 309

    Preserva as letras para não confundir linhas diferentes.
    """

    codigo = str(codigo).strip().upper()

    return re.sub(r"[\s_-]+", "", codigo)


def consultar_linhas(codigo=None):
    """
    Consulta os registros das linhas nas OSOs da STTU.

    Args:
        codigo: Código da linha que queremos consultar.
                Se for None, retorna todos os registros.

    Returns:
        Lista de dicionários com as informações encontradas.
    """

    if codigo is not None and not str(codigo).strip():
        raise ValueError("Informe um código de linha válido.")

    if not CAMINHO_CSV.exists():
        raise FileNotFoundError(
            f"CSV não encontrado: {CAMINHO_CSV}"
        )

    resultados = []

    with CAMINHO_CSV.open(
        encoding="utf-8-sig",
        newline=""
    ) as arquivo:

        cabecalho = arquivo.readline()
        arquivo.seek(0)

        separador = max(
            [",", ";", "\t"],
            key=cabecalho.count
        )

        leitor = csv.DictReader(
            arquivo,
            delimiter=separador
        )

        colunas_obrigatorias = {
            "numero_oso",
            "linha",
            "nome_linha",
            "empresa",
            "periodo_operacao",
            "vigencia",
            "fonte",
            "arquivo_origem",
        }

        colunas_encontradas = set(leitor.fieldnames or [])

        faltantes = colunas_obrigatorias - colunas_encontradas

        if faltantes:
            raise ValueError(
                f"Colunas ausentes: {sorted(faltantes)}"
            )

        for registro in leitor:

            linha = (registro["linha"] or "").strip()

            if not linha:
                continue

            # Filtrar pela linha solicitada, quando houver
            if codigo is not None:
                if normalizar_codigo(linha) != normalizar_codigo(codigo):
                    continue

            resultados.append({
                "linha": linha,
                "nome_linha": registro["nome_linha"],
                "empresa": registro["empresa"],
                "numero_oso": registro["numero_oso"],
                "periodo_operacao": registro["periodo_operacao"],
                "descricao_operacao": registro.get(
                    "descricao_operacao", ""
                ),
                "vigencia": registro["vigencia"],
                "fonte": registro["fonte"],
                "arquivo_origem": registro["arquivo_origem"],
            })

    resultados.sort(
        key=lambda item: (
            normalizar_codigo(item["linha"]),
            item["periodo_operacao"],
            item["numero_oso"],
        )
    )

    return resultados


def main():
    """Permite testar a consulta pelo terminal."""

    parser = argparse.ArgumentParser(
        description="Consultar linhas de ônibus nas OSOs da STTU"
    )

    parser.add_argument(
        "--linha",
        type=str,
        default=None,
        help="Código da linha. Exemplo: 309 ou L-54"
    )

    args = parser.parse_args()

    resultados = consultar_linhas(
        codigo=args.linha
    )

    linhas_distintas = {
        normalizar_codigo(item["linha"])
        for item in resultados
    }

    resposta = {
        "total_registros_oso": len(resultados),
        "total_linhas_distintas": len(linhas_distintas),
        "resultados": resultados,
        "observacao": (
            "Os registros representam documentos OSO disponíveis. "
            "A data de vigência não confirma, sozinha, "
            "que a programação continua em operação atualmente."
        ),
    }

    print(
        json.dumps(
            resposta,
            ensure_ascii=False,
            indent=2
        )
    )


if __name__ == "__main__":
    main()
