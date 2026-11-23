"""
Este arquivo é para limpeza de dados dos csv, para que o agente consiga consultar informações estruturadas de mandeira confiável (correta), não apenas depender do RAG.

# Como será a organização do que o RAG vai consultar e quais pelo python/pandas:
- CSV: python/pandas
- OSO: RAG
- Bus2: provisoriamente RAG

# o que o tratamento fez:
- todos os arquivos com 4 colunas
- cabeçalho padronizado
- periodos padronizados

# Onde cada novo csv está localizado:
agente-onibus-natal-parnamirim/dados/historicos/tratados
"""


import csv
import pandas as pd
import re
import unicodedata


from pathlib import Path
from io import StringIO # permite que o leitor csv percorra o texto já decodificado




# Caminho da pasta dos csv itinerario
RAIZ_PROJETO = Path(__file__).resolve().parent.parent
PASTA_CSV = RAIZ_PROJETO / "dados" / "historicos"
PASTA_TRATADOS = RAIZ_PROJETO / "dados" / "historicos" / "tratados"

# LEITURA DO TEXTO
def ler_texto(caminho: Path) -> tuple[str, str]:
    """Tenta ler o arquivo sem substituir bytes inválidos."""
    conteudo = caminho.read_bytes() # decode

    try:
        return conteudo.decode("utf-8-sig"), "UTF-8"
    except UnicodeDecodeError:
        return conteudo.decode("cp1252"), "Windows-1252 (a confirmar)"


# VERIFICAR A ESTRUTUR DO TEXTO
def verificar_estrutura(texto: str) -> None:
    """Compara a quantidade de campos dos registros com o cabeçalho."""
    leitor = csv.reader(
        StringIO(texto, newline=""),
        delimiter=",",
        strict=True,
    )

    total = 0
    divergentes = 0
    linhas_vazias = 0
    exemplos = []

    try:
        cabecalho = next(leitor, None)

        if not cabecalho:
            print("ERRO: cabeçalho ausente ou primeira linha vazia.")
            return

        quantidade_esperada = len(cabecalho)
        colunas_sem_nome = [
            posicao
            for posicao, nome in enumerate(cabecalho, start=1)
            if not nome.strip()
        ]

        print(f"Cabeçalho: {cabecalho}")
        print(f"Quantidade de campos no cabeçalho: {quantidade_esperada}")

        if colunas_sem_nome:
            print(f"ALERTA: colunas sem nome nas posições {colunas_sem_nome}")

        for registro in leitor:
            if not registro:
                linhas_vazias += 1
                continue

            total += 1

            if len(registro) != quantidade_esperada:
                divergentes += 1

                if len(exemplos) < 3:
                    exemplos.append(
                        (leitor.line_num, len(registro), registro)
                    )

    except csv.Error as erro:
        print(f"ERRO CSV próximo à linha física {leitor.line_num}: {erro}")
        print("A verificação deste arquivo foi interrompida.")
        return

    print(f"Registros analisados: {total}")
    print(f"Linhas vazias ignoradas na contagem: {linhas_vazias}")
    print(f"Registros com quantidade divergente de campos: {divergentes}")

    for numero_linha, quantidade, registro in exemplos:
        print(
            f"  Linha física final {numero_linha}: "
            f"{quantidade} campos; esperado: {quantidade_esperada}"
        )
        print(f"  Conteúdo: {registro}")


# CRIAR TABELA COM PANDAS
def criar_dataframe(texto: str) -> pd.DataFrame:
    """Cria uma tabela após conferir a quantidade de campos."""
    leitor = csv.reader(
        StringIO(texto, newline=""),
        delimiter=",",
        strict=True,
    )

    cabecalho = next(leitor, None)

    if not cabecalho:
        raise ValueError("Cabeçalho ausente ou primeira linha vazia.")

    for registro in leitor:
        if not registro:
            continue

        if len(registro) != len(cabecalho):
            raise ValueError(
                f"Registro terminado na linha física {leitor.line_num} "
                f"possui {len(registro)} campos; "
                f"o cabeçalho possui {len(cabecalho)}."
            )

    return pd.read_csv(
        StringIO(texto, newline=""),
        sep=",",
        dtype="string",
        keep_default_na=False,
        on_bad_lines="error", # para linhas consideradas invalidas
    )

