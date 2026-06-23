---
title: Reforçar discriminação de modelo (model-words + visual como desempate)
date: 2026-06-13
priority: medium
resolves_phase: 23
context: Resolve o caso de falso positivo "Aramis errado" (marca certa, modelo/linha errada). Ver .planning/notes/diagnostico-falsos-positivos-busca-sku.md
---

# Reforçar discriminação de modelo

## Problema
Falso positivo do tipo "Aramis errado": retorna uma polo Aramis diferente da buscada
(outra cor/linha/modelo). Hoje:
- `_apply_model_word_penalty` em `services/nlp_service.py` é multiplicativo e brando.
- O CLIP visual só roda nos top-N **já escolhidos pelo texto** em
  `services/cross_marketplace_service.py` — se o texto elegeu o modelo errado, o visual
  não corrige, apenas confirma.

## O que fazer (a investigar/decidir na fase)
- [ ] Tornar as model-words decisivas: avaliar penalidade mais forte ou exigência mínima de
      hits de model-word quando a marca já bate (caso "mesmo fabricante, qual modelo?").
- [ ] Usar CLIP como **desempate de mesmo-produto** entre candidatos da mesma marca, não só
      como filtro pós-texto — considerar reordenar/reescolher top candidatos com base no
      score visual quando o texto está ambíguo.
- [ ] Reavaliar a régua de combinação em `relevance_gates.compute_final_match_score`
      (hoje "texto forte domina") para o cenário onde texto é forte mas ambíguo entre modelos.

## Critério de pronto
Para um SKU Aramis com vários modelos similares no catálogo, o topo do resultado deve ser o
modelo correto (validável visualmente), não um modelo Aramis adjacente.

## Dependência
Idealmente após o spike do gate rígido de marca (elimina o ruído de marca errada primeiro,
isolando o problema de modelo).
