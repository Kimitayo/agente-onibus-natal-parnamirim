
from pathlib import Path
import re
import pdfplumber


RAIZ_PROJETO = Path(__file__).resolve().parent.parent

PASTA_OSO = RAIZ_PROJETO / "dados" / "oso"
PASTA_ORIGINAIS = PASTA_OSO / "originais"


def contar_horarios_por_bloco(pagina):
    """Conta os horários encontrados em cada um dos quatro blocos."""

    palavras = pagina.extract_words()

    largura_pagina = pagina.width

    # Limites aproximados da tabela
    inicio_tabela = largura_pagina * 0.055
    fim_tabela = largura_pagina * 0.945

    largura_bloco = (
        (fim_tabela - inicio_tabela) / 4
    )

    contagens = [0, 0, 0, 0]

    for palavra in palavras:

        texto = palavra["text"]

        # Identifica valores no formato HH:MM
        if not re.fullmatch(r"\d{1,2}:\d{2}", texto):
            continue

        x = palavra["x0"]

        # Identifica em qual bloco o horário está
        for indice in range(4):

            centro = (
                inicio_tabela
                + largura_bloco * (indice + 0.485)
            )

            tolerancia = largura_bloco * 0.30

            if abs(x - centro) <= tolerancia:

                contagens[indice] += 1
                break

    return contagens


def diagnosticar_documento(caminho):

    print("\n" + "=" * 75)
    print(f"ARQUIVO: {caminho.name}")
    print("=" * 75)

    encontrou_quadro = False

    with pdfplumber.open(caminho) as pdf:

        for numero, pagina in enumerate(pdf.pages, start=1):

            texto = pagina.extract_text() or ""

            texto = " ".join(texto.upper().split())

            # Procura a página que contém o quadro de horários
            if "QUADRO" not in texto or "HOR" not in texto:
                continue

            encontrou_quadro = True

            contagens = contar_horarios_por_bloco(pagina)

            print(f"\nPágina: {numero}")

            for indice, quantidade in enumerate(
                contagens,
                start=1
            ):

                print(
                    f"Bloco {indice}: "
                    f"{quantidade} horários"
                )

            total = sum(contagens)

            blocos_preenchidos = sum(
                quantidade > 0
                for quantidade in contagens
            )

            print(f"Total de horários: {total}")
            print(
                f"Blocos utilizados: {blocos_preenchidos}/4"
            )

            if blocos_preenchidos > 1:
                print("ATENÇÃO: documento utiliza múltiplos blocos!")

    if not encontrou_quadro:
        print("Quadro de horários não localizado.")


def main():

    arquivos = sorted(
        PASTA_ORIGINAIS.glob("*.pdf")
    )

    print("=" * 75)
    print("DIAGNÓSTICO DOS QUATRO BLOCOS DAS OSOs")
    print("=" * 75)

    print(f"PDFs encontrados: {len(arquivos)}")

    for caminho in arquivos:

        try:
            diagnosticar_documento(caminho)

        except Exception as erro:

            print(f"Falha em {caminho.name}: {erro}")


if __name__ == "__main__":
    main()