# REMOVER COLUNAS VAZIAS
def remover_colunas_sem_nome_vazias(
    tabela: pd.DataFrame,
    texto: str,
) -> pd.DataFrame:
    """Remove da tabela somente colunas sem nome e sem conteúdo."""
    cabecalho = next(
        csv.reader(StringIO(texto, newline=""), delimiter=",", strict=True)
    )

    remover = []

    for posicao, nome_original in enumerate(cabecalho):
        if nome_original.strip():
            continue

        nome_coluna = tabela.columns[posicao]
        valores = tabela.iloc[:, posicao]

        tem_conteudo = valores.fillna("").str.strip().ne("").any()

        if tem_conteudo:
            print(
                f"ALERTA: coluna sem nome na posição {posicao + 1} "
                "possui conteúdo e será preservada."
            )
        else:
            remover.append(nome_coluna)

    print(f"Colunas sem nome e vazias removidas da tabela: {len(remover)}")

    return tabela.drop(columns=remover)

# RECONSTRUIR TABELA CONCEICAO HORÁRIO
def reconstruir_horario_conceicao(campos: list[str]) -> list[str]:
    """Organiza os campos de Conceição conforme a estrutura observada."""
    if len(campos) < 7:
        raise ValueError("Registro com menos de sete campos.")

    linha = campos[0].strip()
    nome = ",".join(campos[1:-5]).strip()

    viagem, carro, saida, frequencia, periodo = [
        valor.strip() for valor in campos[-5:]
    ]

    if not linha or not nome:
        raise ValueError("Código da linha ou nome vazio.")

    return [linha, nome, viagem, carro, saida, frequencia, periodo]

def criar_dataframe_conceicao(texto: str) -> pd.DataFrame:
    """Reconstrói os horários de Conceição e verifica todos os registros."""
    leitor = csv.reader(
        StringIO(texto, newline=""),
        delimiter=",",
        strict=True,
    )

    cabecalho = next(leitor, None)
    esperado = [
        "linha", "nome", "viagem", "carro",
        "saida terminal", "frequencia", "",
    ]

    if cabecalho is None or [
        nome.strip().casefold() for nome in cabecalho
    ] != esperado:
        raise ValueError("Cabeçalho diferente do esperado para Conceição.")

    registros = []
    total = 0
    nomes_reunidos = 0
    falhas = 0
    exemplos_falhas = []

    for campos in leitor:
        if not campos:
            continue

        total += 1

        try:
            registro = reconstruir_horario_conceicao(campos)
        except ValueError as erro:
            falhas += 1

            if len(exemplos_falhas) < 3:
                exemplos_falhas.append(
                    (leitor.line_num, str(erro), campos)
                )

            continue

        registros.append(registro)

        if len(campos) > 7:
            nomes_reunidos += 1

    print("\nRECONSTRUÇÃO DE CONCEIÇÃO")
    print(f"Registros analisados: {total}")
    print(f"Registros que passaram: {len(registros)}")
    print(f"Registros com partes do nome reunidas: {nomes_reunidos}")
    print(f"Registros que precisam de revisão: {falhas}")

    for linha_fisica, motivo, campos in exemplos_falhas:
        print(f"  Linha física final {linha_fisica}: {motivo}")
        print(f"  Conteúdo original: {campos}")

    if falhas:
        raise ValueError(
            "Reconstrução com pendências; tabela completa não criada."
        )

    if total == 0:
        raise ValueError("Arquivo sem registros de dados.")

    tabela = pd.DataFrame(
        registros,
        columns=[
            "Linha", "Nome", "Viagem", "Carro",
            "Saida Terminal", "Frequencia", "Periodo",
        ],
        dtype="string",
    )

    colunas_manter = ["Linha", "Nome", "Saida Terminal", "Periodo"]
    tabela = tabela.loc[:, colunas_manter].copy()

    horario_valido = tabela["Saida Terminal"].str.fullmatch(
        r"(?:[01][0-9]|2[0-3]):[0-5][0-9]",
        na=False,
    )

    rejeitados = tabela.loc[~horario_valido]
    tabela_tratada = tabela.loc[horario_valido].copy()

    print("\nSIMPLIFICAÇÃO DOS HORÁRIOS DE CONCEIÇÃO")
    print(f"Registros antes do filtro: {len(tabela)}")
    print(f"Registros com horário válido: {len(tabela_tratada)}")
    print(f"Registros fora do formato: {len(rejeitados)}")

    if not rejeitados.empty:
        print("Até três exemplos fora do formato:")
        print(rejeitados.head(3).to_string(index=False))

    return tabela_tratada


