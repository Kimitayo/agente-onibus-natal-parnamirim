
"""
OBJETIVO: Ferramenta de consulta de itinerários de ônibus.

-> Consulta o arquivo osos_itinerarios.csv, gerado a partir OSOs
da STTU de Natal/RN.

Permite consultar as ruas e avenidas percorridas por uma
linha de ônibus, preservando a ordem dos logradouros
e separando os sentidos de IDA e VOLTA.

Associa cada itinerário ao seu documento oficial,
empresa, período de operação, data de vigência e fonte.

Esta ferramenta será integrada ao servidor MCP próprio
do projeto, permitindo que o agente responda perguntas
sobre os percursos das linhas.

Observação: os itinerários descrevem logradouros.
Não identificam, por si só, as paradas de embarque
e desembarque nem a posição atual dos veículos.
"""

import argparse
import csv
import json
from pathlib import Path

from tools.linhas import consultar_linhas, normalizar_codigo


RAIZ_PROJETO = Path(__file__).resolve().parents[1]

CAMINHO_CSV = (
    RAIZ_PROJETO
    / "dados"
    / "oso"
    / "tratados"
    / "osos_itinerarios.csv"
)


def consultar_itinerarios(codigo, sentido=None):
    """
    Consulta os itinerários de uma linha.

    Args:
        codigo: Código da linha, como "309" ou "L-54".
        sentido: "IDA", "VOLTA" ou None para ambos.

    Returns:
        Dicionário com itinerários agrupados por OSO
        e organizados por sentido e ordem.
    """

    if codigo is None or not str(codigo).strip():
        raise ValueError("Informe o código da linha.")

    if sentido is not None:
        sentido = str(sentido).strip().upper()

        if sentido not in {"IDA", "VOLTA"}:
            raise ValueError(
                "O sentido deve ser IDA ou VOLTA."
            )

    if not CAMINHO_CSV.is_file():
        raise FileNotFoundError(
            f"CSV não encontrado: {CAMINHO_CSV}"
        )

    metadados = consultar_linhas(codigo)

    metadados_por_oso = {
        (
            item["numero_oso"].strip(),
            item["vigencia"].strip(),
            item["arquivo_origem"].strip(),
        ): item
        for item in metadados
    }

    grupos = {}

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

        if cabecalho.count(separador) == 0:
            raise ValueError(
                "Não foi possível identificar o separador."
            )

        leitor = csv.DictReader(
            arquivo,
            delimiter=separador
        )

        colunas_obrigatorias = {
            "numero_oso",
            "linha",
            "empresa",
            "vigencia",
            "sentido",
            "ordem",
            "logradouro",
            "pagina_itinerario",
            "arquivo_origem",
            "fonte",
        }

        faltantes = colunas_obrigatorias - set(
            leitor.fieldnames or []
        )

        if faltantes:
            raise ValueError(
                f"Colunas ausentes: {sorted(faltantes)}"
            )

        for registro in leitor:

            linha = (registro["linha"] or "").strip()

            if normalizar_codigo(linha) != normalizar_codigo(codigo):
                continue

            sentido_registro = (
                registro["sentido"] or ""
            ).strip().upper()

            if sentido is not None and sentido_registro != sentido:
                continue

            logradouro = (
                registro["logradouro"] or ""
            ).strip()

            if not logradouro:
                continue

            numero_oso = (
                registro["numero_oso"] or ""
            ).strip()

            vigencia = (
                registro["vigencia"] or ""
            ).strip()

            arquivo_origem = (
                registro["arquivo_origem"] or ""
            ).strip()

            chave = (
                numero_oso,
                vigencia,
                arquivo_origem,
            )

            if chave not in grupos:

                metadado = metadados_por_oso.get(chave)

                grupos[chave] = {
                    "linha": linha,
                    "nome_linha": (
                        metadado["nome_linha"]
                        if metadado else None
                    ),
                    "empresa": (
                        metadado["empresa"]
                        if metadado else registro["empresa"]
                    ),
                    "numero_oso": numero_oso,
                    "vigencia": vigencia,
                    "periodo_operacao": (
                        metadado["periodo_operacao"]
                        if metadado else None
                    ),
                    "fonte": registro["fonte"],
                    "arquivo_origem": arquivo_origem,
                    "sentidos": {},
                }

            if sentido_registro not in grupos[chave]["sentidos"]:
                grupos[chave]["sentidos"][sentido_registro] = []

            grupos[chave]["sentidos"][sentido_registro].append({
                "ordem": registro["ordem"],
                "logradouro": logradouro,
                "pagina_itinerario": registro["pagina_itinerario"],
            })

    def ordenar_trecho(trecho):
        try:
            return int(trecho["ordem"])
        except (ValueError, TypeError):
            return 999999

    resultados = []

    for grupo in grupos.values():

        sentidos_organizados = []

        for nome_sentido in sorted(
            grupo["sentidos"],
            key=lambda s: (
                {"IDA": 0, "VOLTA": 1}.get(s, 2),
                s,
            )
        ):

            trechos = grupo["sentidos"][nome_sentido]
            trechos.sort(key=ordenar_trecho)

            sentidos_organizados.append({
                "sentido": nome_sentido,
                "total_registros": len(trechos),
                "logradouros": trechos,
            })

        grupo["sentidos"] = sentidos_organizados
        resultados.append(grupo)

    resultados.sort(
        key=lambda item: (
            item["numero_oso"],
            item["arquivo_origem"],
        )
    )

    total_registros = sum(
        sentido_item["total_registros"]
        for oso in resultados
        for sentido_item in oso["sentidos"]
    )

    return {
        "linha_consultada": str(codigo),
        "sentido_consultado": sentido,
        "total_osos": len(resultados),
        "total_registros_itinerario": total_registros,
        "osos": resultados,
        "observacao": (
            "Os itinerários são sequências de logradouros "
            "extraídas das OSOs disponíveis. "
            "Não comprovam quais paradas são atendidas "
            "nem confirmam que o percurso continua vigente."
        ),
    }


def main():

    parser = argparse.ArgumentParser(
        description="Consultar itinerários nas OSOs da STTU"
    )

    parser.add_argument(
        "--linha",
        type=str,
        required=True,
        help="Código da linha. Exemplo: 309 ou L-54"
    )

    parser.add_argument(
        "--sentido",
        type=str.upper,
        choices=["IDA", "VOLTA"],
        default=None,
        help="Filtrar por IDA ou VOLTA. Padrão: ambos."
    )

    args = parser.parse_args()

    resultado = consultar_itinerarios(
        codigo=args.linha,
        sentido=args.sentido,
    )

    print(
        json.dumps(
            resultado,
            ensure_ascii=False,
            indent=2
        )
    )


if __name__ == "__main__":
    main()
