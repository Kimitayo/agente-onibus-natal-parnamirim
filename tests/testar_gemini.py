
"""
Testa a conexão com o Gemini utilizando LangChain.

Carrega a chave da API armazenada no .env
e realiza uma primeira chamada ao modelo.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI


# Localiza e carrega o arquivo .env na raiz do projeto.
RAIZ_PROJETO = Path(__file__).resolve().parents[1]

load_dotenv(RAIZ_PROJETO / ".env")


# Recupera a chave sem exibi-la no terminal.
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError(
        "GOOGLE_API_KEY não encontrada. Verifique o arquivo .env."
    )


# Inicializa o modelo Gemini.
model = ChatGoogleGenerativeAI(
    model="gemini-3.6-flash",
    api_key=api_key,
)


# Envia uma pergunta ao modelo.
resposta = model.invoke(
    "Explique em uma frase o que é um agente de IA."
)


# Exibe o resultado.
print("\nCONEXÃO COM GEMINI: OK")
print("\nRESPOSTA DO MODELO:")

if isinstance(resposta.content, list):
    for bloco in resposta.content:
        if isinstance(bloco, dict) and bloco.get("type") == "text":
            print(bloco["text"])
else:
    print(resposta.content)
