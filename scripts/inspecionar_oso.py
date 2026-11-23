
"""
OBJETIVO:
    Realizar a inspeção e os experimentos de extração de dados dos arquivos PDF de Ordem de Serviço Operacional (OSO), disponibilizados pela STTU de Natal/RN.

FUNCIONALIDADES:
    - INSPEÇÃO DO DOCUMENTO
    - DIAGNÓSTICO VISUAL DE TABELAS
    - INSPEÇÃO DE COORDENADAS
    - RECONSTRUÇÃO DO QUADRO DE HORÁRIOS

Foi usado: pdfplumber
"""





from pathlib import Path
import pdfplumber
import re


# CONFIGURAÇÕES E CAMINHOS DO PROJETO
RAIZ_PROJETO = Path(__file__).resolve().parent.parent

PASTA_ORIGINAIS = RAIZ_PROJETO / "dados" / "oso" / "originais"
PASTA_DIAGNOSTICOS = RAIZ_PROJETO / "dados" / "oso" / "diagnosticos"

PAGINA_QUADRO = 2

# Região vertical em que ficam o cabeçalho e as partidas do quadro.
Y_MIN_QUADRO = 190
Y_MAX_QUADRO = 700

# Diferença vertical máxima para considerar palavras pertencentes à mesma linha.
TOLERANCIA_LINHA = 1.5


# Cada bloco possui uma faixa horizontal própria para cada campo.
# As faixas foram definidas a partir das coordenadas observadas nos PDFs OSO.
# Os quatro blocos são percorridos, mesmo quando algum deles está vazio.
BLOCOS_QUADRO = [
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



# LOCALIZAR PDF DE TESTE
def localizar_pdf_teste():
    """Localiza o PDF utilizado nos experimentos de extração."""

    caminho = (
        PASTA_ORIGINAIS
        / "n-73-transnacional-vigencia-31-12-2023-domingos-feriados-santarem-ponta-negra-via-av.-nevaldo-rocha.pdf"
    )

    if not caminho.is_file():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {caminho}"
        )

    return caminho



# INSPECIONAR TEXTO E TABELAS
def inspecionar_pdf(caminho: Path):
    """Extrai e apresenta os textos e as tabelas identificadas em cada página."""

    with pdfplumber.open(caminho) as pdf:

        print("=" * 70)
        print("INFORMAÇÕES DO DOCUMENTO")
        print("=" * 70)

        print(f"Arquivo: {caminho.name}")
        print(f"Total de páginas: {len(pdf.pages)}")

        for numero, pagina in enumerate(pdf.pages, start=1):

            print("\n" + "=" * 70)
            print(f"PÁGINA {numero}")
            print("=" * 70)

            # EXTRAÇÃO DE TEXTO
            texto = pagina.extract_text()

            print("\nTEXTO EXTRAÍDO:")

            if texto:
                print(texto)
            else:
                print("Nenhum texto encontrado.")

            # EXTRAÇÃO DE TABELAS
            tabelas = pagina.extract_tables()

            print("\n" + "-" * 70)
            print(f"TABELAS IDENTIFICADAS: {len(tabelas)}")
            print("-" * 70)

            for indice, tabela in enumerate(tabelas, start=1):

                print(f"\nTABELA {indice}:")

                for linha in tabela:

                    valores = [
                        str(valor).replace("\n", " ").strip()
                        if valor is not None
                        else ""
                        for valor in linha
                    ]

                    print(" | ".join(valores))



# DIAGNÓSTICO VISUAL DA TABELA
def gerar_diagnostico_tabela(caminho: Path, numero_pagina=PAGINA_QUADRO):
    """Gera uma imagem que mostra como o pdfplumber identifica as tabelas."""

    PASTA_DIAGNOSTICOS.mkdir(
        parents=True,
        exist_ok=True
    )

    with pdfplumber.open(caminho) as pdf:

        indice = numero_pagina - 1

        if indice < 0 or indice >= len(pdf.pages):
            raise ValueError(
                f"O PDF não possui a página {numero_pagina}."
            )

        pagina = pdf.pages[indice]

        # Converte a página em imagem.
        imagem = pagina.to_image(resolution=160)

        # Desenha as linhas, interseções e células identificadas.
        imagem.debug_tablefinder()

        # Define onde salvar o diagnóstico.
        destino = (
            PASTA_DIAGNOSTICOS
            / f"{caminho.stem}_pagina_{numero_pagina}_diagnostico.png"
        )

        imagem.save(destino)

        print("\nDIAGNÓSTICO VISUAL")
        print(f"Imagem salva em: {destino}")



