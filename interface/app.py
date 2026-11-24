"""Interface de chat do assistente de transporte público."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

import streamlit as st
from dotenv import load_dotenv

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

load_dotenv(RAIZ_PROJETO / ".env")

from agente.grafo import executar_consulta  # noqa: E402

st.set_page_config(
    page_title="Agente de Transporte",
    page_icon="🚌",
    layout="centered",
)


def iniciar_conversa() -> None:
    st.session_state.thread_id = str(uuid4())
    st.session_state.historico = []


if "thread_id" not in st.session_state:
    iniciar_conversa()
if "historico" not in st.session_state:
    st.session_state.historico = []

st.title("🚌 Assistente de Transporte")
st.caption("Consultas sobre linhas, horários, itinerários e paradas de Natal e Parnamirim.")

with st.sidebar:
    st.subheader("Conversa")
    if st.button("＋ Nova conversa", use_container_width=True):
        iniciar_conversa()
        st.rerun()

    st.divider()
    st.subheader("Fontes disponíveis")
    st.markdown(
        "- **STTU / OSO:** linhas, horários programados e itinerários.\n"
        "- **GeoNatal:** cadastro de paradas.\n"
        "- **MCP comunitário:** horário local.\n"
        "- **RAG:** consulta textual aos PDFs originais das OSOs."
    )
    st.caption(
        "Esta versão não consulta o BUS2 e não fornece localização de veículos ou previsão em tempo real."
    )

for item in st.session_state.historico:
    with st.chat_message(item["role"]):
        st.markdown(item["content"])
        if item["role"] == "assistant":
            with st.expander("Ferramentas e skills desta resposta"):
                chamadas = item.get("ferramentas", [])
                skills = item.get("skills", [])
                st.markdown("**Ferramentas chamadas**")
                if chamadas:
                    for chamada in chamadas:
                        st.write(f"- `{chamada['nome']}` — {chamada['argumentos']}")
                else:
                    st.write("Nenhuma ferramenta foi acionada.")
                st.markdown("**Skills carregadas**")
                st.write(", ".join(skills) if skills else "Nenhuma skill carregada.")

pergunta = st.chat_input("Pergunte sobre uma linha, horário, itinerário ou parada...")

if pergunta:
    st.session_state.historico.append({"role": "user", "content": pergunta})
    with st.chat_message("user"):
        st.markdown(pergunta)

    with st.chat_message("assistant"):
        with st.spinner("Consultando as fontes disponíveis..."):
            try:
                resultado = asyncio.run(
                    executar_consulta(pergunta, st.session_state.thread_id)
                )
                resposta = resultado["resposta"]
                chamadas = resultado["ferramentas"]
                skills = resultado["skills"]
                st.markdown(resposta)
                with st.expander("Ferramentas e skills desta resposta"):
                    st.markdown("**Ferramentas chamadas**")
                    if chamadas:
                        for chamada in chamadas:
                            st.write(f"- `{chamada['nome']}` — {chamada['argumentos']}")
                    else:
                        st.write("Nenhuma ferramenta foi acionada.")
                    st.markdown("**Skills carregadas**")
                    st.write(", ".join(skills) if skills else "Nenhuma skill carregada.")

                st.session_state.historico.append({
                    "role": "assistant",
                    "content": resposta,
                    "ferramentas": chamadas,
                    "skills": skills,
                })
            except Exception as erro:
                mensagem = (
                    "Não consegui concluir a consulta. Verifique se o índice RAG foi criado, "
                    "se os servidores MCP estão disponíveis e se a chave Gemini está configurada."
                )
                st.error(mensagem)
                st.caption(f"Detalhe técnico: {type(erro).__name__}: {erro}")
                st.session_state.historico.append({
                    "role": "assistant",
                    "content": mensagem,
                    "ferramentas": [],
                    "skills": [],
                })
