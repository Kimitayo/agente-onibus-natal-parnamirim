"""
OBJETIVO:  Extrair e organizar informações dos PDFs OSO

FUNCIONALIDADES: 
1. Percorre todos os PDFs de dados/oso/originais/.
2. Extrai metadados da OSO.
3. Reconstrói os itinerários de ida e volta usando coordenadas.
4. Reconstrói os quadros de horários nos quatro blocos horizontais.
5. Preserva registros incompletos para revisão, sem descartá-los.
6. Verifica sequências duplicadas e ausentes.
7. Compara o número de viagens declarado com as partidas extraídas. Quando
   existem marcações MI/MF, calcula também o equivalente de viagens completas:
       partidas completas - (quantidade de MI/MF / 2)
   Essa comparação é diagnóstica e não altera os registros.
8. Salva CSVs e uma cópia TXT do texto de cada PDF para apoiar a preparação
   futura do RAG. Os PDFs originais continuam sendo a fonte documental.

   
O doc l56 tem inconscistencia entre quantidade de viagens e o quadro de horários -> foi preservado no extrator
   
"""

from collections import Counter
from datetime import datetime
from pathlib import Path
import re
import unicodedata

import pandas as pd
import pdfplumber



# 1. CAMINHOS E CONFIGURAÇÕES
RAIZ_PROJETO = Path(__file__).resolve().parent.parent
PASTA_ORIGINAIS = RAIZ_PROJETO / "dados" / "oso" / "originais"
PASTA_TRATADOS = RAIZ_PROJETO / "dados" / "oso" / "tratados"
PASTA_TEXTOS_EXTRAIDOS = PASTA_TRATADOS / "textos_extraidos"

# Dimensões aproximadas do PDF usado como referência na inspeção.
LARGURA_REFERENCIA = 595.32
ALTURA_REFERENCIA = 913.36
Y_MIN_QUADRO = 190
Y_MAX_QUADRO = 700
TOLERANCIA_LINHA = 1.5

# Faixas horizontais dos campos em cada um dos quatro blocos.
# Mantêm as coordenadas já testadas no inspecionar_oso.py.

BLOCOS_QUADRO = [
    {
        "nome": "Bloco 1",
        "sequencia": (30, 50),
        "codigo": (48, 85),
        "tipo": (110, 125),
        "saida": (85, 125),
        "frequencia": (125, 165),
    },
    {
        "nome": "Bloco 2",
        "sequencia": (162, 182),
        "codigo": (182, 202),
        "tipo": (242, 257),
        "saida": (218, 258),
        "frequencia": (255, 295),
    },
    {
        "nome": "Bloco 3",
        "sequencia": (298, 318),
        "codigo": (318, 338),
        "tipo": (378, 393),
        "saida": (355, 395),
        "frequencia": (390, 430),
    },
    {
        "nome": "Bloco 4",
        "sequencia": (432, 452),
        "codigo": (453, 473),
        "tipo": (512, 527),
        "saida": (490, 530),
        "frequencia": (525, 565),
    },
]


COLUNAS_METADADOS = [
    "numero_oso", "linha", "nome_linha", "empresa", "descricao_operacao",
    "periodo_operacao", "tipo_operacao", "data_emissao", "vigencia",
    "numero_viagens_declarado", "numero_meias_viagens_declaradas", "frota",
    "numero_paradas", "extensao", "tempo_viagem", "velocidade_media",
    "km_morta", "data_permissao", "substitui_os", "estacoes_transferencia",
    "quantidade_paginas", "arquivo_origem", "fonte", "prioridade_fonte",
    "data_extracao",
]

COLUNAS_ITINERARIOS = [
    "numero_oso", "linha", "empresa", "vigencia", "sentido", "ordem",
    "logradouro", "pagina_itinerario", "arquivo_origem", "fonte",
    "prioridade_fonte",
]

COLUNAS_HORARIOS = [
    "numero_oso", "linha", "empresa", "vigencia", "sequencia",
    "codigo_tabela", "tipo_viagem", "saida_terminal", "frequencia_min",
    "bloco", "pagina_quadro", "status_registro", "campos_faltantes",
    "arquivo_origem", "fonte", "prioridade_fonte",
]

COLUNAS_RELATORIO = [
    "arquivo_origem", "numero_oso", "linha", "empresa", "vigencia",
    "pagina_itinerario", "pagina_quadro", "total_itinerarios", "total_partidas",
    "partidas_completas", "partidas_incompletas", "total_MI", "total_MF",
    "meias_viagens_detectadas", "meias_viagens_declaradas",
    "numero_viagens_declarado", "viagens_equivalentes_calculadas",
    "comparacao_viagens", "status_metadados", "status_itinerario",
    "status_horarios", "sequencias_duplicadas", "sequencias_ausentes",
    "status_geral", "observacoes", "data_extracao",
]



