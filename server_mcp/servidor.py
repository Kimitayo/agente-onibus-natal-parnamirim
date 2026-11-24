"""Servidor MCP próprio do assistente de transporte.

Disponibiliza quatro ferramentas, dois recursos (um deles parametrizado)
e um prompt reutilizável, usando as funções já existentes em tools/.
"""

import json

from fastmcp import FastMCP

from tools.paradas import buscar_paradas_proximas
from tools.linhas import consultar_linhas
from tools.horarios import consultar_horarios
from tools.itinerarios import consultar_itinerarios

mcp = FastMCP("transporte-natal-parnamirim")


@mcp.tool()
def buscar_paradas(latitude: float, longitude: float, limite: int = 5) -> list[dict]:
    """Busca as paradas GeoNatal mais próximas de uma coordenada.

    Retorna nome, coordenadas e distância geográfica em metros.
    Não comprova quais linhas atendem cada parada nem calcula rota a pé.
    """
    return buscar_paradas_proximas(
        latitude=latitude,
        longitude=longitude,
        limite=limite,
    )


@mcp.tool()
def buscar_linhas(codigo: str) -> list[dict]:
    """Consulta identificação, empresa, período, vigência e origem das OSOs de uma linha."""
    return consultar_linhas(codigo)


@mcp.tool()
def buscar_horarios(codigo: str) -> dict:
    """Consulta partidas programadas de uma linha nas OSOs; não é previsão em tempo real."""
    return consultar_horarios(codigo)


@mcp.tool()
def buscar_itinerarios(codigo: str, sentido: str | None = None) -> dict:
    """Consulta logradouros do itinerário de uma linha, por IDA, VOLTA ou ambos."""
    return consultar_itinerarios(codigo=codigo, sentido=sentido)


@mcp.resource("transporte://catalogo/linhas")
def recurso_catalogo_linhas() -> str:
    """Lista registros de linhas e OSOs disponíveis na base local."""
    registros = consultar_linhas()
    return json.dumps(
        {
            "fonte": "STTU - OSO",
            "total_registros": len(registros),
            "registros": registros,
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.resource("transporte://linha/{codigo}")
def recurso_ficha_linha(codigo: str) -> str:
    """Reúne metadados, horários e itinerários de uma linha em um recurso."""
    resultado = {
        "linha": consultar_linhas(codigo),
        "horarios": consultar_horarios(codigo),
        "itinerarios": consultar_itinerarios(codigo),
        "observacao": (
            "Horários são partidas programadas das OSOs. Itinerários são logradouros; "
            "não comprovam quais paradas são atendidas nem operação em tempo real."
        ),
    }
    return json.dumps(resultado, ensure_ascii=False, indent=2)


@mcp.prompt()
def orientar_consulta_linha(codigo: str, necessidade: str = "completa") -> str:
    """Monta instruções reutilizáveis para consultar uma linha de ônibus."""
    return (
        f"Consulte a linha {codigo} para a necessidade: {necessidade}. "
        "Use os recursos e ferramentas do servidor para obter identificação, empresa, "
        "período de operação, vigência, horários e itinerários. Separe registros de OSOs "
        "diferentes, cite a fonte e seja direto. Não trate horários programados como "
        "previsões em tempo real e não deduza quais paradas são atendidas."
    )


if __name__ == "__main__":
    # O servidor usa stdio; banner e logs extras podem interferir no protocolo.
    mcp.run(show_banner=False)
