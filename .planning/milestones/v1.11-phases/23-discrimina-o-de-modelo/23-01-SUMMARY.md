---
phase: 23-discrimina-o-de-modelo
plan: "01"
subsystem: relevance-config
tags: [model-discrimination, config, multiplier, tiebreak-knobs]
dependency_graph:
  requires: []
  provides:
    - RelevanceSettings.NLP_MODEL_PENALTY_HEAVY_WITH_BRAND=0.40
    - RelevanceSettings.NLP_MODEL_PENALTY_MED_WITH_BRAND=0.75
    - RelevanceSettings.VISUAL_TIEBREAK_ENABLED (bool, default True)
    - RelevanceSettings.VISUAL_TIEBREAK_TEXT_WINDOW (float, default 10.0)
  affects:
    - services/nlp_service.py (_apply_model_word_penalty reads HEAVY_WITH_BRAND and MED_WITH_BRAND via cfg)
    - services/cross_marketplace_service.py (Plan 02 will consume VISUAL_TIEBREAK_* knobs)
tech_stack:
  added: []
  patterns:
    - pydantic-settings Field(default=..., description=...) idiom for .env-overridable config
key_files:
  created: []
  modified:
    - config.py
decisions:
  - "HEAVY_WITH_BRAND=0.40 chosen (not 0.45): conservative limit — 99*0.40=39.6 < MED_TEXT_FLOOR(40) covers all realistic raw blends; 0.45 fails at raw=90 (90*0.45=40.5 >= 40)"
  - "MED_WITH_BRAND=0.75 (was 0.90): more discriminating for MED range but by design does NOT fully block visual rescue — residual ambiguity is MODEL-02's domain (Plan 02)"
  - "VISUAL_TIEBREAK_ENABLED/TEXT_WINDOW added as .env-overridable knobs following BRAND_GATE_ENABLED idiom (BRAND-03 pattern)"
metrics:
  duration: "1m"
  completed_date: "2026-06-14"
  tasks_completed: 1
  tasks_total: 1
  files_modified: 1
---

# Phase 23 Plan 01: Reforço de Multiplicadores WITH_BRAND e Knobs VISUAL_TIEBREAK_* Summary

**One-liner:** Reforço dos multiplicadores de penalidade WITH_BRAND em `RelevanceSettings` (HEAVY: 0.70→0.40, MED: 0.90→0.75) para defeatar o resgate do Gate 1 visual em candidatos de modelo divergente, mais adição dos knobs `VISUAL_TIEBREAK_ENABLED`/`VISUAL_TIEBREAK_TEXT_WINDOW` consumidos pela Lever 2 (Plan 02).

## What Was Built

Mudança de dois defaults e adição de dois Field em `config.py::RelevanceSettings` — zero código estrutural em `services/`:

1. **`NLP_MODEL_PENALTY_HEAVY_WITH_BRAND`: 0.70 → 0.40** (MODEL-01, criterion 3)
   - Com 0.40, qualquer blend bruto realista <= 99 produz texto penalizado = 99*0.40 = 39.6 < MED_TEXT_FLOOR (40.0)
   - Gate 1 (`if img >= 85 and text >= 40`) NÃO dispara — candidato cai na média ponderada (55.12 e 57.60 para blends 88 e 90 com image=85/90), abaixo do cutoff 60
   - `compute_final_match_score(88*0.40, 85.0)` = 55.12 < 60 e `(90*0.40, 90.0)` = 57.60 < 60 (verificados)

2. **`NLP_MODEL_PENALTY_MED_WITH_BRAND`: 0.90 → 0.75** (MODEL-01, faixa MED)
   - Mais discriminante para ratio em [0.50, 0.75): não derruba completamente (resíduo é para MODEL-02)
   - Por design: empurra ambiguidade para o desempate visual do Plan 02

3. **`VISUAL_TIEBREAK_ENABLED`: bool Field(default=True)** (MODEL-02 knob)
   - Espelha o idioma de `BRAND_GATE_ENABLED`; rollback via `.env` sem alterar código

4. **`VISUAL_TIEBREAK_TEXT_WINDOW`: float Field(default=10.0)** (MODEL-02 knob)
   - Janela de 10.0 pontos cobre dispersão de variantes de cor (~5.3) + candidatos adjacentes (~8)
   - Tunável via `.env`; marcado para recalibração em categorias além de polo

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Reforçar multiplicadores WITH_BRAND e adicionar knobs VISUAL_TIEBREAK_* | 85807bc | config.py |

## Verification Results

```
config ok
heavy 0.40 blocks Gate 1 rescue at raw=88, final=55.12
heavy 0.40 robust at raw=90 img=90, final=57.60
relevance_gates.py UNCHANGED ok
nlp_service.py UNCHANGED ok
30 passed in 0.33s
```

All acceptance criteria met:
- `NLP_MODEL_PENALTY_HEAVY_WITH_BRAND == 0.40` — verified
- `NLP_MODEL_PENALTY_MED_WITH_BRAND == 0.75` — verified
- `NLP_MODEL_PENALTY_HEAVY_WITHOUT_BRAND == 0.55` — unchanged, verified
- `NLP_MODEL_PENALTY_MED_WITHOUT_BRAND == 0.80` — unchanged, verified
- `NLP_MODEL_PENALTY_LOW_THRESHOLD == 0.50` and `NLP_MODEL_PENALTY_MED_THRESHOLD == 0.75` — unchanged, verified
- `VISUAL_TIEBREAK_ENABLED is True` — verified
- `VISUAL_TIEBREAK_TEXT_WINDOW == 10.0` — verified
- `compute_final_match_score(88*0.40, 85.0) = 55.12 < 60.0` — Gate 1 defeated
- `compute_final_match_score(90*0.40, 90.0) = 57.60 < 60.0` — Gate 1 defeated
- `git diff --quiet -- services/relevance_gates.py` → exit 0 (LOCKED purity preserved)
- `git diff --quiet -- services/nlp_service.py` → exit 0 (zero structural change)
- 30 existing tests green (no regression)

## Deviations from Plan

None — plan executed exactly as written. The PATTERNS.md showed 0.45 as a candidate value in the float Field idiom comment, but the plan frontmatter and objective explicitly mandated 0.40. The phase-specific constraints confirmed `HEAVY_WITH_BRAND=0.40`. Applied 0.40 per plan directive.

## Known Stubs

None — this plan only modifies config defaults; no UI rendering or data wiring involved.

## Threat Flags

None — no new trust boundaries introduced. All new fields are pydantic-settings typed floats/bool, validated at startup. Consistent with T-23-* analysis in the plan's threat model.

## Self-Check: PASSED

- [x] `config.py` modified with 4 changes (2 default updates, 2 new fields)
- [x] Commit 85807bc exists: `git log --oneline | grep 85807bc` — confirmed
- [x] `services/relevance_gates.py` unchanged
- [x] `services/nlp_service.py` unchanged
- [x] 30 tests green