def simplificar_horarios(tabela: pd.DataFrame) -> pd.DataFrame:
    tabela = tabela.copy()

    # Uniformiza os títulos para reconhecer as variações dos arquivos.
    tabela.columns = tabela.columns.str.strip().str.casefold()

    tabela = tabela.rename(columns={
        "linha": "Linha",
        "nome": "Nome",
        "saida terminal": "Saida Terminal",
        "saida do terminal": "Saida Terminal",
        "periodo": "Periodo",
    })

    # Ausência de período significa informação desconhecida.
    if "Periodo" not in tabela.columns:
        tabela["Periodo"] = pd.NA

    colunas_manter = ["Linha", "Nome", "Saida Terminal", "Periodo"]
    tabela = tabela.loc[:, colunas_manter].copy()

    tabela["Saida Terminal"] = tabela["Saida Terminal"].str.strip()

    horario_valido = tabela["Saida Terminal"].str.fullmatch(
        r"(?:[01][0-9]|2[0-3]):[0-5][0-9]",
        na=False,
    )

    rejeitados = tabela.loc[~horario_valido]
    tabela_tratada = tabela.loc[horario_valido].copy()

    print("\nSIMPLIFICAÇÃO DOS HORÁRIOS")
    print(f"Registros antes do filtro: {len(tabela)}")
    print(f"Registros com horário válido: {len(tabela_tratada)}")
    print(f"Registros fora do formato: {len(rejeitados)}")

    if not rejeitados.empty:
        print("Até três exemplos fora do formato:")
        print(rejeitados.head(3).to_string(index=False))

    return tabela_tratada


def reconstruir_horario_reunidas(campos: list[str]) -> list[str]:
    if len(campos) < 6:
        raise ValueError("Registro de Reunidas com menos de seis campos.")

    linha = campos[0].strip()
    nome = ",".join(campos[1:-4]).strip()

    viagem, carro, saida, frequencia = [
        valor.strip() for valor in campos[-4:]
    ]

    if not linha or not nome:
        raise ValueError("Registro de Reunidas sem linha ou nome.")

    return [linha, nome, viagem, carro, saida, frequencia]


def criar_dataframe_reunidas(texto: str) -> pd.DataFrame:
    leitor = csv.reader(
        StringIO(texto, newline=""),
        delimiter=",",
        strict=True,
    )

    cabecalho = next(leitor, [])
    esperado = [
        "linha", "nome", "viagem", "carro",
        "saida terminal", "frequencia",
    ]

    if [campo.strip().casefold() for campo in cabecalho] != esperado:
        raise ValueError("Cabeçalho de Reunidas diferente do esperado.")

    registros = []
    nomes_reunidos = 0

    for campos in leitor:
        if not campos:
            continue

        try:
            registro = reconstruir_horario_reunidas(campos)
        except ValueError as erro:
            raise ValueError(
                f"Linha física {leitor.line_num}: {erro}"
            ) from erro

        registros.append(registro)

        if len(campos) > 6:
            nomes_reunidos += 1
            if nomes_reunidos <= 3:
                print(f"Exemplo reconstruído: {registro}")

    if not registros:
        raise ValueError("Nenhum registro encontrado em Reunidas.")

    print("\nRECONSTRUÇÃO DE REUNIDAS")
    print(f"Registros reconstruídos: {len(registros)}")
    print(f"Registros com partes do nome reunidas: {nomes_reunidos}")

    tabela = pd.DataFrame(
        registros,
        columns=[
            "Linha", "Nome", "Viagem", "Carro",
            "Saida Terminal", "Frequencia",
        ],
        dtype="string",
    )

    return simplificar_horarios(tabela)

