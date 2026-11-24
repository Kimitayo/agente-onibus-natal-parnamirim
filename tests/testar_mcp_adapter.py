
"""
Integra os servidores MCP próprio e comunitário
utilizando o MCPAdapter do LangChain.

Servidor próprio:
- Paradas
- Linhas
- Horários
- Itinerários

Servidor comunitário:
- Horário atual
- Conversão de horário
- Tempo decorrido
"""

import asyncio
import sys

from langchain.mcp import MCPAdapter


# Configuração dos dois servidores MCP.
servers = {
    "transporte": {
        "command": sys.executable,
        "args": [
            "-m",
            "server_mcp.servidor",
        ],
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

    # Reúne os servidores em um único adaptador.
    adapter = MCPAdapter({
        "mcpServers": servers
    })

    async with adapter:

        # Descobre as ferramentas dos dois servidores.
        ferramentas = await adapter.list_tools()

        print("\nFERRAMENTAS INTEGRADAS:")

        for ferramenta in ferramentas:
            print("-", ferramenta.name)

        print("\nTOTAL DE FERRAMENTAS:", len(ferramentas))


if __name__ == "__main__":
    asyncio.run(main())
