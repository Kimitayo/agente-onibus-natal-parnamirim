# Como aplicar este pacote ao repositório existente

1. Faça commit ou backup do estado atual do repositório.
2. Extraia o conteúdo deste ZIP diretamente na raiz `agente-onibus-natal-parnamirim/`.
3. Quando o Windows perguntar, permita mesclar pastas e substituir os arquivos indicados.
4. Não substitua nem apague `dados/`, `tools/` ou `scripts/`: eles já existem e são reaproveitados.

## Arquivos substituídos

- `requirements.txt`
- `.gitignore`
- `README.md` (o repositório não tinha README de relatório na raiz)
- `server_mcp/servidor.py`
- `server_mcp/__init__.py`
- `tests/testar_agente_mcp.py` (deixa de usar `create_agent` e chama o grafo explícito)
- `tests/testar_mcp_adapter.py` (define o diretório de execução dos dois servidores)
- `tests/testar_servidor_mcp.py` (valida tools, resources e prompt)

## Arquivos novos

- `agente/__init__.py`
- `agente/grafo.py`
- `agente/guardrails.py`
- `agente/skills.py`
- `rag/__init__.py`
- `rag/indice.py`
- `rag/indexar_osos.py`
- `rag/grafo_rag.py`
- `skills/consultar_linha_completa/SKILL.md`
- `skills/localizar_parada_proxima/SKILL.md`
- `interface/__init__.py`
- `interface/app.py`
- `tests/test_guardrails_unitarios.py`
- `tests/testes_unitarios.py`
- `tests/testar_guardrails.py`
- `tests/avaliar_agente.py`
- `.env.example`
- `docs/roteiro_video.md`

O arquivo `.env` não está incluído e não deve ser enviado ao GitHub.