# 2. FUNÇÕES GERAIS
def limpar_espacos(texto):
    """Reduz espaços e quebras de linha consecutivos a um único espaço."""
    if texto is None:
        return None
    texto = re.sub(r"\s+", " ", str(texto)).strip()
    return texto or None


def normalizar_busca(texto):
    """Remove acentos e converte para maiúsculas, apenas para comparação."""
    texto = unicodedata.normalize("NFD", str(texto))
    texto = "".join(
        caractere for caractere in texto
        if unicodedata.category(caractere) != "Mn"
    )
    return texto.upper().strip()


def buscar_padrao(padrao, texto):
    """Retorna o primeiro grupo de uma expressão regular ou None."""
    match = re.search(padrao, texto or "", flags=re.IGNORECASE | re.DOTALL)
    return limpar_espacos(match.group(1)) if match else None


def converter_numero_br(valor):
    """Converte, por exemplo, '31,00' em 31.0 para comparação numérica."""
    if valor is None or str(valor).strip() == "":
        return None
    texto = str(valor).strip()
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def limpar_texto_coluna(texto):
    """Reconstrói o texto de uma coluna e corrige espaços junto à pontuação."""
    texto = limpar_espacos(texto)
    if not texto:
        return None
    texto = re.sub(r"\s+([,.;:)])", r"\1", texto)
    texto = re.sub(r"([(])\s+", r"\1", texto)
    return texto.strip()


def agrupar_palavras_por_linha(palavras, tolerancia=2.5):
    """Agrupa palavras com coordenadas verticais próximas."""
    ordenadas = sorted(palavras, key=lambda p: (p["top"], p["x0"]))
    linhas = []

    for palavra in ordenadas:
        if not linhas or abs(palavra["top"] - linhas[-1]["top_medio"]) > tolerancia:
            linhas.append({"palavras": [palavra], "top_medio": palavra["top"]})
        else:
            atual = linhas[-1]
            atual["palavras"].append(palavra)
            atual["top_medio"] = sum(p["top"] for p in atual["palavras"]) / len(atual["palavras"])

    return linhas


def texto_das_palavras(palavras):
    """Junta palavras da esquerda para a direita."""
    ordenadas = sorted(palavras, key=lambda p: p["x0"])
    return limpar_texto_coluna(" ".join(p["text"] for p in ordenadas))