# INSPECIONAR COORDENADAS DO QUADRO DE HORÁRIOS
def obter_pagina_quadro(pdf):
    """Retorna a página que contém o quadro de horários."""

    indice = PAGINA_QUADRO - 1

    if indice < 0 or indice >= len(pdf.pages):
        raise ValueError(
            f"O PDF não possui a página {PAGINA_QUADRO}, "
            "onde se espera encontrar o quadro de horários."
        )

    return pdf.pages[indice]


def inspecionar_coordenadas_quadro(caminho: Path):
    """Exibe as palavras e suas coordenadas na região do quadro de horários."""

    with pdfplumber.open(caminho) as pdf:

        pagina = obter_pagina_quadro(pdf)

        palavras = pagina.extract_words(
            x_tolerance=2,
            y_tolerance=3
        )

        print("\n" + "=" * 70)
        print("COORDENADAS DO QUADRO DE HORÁRIOS")
        print("=" * 70)

        print(f"Largura da página: {pagina.width}")
        print(f"Altura da página: {pagina.height}")
        print(
            f"Região inspecionada: Y entre {Y_MIN_QUADRO} e {Y_MAX_QUADRO}"
        )

        for palavra in sorted(
            palavras,
            key=lambda p: (p["top"], p["x0"])
        ):

            if Y_MIN_QUADRO <= palavra["top"] <= Y_MAX_QUADRO:

                print(
                    f"Texto: {palavra['text']!r:<18} "
                    f"X inicial: {palavra['x0']:7.2f} "
                    f"Y superior: {palavra['top']:7.2f}"
                )



# FUNÇÕES AUXILIARES PARA RECONSTRUÇÃO DO QUADRO
def esta_na_faixa_x(palavra, faixa):
    """Verifica se a palavra começa dentro da faixa horizontal informada."""

    return faixa[0] <= palavra["x0"] < faixa[1]


def encontrar_palavra(linha, faixa_x, padrao):
    """Localiza, em uma linha, a primeira palavra que atende à faixa e ao padrão."""

    return next(
        (
            palavra
            for palavra in linha
            if esta_na_faixa_x(palavra, faixa_x)
            and re.fullmatch(
                padrao,
                palavra["text"],
                flags=re.IGNORECASE
            )
        ),
        None
    )


def extrair_frequencia(linha, faixa_x):
    """
    Localiza a frequência e retorna seu valor numérico.

    O PDF pode apresentar a frequência como '25', '25min' ou '25 min'.
    Quando 'min' aparece separado, somente o número é utilizado.
    """

    for palavra in linha:
        if not esta_na_faixa_x(palavra, faixa_x):
            continue

        texto = palavra["text"].replace(" ", "")

        if re.fullmatch(r"\d+(?:min)?", texto, flags=re.IGNORECASE):
            correspondencia = re.match(r"\d+", texto)
            return int(correspondencia.group())

    return None


