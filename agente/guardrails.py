"""Guardrails determinísticos de entrada e saída do agente.

Inspirado nas práticas do notebook 14 - Guardrails and Security:
triagem de prompt injection e detecção/redação de dados sensíveis.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable


PADROES_INJECAO = [
    re.compile(r"\b(ignore|desconsidere|esqueca)\b.{0,70}\b(instrucoes|regras|prompt|sistema)\b", re.I),
    re.compile(r"\b(revele|mostre|exiba|imprima|copie|retorne)\b.{0,80}\b(prompt|chave|segredo|variaveis de ambiente|\.env|api key)\b", re.I),
    re.compile(r"\b(google_api_key|gemini_api_key|openai_api_key|system prompt|prompt de sistema)\b", re.I),
    re.compile(r"\b(cat|type|get-content|leia|abra|acesse)\b.{0,50}\.env\b", re.I),
    re.compile(r"\b(desative|burle|ignore)\b.{0,50}\b(guardrails|guardrail|seguranca|politica)\b", re.I),
]

TERMOS_DOMINIO = {
    "onibus", "linha", "linhas", "horario", "horarios", "parada", "paradas",
    "ponto de onibus", "itinerario", "itinerarios", "trajeto", "terminal", "sttu", "oso",
    "natal", "parnamirim", "transporte", "passagem", "embarque", "desembarque",
    "mobilidade", "geonatal", "bus2", "rocas", "alecrim", "ponta negra", "igapo",
    "redinha", "frequencia", "intervalo entre partidas", "saida do terminal",
    "partida programada", "tempo de viagem", "como chegar",
}

PADROES_CUMPRIMENTO = re.compile(
    r"^(oi|ola|bom dia|boa tarde|boa noite|tudo bem\??|obrigado|obrigada|valeu|ate mais)[!. ]*$",
    re.I,
)

# Padrões de dados sensíveis adaptados do notebook 14.
CPF_PATTERN = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
PHONE_PATTERN = re.compile(r"(?:\+55\s?)?\(?\d{2}\)?\s?9?\d{4}[-. ]?\d{4}\b")
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
GOOGLE_KEY_PATTERN = re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b")
OPENAI_KEY_PATTERN = re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")
GENERIC_AQ_KEY_PATTERN = re.compile(r"\bAQ\.[A-Za-z0-9_-]{12,}\b")


def normalizar_texto(texto: str) -> str:
    """Remove acentos e normaliza espaços para comparação."""
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(char for char in texto if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", texto).strip().lower()


def texto_da_mensagem(conteudo: object) -> str:
    """Converte conteúdo textual simples ou multimodal em texto legível."""
    if isinstance(conteudo, str):
        return conteudo
    if isinstance(conteudo, list):
        partes = []
        for bloco in conteudo:
            if isinstance(bloco, dict) and bloco.get("type") == "text":
                partes.append(str(bloco.get("text", "")))
            elif isinstance(bloco, str):
                partes.append(bloco)
        return "\n".join(partes)
    return str(conteudo or "")


def _tem_termo_de_dominio(texto: str) -> bool:
    normalizado = normalizar_texto(texto)
    for termo in TERMOS_DOMINIO:
        if " " in termo:
            if termo in normalizado:
                return True
        elif re.search(rf"(?<!\w){re.escape(termo)}(?!\w)", normalizado):
            return True
    return False


def avaliar_entrada(pergunta: str, historico: Iterable[str] | None = None) -> tuple[bool, str | None]:
    """Retorna (permitida, motivo_de_bloqueio).

    Riscos tratados:
    1. prompt injection e tentativa de extrair instruções/credenciais;
    2. solicitações fora do domínio de transporte público de Natal/Parnamirim.
    """
    pergunta = (pergunta or "").strip()
    normalizado = normalizar_texto(pergunta)

    if not pergunta:
        return False, "Envie uma pergunta sobre linhas, horários, itinerários ou paradas."

    if len(pergunta) > 2000:
        return False, "A pergunta é muito extensa. Envie uma consulta de até 2.000 caracteres."

    for padrao in PADROES_INJECAO:
        if padrao.search(normalizado):
            return False, (
                "Não posso revelar instruções internas, credenciais ou variáveis de ambiente. "
                "Posso ajudar com informações de transporte público."
            )

    if PADROES_CUMPRIMENTO.fullmatch(normalizado):
        return True, None

    contexto = " ".join(historico or [])
    if _tem_termo_de_dominio(pergunta) or _tem_termo_de_dominio(contexto):
        return True, None

    return False, (
        "Sou um assistente de transporte público. Posso ajudar com linhas, horários, "
        "itinerários e paradas de Natal e Parnamirim."
    )


def validar_saida(resposta: str) -> str:
    """Impede a exibição de PII e credenciais na resposta final."""
    resposta = resposta or ""
    padroes = (
        CPF_PATTERN,
        PHONE_PATTERN,
        EMAIL_PATTERN,
        GOOGLE_KEY_PATTERN,
        OPENAI_KEY_PATTERN,
        GENERIC_AQ_KEY_PATTERN,
    )
    if any(padrao.search(resposta) for padrao in padroes):
        return (
            "Não posso exibir dados pessoais ou credenciais. "
            "Posso ajudar com informações de transporte público."
        )
    return resposta
