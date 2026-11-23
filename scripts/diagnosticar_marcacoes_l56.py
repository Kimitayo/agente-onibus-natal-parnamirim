"""
OBJETIVO: Fazer um diagnóstico visual das coordenadas na linha L-56

O que vai ser descoberto?
As sequencias 1, 11 e 17, porque pode conter as marcações horário e marcação esperada.
"""


from pathlib import Path
import pdfplumber

# PDF que estamos investigando
RAIZ_PROJETO = Path(__file__).resolve().parent.parent

ARQUIVO = (
    RAIZ_PROJETO
    / "dados"
    / "oso"
    / "originais"
    / "l-56-opcional-vigencia-26-04-2026-domingos-feriados-rocas-ponta-negra-via-via-costeira.pdf"
)

# Dimensões de referência utilizadas no extrator
LARGURA_REFERENCIA = 595.32
ALTURA_REFERENCIA = 913.36

# Coordenadas dos quatro blocos
BLOCOS = [
    {
        "nome": "Bloco 1",
        "sequencia": (30, 50),
        "codigo": (48, 85),
        "tipo": (68, 95),
        "saida": (85, 125),
        "frequencia": (125, 165),
    },
    {
        "nome": "Bloco 2",
        "sequencia": (162, 182),
        "codigo": (182, 202),
        "tipo": (200, 225),
        "saida": (218, 258),
        "frequencia": (255, 295),
    },
    {
        "nome": "Bloco 3",
        "sequencia": (298, 318),
        "codigo": (318, 338),
        "tipo": (335, 360),
        "saida": (355, 395),
        "frequencia": (390, 430),
    },
    {
        "nome": "Bloco 4",
        "sequencia": (432, 452),
        "codigo": (453, 473),
        "tipo": (470, 495),
        "saida": (490, 530),
        "frequencia": (525, 565),
    },
]

if not ARQUIVO.exists():
    raise FileNotFoundError(f"PDF não encontrado: {ARQUIVO}")

with pdfplumber.open(ARQUIVO) as pdf:

    # O quadro de horários está na página 2
    pagina = pdf.pages[1]

    palavras = pagina.extract_words(
        x_tolerance=2,
        y_tolerance=3
    )

    escala_x = pagina.width / LARGURA_REFERENCIA
    escala_y = pagina.height / ALTURA_REFERENCIA

    y_min = 190 * escala_y
    y_max = min(700 * escala_y, pagina.height - 5)
    tolerancia = 1.5 * escala_y

    print("=" * 70)
    print("DIAGNÓSTICO DAS MARCAÇÕES DA OSO L-56")
    print("=" * 70)

    print(f"Dimensões: {pagina.width:.2f} x {pagina.height:.2f}")

    # Primeiro: localizar todas as ocorrências de I, F, MI e MF
    print("\nMARCAÇÕES ENCONTRADAS NA PÁGINA:")

    for palavra in palavras:
        texto = palavra["text"].upper()

        if texto in {"I", "F", "MI", "MF"}:
            print(
                f"Texto: {texto:3} | "
                f"X: {palavra['x0'] / escala_x:.2f} | "
                f"Y: {palavra['top'] / escala_y:.2f}"
            )

    # Segundo: inspecionar as linhas das sequências 1, 11 e 17
    print("\n" + "=" * 70)
    print("PALAVRAS NAS LINHAS DE REFERÊNCIA")
    print("=" * 70)

    sequencias_alvo = {"1", "11", "17"}

    for bloco in BLOCOS:

        seq_min, seq_max = bloco["sequencia"]
        freq_max = bloco["frequencia"][1]

        sequencias = [
            p for p in palavras
            if seq_min * escala_x <= p["x0"] < seq_max * escala_x
            and p["text"] in sequencias_alvo
            and y_min <= p["top"] <= y_max
        ]

        for sequencia in sequencias:

            linha = [
                p for p in palavras
                if abs(p["top"] - sequencia["top"]) <= tolerancia
                and seq_min * escala_x <= p["x0"] < freq_max * escala_x
            ]

            print(
                f"\n{bloco['nome']} | "
                f"Sequência {sequencia['text']}"
            )

            for palavra in sorted(linha, key=lambda p: p["x0"]):

                x = palavra["x0"] / escala_x

                zonas = [
                    campo
                    for campo in (
                        "sequencia",
                        "codigo",
                        "tipo",
                        "saida",
                        "frequencia",
                    )
                    if bloco[campo][0] <= x < bloco[campo][1]
                ]

                print(
                    f"X={x:7.2f} | "
                    f"Texto={palavra['text']:10} | "
                    f"Campo={','.join(zonas) or 'FORA DAS FAIXAS'}"
                )

print("\nDiagnóstico finalizado.")
