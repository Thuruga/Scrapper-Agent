---
phase: 23-discrimina-o-de-modelo
plan: "02"
subsystem: relevance-pipeline
tags: [model-discrimination, visual-tiebreak, cross-candidate, tdd]
dependency_graph:
  requires:
    - RelevanceSettings.VISUAL_TIEBREAK_ENABLED (Plan 01)
    - RelevanceSettings.VISUAL_TIEBREAK_TEXT_WINDOW (Plan 01)
    - RelevanceSettings.NLP_MODEL_PENALTY_HEAVY_WITH_BRAND=0.40 (Plan 01)
  provides:
    - apply_visual_tiebreak(candidates, window, enabled, official_title) -> list
    - _detect_candidate_brand(titulo, vocab_brands) -> str | None
    - Wiring: compare_product reordena via apply_visual_tiebreak antes do cap por plataforma
    - tests/test_model_discrimination.py com 5 testes-âncora MODEL-01, MODEL-02, criterion 3, criterion 4, fallback
  affects:
    - services/cross_marketplace_service.py (2 novas funções de módulo + wiring em compare_product)
    - tests/test_model_discrimination.py (novo arquivo, 6 testes)
tech_stack:
  added: []
  patterns:
    - module-level pure function (mirrors passes_brand_gate anti-tautologia HIGH-1)
    - TDD RED/GREEN cycle (test commit antes do feat commit)
    - window-bucket sort_key para desempate cross-candidato
key_files:
  created:
    - tests/test_model_discrimination.py
  modified:
    - services/cross_marketplace_service.py
decisions:
  - "apply_visual_tiebreak recebe window/enabled como argumentos (não lê relevance_settings internamente) — espelha passes_brand_gate, permite testes sem monkey-patch"
  - "_detect_candidate_brand definida como helper privado de módulo em cross_marketplace_service.py (não expande NLPService API pública) — decisão de planner confirmada"
  - "Agrupamento por marca apenas (não por plataforma+marca) — discriminação cross-plataforma do mesmo modelo Aramis é caso válido"
  - "guard max(window, 0.1) no denominador do bucket para proteger contra VISUAL_TIEBREAK_TEXT_WINDOW=0 (T-23-05)"
  - "official_title aceito na assinatura por paridade de API mas não usado internamente — vocab_brands derivado de nlp_service._vocab, fonte única de verdade"
metrics:
  duration: "5m"
  completed_date: "2026-06-13"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 23 Plan 02: Desempate Visual Cross-Candidato (apply_visual_tiebreak) Summary

**One-liner:** Função pura `apply_visual_tiebreak` com helper `_detect_candidate_brand` em `cross_marketplace_service.py` promove o sinal CLIP a desempate explícito entre candidatos da mesma marca dentro de uma janela de ambiguidade de texto, substituindo o `.sort()` in-place da linha 253, com 6 testes-âncora TDD verdes.

## What Was Built

### 1. `_detect_candidate_brand(titulo, vocab_brands) -> str | None` (helper privado de módulo)

Reutiliza `nlp_service._clean_text` para normalizar o título e compara tokens contra o frozenset `nlp_service._vocab.known_brands_for_detection` (fonte única de verdade de `data/nlp_vocabulary.json`). Sem lista literal de marcas.

### 2. `apply_visual_tiebreak(candidates, window, enabled, official_title) -> list` (função pura de módulo)

- Recebe `window` e `enabled` como argumentos lidos pelo chamador — nunca lê `relevance_settings` internamente (anti-tautologia HIGH-1)
- Fallback (enabled=False OU todos image_match_score==0): `sorted(-final, preco)` — idêntico ao comportamento anterior, zero regressão
- Caminho ativo: agrupa por marca via `_detect_candidate_brand`, calcula `brand_top` (top-score por marca), ordena por `_sort_key`:
  - Candidatos in-window da mesma marca (mesma brand, img>0, top-final<=window): bucket-floor + -image_score como desempate
  - Candidatos out-of-window: -final_score exato (sem interferência de bucket — Pitfall 4 verificado)
- Guard `max(window, 0.1)` no denominador do bucket (proteção T-23-05 contra window=0)
- Retorna nova lista via `sorted()` — não muta in-place

### 3. Wiring em `compare_product` (substituição da linha 253)

`produtos_filtrados.sort(...)` substituído por reatribuição `produtos_filtrados = apply_visual_tiebreak(...)` com flags lidas inline de `relevance_settings`. Posição: após comprehension de filtros (cutoff + preço + brand_gate), antes do cap por plataforma.

### 4. `tests/test_model_discrimination.py` (novo arquivo, 6 testes TDD)

