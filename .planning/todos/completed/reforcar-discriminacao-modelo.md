---
title: Reforçar discriminação de modelo (model-words + visual como desempate)
date: 2026-06-13
priority: medium
resolves_phase: 23
status: resolved
resolved: 2026-07-06
context: Resolve o caso de falso positivo "Aramis errado" (marca certa, modelo/linha errada). Ver .planning/notes/diagnostico-falsos-positivos-busca-sku.md
---

**Resolvido pela Phase 23 (Discriminação de Modelo, milestone v1.11, verificado
2026-06-13, status: passed, 8/8 truths).** MODEL-01 (penalidade de model-word mais
dura: HEAVY_WITH_BRAND 0.70→0.40, MED_WITH_BRAND 0.90→0.75, `nlp_service.py`) e
MODEL-02 (`apply_visual_tiebreak` em `cross_marketplace_service.py:84`, aplicado
em produção na linha 273, `VISUAL_TIEBREAK_ENABLED` ligado por padrão) foram
implementados e verificados. O terceiro item (reavaliar `compute_final_match_score`)
foi resolvido indiretamente: a penalidade de model-word agora derruba o texto do
candidato errado abaixo de `MED_TEXT_FLOOR`, o que já derrota o atalho "texto forte
domina" sem precisar reescrever a régua de combinação. Este todo ficou pendente por
engano — nunca foi movido para `completed/` após a Phase 23 fechar.

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