def padronizar_colunas_itinerarios(tabela: pd.DataFrame) -> pd.DataFrame:
    tabela = tabela.copy()

    tabela.columns = tabela.columns.str.strip().str.casefold()

    tabela = tabela.rename(columns={
        "empresa": "Empresa",
        "linha": "Linha",
        "linha numero": "Linha",
        "nome": "Nome",
        "linha nome": "Nome",
        "periodo": "Periodo",
        "ida": "Ida",
        "volta": "Volta",
    })

    if tabela.columns.duplicated().any():
        raise ValueError("A padronização gerou títulos de coluna repetidos.")

    obrigatorias = ["Empresa", "Linha", "Nome", "Periodo", "Ida", "Volta"]
    faltantes = [
        coluna for coluna in obrigatorias
        if coluna not in tabela.columns
    ]

    if faltantes:
        raise ValueError(f"Colunas de itinerários ausentes: {faltantes}")

    return tabela


# PADRONIZAR OS NOMES EM PERIODO
def padronizar_periodo(valor):
    if pd.isna(valor):
        return pd.NA

    equivalencias = {
        "util": "Útil",
        "útil": "Útil",
        "dias uteis": "Útil",
        "dias úteis": "Útil",

        "sabado": "Sábado",
        "sábado": "Sábado",

        "domigo": "Domingo",
        "domingo": "Domingo",

        "feriado": "Feriado",
    }

    partes = [
        parte.strip()
        for parte in str(valor).split("/")
    ]

    partes_padronizadas = [
        equivalencias.get(parte.casefold(), parte)
        for parte in partes
    ]

    ordem = {
        "Domingo": 0,
        "Útil": 1,
        "Sábado": 2,
        "Feriado": 3,
    }

    partes_padronizadas = list(
        dict.fromkeys(partes_padronizadas)
    )

    partes_padronizadas.sort(
        key=lambda parte: ordem.get(parte, 99)
    )

    return "/".join(partes_padronizadas)




# NORMALIZAR IDENTIFICADORES PARA COMPARAÇÃO

def normalizar_nome_linha(valor: object) -> str:
    """Cria uma versão normalizada do nome da linha."""

    if pd.isna(valor):
        return ""

    texto = str(valor).casefold().strip()

    # Remove acentos
    texto = unicodedata.normalize("NFKD", texto)

    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )

    # Substitui pontuação e separadores por espaços
    texto = re.sub(r"[^a-z0-9]+", " ", texto)

    # Remove espaços repetidos
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto


def normalizar_codigo_linha(valor: object) -> str:
    """Padroniza o código da linha para comparação."""

    if pd.isna(valor):
        return ""

    return re.sub(r"\s+", "", str(valor).strip()).upper()


# NORMALIZAR NOMES LINHAS
def preparar_rotas(tabela: pd.DataFrame) -> pd.DataFrame:
    """Extrai identificadores únicos de linhas de uma tabela."""

    colunas = ["Linha", "Nome"]

    faltantes = [
        coluna
        for coluna in colunas
        if coluna not in tabela.columns
    ]

    if faltantes:
        raise ValueError(
            f"Colunas necessárias para comparação ausentes: {faltantes}"
        )

    rotas = tabela[colunas].copy()

    rotas["Linha"] = (
        rotas["Linha"].astype("string").fillna("").str.strip()
    )

    rotas["Nome"] = (
        rotas["Nome"].astype("string").fillna("").str.strip()
    )

    rotas["linha_norm"] = rotas["Linha"].map(
        normalizar_codigo_linha
    )

    rotas["nome_norm"] = rotas["Nome"].map(
        normalizar_nome_linha
    )

    # Não considera registros sem código ou nome
    rotas = rotas.loc[
        (rotas["linha_norm"] != "")
        & (rotas["nome_norm"] != "")
    ]

    # Remove repetições da mesma linha
    rotas = rotas.drop_duplicates(
        subset=["linha_norm", "nome_norm"]
    ).reset_index(drop=True)

    return rotas