# 3. METADADOS DA OSO
def extrair_metadados(texto_primeira_pagina, texto_completo, caminho):
    """Extrai os campos textuais da primeira página e observações do PDF."""
    texto = texto_primeira_pagina or ""
    plano = limpar_espacos(texto) or ""

    numero_oso = buscar_padrao(
        r"ORDEM\s+DE\s+SERVI[CÇ]O\s+OPERACIONAL\s*:\s*N[º°o]\s*([0-9./-]+)",
        plano,
    )

    linha_match = re.search(
        r"\bLINHA\s+([A-Z0-9]+(?:-[A-Z0-9]+)?)\s*-\s*(.+?)(?=\s+Empresa\b|$)",
        plano,
        flags=re.IGNORECASE,
    )
    if not linha_match:
        linha_match = re.search(
            r"^\s*LINHA\s+([A-Z0-9-]+)\s*-\s*(.+?)\s*$",
            texto,
            flags=re.IGNORECASE | re.MULTILINE,
        )

    linha = limpar_espacos(linha_match.group(1)) if linha_match else None
    descricao = limpar_espacos(linha_match.group(2)) if linha_match else None

    tipo_operacao = None
    periodo_operacao = descricao
    if descricao:
        tipo_match = re.search(r"\(([^()]*)\)\s*$", descricao)
        if tipo_match:
            tipo_operacao = limpar_espacos(tipo_match.group(1))
            periodo_operacao = limpar_espacos(descricao[:tipo_match.start()])

    nome_linha = buscar_padrao(
        r"Linha\s*-\s*N[º°o]\s*e\s*Nome\s+(.+?)\s+Vel\.\s*M[eé]dia\b",
        plano,
    )
    if nome_linha:
        nome_linha = re.sub(r"^[A-Z0-9-]+\s*-\s*", "", nome_linha).strip()

    empresa = buscar_padrao(r"\bEmpresa\s+(.+?)\s+Tempo\s+de\s+Viagem\b", plano)
    tempo_viagem = buscar_padrao(
        r"Tempo\s+de\s+Viagem\s+(.+?)\s+Linha\s*-\s*N[º°o]\s*e\s*Nome",
        plano,
    )
    velocidade_media = buscar_padrao(r"Vel\.\s*M[eé]dia\s+([\d.,]+)\s*km/h", plano)
    vigencia = buscar_padrao(r"In[ií]cio\s+Vig[eê]ncia\s+(\d{2}/\d{2}/\d{4})", plano)
    km_morta = buscar_padrao(r"\bKm\s+Morta\s+([\d.,]+)", plano)
    frota = buscar_padrao(r"\bFrota\s+(\d+)", plano)
    numero_paradas = buscar_padrao(r"N[º°o]\s+de\s+Paradas\s+(\d+)", plano)
    numero_viagens = buscar_padrao(r"N[º°o]\s+de\s+Viagens\s+([\d.,]+)", plano)
    data_permissao = buscar_padrao(r"Data\s+da\s+Permiss[aã]o\s+(\d{2}/\d{2}/\d{4})", plano)
    extensao = buscar_padrao(r"\bExtens[aã]o\s+([\d.,]+)", plano)
    data_emissao = buscar_padrao(
        r"Emitido\s+em.*?(\d{2}/\d{2}/\d{4}\s+às\s+\d{2}:\d{2}:\d{2})",
        texto,
    )
    substitui_os = buscar_padrao(
        r"Substitui\s+a\s+OS\s*(.*?)(?=Esta[cç][oõ]es|\s+ITINER[AÁ]RIO|$)",
        plano,
    )
    estacoes = buscar_padrao(
        r"Esta[cç][oõ]es\s+de\s+Transfer[eê]ncia\s*:\s*(.*?)(?=\s+ITINER[AÁ]RIO|$)",
        plano,
    )
    meias = buscar_padrao(r"(\d+)\s+MEIAS?\s+VIAGENS?", texto_completo or "")

    return {
        "numero_oso": numero_oso,
        "linha": linha,
        "nome_linha": nome_linha,
        "empresa": empresa,
        "descricao_operacao": descricao,
        "periodo_operacao": periodo_operacao,
        "tipo_operacao": tipo_operacao,
        "data_emissao": data_emissao,
        "vigencia": vigencia,
        "numero_viagens_declarado": numero_viagens,
        "numero_meias_viagens_declaradas": int(meias) if meias else None,
        "frota": frota,
        "numero_paradas": numero_paradas,
        "extensao": extensao,
        "tempo_viagem": tempo_viagem,
        "velocidade_media": velocidade_media,
        "km_morta": km_morta,
        "data_permissao": data_permissao,
        "substitui_os": substitui_os,
        "estacoes_transferencia": estacoes,
        "arquivo_origem": caminho.name,
        "fonte": "STTU - OSO",
        "prioridade_fonte": "ALTA",
    }



# 4. ITINERÁRIOS: IDA E VOLTA
def extrair_itinerarios_pagina(pagina, numero_pagina):
    """Reconstrói as colunas IDA e VOLTA de uma página de itinerário."""
    palavras = pagina.extract_words(x_tolerance=2, y_tolerance=3)

    titulo = next(
        (p for p in palavras if normalizar_busca(p["text"]) == "ITINERARIO"),
        None,
    )
    if titulo is None:
        return []

    candidatas_ida = [
        p for p in palavras
        if normalizar_busca(p["text"]) == "IDA" and p["top"] >= titulo["top"]
    ]
    candidatas_volta = [
        p for p in palavras
        if normalizar_busca(p["text"]) == "VOLTA" and p["top"] >= titulo["top"]
    ]
    if not candidatas_ida or not candidatas_volta:
        return []

    ida = min(candidatas_ida, key=lambda p: p["top"])
    volta = min(candidatas_volta, key=lambda p: p["top"])
    centro_ida = (ida["x0"] + ida["x1"]) / 2
    centro_volta = (volta["x0"] + volta["x1"]) / 2
    divisao = (centro_ida + centro_volta) / 2
    topo_inicio = max(ida["top"], volta["top"]) + 5

    limites = [
        p["top"] for p in palavras
        if normalizar_busca(p["text"]) in {"PONTOS", "PAVIMENTACAO"}
        and p["top"] > topo_inicio
    ]



    topo_fim = min(limites) if limites else pagina.height - 80

    # Localiza observações administrativas que aparecem
    # entre o itinerário e a seção seguinte do documento.
    palavras_candidatas = [
        p for p in palavras
        if topo_inicio <= p["top"] < topo_fim
    ]

    linhas_candidatas = agrupar_palavras_por_linha(
        palavras_candidatas,
        tolerancia=2.5
    )

    marcadores_observacao = (
        "A OSO OBEDECE",
        "EM FUNCAO DA GRATUIDADE",
    )

    for linha_candidata in linhas_candidatas:
        texto_linha = normalizar_busca(
            texto_das_palavras(linha_candidata["palavras"]) or ""
        )

        if any(
            marcador in texto_linha
            for marcador in marcadores_observacao
        ):
            topo_fim = min(
                topo_fim,
                min(p["top"] for p in linha_candidata["palavras"])
            )
            break

    palavras_rota = [
        p for p in palavras
        if topo_inicio <= p["top"] < topo_fim
    ]

    

    
    linhas = agrupar_palavras_por_linha(palavras_rota, tolerancia=2.5)

    registros = []
    for linha in linhas:
        palavras_linha = linha["palavras"]
        esquerda = [p for p in palavras_linha if p["x0"] < divisao]
        direita = [p for p in palavras_linha if p["x0"] >= divisao]
        texto_ida = texto_das_palavras(esquerda)
        texto_volta = texto_das_palavras(direita)

        if texto_ida:
            registros.append({
                "sentido": "IDA",
                "logradouro": texto_ida,
                "pagina_itinerario": numero_pagina,
            })
        if texto_volta:
            registros.append({
                "sentido": "VOLTA",
                "logradouro": texto_volta,
                "pagina_itinerario": numero_pagina,
            })

    return registros