| Classe | Método | Âncora |
|--------|--------|--------|
| TestModelPenalty | test_model_ratio_zero_below_cutoff_with_high_image | Criterion 3 / Anchor 3 |
| TestModelPenalty | test_correct_model_unaffected_by_penalty | Criterion 4 / Anchor 4 |
| TestVisualTiebreak | test_correct_model_ranks_above_adjacent | MODEL-01 / Anchor 1 |
| TestVisualTiebreak | test_promotes_higher_image_within_window | MODEL-02 / Anchor 2 |
| TestVisualTiebreak | test_fallback_when_disabled | Fallback / Anchor 5 |
| TestVisualTiebreak | test_out_of_window_candidate_not_demoted | Guard Pitfall 4 |

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Criar 5 testes-âncora (falhando — TDD RED) | aa85f8e | tests/test_model_discrimination.py |
| 1 (GREEN) | Implementar apply_visual_tiebreak + _detect_candidate_brand | bbe3ef6 | services/cross_marketplace_service.py |
| 2 | Conectar apply_visual_tiebreak em compare_product | faebc7e | services/cross_marketplace_service.py |

## Verification Results

```
71 passed in 1.01s
relevance_gates.py UNCHANGED ok
apply_visual_tiebreak ok (desempate por image_score dentro da janela)
criterion3: 55.12 < 60 = True (Gate 1 bloqueado com HEAVY=0.40)
```

Todos os critérios de aceitação atendidos:

- `def apply_visual_tiebreak(` e `def _detect_candidate_brand(` presentes no nível de módulo em `cross_marketplace_service.py` — verificado
- `apply_visual_tiebreak` NÃO contém `relevance_settings.` no corpo — verificado
- `_detect_candidate_brand` usa `nlp_service._clean_text` + `known_brands_for_detection` — verificado
- Usa `sorted(` (não `.sort()`) e contém `max(window, 0.1)` — verificado
- `tests/test_model_discrimination.py` contém `from services.cross_marketplace_service import apply_visual_tiebreak` e NÃO reimplementa sort/bucket — verificado
- `pytest tests/test_model_discrimination.py -q` — 6 testes verdes — verificado
- `compute_final_match_score(88*0.40, 85.0) = 55.12 < 60` e `(90*0.40, 90.0) = 57.60 < 60` — verificado
- `produtos_filtrados = apply_visual_tiebreak(` com `window=relevance_settings.VISUAL_TIEBREAK_TEXT_WINDOW` e `enabled=relevance_settings.VISUAL_TIEBREAK_ENABLED` — verificado
- Antiga `produtos_filtrados.sort(...)` removida — verificado
- Chamada posicionada ANTES do cap por plataforma, DEPOIS da comprehension — verificado
- `git diff --quiet -- services/relevance_gates.py` → exit 0 (pureza LOCKED) — verificado
- Suíte completa: 71 testes verdes — verificado

## Deviations from Plan

**1. [Rule 2 - Missing critical functionality] Adicionado `test_out_of_window_candidate_not_demoted` como 6º teste**

- **Found during:** Task 1 (TDD)
- **Issue:** O plano menciona o guard de Pitfall 4 como "asserção extra ou teste dedicado" dentro dos testes de tiebreak. Para cobertura verificável e isolada, foi adicionado como método de teste separado em `TestVisualTiebreak`.
- **Fix:** Teste `test_out_of_window_candidate_not_demoted` verifica que candidato in-window (final=86, img=92) não desloca candidato out-of-window (final=92, img=80).
- **Files modified:** tests/test_model_discrimination.py
- **Justification:** Dentro do escopo do plano ("pode ser asserção extra ou teste adicional") — não é desvio arquitetural.

## Known Stubs

None — nenhuma renderização de UI ou wiring de dados envolvido. As funções operam sobre dicts com valores float controlados pelo pipeline existente.

## Threat Flags

None — nenhuma nova trust boundary introduzida. `_detect_candidate_brand` e `apply_visual_tiebreak` fazem apenas comparações de membros de conjunto (`in`), aritmética de float e `sorted()`; sem `eval`, SQL, ou regex construída a partir de entrada externa. Consistent with T-23-04, T-23-05, T-23-06, T-23-07 analysis in the plan's threat model.

## Self-Check: PASSED

- [x] `services/cross_marketplace_service.py` modificado com `import math`, `_detect_candidate_brand`, `apply_visual_tiebreak` e wiring
- [x] `tests/test_model_discrimination.py` criado com 6 testes
- [x] Commit aa85f8e existe (RED): `git log --oneline | grep aa85f8e`
- [x] Commit bbe3ef6 existe (GREEN feat): `git log --oneline | grep bbe3ef6`
- [x] Commit faebc7e existe (wiring): `git log --oneline | grep faebc7e`
- [x] `services/relevance_gates.py` intocado — `git diff --quiet` exit 0
- [x] 71 testes verdes (6 novos + 30 test_brand_gate + 30 test_relevance_gates + outros existentes)