# DIAGNÓSTICO DE CORRESPONDÊNCIA ENTRE HORÁRIOS E ITINERÁRIOS
def diagnosticar_correspondencias(
    tabelas: dict[str, pd.DataFrame]
) -> None:
    """Compara as linhas dos arquivos de horários e itinerários."""

    empresas = [
        "conceicao",
        "guanabara",
        "natal",
        "reunidas",
        "santamaria",
        "viasul",
    ]

    for empresa in empresas:

        nome_horarios = f"horarios_{empresa}"
        nome_itinerarios = f"itinerarios_{empresa}"

        print("\n" + "=" * 75)
        print(f"DIAGNÓSTICO DE CORRESPONDÊNCIA: {empresa.upper()}")
        print("=" * 75)

        # Verifica se os dois arquivos foram processados
        if (
            nome_horarios not in tabelas
            or nome_itinerarios not in tabelas
        ):
            print("Um ou ambos os arquivos não foram processados.")
            continue

        # Extrai as linhas únicas
        rotas_h = preparar_rotas(tabelas[nome_horarios])
        rotas_i = preparar_rotas(tabelas[nome_itinerarios])

        print(f"Rotas únicas nos horários: {len(rotas_h)}")
        print(f"Rotas únicas nos itinerários: {len(rotas_i)}")

        # 1. Correspondência por código e nome
        exatas = rotas_h.merge(
            rotas_i,
            on=["linha_norm", "nome_norm"],
            suffixes=("_horarios", "_itinerarios"),
        )

        # 2. Mesmo nome, mas códigos diferentes
        mesmo_nome = rotas_h.merge(
            rotas_i,
            on="nome_norm",
            suffixes=("_horarios", "_itinerarios"),
        )

        mesmo_nome = mesmo_nome.loc[
            mesmo_nome["linha_norm_horarios"]
            != mesmo_nome["linha_norm_itinerarios"]
        ]

        # 3. Mesmo código, mas nomes diferentes
        mesmo_codigo = rotas_h.merge(
            rotas_i,
            on="linha_norm",
            suffixes=("_horarios", "_itinerarios"),
        )

        mesmo_codigo = mesmo_codigo.loc[
            mesmo_codigo["nome_norm_horarios"]
            != mesmo_codigo["nome_norm_itinerarios"]
        ]

        print("\nRESULTADOS DA COMPARAÇÃO")

        print(
            "Códigos de linha em comum:",
            len(
                set(rotas_h["linha_norm"])
                & set(rotas_i["linha_norm"])
            ),
        )

        print(
            "Nomes normalizados em comum:",
            len(
                set(rotas_h["nome_norm"])
                & set(rotas_i["nome_norm"])
            ),
        )

        print(
            f"Correspondências exatas (código + nome): "
            f"{len(exatas)}"
        )

        print(
            f"Mesmo nome, código diferente: "
            f"{len(mesmo_nome)} pares candidatos"
        )

        print(
            f"Mesmo código, nome diferente: "
            f"{len(mesmo_codigo)} pares candidatos"
        )

        # Identifica possíveis ambiguidades
        ambiguas_nome = (
            mesmo_nome.groupby(
                ["linha_norm_horarios", "nome_norm"]
            )["linha_norm_itinerarios"].nunique()
        )

        ambiguas_codigo = (
            mesmo_codigo.groupby(
                ["linha_norm", "nome_norm_horarios"]
            )["nome_norm_itinerarios"].nunique()
        )

        print(
            "Rotas com mais de um código candidato pelo nome:",
            int((ambiguas_nome > 1).sum()),
        )

        print(
            "Rotas com mais de um nome candidato pelo código:",
            int((ambiguas_codigo > 1).sum()),
        )

        # Descobre quais rotas não possuem nenhum candidato
        chaves_h = set(
            zip(exatas["linha_norm"], exatas["nome_norm"])
        )

        chaves_i = set(
            zip(exatas["linha_norm"], exatas["nome_norm"])
        )

        chaves_h.update(
            zip(
                mesmo_nome["linha_norm_horarios"],
                mesmo_nome["nome_norm"],
            )
        )

        chaves_i.update(
            zip(
                mesmo_nome["linha_norm_itinerarios"],
                mesmo_nome["nome_norm"],
            )
        )

        chaves_h.update(
            zip(
                mesmo_codigo["linha_norm"],
                mesmo_codigo["nome_norm_horarios"],
            )
        )

        chaves_i.update(
            zip(
                mesmo_codigo["linha_norm"],
                mesmo_codigo["nome_norm_itinerarios"],
            )
        )

        sem_correspondencia_h = rotas_h.loc[
            [
                (linha, nome) not in chaves_h
                for linha, nome in zip(
                    rotas_h["linha_norm"],
                    rotas_h["nome_norm"],
                )
            ]
        ]

        sem_correspondencia_i = rotas_i.loc[
            [
                (linha, nome) not in chaves_i
                for linha, nome in zip(
                    rotas_i["linha_norm"],
                    rotas_i["nome_norm"],
                )
            ]
        ]

        print(
            "\nRotas sem candidato nos itinerários:",
            len(sem_correspondencia_h),
        )

        print(
            "Rotas sem candidato nos horários:",
            len(sem_correspondencia_i),
        )

        # Mostra exemplos para investigação manual
        if not mesmo_nome.empty:
            print("\nEXEMPLOS: MESMO NOME, CÓDIGO DIFERENTE")

            print(
                mesmo_nome[
                    [
                        "Linha_horarios",
                        "Nome_horarios",
                        "Linha_itinerarios",
                        "Nome_itinerarios",
                    ]
                ]
                .drop_duplicates()
                .head(5)
                .to_string(index=False)
            )

        if not mesmo_codigo.empty:
            print("\nEXEMPLOS: MESMO CÓDIGO, NOME DIFERENTE")

            print(
                mesmo_codigo[
                    [
                        "Linha_horarios",
                        "Nome_horarios",
                        "Linha_itinerarios",
                        "Nome_itinerarios",
                    ]
                ]
                .drop_duplicates()
                .head(5)
                .to_string(index=False)
            )

        if not sem_correspondencia_h.empty:
            print("\nEXEMPLOS: HORÁRIOS SEM CANDIDATO")

            print(
                sem_correspondencia_h[
                    ["Linha", "Nome"]
                ].head(10).to_string(index=False)
            )

        if not sem_correspondencia_i.empty:
            print("\nEXEMPLOS: ITINERÁRIOS SEM CANDIDATO")

            print(
                sem_correspondencia_i[
                    ["Linha", "Nome"]
                ].head(10).to_string(index=False)
            )




