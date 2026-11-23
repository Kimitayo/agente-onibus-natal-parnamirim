"""
Vai verificar os 40 pdfs e gerar um csv mostrando a qualidade dos pdfs.

agente-onibus-natal-parnamirim/dados/oso

Resultado: ok
"""


from pathlib import Path

import pandas as pd
import pdfplumber


# CAMINHOS DO PROJETO
RAIZ_PROJETO = Path(__file__).resolve().parent.parent

PASTA_OSO = RAIZ_PROJETO / "dados" / "oso"
PASTA_ORIGINAIS = PASTA_OSO / "originais"

ARQUIVO_RELATORIO = PASTA_OSO / "relatorio_validacao_osos.csv"



def validar_pdf(caminho: Path) -> dict:
    """Extrai o texto de um PDF e verifica sua qualidade."""

    try:
        # ABRIR PDF E EXTRAIR O TEXTO
        with pdfplumber.open(caminho) as pdf:

            quantidade_paginas = len(pdf.pages)

            textos = [
                pagina.extract_text() or ""
                for pagina in pdf.pages
            ]

            caracteres = sum(
                len(texto.strip())
                for texto in textos
            )

            paginas_vazias = sum(
                not texto.strip()
                for texto in textos
            )

        # CLASSIFICAR RESULTADO
        if quantidade_paginas == 0 or caracteres == 0:
            status = "SEM TEXTO EXTRAIDO"

        elif paginas_vazias > 0:
            status = "REVISAR PAGINAS VAZIAS"

        else:
            status = "OK"

        return {
            "arquivo": caminho.name,
            "paginas": quantidade_paginas,
            "caracteres": caracteres,
            "paginas_vazias": paginas_vazias,
            "status": status,
            "erro": "",
        }

    except Exception as erro:

        return {
            "arquivo": caminho.name,
            "paginas": 0,
            "caracteres": 0,
            "paginas_vazias": 0,
            "status": "ERRO",
            "erro": str(erro),
        }



def main():

    if not PASTA_ORIGINAIS.exists():
        raise FileNotFoundError(
            f"Pasta não encontrada: {PASTA_ORIGINAIS}"
        )

    arquivos = sorted(
        PASTA_ORIGINAIS.glob("*.pdf")
    )

    if not arquivos:
        print("Nenhum PDF encontrado.")
        return

    print(f"PDFs encontrados: {len(arquivos)}")

    resultados = []

    for i, caminho in enumerate(arquivos, start=1):

        print(
            f"\n[{i}/{len(arquivos)}] "
            f"Analisando: {caminho.name}"
        )

        resultado = validar_pdf(caminho)

        resultados.append(resultado)

        print(f"Páginas: {resultado['paginas']}")
        print(f"Caracteres extraídos: {resultado['caracteres']}")
        print(f"Páginas sem texto: {resultado['paginas_vazias']}")
        print(f"Status: {resultado['status']}")

        if resultado["erro"]:
            print(f"Erro: {resultado['erro']}")

    # Cria o relatório geral
    tabela = pd.DataFrame(resultados)

    tabela.to_csv(
        ARQUIVO_RELATORIO,
        index=False,
        encoding="utf-8-sig"
    )

    # Resumo da validação
    print("\n" + "=" * 60)
    print("RESUMO DA VALIDAÇÃO DAS OSOs")
    print("=" * 60)

    print(f"Total de PDFs: {len(tabela)}")
    print(f"Total de páginas: {tabela['paginas'].sum()}")
    print(f"Total de caracteres: {tabela['caracteres'].sum()}")

    print("\nSituação dos documentos:")

    print(
        tabela["status"]
        .value_counts()
        .to_string()
    )

    print(
        f"\nRelatório salvo em: {ARQUIVO_RELATORIO}"
    )


if __name__ == "__main__":
    main()
