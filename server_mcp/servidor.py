"""
OBJETIVO: Disponibiliza ferramentas para consultar paradas, linhas,
horários e itinerários do transporte público.

Reutiliza as funções Python da pasta tools/.
"""

from fastmcp import FastMCP # Que possibilita criar os mcp

# As tools
from tools.paradas import buscar_paradas_proximas
from tools.linhas import consultar_linhas
from tools.horarios import consultar_horarios
from tools.itinerarios import consultar_itinerarios

# nome do server
mcp = FastMCP("transporte-natal-parnamirim")


@mcp.tool()
def buscar_paradas(
    latitude: float,
    longitude: float,
    limite: int = 5
) -> list[dict]:
    """
    Busca as paradas do GeoNatal mais próximas de uma localização.

    Retorna nomes, coordenadas e distâncias em metros.
    Não confirma quais linhas passam pelas paradas.
    """
    return buscar_paradas_proximas(
        latitude=latitude,
        longitude=longitude,
        limite=limite
    )


@mcp.tool()
def buscar_linhas(codigo: str) -> list[dict]:
    """
    Consulta uma linha de ônibus nos metadados das OSOs da STTU.

    Retorna nome, empresa, período de operação,
    vigência e documento de origem.
    """
    return consultar_linhas(codigo)


@mcp.tool()
def buscar_horarios(codigo: str) -> dict:
    """
    Consulta horários programados de saída de uma linha.

    Retorna as partidas agrupadas por OSO e período.
    Não representa previsão em tempo real.
    """
    return consultar_horarios(codigo)


@mcp.tool()
def buscar_itinerarios(
    codigo: str,
    sentido: str | None = None
) -> dict:
    """
    Consulta os logradouros do itinerário de uma linha.

    Permite filtrar por IDA ou VOLTA.
    Retorna ruas na ordem descrita na OSO.
    """
    return consultar_itinerarios(
        codigo=codigo,
        sentido=sentido
    )


if __name__ == "__main__":
    mcp.run()
