"""Catálogo e carregamento sob demanda de Agent Skills."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
PASTA_SKILLS = RAIZ_PROJETO / "skills"


def carregar_catalogo() -> dict[str, dict[str, str]]:
    """Lê metadados YAML e conteúdo das skills disponíveis."""
    catalogo: dict[str, dict[str, str]] = {}

    for caminho in sorted(PASTA_SKILLS.glob("*/SKILL.md")):
        conteudo = caminho.read_text(encoding="utf-8")
        correspondencia = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", conteudo, re.S)
        if not correspondencia:
            raise ValueError(f"Front matter YAML ausente em {caminho}")

        metadados = yaml.safe_load(correspondencia.group(1)) or {}
        nome = str(metadados.get("name", caminho.parent.name)).strip()
        descricao = str(metadados.get("description", "")).strip()

        if not nome or not descricao:
            raise ValueError(f"A skill {caminho} precisa de name e description.")

        catalogo[nome] = {
            "description": descricao,
            "instructions": correspondencia.group(2).strip(),
            "path": str(caminho.relative_to(RAIZ_PROJETO)),
        }

    if len(catalogo) < 2:
        raise RuntimeError("O projeto precisa ter pelo menos duas skills em skills/*/SKILL.md.")

    return catalogo


def formatar_catalogo(catalogo: dict[str, dict[str, str]]) -> str:
    """Formata o catálogo para inclusão na mensagem de sistema."""
    return "\n".join(
        f"- {nome}: {dados['description']}"
        for nome, dados in catalogo.items()
    )


def criar_ferramenta_carregar_skill(catalogo: dict[str, dict[str, str]] | None = None):
    """Cria a ferramenta que carrega somente a skill solicitada."""
    from langchain.tools import tool

    catalogo = catalogo or carregar_catalogo()

    @tool
    def carregar_skill(nome: str) -> str:
        """Carrega as instruções completas de uma skill pelo nome do catálogo."""
        if nome not in catalogo:
            nomes = ", ".join(sorted(catalogo))
            return f"Skill '{nome}' não encontrada. Skills disponíveis: {nomes}."
        return (
            f"INSTRUÇÕES DA SKILL: {nome}\n"
            f"Arquivo: {catalogo[nome]['path']}\n\n"
            f"{catalogo[nome]['instructions']}"
        )

    return carregar_skill
