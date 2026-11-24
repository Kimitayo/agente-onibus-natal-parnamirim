"""Converte uma resposta criptografada de stop times do BUS2 em JSON e CSV.

Uso:
    pip install cryptography
    python extrair_bus2.py --entrada resposta.txt --data 2026-11-22 --linha L-54 --saida ./dados/bus2

O script não coleta dados da internet: processa apenas arquivos já obtidos.
A data informada representa a data de referência da requisição, não
uma confirmação de vigência de toda a programação.
"""
from __future__ import annotations

import argparse
import base64
import csv
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7


def senhas_da_data(d: date) -> tuple[str, str]:
    """Gera as duas senhas de data observadas no JavaScript do BUS2."""
    ano = d.year
    mes_utc = d.month - 1  # JavaScript getUTCMonth(): 0 = janeiro
    dia_semana_utc = (d.weekday() + 1) % 7  # JavaScript getUTCDay(): 0 = domingo
    opcao_a = (
        f"4ALHGa@Nk<,{ano}X9WM0a^Y^zTg%Wc{dia_semana_utc}"
        f"}}QZ_*cm@9fq&t)6jis[31{mes_utc}%HKvpfZJfglbwD}}F{{4"
    )
    opcao_b = (
        f"BZ=>I1[gK9jk{ano}IaiF.@0#kaQyYa+{dia_semana_utc}"
        f"WS^LV=f6Z]sb=[IIiEU{mes_utc}E>*BM>:[%[So-q@@("
    )
    return opcao_a, opcao_b


def descriptografar(resposta_base64: str, data_referencia: date):
    """Descriptografa OpenSSL/CryptoJS AES-CBC usando senhas de data."""
    dados = base64.b64decode(resposta_base64.strip(), validate=True)
    if not dados.startswith(b"Salted__") or len(dados) < 32:
        raise ValueError("Arquivo não tem o cabeçalho OpenSSL Salted__ esperado.")

    sal = dados[8:16]
    criptografado = dados[16:]
    if len(criptografado) % 16:
        raise ValueError("O corpo criptografado não é múltiplo de 16 bytes.")

    for delta in (0, -1, 1):
        data_tentativa = data_referencia + timedelta(days=delta)
        for senha in senhas_da_data(data_tentativa):
            material = b""
            anterior = b""
            while len(material) < 48:
                anterior = hashlib.md5(anterior + senha.encode("utf-8") + sal).digest()
                material += anterior
            chave, iv = material[:32], material[32:48]
            descriptografador = Cipher(
                algorithms.AES(chave), modes.CBC(iv)
            ).decryptor()
            bruto = descriptografador.update(criptografado) + descriptografador.finalize()
            try:
                unpadder = PKCS7(128).unpadder()
                texto = (unpadder.update(bruto) + unpadder.finalize()).decode("utf-8")
                obj = json.loads(texto)
            except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            return obj, data_tentativa
    raise ValueError("Não foi possível descriptografar com as datas de referência testadas.")


def horario(segundos: int | None) -> str:
    """Formata segundos desde o início do dia; preserva horas acima de 23."""
    if segundos is None:
        return ""
    segundos = int(segundos)
    return f"{segundos // 3600:02d}:{segundos % 3600 // 60:02d}:{segundos % 60:02d}"


def normalizar_paradas(obj, data_referencia: date, linha: str) -> list[dict]:
    """Normaliza somente respostas que listam paradas e horários."""
    if not isinstance(obj, list):
        raise ValueError("Resposta não é uma lista de paradas.")
    linhas = []
    for item in obj:
        if not isinstance(item, dict) or not isinstance(item.get("stop"), dict):
            raise ValueError("Resposta não corresponde ao formato de stop times esperado.")
        parada = item["stop"]
        linhas.append({
            "fonte": "BUS2",
            "data_referencia": data_referencia.isoformat(),
            "linha": linha,
            "sentido": item.get("headsign", ""),
            "ordem": parada.get("index", ""),
            "id_parada": parada.get("id", ""),
            "nome_parada": parada.get("name", ""),
            "latitude": parada.get("lat", ""),
            "longitude": parada.get("lon", ""),
            "chegada_segundos": item.get("scheduledArrival", ""),
            "chegada_programada": horario(item.get("scheduledArrival")),
            "saida_segundos": item.get("scheduledDeparture", ""),
            "saida_programada": horario(item.get("scheduledDeparture")),
            "estado_tempo_real": item.get("realtimeState", ""),
            "tem_tempo_real": item.get("realtime", ""),
            "parada_cancelada": item.get("cancelledStop", ""),
        })
    return linhas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", required=True, type=Path, help="Arquivo TXT com Base64 criptografado")
    parser.add_argument("--data", required=True, type=date.fromisoformat, help="Data YYYY-MM-DD")
    parser.add_argument("--linha", required=True, help="Identificação da linha, por exemplo L-54")
    parser.add_argument("--saida", required=True, type=Path, help="Diretório dos arquivos gerados")
    args = parser.parse_args()

    obj, data_chave = descriptografar(args.entrada.read_text(encoding="utf-8"), args.data)
    linhas = normalizar_paradas(obj, args.data, args.linha)
    args.saida.mkdir(parents=True, exist_ok=True)
    base = f"bus2_{args.linha.lower().replace('-', '')}_{args.data.isoformat()}"
    caminho_json = args.saida / f"{base}.json"
    caminho_csv = args.saida / f"{base}.csv"
    caminho_json.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    with caminho_csv.open("w", encoding="utf-8-sig", newline="") as arquivo:
        writer = csv.DictWriter(arquivo, fieldnames=list(linhas[0]))
        writer.writeheader()
        writer.writerows(linhas)
    print(f"Data usada para a chave: {data_chave.isoformat()}")
    print(f"Registros de paradas: {len(linhas)}")
    print(f"IDs de paradas distintos: {len(set(p['id_parada'] for p in linhas))}")
    print(f"CSV: {caminho_csv}")
    print(f"JSON: {caminho_json}")


if __name__ == "__main__":
    main()