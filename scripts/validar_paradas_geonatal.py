"""
Arquivo para a validação da corretude dos dados extraidos do paradas geonatal
"""


import csv
from pathlib import Path

# Localizar a pasta principal do projeto
RAIZ = Path(__file__).resolve().parents[1]

# Caminho do CSV
CAMINHO = RAIZ / "dados" / "paradas" / "geonatal_paradas_2025.csv"

if not CAMINHO.exists():
    raise FileNotFoundError(f"CSV não encontrado: {CAMINHO}")

# Carregar os registros
with CAMINHO.open(encoding="utf-8-sig", newline="") as arquivo:
    leitor = csv.DictReader(arquivo)
    colunas = leitor.fieldnames or []
    paradas = list(leitor)

# Conferir a estrutura
obrigatorias = {"id_geonatal", "nome", "latitude", "longitude"}
faltantes = obrigatorias - set(colunas)

if faltantes:
    raise ValueError(f"Colunas ausentes: {faltantes}")

# Validar nomes e coordenadas
sem_nome = 0
coordenadas_invalidas = 0
ids_vazios = 0

for parada in paradas:
    if not parada["nome"].strip():
        sem_nome += 1

    if not parada["id_geonatal"].strip():
        ids_vazios += 1

    try:
        lat = float(parada["latitude"])
        lon = float(parada["longitude"])

        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            coordenadas_invalidas += 1
    except (ValueError, TypeError):
        coordenadas_invalidas += 1

print("\n=== VALIDAÇÃO DAS PARADAS ===")
print(f"Total de registros: {len(paradas)}")
print(f"Colunas: {colunas}")
print(f"Paradas sem nome: {sem_nome}")
print(f"Paradas sem ID: {ids_vazios}")
print(f"Coordenadas inválidas: {coordenadas_invalidas}")

print("\n=== EXEMPLOS ===")
for parada in paradas[:5]:
    print(
        f"{parada['id_geonatal']} | "
        f"{parada['nome']} | "
        f"{parada['latitude']}, {parada['longitude']}"
    )