# RECONSTRUIR O QUADRO DE HORÁRIOS DOS QUATRO BLOCOS
def extrair_horarios_quadro(caminho: Path):
    """
    Reconstrói as partidas dos quatro blocos do quadro de horários.

    A identificação dos campos é feita por coordenadas:
    - sequência;
    - código da tabela;
    - tipo de viagem (MI/MF), quando informado;
    - horário de saída;
    - frequência em minutos.

    Ao final, as partidas dos blocos são reunidas e ordenadas pela sequência.
    """

    with pdfplumber.open(caminho) as pdf:

        pagina = obter_pagina_quadro(pdf)

        palavras = pagina.extract_words(
            x_tolerance=2,
            y_tolerance=3
        )

        # Considera somente a região vertical do quadro de horários.
        palavras_quadro = [
            palavra
            for palavra in palavras
            if Y_MIN_QUADRO <= palavra["top"] <= Y_MAX_QUADRO
        ]

        horarios = []
        resumo_blocos = []

        # Percorre os quatro blocos horizontais.
        for numero_bloco, bloco in enumerate(BLOCOS_QUADRO, start=1):

            # Limita a busca à área horizontal do bloco atual.
            x_min = bloco["sequencia"][0]
            x_max = bloco["frequencia"][1]

            palavras_bloco = [
                palavra
                for palavra in palavras_quadro
                if x_min <= palavra["x0"] < x_max
            ]

            # Identifica os números de sequência do bloco.
            sequencias = [
                palavra
                for palavra in palavras_bloco
                if esta_na_faixa_x(
                    palavra,
                    bloco["sequencia"]
                )
                and re.fullmatch(
                    r"\d{1,3}",
                    palavra["text"]
                )
            ]

            sequencias.sort(key=lambda palavra: palavra["top"])

            partidas_bloco = []

            for sequencia in sequencias:

                # Reúne as palavras que estão aproximadamente na mesma altura.
                linha = [
                    palavra
                    for palavra in palavras_bloco
                    if abs(
                        palavra["top"] - sequencia["top"]
                    ) <= TOLERANCIA_LINHA
                ]

                # Identifica o código da tabela, como A1, B2 ou 1A1.
                codigo = encontrar_palavra(
                    linha,
                    bloco["codigo"],
                    r"(?:\d+[A-Za-z]\d+|[A-Za-z]\d+)"
                )

                # Identifica o horário de saída, como 05:30.
                saida = encontrar_palavra(
                    linha,
                    bloco["saida"],
                    r"\d{2}:\d{2}"
                )

                # Identifica a frequência em minutos.
                frequencia = extrair_frequencia(
                    linha,
                    bloco["frequencia"]
                )

                # MI e MF são informações opcionais.
                tipo_viagem = encontrar_palavra(
                    linha,
                    bloco["tipo"],
                    r"MI|MF"
                )

                # Verifica os campos obrigatórios.
                campos_faltantes = []

                if codigo is None:
                    campos_faltantes.append("código da tabela")

                if saida is None:
                    campos_faltantes.append("horário de saída")

                if frequencia is None:
                    campos_faltantes.append("frequência")

                if campos_faltantes:
                    print(
                        f"Registro incompleto no {bloco['nome']}: "
                        f"sequência {sequencia['text']}. "
                        f"Campos não identificados: "
                        f"{', '.join(campos_faltantes)}."
                    )
                    continue

                registro = {
                    "sequencia": int(sequencia["text"]),
                    "tabela": codigo["text"],
                    "tipo_viagem": (
                        tipo_viagem["text"].upper()
                        if tipo_viagem
                        else None
                    ),
                    "saida": saida["text"],
                    "frequencia_min": frequencia
                }

                partidas_bloco.append(registro)

            horarios.extend(partidas_bloco)

            resumo_blocos.append({
                "nome": bloco["nome"],
                "sequencias": len(sequencias),
                "partidas_extraidas": len(partidas_bloco)
            })

        # A numeração das partidas continua de um bloco para o outro.
        # Por isso, os registros são reunidos e ordenados pela sequência.
        horarios.sort(
            key=lambda registro: registro["sequencia"]
        )

        # Apresenta a quantidade identificada em cada bloco.
        print("\n" + "=" * 70)
        print("RESUMO DA EXTRAÇÃO POR BLOCO")
        print("=" * 70)

        for resumo in resumo_blocos:
            print(
                f"{resumo['nome']}: "
                f"{resumo['sequencias']} sequências identificadas; "
                f"{resumo['partidas_extraidas']} partidas extraídas."
            )

        # Verifica se há números de sequência repetidos.
        sequencias_extraidas = [
            horario["sequencia"]
            for horario in horarios
        ]

        repetidas = sorted({
            sequencia
            for sequencia in sequencias_extraidas
            if sequencias_extraidas.count(sequencia) > 1
        })

        if repetidas:
            print(
                "\nATENÇÃO: foram encontradas sequências repetidas: "
                f"{repetidas}"
            )

        # Exibe o quadro reconstruído.
        print("\n" + "=" * 70)
        print("QUADRO DE HORÁRIOS RECONSTRUÍDO")
        print("=" * 70)

        print(
            f"{'Seq.':<8}"
            f"{'Tab':<10}"
            f"{'Tipo':<12}"
            f"{'Saída':<12}"
            f"{'Frequência':<15}"
        )

        print("-" * 57)

        for horario in horarios:

            print(
                f"{horario['sequencia']:<8}"
                f"{horario['tabela']:<10}"
                f"{(horario['tipo_viagem'] or '-'):<12}"
                f"{horario['saida']:<12}"
                f"{horario['frequencia_min']} min"
            )

        print("-" * 57)
        print(
            f"Total de partidas extraídas: {len(horarios)}"
        )

        return horarios



# EXECUÇÃO PRINCIPAL
def main():

    arquivo = localizar_pdf_teste()

    inspecionar_pdf(arquivo)

    gerar_diagnostico_tabela(
        arquivo,
        numero_pagina=PAGINA_QUADRO
    )

    inspecionar_coordenadas_quadro(arquivo)

    extrair_horarios_quadro(arquivo)


if __name__ == "__main__":
    main()
