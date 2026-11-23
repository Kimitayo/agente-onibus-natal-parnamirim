
from pathlib import Path
import pdfplumber

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
PASTA_ORIGINAIS = RAIZ_PROJETO / "dados" / "oso" / "originais"

arquivos = list(PASTA_ORIGINAIS.glob("*l-54*.pdf"))

if len(arquivos) != 1:
    print("Arquivos encontrados:")
    for arquivo in arquivos:
        print(arquivo.name)

    raise ValueError("Esperado exatamente um PDF da L-54.")

ARQUIVO = arquivos[0]

with pdfplumber.open(ARQUIVO) as pdf:

    pagina = pdf.pages[1]

    palavras = pagina.extract_words(
        x_tolerance=2,
        y_tolerance=3
    )

    print("=" * 70)
    print("DIAGNÓSTICO DAS MARCAÇÕES DA OSO L-54")
    print("=" * 70)

    print(f"Arquivo: {ARQUIVO.name}")
    print(f"Dimensões: {pagina.width} x {pagina.height}")

    marcacoes = [
        p for p in palavras
        if p["text"].strip().upper() in {"MI", "MF", "I", "F"}
    ]

    print(f"\nTotal de marcações encontradas: {len(marcacoes)}")

    for marcacao in marcacoes:

        linha = [
            p for p in palavras
            if abs(p["top"] - marcacao["top"]) <= 2.5
        ]

        print("\n" + "-" * 60)

        print(
            f"MARCAÇÃO: {marcacao['text']} | "
            f"X: {marcacao['x0']:.2f} | "
            f"Y: {marcacao['top']:.2f}"
        )

        print("PALAVRAS DA MESMA LINHA:")

        for palavra in sorted(linha, key=lambda p: p["x0"]):
            print(
                f"X={palavra['x0']:7.2f} | "
                f"Texto={palavra['text']}"
            )

print("\nDiagnóstico finalizado.")