def extrair_itinerarios_pdf(pdf):
    """Procura páginas de itinerário e numera os trechos de cada sentido."""
    registros = []
    paginas = []
    contadores = {"IDA": 0, "VOLTA": 0}

    for numero, pagina in enumerate(pdf.pages, start=1):
        texto = normalizar_busca(pagina.extract_text() or "")
        if "ITINERARIO" not in texto:
            continue

        encontrados = extrair_itinerarios_pagina(pagina, numero)
        if not encontrados:
            continue

        paginas.append(numero)
        for registro in encontrados:
            sentido = registro["sentido"]
            contadores[sentido] += 1
            registro["ordem"] = contadores[sentido]
            registros.append(registro)

    return registros, paginas



# 5. QUADRO DE HORÁRIOS: QUATRO BLOCOS
def esta_na_faixa_x(palavra, faixa):
    return faixa[0] <= palavra["x0"] < faixa[1]


def encontrar_palavra(linha, faixa_x, padrao):
    return next(
        (
            palavra for palavra in linha
            if esta_na_faixa_x(palavra, faixa_x)
            and re.fullmatch(padrao, palavra["text"], flags=re.IGNORECASE)
        ),
        None,
    )


def encontrar_tipo_viagem(linha, codigo, faixa_frequencia):
    """
    Identifica a marcação de meia viagem independentemente
    de ela aparecer antes ou depois do horário de saída.

    Formatos aceitos:
    - MI: meia viagem inicial
    - MF: meia viagem final
    - I: abreviação de MI
    - F: abreviação de MF
    """

    limite_esquerdo = (
        codigo["x1"] if codigo else float("-inf")
    )

    for palavra in sorted(linha, key=lambda p: p["x0"]):

        texto = palavra["text"].strip().upper()

        if (
            texto in {"MI", "MF", "I", "F"}
            and limite_esquerdo < palavra["x0"]
            and palavra["x0"] < faixa_frequencia[0]
        ):
            return palavra

    return None


def normalizar_tipo_viagem(texto):
    """
    Padroniza as abreviações encontradas nos PDFs.

    I  -> MI
    F  -> MF
    """

    tipo = texto.strip().upper()

    return {
        "I": "MI",
        "F": "MF"
    }.get(tipo, tipo)


