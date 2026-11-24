"""Teste rápido do grafo LangGraph integrado aos dois servidores MCP."""

import asyncio
import uuid

from agente.grafo import executar_consulta


async def main() -> None:
    pergunta = (
        "Consulte os horários programados da linha 309. "
        "Informe o período de operação, a vigência e as partidas, de forma direta."
    )
    resultado = await executar_consulta(pergunta, thread_id=f"teste-{uuid.uuid4()}")

    print("PERGUNTA:", pergunta)
    print("\nFERRAMENTAS ACIONADAS:")
    for chamada in resultado["ferramentas"]:
        print("-", chamada["nome"], chamada["argumentos"])
    print("\nSKILLS CARREGADAS:", resultado["skills"] or "Nenhuma")
    print("\nRESPOSTA FINAL:\n", resultado["resposta"])


if __name__ == "__main__":
    asyncio.run(main())
