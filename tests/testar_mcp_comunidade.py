
"""
Valida o servidor MCP da comunidade para consulta de horário.

Utiliza o mesmo ambiente Python do projeto e o transporte stdio.
"""

import asyncio
import sys
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


RAIZ_PROJETO = Path(__file__).resolve().parents[1]


async def main():
    transporte = StdioTransport(
        command=sys.executable,
        args=[
            "-m",
            "mcp_server_time",
            "--local-timezone=America/Fortaleza",
        ],
        cwd=str(RAIZ_PROJETO),
    )

    async with Client(transporte) as cliente:
        ferramentas = await cliente.list_tools()

        print("FERRAMENTAS DO SERVIDOR DA COMUNIDADE:")

        nomes = []

        for ferramenta in ferramentas:
            print("-", ferramenta.name)
            nomes.append(ferramenta.name)

        if "get_current_time" not in nomes:
            raise RuntimeError(
                "A ferramenta get_current_time não foi encontrada."
            )

        resultado = await cliente.call_tool(
            "get_current_time",
            {"timezone": "America/Fortaleza"},
        )

        if resultado.is_error:
            raise RuntimeError(f"Falha na consulta: {resultado}")

        print("\nHORÁRIO DE NATAL/PARNAMIRIM:")
        print(resultado.data)

        print("\nTESTE MCP DA COMUNIDADE: APROVADO")


if __name__ == "__main__":
    asyncio.run(main())
