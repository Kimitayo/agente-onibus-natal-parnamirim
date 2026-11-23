
"""
OBJETIVO: Ferramenta de busca de paradas de ônibus próximas.

Consulta o CSV do GeoNatal, que contém as coordenadas geográficas
das paradas de ônibus de Natal/RN.

A partir da latitude e longitude informadas pelo usuário,
calcula a distância geográfica até cada parada utilizando
a fórmula de Haversine.

Retorna as paradas mais próximas, ordenadas por distância,
incluindo nome, identificador, coordenadas, distância em metros
e fonte dos dados.

Esta ferramenta será integrada ao servidor MCP próprio do
projeto, permitindo que o agente identifique paradas próximas
à localização do usuário.

Observação: as distâncias são calculadas em linha reta,
não considerando o percurso real pelas ruas.
"""



import argparse
import csv
import json
import math
from pathlib import Path


# Pasta principal do projeto
RAIZ_PROJETO = Path(__file__).resolve().parents[1]

# Arquivo com as paradas do GeoNatal
CAMINHO_CSV = (
    RAIZ_PROJETO
    / "dados"
    / "paradas"
    / "geonatal_paradas_2025.csv"
)

# Raio médio aproximado da Terra, em metros
RAIO_TERRA = 6_371_000


def calcular_distancia(lat1, lon1, lat2, lon2):
    """
    Calcula a distância em linha reta entre duas coordenadas
    geográficas utilizando a fórmula de Haversine.

    Retorna a distância em metros.
    """

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    diferenca_lat = lat2 - lat1
    diferenca_lon = lon2 - lon1

    a = (
        math.sin(diferenca_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(diferenca_lon / 2) ** 2
    )

    a = max(0.0, min(1.0, a))

    distancia = (
        2 * RAIO_TERRA * math.asin(math.sqrt(a))
    )

    return distancia


def buscar_paradas_proximas(latitude, longitude, limite=5):
    """
    Busca as paradas mais próximas de uma localização.

    Args:
        latitude: Latitude do usuário.
        longitude: Longitude do usuário.
        limite: Quantidade máxima de paradas retornadas.

    Returns:
        Lista de dicionários com informações das paradas,
        ordenada pela distância em metros.
    """

    # Validar as coordenadas recebidas
    if (
        not math.isfinite(latitude)
        or not -90 <= latitude <= 90
    ):
        raise ValueError("Latitude inválida.")

    if (
        not math.isfinite(longitude)
        or not -180 <= longitude <= 180
    ):
        raise ValueError("Longitude inválida.")

    if not isinstance(limite, int) or limite < 1:
        raise ValueError("O limite deve ser inteiro e positivo.")

    # Verificar se existe o CSV
    if not CAMINHO_CSV.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {CAMINHO_CSV}"
        )

    resultados = []

    # Abrir a base de paradas
    with CAMINHO_CSV.open(
        encoding="utf-8-sig",
        newline=""
    ) as arquivo:

        leitor = csv.DictReader(arquivo)

        for parada in leitor:

            # Coordenadas da parada
            lat_parada = float(parada["latitude"])
            lon_parada = float(parada["longitude"])

            # Calcular a distância até o usuário
            distancia = calcular_distancia(
                latitude,
                longitude,
                lat_parada,
                lon_parada
            )

            # Registrar o resultado
            resultados.append({
                "id_geonatal": parada["id_geonatal"],
                "nome": parada["nome"],
                "latitude": lat_parada,
                "longitude": lon_parada,
                "distancia_metros": round(distancia, 2),
                "fonte": parada["fonte"]
            })

    # Organizar da menor para a maior distância
    resultados.sort(
        key=lambda parada: parada["distancia_metros"]
    )

    # Retornar apenas a quantidade solicitada
    return resultados[:limite]


def main():
    """Permite testar a ferramenta pelo terminal."""

    parser = argparse.ArgumentParser(
        description="Buscar paradas próximas em Natal"
    )

    parser.add_argument(
        "--lat",
        type=float,
        required=True
    )

    parser.add_argument(
        "--lon",
        type=float,
        required=True
    )

    parser.add_argument(
        "--limite",
        type=int,
        default=5
    )

    args = parser.parse_args()

    paradas = buscar_paradas_proximas(
        latitude=args.lat,
        longitude=args.lon,
        limite=args.limite
    )

    print(json.dumps(
        paradas,
        ensure_ascii=False,
        indent=2
    ))


if __name__ == "__main__":
    main()
