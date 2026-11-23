"""Baixa a base de paradas do GeoNatal e converte GeoJSON em CSV.
"""

import argparse
import csv
import json
from pathlib import Path
from urllib.request import Request, urlopen

URL = (
    "https://geomapas.natal.rn.gov.br/uploads/"
    "parada_de_onibus_12_02_2025_fb07b4272c993ec3998b83e7dcf71834.geojson"
)
COLUNAS = ["id_geonatal", "nome", "latitude", "longitude", "fonte"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arquivo", type=Path, help="GeoJSON local (opcional)")
    parser.add_argument("--saida", type=Path, default=Path("../dados/paradas/geonatal_paradas_2025.csv"))
    args = parser.parse_args()

    if args.arquivo:
        raw = args.arquivo.read_bytes()
    else:
        print("Baixando paradas do GeoNatal...")
        req = Request(URL, headers={"User-Agent": "Mozilla/5.0 (Projeto Academico Transporte Natal)"})
        with urlopen(req, timeout=45) as response:
            raw = response.read()

    data = json.loads(raw.decode("utf-8-sig"))
    if data.get("type") != "FeatureCollection":
        raise ValueError("Arquivo não é uma coleção GeoJSON de feições")

    linhas = []
    for feature in data.get("features", []):
        properties = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        if geometry.get("type") != "Point" or len(coordinates) < 2:
            continue
        longitude, latitude = coordinates[:2]  # GeoJSON usa longitude primeiro!
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            continue
        nome = " ".join(str(properties.get("name") or "").split())
        linhas.append({
            "id_geonatal": properties.get("id"),
            "nome": nome,
            "latitude": latitude,
            "longitude": longitude,
            "fonte": "GeoNatal - Prefeitura do Natal - arquivo 12/02/2025",
        })

    if not linhas:
        raise ValueError("Nenhuma parada georreferenciada foi encontrada")

    args.saida.parent.mkdir(parents=True, exist_ok=True)
    with args.saida.open("w", encoding="utf-8-sig", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=COLUNAS)
        writer.writeheader()
        writer.writerows(linhas)

    print(f"Paradas exportadas: {len(linhas)}")
    print(f"CSV gerado em: {args.saida.resolve()}")
    print("Importante: esta base não informa que linhas atendem cada parada, nem horários.")


if __name__ == "__main__":
    main()
