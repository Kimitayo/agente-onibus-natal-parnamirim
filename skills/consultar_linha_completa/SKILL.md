---
name: consultar_linha_completa
description: Executa uma consulta integrada de uma linha quando a pessoa pede uma visão completa, reunindo identificação, programação de horários e itinerários de ida e volta.
---

# Objetivo
Produzir uma visão integrada de uma linha sem misturar documentos, períodos de operação ou vigências diferentes.

# Procedimento
1. Identifique o código da linha na pergunta. Se não houver código, pergunte qual linha deve ser consultada.
2. Use `transporte_buscar_linhas` para obter nome, empresa, número da OSO, período de operação, vigência e arquivo de origem.
3. Use `transporte_buscar_horarios` para obter as partidas programadas. Preserve sequência, horário, tabela e frequência; não transforme esses dados em previsão em tempo real.
4. Use `transporte_buscar_itinerarios` sem filtro de sentido para obter IDA e VOLTA. Preserve a ordem dos logradouros.
5. Quando precisar confirmar uma informação textual do documento original, use `consultar_documentos_oso` e cite o arquivo e a página retornados.
6. Cruze os resultados pelo mesmo número de OSO, arquivo de origem e vigência. Não combine horários de uma OSO com itinerário de outra sem avisar.
7. Se existirem várias OSOs da linha, separe os resultados por período de operação e vigência; não escolha uma como atual sem evidência.
8. Se algum dado estiver ausente, informe que não foi localizado. Não invente paradas atendidas nem a posição atual do ônibus.

# Formato da resposta
Responda diretamente, em até três frases curtas ou três tópicos. Inclua nome/empresa, período/vigência e um resumo dos horários e do percurso. Informe a fonte OSO. Se a pessoa pedir a lista completa, apresente os dados solicitados sem explicações desnecessárias.
