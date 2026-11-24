---
name: localizar_parada_proxima
description: Avalia quais paradas cadastradas no GeoNatal ficam próximas de uma localização informada e explica os limites da distância e dos dados disponíveis.
---

# Objetivo
Ajudar a pessoa a identificar paradas cadastradas próximas de um ponto, sem afirmar que a distância em linha reta equivale a um trajeto a pé.

# Procedimento
1. Verifique se a pessoa forneceu latitude e longitude. Se não forneceu, peça essas coordenadas; não presuma a localização atual.
2. Use `transporte_buscar_paradas` com as coordenadas e limite de até cinco resultados.
3. Ordene os resultados pela distância retornada e apresente nome, distância em metros e fonte.
4. Explique que a distância é geográfica, em linha reta, e não representa rota de caminhada, acessibilidade da calçada ou tempo de deslocamento.
5. Se a pessoa perguntar quais linhas passam pela parada, não deduza a relação: a base GeoNatal usada neste projeto não associa cada parada às linhas. Se ela informar uma linha, consulte `transporte_buscar_itinerarios`, mas esclareça que o itinerário contém logradouros e não comprova atendimento de uma parada específica.
6. Informe que o cadastro GeoNatal disponível é datado de 12/02/2025 e pode não refletir alterações posteriores.

# Formato da resposta
Seja direto: liste as paradas mais próximas e suas distâncias. Finalize com uma frase curta explicando a limitação da distância e da associação parada-linha.
