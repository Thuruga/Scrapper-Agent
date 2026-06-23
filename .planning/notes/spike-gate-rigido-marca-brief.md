---
title: Spike brief - Gate rígido de marca com medição de impacto em cobertura
date: 2026-06-13
context: Brief pronto para rodar /gsd-spike. Deriva do diagnóstico de falsos positivos. Ver .planning/notes/diagnostico-falsos-positivos-busca-sku.md
---

# Spike brief: Gate rígido de marca

## Hipótese
Transformar a penalidade suave de marca (`score * 0.50` em
[`_apply_brand_penalty`](../../services/nlp_service.py)) em um **gate rígido configurável**:
quando a query especifica uma marca conhecida e o título do marketplace não a contém, o
candidato é **descartado** em vez de penalizado.

Espera-se eliminar o falso positivo "marca errada" (Hering numa busca de Aramis).

## Risco a medir
Cobertura. O gate rígido pode derrubar anúncios legítimos do produto Aramis cujo título
**omite** a marca. O spike de EAN já mostrou que cobertura em moda é frágil — então a decisão
de adotar depende do tamanho dessa perda.

## O que medir (em buscas reais recentes)
1. Coletar um conjunto de SKUs Aramis já buscados (usar `services/search_history_service.py`
   / histórico se disponível).
2. Para cada um, rodar o pipeline em dois modos: penalidade `0.50` atual vs. gate rígido.
3. Comparar:
   - **Precisão:** quantos resultados de marca errada o gate elimina.
   - **Cobertura:** quantos resultados legítimos (mesmo produto Aramis) o gate derruba por
     omissão da marca no título.
   - Casos de borda: anúncio legítimo sem "aramis" no título mas com match visual CLIP alto —
     o gate deveria ter uma válvula de escape visual?

## Critério de decisão
Adotar o gate rígido se a perda de cobertura de itens legítimos for baixa (a definir o
limiar) OU se uma válvula de escape (resgate por alto score visual) recuperar os legítimos
sem readmitir o ruído de marca.

## Como rodar
`/gsd-spike Gate rígido de marca na busca por SKU — medir impacto em cobertura vs. precisão`
(este brief serve de ponto de partida).
