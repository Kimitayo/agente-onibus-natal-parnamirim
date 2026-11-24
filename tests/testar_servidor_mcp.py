"""Teste de integração do servidor MCP próprio: tools, resources e prompt."""

import asyncio
import sys
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

RAIZ_PROJETO = Path(__file__).resolve().parents[1]


async def main() -> None:
    transporte = StdioTransport(
        command=sys.executable,
        args=["-m", "server_mcp.servidor"],
        cwd=str(RAIZ_PROJETO),
    )

    testes_ferramentas = [
        ("buscar_paradas", {"latitude": -5.7999937, "longitude": -35.1825303, "limite": 3}),
        ("buscar_linhas", {"codigo": "309"}),
        ("buscar_horarios", {"codigo": "309"}),
        ("buscar_itinerarios", {"codigo": "309", "sentido": "IDA"}),
    ]

    async with Client(transporte) as cliente:
        ferramentas = await cliente.list_tools()
        nomes_ferramentas = {item.name for item in ferramentas}
        print("FERRAMENTAS:", sorted(nomes_ferramentas))

        aprovados = 0
        for nome, argumentos in testes_ferramentas:
            if nome not in nomes_ferramentas:
                print(f"FALHOU: ferramenta {nome} não encontrada")
                continue
            resultado = await cliente.call_tool(nome, argumentos)
            if resultado.is_error or resultado.data is None:
                print(f"FALHOU: {nome} -> {resultado}")
                continue
            aprovados += 1
            print(f"APROVADO: {nome}")

        recursos = await cliente.list_resources()
        modelos_recursos = await cliente.list_resource_templates()
        prompts = await cliente.list_prompts()

        assert any(str(item.uri) == "transporte://catalogo/linhas" for item in recursos)
        assert any("transporte://linha/{codigo}" in item.uri_template for item in modelos_recursos)
        assert any(item.name == "orientar_consulta_linha" for item in prompts)

        catalogo = await cliente.read_resource("transporte://catalogo/linhas")
        ficha = await cliente.read_resource("transporte://linha/309")
        prompt = await cliente.get_prompt(
            "orientar_consulta_linha",
            {"codigo": "309", "necessidade": "horários e itinerário"},
        )

        assert catalogo and ficha and prompt.messages
        print("RECURSOS:", len(recursos), "| MODELOS:", len(modelos_recursos))
        print("PROMPTS:", [item.name for item in prompts])
        print("RECURSO DA LINHA 309: APROVADO")
        print("PROMPT orientar_consulta_linha: APROVADO")

    print(f"\nFERRAMENTAS APROVADAS: {aprovados}/4")
    if aprovados != 4:
        raise SystemExit("O servidor MCP não passou em todas as ferramentas.")
    print("TESTE DO SERVIDOR MCP: APROVADO")


if __name__ == "__main__":
    asyncio.run(main())
