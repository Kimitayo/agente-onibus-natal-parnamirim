
"""
Primeiro agente de IA do projeto de transporte.

Utiliza:
- Gemini como modelo de linguagem.
- LangChain para criar o agente.
- MCPAdapter para disponibilizar as ferramentas.
- Servidor MCP próprio e servidor comunitário.
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain.mcp import MCPAdapter
from langchain_google_genai import ChatGoogleGenerativeAI


# Localiza a raiz do projeto.
RAIZ_PROJETO = Path(__file__).resolve().parents[1]

# Carrega as variáveis do arquivo .env.
load_dotenv(RAIZ_PROJETO / ".env")

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("GOOGLE_API_KEY não encontrada no .env.")


# Inicializa o Gemini.
model = ChatGoogleGenerativeAI(
    model="gemini-3.6-flash",
    api_key=api_key,
    # temperature=0.0, # nao precisa pra versão do gemini que estou usando
)


# Configura os servidores MCP.
servers = {
    "transporte": {
        "command": sys.executable,
        "args": ["-m", "server_mcp.servidor"],
    },

    "time": {
        "command": sys.executable,
        "args": [
            "-m",
            "mcp_server_time",
            "--local-timezone=America/Fortaleza",
        ],
    },
}


async def main():

    adapter = MCPAdapter({
        "mcpServers": servers
    })

    async with adapter:

        # Recupera as ferramentas dos dois servidores.
        tools = await adapter.list_tools()

        print("TOTAL DE FERRAMENTAS DISPONÍVEIS:", len(tools))

        # Cria o agente utilizando Gemini e as ferramentas MCP.
        agent = create_agent(
            model,
            tools=tools,
            system_prompt="""
            Você é um assistente especializado em transporte
            público de Natal e Parnamirim.

            Responda sempre em português.

            Para consultar informações sobre linhas, horários,
            itinerários ou paradas, utilize as ferramentas MCP.

            Nunca invente informações sobre o transporte.

            Preserve a fonte e a vigência dos dados consultados.

            Diferencie horários programados de previsões em tempo real.
            """
        )

        # Pergunta que exige consulta à ferramenta MCP.
        pergunta = (
            "Consulte os horários de partida programados da linha 309. "
            "Informe os horários, a frequência entre partidas, "
            "o período de operação e a vigência da programação."
        )

        print("\nPERGUNTA:", pergunta)

        # Executa o agente.
        resultado = await agent.ainvoke({
            "messages": [
                HumanMessage(content=pergunta)
            ]
        })

        # Mostra as ferramentas chamadas pelo agente.
        print("\nFERRAMENTAS ACIONADAS:")

        for mensagem in resultado["messages"]:
            for chamada in getattr(mensagem, "tool_calls", []):
                print("-", chamada["name"])
                print("  Argumentos:", chamada["args"])

        # Exibe a resposta final.
        resposta = resultado["messages"][-1].content

        print("\nRESPOSTA FINAL:")

        if isinstance(resposta, list):
            for bloco in resposta:
                if isinstance(bloco, dict) and bloco.get("type") == "text":
                    print(bloco["text"])
        else:
            print(resposta)


if __name__ == "__main__":
    asyncio.run(main())
