"""Configuração do índice vetorial Chroma para os PDFs das OSOs."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
PASTA_INDICE = RAIZ_PROJETO / "dados" / "rag" / "chroma_osos"
NOME_COLECAO = "documentos_oso_sttu"

load_dotenv(RAIZ_PROJETO / ".env")


def criar_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Cria embeddings Gemini; usa a mesma chave Google do modelo de chat."""
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Defina GOOGLE_API_KEY no arquivo .env antes de indexar os PDFs.")

    modelo = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
    return GoogleGenerativeAIEmbeddings(
        model=modelo,
        google_api_key=api_key,
    )


@lru_cache(maxsize=1)
def carregar_vector_store() -> Chroma:
    """Abre o índice persistido. A indexação é executada separadamente."""
    if not PASTA_INDICE.exists():
        raise RuntimeError(
            "Índice RAG ainda não existe. Execute primeiro: python -m rag.indexar_osos"
        )

    vector_store = Chroma(
        collection_name=NOME_COLECAO,
        embedding_function=criar_embeddings(),
        persist_directory=str(PASTA_INDICE),
        collection_metadata={"hnsw:space": "cosine"},
    )

    if not vector_store.get().get("ids"):
        raise RuntimeError(
            "O índice RAG está vazio. Execute: python -m rag.indexar_osos"
        )

    return vector_store
