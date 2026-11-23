
"""
Testa as quatro ferramentas do servidor MCP próprio.

O cliente inicia o servidor como um processo separado
e se comunica com ele pelo transporte stdio.
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
        args=["-m", "server_mcp.servidor"],
        cwd=str(RAIZ_PROJETO),
    )

    testes = [
        (
            "buscar_paradas",
            {
                "latitude": -5.7999937,
                "longitude": -35.1825303,
                "limite": 3,
            },
        ),
        (
            "buscar_linhas",
            {"codigo": "309"},
        ),
        (
            "buscar_horarios",
            {"codigo": "309"},
        ),
        (
            "buscar_itinerarios",
            {
                "codigo": "309",
                "sentido": "IDA",
            },
        ),
    ]

    async with Client(transporte) as cliente:
        ferramentas = await cliente.list_tools()
        nomes = {ferramenta.name for ferramenta in ferramentas}

        aprovados = 0

        for nome, parametros in testes:
            print(f"\nTESTANDO: {nome}")

            if nome not in nomes:
                print("FALHOU: ferramenta não encontrada")
                continue

            try:
                resultado = await cliente.call_tool(
                    nome,
                    parametros,
                )

                if resultado.is_error:
                    print("FALHOU:", resultado)
                    continue

                if not resultado.data:
                    print("FALHOU: resultado vazio")
                    continue

                aprovados += 1
                print("APROVADO")
                print("Resultado:", str(resultado.data)[:300])

            except Exception as erro:
                print("FALHOU:", erro)

        print("\n" + "=" * 40)
        print(f"RESULTADO FINAL: {aprovados}/4 testes aprovados")
        print("=" * 40)


if __name__ == "__main__":
    asyncio.run(main())
