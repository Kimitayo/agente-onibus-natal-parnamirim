"""Confirma que o MCPAdapter integra os dois servidores e encontra 7 tools."""

import asyncio
import sys
from pathlib import Path

from langchain.mcp import MCPAdapter

RAIZ_PROJETO = Path(__file__).resolve().parents[1]

SERVIDORES = {
    "transporte": {
        "command": sys.executable,
        "args": ["-m", "server_mcp.servidor"],
        "cwd": str(RAIZ_PROJETO),
    },
    "time": {
        "command": sys.executable,
        "args": ["-m", "mcp_server_time", "--local-timezone=America/Fortaleza"],
        "cwd": str(RAIZ_PROJETO),
    },
}


async def main() -> None:
    adapter = MCPAdapter({"mcpServers": SERVIDORES})
    async with adapter:
        ferramentas = await adapter.list_tools()
        nomes = sorted(ferramenta.name for ferramenta in ferramentas)
        print("FERRAMENTAS MCP INTEGRADAS:")
        for nome in nomes:
            print("-", nome)
        print("TOTAL:", len(nomes))

        nomes_proprios = ("buscar_paradas", "buscar_linhas", "buscar_horarios", "buscar_itinerarios")
        nomes_comunidade = ("get_current_time", "convert_time", "get_time_ago")
        transporte = [nome for nome in nomes if any(nome.endswith(sufixo) for sufixo in nomes_proprios)]
        comunidade = [nome for nome in nomes if any(sufixo in nome for sufixo in nomes_comunidade)]
        if len(transporte) != 4 or len(comunidade) != 3 or len(nomes) != 7:
            raise RuntimeError(
                f"Esperadas 4 tools próprias e 3 comunitárias; encontradas {len(transporte)} e {len(comunidade)}."
            )

    print("INTEGRAÇÃO MCP: APROVADA (7/7)")


if __name__ == "__main__":
    asyncio.run(main())