def extrair_frequencia(linha, faixa_x):
    """Extrai a frequência numérica; zero é um valor válido."""
    for palavra in linha:
        if not esta_na_faixa_x(palavra, faixa_x):
            continue
        texto = palavra["text"].replace(" ", "")
        match = re.fullmatch(r"(\d{1,3})(?:min)?", texto, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def localizar_paginas_quadro(pdf):
    """Localiza todas as páginas cujo texto contém QUADRO DE HORÁRIO."""
    paginas = []
    for numero, pagina in enumerate(pdf.pages, start=1):
        texto = normalizar_busca(pagina.extract_text() or "")
        if "QUADRO DE HORARIO" in texto:
            paginas.append((numero, pagina))
    return paginas


def escalar_blocos(pagina):
    """Adapta as faixas de coordenadas às dimensões da página atual."""
    escala_x = pagina.width / LARGURA_REFERENCIA
    escala_y = pagina.height / ALTURA_REFERENCIA
    blocos = []

    for bloco in BLOCOS_QUADRO:
        escalado = {"nome": bloco["nome"]}
        for campo in ("sequencia", "codigo", "tipo", "saida", "frequencia"):
            escalado[campo] = (
                bloco[campo][0] * escala_x,
                bloco[campo][1] * escala_x,
            )
        blocos.append(escalado)

    y_min = Y_MIN_QUADRO * escala_y
    y_max = min(Y_MAX_QUADRO * escala_y, pagina.height - 5)
    tolerancia = TOLERANCIA_LINHA * escala_y
    return blocos, y_min, y_max, tolerancia


def extrair_horarios_pagina(pagina, numero_pagina):
    """Extrai partidas dos quatro blocos, preservando registros incompletos."""
    palavras = pagina.extract_words(x_tolerance=2, y_tolerance=3)
    blocos, y_min, y_max, tolerancia = escalar_blocos(pagina)
    palavras_quadro = [p for p in palavras if y_min <= p["top"] <= y_max]

    horarios = []
    resumos = []

    for bloco in blocos:
        x_min = bloco["sequencia"][0]
        x_max = bloco["frequencia"][1]
        palavras_bloco = [p for p in palavras_quadro if x_min <= p["x0"] < x_max]

        sequencias = [
            p for p in palavras_bloco
            if esta_na_faixa_x(p, bloco["sequencia"])
            and re.fullmatch(r"\d{1,3}", p["text"])
        ]
        sequencias.sort(key=lambda p: p["top"])
        partidas_bloco = []

        for sequencia in sequencias:
            linha = [
                p for p in palavras_bloco
                if abs(p["top"] - sequencia["top"]) <= tolerancia
            ]
            
            codigo = encontrar_palavra(
                linha,
                bloco["codigo"],
                r"(?!(?:MI|MF|I|F)$)[A-Za-z0-9]+"
            )

            tipo = encontrar_tipo_viagem(
                linha,
                codigo,
                bloco["frequencia"]
            )

            saida = encontrar_palavra(linha, bloco["saida"], r"\d{2}:\d{2}")
            frequencia = extrair_frequencia(linha, bloco["frequencia"])

            faltantes = []
            if codigo is None:
                faltantes.append("codigo_tabela")
            if saida is None:
                faltantes.append("saida_terminal")
            if frequencia is None:
                faltantes.append("frequencia_min")

            registro = {
                "sequencia": int(sequencia["text"]),
                "codigo_tabela": codigo["text"].upper() if codigo else None,
                "tipo_viagem": normalizar_tipo_viagem(
                    tipo["text"]
                ) if tipo else None,
                "saida_terminal": saida["text"] if saida else None,
                "frequencia_min": frequencia,
                "bloco": bloco["nome"],
                "pagina_quadro": numero_pagina,
                "status_registro": "INCOMPLETO" if faltantes else "OK",
                "campos_faltantes": ", ".join(faltantes) or None,
            }
            # Não descarta a partida: os campos ausentes ficam registrados.
            partidas_bloco.append(registro)

        horarios.extend(partidas_bloco)
        resumos.append({
            "bloco": bloco["nome"],
            "pagina_quadro": numero_pagina,
            "sequencias_identificadas": len(sequencias),
            "partidas_extraidas": len(partidas_bloco),
        })

    horarios.sort(key=lambda registro: registro["sequencia"])
    return horarios, resumos


def extrair_horarios_pdf(pdf):
    """Extrai horários de todas as páginas que contêm o quadro."""
    paginas_quadro = localizar_paginas_quadro(pdf)
    horarios = []
    resumos = []

    for numero, pagina in paginas_quadro:
        encontrados, resumo = extrair_horarios_pagina(pagina, numero)
        horarios.extend(encontrados)
        resumos.extend(resumo)

    return horarios, paginas_quadro, resumos



# 6. VALIDAÇÕES DOS HORÁRIOS
def analisar_sequencias(horarios):
    """Identifica sequências duplicadas e lacunas, separadamente por página."""
    duplicadas = []
    ausentes = []
    paginas = sorted({r["pagina_quadro"] for r in horarios})

    for pagina in paginas:
        sequencias = [
            r["sequencia"] for r in horarios
            if r["pagina_quadro"] == pagina
        ]
        contagem = Counter(sequencias)
        repetidas = sorted(seq for seq, qtd in contagem.items() if qtd > 1)
        if repetidas:
            duplicadas.append(f"página {pagina}: {repetidas}")

        if sequencias:
            faltantes = sorted(set(range(1, max(sequencias) + 1)) - set(sequencias))
            if faltantes:
                ausentes.append(f"página {pagina}: {faltantes}")

    return duplicadas, ausentes


def calcular_viagens_equivalentes(horarios):
    """Calcula o equivalente de viagens completas usando as marcações MI/MF."""
    completos = [r for r in horarios if r["status_registro"] == "OK"]

    total_mi = sum(
        r["tipo_viagem"] in {"MI", "I"}
        for r in completos
    )

    total_mf = sum(
        r["tipo_viagem"] in {"MF", "F"}
        for r in completos
    )

    total_meias = total_mi + total_mf
    equivalentes = len(completos) - (total_meias / 2)

    return {
        "partidas_completas": len(completos),
        "total_MI": total_mi,
        "total_MF": total_mf,
        "meias_viagens_detectadas": total_meias,
        "viagens_equivalentes_calculadas": round(equivalentes, 2),
    }


def comparar_numero_viagens(metadados, horarios, paginas_quadro):
    """Compara o declarado com o cálculo diagnóstico, sem alterar os dados."""
    declarado = converter_numero_br(metadados.get("numero_viagens_declarado"))

    if declarado is None:
        return None, "SEM_DADO"
    if len(paginas_quadro) != 1:
        return None, "MULTIPLAS_PAGINAS"
    if any(r["status_registro"] != "OK" for r in horarios):
        return None, "NAO_COMPARADO_REGISTROS_INCOMPLETOS"

    calculado = calcular_viagens_equivalentes(horarios)["viagens_equivalentes_calculadas"]
    if abs(declarado - calculado) <= 0.01:
        return calculado, "CONFERE"
    return calculado, "DIVERGENTE"



# 7. TEXTO EXTRAÍDO PARA APOIAR O RAG
def salvar_texto_extraido(caminho_pdf, textos_paginas):
    """Salva o texto de todas as páginas em TXT, mantendo a origem por página."""
    PASTA_TEXTOS_EXTRAIDOS.mkdir(parents=True, exist_ok=True)
    partes = []

    for numero, texto in textos_paginas:
        partes.append(f"\n{'=' * 20} PÁGINA {numero} {'=' * 20}\n")
        partes.append(texto or "")

    destino = PASTA_TEXTOS_EXTRAIDOS / f"{caminho_pdf.stem}.txt"
    destino.write_text("\n".join(partes), encoding="utf-8")
    return destino



# 8. PROCESSAMENTO DE UM PDF

def processar_oso(caminho, data_extracao):
    """Processa um PDF e retorna metadados, itinerários, horários e relatório."""
    observacoes = []

    with pdfplumber.open(caminho) as pdf:
        if not pdf.pages:
            raise ValueError("O PDF não possui páginas.")

        textos_paginas = [
            (numero, pagina.extract_text() or "")
            for numero, pagina in enumerate(pdf.pages, start=1)
        ]
        texto_primeira_pagina = textos_paginas[0][1]
        texto_completo = "\n\n".join(texto for _, texto in textos_paginas)

        metadados = extrair_metadados(
            texto_primeira_pagina, texto_completo, caminho
        )
        metadados["quantidade_paginas"] = len(pdf.pages)
        metadados["data_extracao"] = data_extracao

        try:
            itinerarios, paginas_itinerario = extrair_itinerarios_pdf(pdf)
        except Exception as erro:
            itinerarios, paginas_itinerario = [], []
            observacoes.append(f"Erro na extração do itinerário: {erro}")

        try:
            horarios, paginas_quadro, resumo_blocos = extrair_horarios_pdf(pdf)
        except Exception as erro:
            horarios, paginas_quadro, resumo_blocos = [], [], []
            observacoes.append(f"Erro na extração dos horários: {erro}")

        try:
            destino_txt = salvar_texto_extraido(caminho, textos_paginas)
            observacoes.append(f"Texto extraído salvo: {destino_txt.name}")
        except Exception as erro:
            observacoes.append(f"Não foi possível salvar o TXT: {erro}")

    itinerarios_saida = []
    for registro in itinerarios:
        itinerarios_saida.append({
            "numero_oso": metadados.get("numero_oso"),
            "linha": metadados.get("linha"),
            "empresa": metadados.get("empresa"),
            "vigencia": metadados.get("vigencia"),
            **registro,
            "arquivo_origem": caminho.name,
            "fonte": "STTU - OSO",
            "prioridade_fonte": "ALTA",
        })

    horarios_saida = []
    for registro in horarios:
        horarios_saida.append({
            "numero_oso": metadados.get("numero_oso"),
            "linha": metadados.get("linha"),
            "empresa": metadados.get("empresa"),
            "vigencia": metadados.get("vigencia"),
            **registro,
            "arquivo_origem": caminho.name,
            "fonte": "STTU - OSO",
            "prioridade_fonte": "ALTA",
        })

    duplicadas, ausentes = analisar_sequencias(horarios)
    resumo_viagens = calcular_viagens_equivalentes(horarios)
    viagens_calculadas, comparacao = comparar_numero_viagens(
        metadados, horarios, paginas_quadro
    )

    meias_declaradas = metadados.get("numero_meias_viagens_declaradas")
    meias_detectadas = resumo_viagens["meias_viagens_detectadas"]
    if meias_declaradas is None:
        status_meias = "NAO_INFORMADO"
    elif meias_declaradas == meias_detectadas:
        status_meias = "CONFERE"
    else:
        status_meias = "DIVERGENTE"

    essenciais = ["numero_oso", "linha", "empresa", "vigencia"]
    faltantes = [campo for campo in essenciais if not metadados.get(campo)]
    status_metadados = "OK" if not faltantes else "REVISAR"
    if faltantes:
        observacoes.append("Metadados não identificados: " + ", ".join(faltantes))

    status_itinerario = "OK" if itinerarios_saida else "NAO_IDENTIFICADO"
    if not itinerarios_saida:
        observacoes.append("Nenhum trecho de itinerário foi reconstruído.")

    incompletas = sum(r["status_registro"] == "INCOMPLETO" for r in horarios)
    if not horarios:
        status_horarios = "NAO_IDENTIFICADO"
        observacoes.append("Nenhuma partida foi extraída.")
    elif incompletas or duplicadas or ausentes:
        status_horarios = "REVISAR"
        if incompletas:
            observacoes.append(f"{incompletas} partida(s) incompleta(s).")
        if duplicadas:
            observacoes.append("Sequências duplicadas: " + " | ".join(duplicadas))
        if ausentes:
            observacoes.append("Sequências ausentes: " + " | ".join(ausentes))
    else:
        status_horarios = "OK"

    if comparacao == "DIVERGENTE":
        observacoes.append(
            "O número de viagens declarado diverge do cálculo diagnóstico "
            "baseado nas partidas e nas marcações MI/MF."
        )
    if status_meias == "DIVERGENTE":
        observacoes.append(
            "A quantidade declarada de meias viagens difere das marcações MI/MF extraídas."
        )
    if comparacao == "CONFERE":
        observacoes.append("Quantidade de viagens conferida pelo cálculo diagnóstico.")

    status_geral = "OK"
    if (
        status_metadados != "OK"
        or status_itinerario != "OK"
        or status_horarios != "OK"
        or comparacao == "DIVERGENTE"
        or status_meias == "DIVERGENTE"
    ):
        status_geral = "REVISAR"

    relatorio = {
        "arquivo_origem": caminho.name,
        "numero_oso": metadados.get("numero_oso"),
        "linha": metadados.get("linha"),
        "empresa": metadados.get("empresa"),
        "vigencia": metadados.get("vigencia"),
        "pagina_itinerario": ", ".join(map(str, paginas_itinerario)) or None,
        "pagina_quadro": ", ".join(str(n) for n, _ in paginas_quadro) or None,
        "total_itinerarios": len(itinerarios_saida),
        "total_partidas": len(horarios_saida),
        "partidas_completas": resumo_viagens["partidas_completas"],
        "partidas_incompletas": incompletas,
        "total_MI": resumo_viagens["total_MI"],
        "total_MF": resumo_viagens["total_MF"],
        "meias_viagens_detectadas": meias_detectadas,
        "meias_viagens_declaradas": meias_declaradas,
        "numero_viagens_declarado": metadados.get("numero_viagens_declarado"),
        "viagens_equivalentes_calculadas": viagens_calculadas,
        "comparacao_viagens": comparacao,
        "status_metadados": status_metadados,
        "status_itinerario": status_itinerario,
        "status_horarios": status_horarios,
        "sequencias_duplicadas": " | ".join(duplicadas) or None,
        "sequencias_ausentes": " | ".join(ausentes) or None,
        "status_geral": status_geral,
        "observacoes": " | ".join(observacoes) or None,
        "data_extracao": data_extracao,
    }

    return metadados, itinerarios_saida, horarios_saida, relatorio, resumo_blocos



# 9. GRAVAÇÃO DOS CSVs
def salvar_csv(registros, colunas, destino):
    """Salva os registros com separador ';' e codificação compatível com Excel."""
    tabela = pd.DataFrame(registros, columns=colunas)
    tabela.to_csv(destino, sep=";", index=False, encoding="utf-8-sig")


def salvar_resultados(metadados, itinerarios, horarios, relatorios):
    PASTA_TRATADOS.mkdir(parents=True, exist_ok=True)

    caminhos = {
        "metadados": PASTA_TRATADOS / "osos_metadados.csv",
        "itinerarios": PASTA_TRATADOS / "osos_itinerarios.csv",
        "horarios": PASTA_TRATADOS / "osos_horarios.csv",
        "relatorio": PASTA_TRATADOS / "relatorio_extracao_osos.csv",
    }

    salvar_csv(metadados, COLUNAS_METADADOS, caminhos["metadados"])
    salvar_csv(itinerarios, COLUNAS_ITINERARIOS, caminhos["itinerarios"])
    salvar_csv(horarios, COLUNAS_HORARIOS, caminhos["horarios"])
    salvar_csv(relatorios, COLUNAS_RELATORIO, caminhos["relatorio"])

    return caminhos



# 10. EXECUÇÃO PRINCIPAL: TODOS OS PDFs
def main():
    print("=" * 75)
    print("EXTRAÇÃO AUTOMATIZADA DAS ORDENS DE SERVIÇO OPERACIONAL")
    print("=" * 75)

    if not PASTA_ORIGINAIS.is_dir():
        raise FileNotFoundError(f"Pasta de PDFs não encontrada: {PASTA_ORIGINAIS}")

    arquivos = sorted(PASTA_ORIGINAIS.glob("*.pdf"))
    if not arquivos:
        print("Nenhum PDF foi encontrado na pasta de originais.")
        return

    print(f"PDFs encontrados: {len(arquivos)}")
    print(f"Entrada: {PASTA_ORIGINAIS}")
    print(f"Saída: {PASTA_TRATADOS}")

    todos_metadados = []
    todos_itinerarios = []
    todos_horarios = []
    todos_relatorios = []
    data_extracao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for indice, caminho in enumerate(arquivos, start=1):
        print("\n" + "-" * 75)
        print(f"[{indice}/{len(arquivos)}] {caminho.name}")
        print("-" * 75)

        try:
            metadados, itinerarios, horarios, relatorio, resumos = processar_oso(
                caminho, data_extracao
            )
            todos_metadados.append(metadados)
            todos_itinerarios.extend(itinerarios)
            todos_horarios.extend(horarios)
            todos_relatorios.append(relatorio)

            print(f"OSO: {metadados.get('numero_oso') or 'não identificada'}")
            print(f"Linha: {metadados.get('linha') or 'não identificada'}")
            print(f"Empresa: {metadados.get('empresa') or 'não identificada'}")
            for resumo in resumos:
                print(
                    f"{resumo['bloco']} (página {resumo['pagina_quadro']}): "
                    f"{resumo['sequencias_identificadas']} sequências; "
                    f"{resumo['partidas_extraidas']} partidas."
                )
            print(f"Trechos de itinerário: {len(itinerarios)}")
            print(f"Partidas extraídas: {len(horarios)}")
            print(f"Partidas incompletas: {relatorio['partidas_incompletas']}")
            print(f"Comparação de viagens: {relatorio['comparacao_viagens']}")
            print(f"Status geral: {relatorio['status_geral']}")

        except Exception as erro:
            mensagem = f"{type(erro).__name__}: {erro}"
            print(f"ERRO AO PROCESSAR PDF: {mensagem}")

            todos_metadados.append({
                "arquivo_origem": caminho.name,
                "fonte": "STTU - OSO",
                "prioridade_fonte": "ALTA",
                "data_extracao": data_extracao,
            })
            todos_relatorios.append({
                "arquivo_origem": caminho.name,
                "status_metadados": "ERRO",
                "status_itinerario": "NAO_PROCESSADO",
                "status_horarios": "NAO_PROCESSADO",
                "status_geral": "ERRO",
                "observacoes": mensagem,
                "data_extracao": data_extracao,
            })

    caminhos = salvar_resultados(
        todos_metadados,
        todos_itinerarios,
        todos_horarios,
        todos_relatorios,
    )

    quantidade_ok = sum(r.get("status_geral") == "OK" for r in todos_relatorios)
    quantidade_revisar = sum(r.get("status_geral") == "REVISAR" for r in todos_relatorios)
    quantidade_erro = sum(r.get("status_geral") == "ERRO" for r in todos_relatorios)

    print("\n" + "=" * 75)
    print("RESUMO FINAL DA EXTRAÇÃO")
    print("=" * 75)
    print(f"PDFs encontrados: {len(arquivos)}")
    print(f"OSOs sem apontamentos: {quantidade_ok}")
    print(f"OSOs que precisam de revisão: {quantidade_revisar}")
    print(f"PDFs com erro de processamento: {quantidade_erro}")
    print(f"Total de trechos de itinerário: {len(todos_itinerarios)}")
    print(f"Total de partidas extraídas: {len(todos_horarios)}")

    print("\nARQUIVOS GERADOS:")
    for nome, caminho in caminhos.items():
        print(f"- {nome}: {caminho}")
    print(f"- textos extraídos: {PASTA_TEXTOS_EXTRAIDOS}")

    print("\nExtração finalizada. Consulte o relatório para revisar divergências.")


if __name__ == "__main__":
    main()