def main() -> None:
    if not PASTA_CSV.is_dir():
        print(f"Pasta não encontrada: {PASTA_CSV}")
        return

    arquivos = sorted(PASTA_CSV.glob("*.csv"))
    tabelas_processadas = {}
    PASTA_TRATADOS.mkdir(parents=True, exist_ok=True)

    print(f"Pasta consultada: {PASTA_CSV}")
    print(f"Arquivos CSV encontrados: {len(arquivos)}")

    for caminho in arquivos:
        print(f"\nARQUIVO: {caminho.name}")

        try:
            texto, codificacao = ler_texto(caminho)
        except (UnicodeError, OSError) as erro:
            print(f"ERRO DE LEITURA: {erro}")
            continue

        print(f"Codificação utilizada: {codificacao}")

        if not texto.strip():
            print("ALERTA: arquivo vazio ou contendo apenas espaços.")
            continue

        if "\ufffd" in texto:
            print("ALERTA: o texto contém o caractere de substituição �.")

        print("Amostra:")
        for linha in texto.splitlines()[:3]:
            print(linha)

        verificar_estrutura(texto)

        try:
            if caminho.name == "horarios_conceicao.csv":
                tabela = criar_dataframe_conceicao(texto)

            elif caminho.name == "horarios_reunidas.csv":
                tabela = criar_dataframe_reunidas(texto)

            else:
                tabela = criar_dataframe(texto)
                tabela = remover_colunas_sem_nome_vazias(tabela, texto)

                if caminho.name == "itinerarios_guanabara.csv":
                    coluna = "Unnamed: 25"

                    preenchida = tabela[coluna].fillna("").str.strip().ne("")
                    registros_com_conteudo = tabela.loc[preenchida]

                    print("\nINSPEÇÃO DA COLUNA SEM TÍTULO — GUANABARA")
                    print(f"Registros preenchidos: {len(registros_com_conteudo)}")

                    print("\nValores encontrados e suas quantidades:")
                    print(
                        registros_com_conteudo[coluna]
                        .value_counts()
                        .to_string()
                    )

                    print("\nAté dez registros para análise:")
                    print(registros_com_conteudo.head(10).to_string(index=False))

                    extra = registros_com_conteudo[coluna].fillna("").str.strip()
                    volta = registros_com_conteudo["Volta"].fillna("").str.strip()

                    iguais = extra.eq(volta)
                    divergentes = registros_com_conteudo.loc[~iguais]

                    print("\nCOMPARAÇÃO COM A COLUNA VOLTA")
                    print(f"Registros com conteúdo igual: {int(iguais.sum())}")
                    print(f"Registros com conteúdo diferente: {len(divergentes)}")

                    if not divergentes.empty:
                        print("\nAté dez registros diferentes:")
                        print(divergentes.head(10).to_string(index=False))
                        print("Coluna extra preservada porque existem divergências.")
                    else:
                        tabela = tabela.drop(columns=[coluna])
                        print("Coluna extra removida: todo conteúdo preenchido repete Volta.")

                if caminho.name.startswith("horarios_"):
                    tabela = simplificar_horarios(tabela)

                elif caminho.name.startswith("itinerarios_"):
                    tabela = padronizar_colunas_itinerarios(tabela)
                if caminho.name.startswith("itinerarios_"):
                    tabela["Periodo"] = tabela["Periodo"].apply(
                        padronizar_periodo
                    )

        except (ValueError, csv.Error, pd.errors.ParserError) as erro:
            print(f"TABELA NÃO CRIADA: {erro}")
            continue

        tabelas_processadas[caminho.stem] = tabela.copy()


        print("\nVALORES DE PERIODO")

        periodos = tabela["Periodo"].astype("string")
        ausentes = periodos.fillna("").str.strip().eq("")

        print(f"Registros sem período informado: {int(ausentes.sum())}")

        contagens = periodos.loc[~ausentes].value_counts()

        if contagens.empty:
            print("Nenhum período informado neste arquivo.")
        else:
            for valor, quantidade in contagens.items():
                print(f" {valor!r}: {quantidade} registros")


        print(f"Dimensões da tabela: {tabela.shape}")
        print(f"Colunas: {tabela.columns.tolist()}")
        print("Primeiros dois registros:")
        print(tabela.head(2).to_string(index=False))

        # SALVAR CSV TRATADO
        destino = PASTA_TRATADOS / caminho.name

        tabela.to_csv(
            destino,
            index=False,
            encoding="utf-8-sig"
        )

        print(f"CSV tratado salvo em: {destino}")

        print("\n\nINICIANDO DIAGNÓSTICO DE CORRESPONDÊNCIA")
        diagnosticar_correspondencias(tabelas_processadas)



if __name__ == "__main__":
    main()