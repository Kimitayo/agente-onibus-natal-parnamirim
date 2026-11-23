
"""
OBJETIVO: Ferramenta de consulta de horários de ônibus.

-> Consulta o CSV de horários extraído das OSOs da STTU de Natal/RN.

Permite buscar os horários de saída de uma linha, organizando
os resultados por OSO e associando cada programação ao seu
período de operação e à respectiva fonte documental.

Preserva informações como sequência, horário, código da tabela,
tipo de viagem e status do registro.

Esta ferramenta será integrada ao servidor MCP próprio do
projeto para permitir consultas de horários pelo agente.

Observação: os horários são partidas programadas dos terminais,
não previsões em tempo real de chegada às paradas.
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
    / "osos_horarios.csv"
)


def consultar_horarios(codigo):
    """
    Consulta os horários de saída de uma linha.

    Args:
        codigo: Código da linha, como "309" ou "L-54".

    Returns:
        Dicionário com os horários agrupados por OSO.
    """

    if not str(codigo).strip():
        raise ValueError("Informe o código da linha.")

    if not CAMINHO_CSV.exists():
        raise FileNotFoundError(
            f"CSV não encontrado: {CAMINHO_CSV}"
        )

    # Obtém os metadados das OSOs já consultáveis
    # por meio da ferramenta tools/linhas.py.
    metadados = consultar_linhas(codigo)

    metadados_por_oso = {
        (
            item["numero_oso"],
            item["vigencia"],
            item["arquivo_origem"],
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
                "Não foi possível identificar o separador do CSV."
            )

        leitor = csv.DictReader(
            arquivo,
            delimiter=separador
        )

        colunas_obrigatorias = {
            "numero_oso",
            "linha",
            "vigencia",
            "sequencia",
            "codigo_tabela",
            "tipo_viagem",
            "saida_terminal",
            "status_registro",
            "arquivo_origem",
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

            numero_oso = (registro["numero_oso"] or "").strip()
            vigencia = (registro["vigencia"] or "").strip()
            arquivo_origem = (
                registro["arquivo_origem"] or ""
            ).strip()

            chave = (
                numero_oso,
                vigencia,
                arquivo_origem
            )

            if chave not in grupos:

                metadado = metadados_por_oso.get(chave)

                grupos[chave] = {
                    "linha": linha,
                    "numero_oso": numero_oso,
                    "vigencia": vigencia,
                    "periodo_operacao": (
                        metadado["periodo_operacao"]
                        if metadado else None
                    ),
                    "empresa": (
                        metadado["empresa"]
                        if metadado else (registro.get("empresa") or "")
                    ),
                    "fonte": registro.get("fonte", ""),
                    "arquivo_origem": arquivo_origem,
                    "horarios": []
                }

            grupos[chave]["horarios"].append({
                "sequencia": registro["sequencia"],
                "saida_terminal": registro["saida_terminal"],
                "codigo_tabela": registro["codigo_tabela"],
                "tipo_viagem": registro["tipo_viagem"],
                "frequencia_min": registro.get(
                    "frequencia_min", ""
                ),
                "status_registro": registro["status_registro"],
                "campos_faltantes": registro.get(
                    "campos_faltantes", ""
                )
            })

    osos = list(grupos.values())

    for oso in osos:

        def ordem(horario):
            try:
                return int(horario["sequencia"])
            except (ValueError, TypeError):
                return 999999

        oso["horarios"].sort(key=ordem)
        oso["total_partidas"] = len(oso["horarios"])

    total_partidas = sum(
        oso["total_partidas"]
        for oso in osos
    )

    return {
        "linha_consultada": codigo,
        "total_osos": len(osos),
        "total_partidas": total_partidas,
        "osos": osos,
        "observacao": (
            "Os horários representam partidas programadas "
            "nos documentos OSO disponíveis. "
            "Não são previsões em tempo real e a vigência "
            "não confirma, sozinha, a operação atual."
        )
    }


def main():
    parser = argparse.ArgumentParser(
        description="Consultar horários nas OSOs da STTU"
    )

    parser.add_argument(
        "--linha",
        type=str,
        required=True,
        help="Código da linha. Exemplo: 309 ou L-54"
    )

    args = parser.parse_args()

    resultado = consultar_horarios(
        codigo=args.linha
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
