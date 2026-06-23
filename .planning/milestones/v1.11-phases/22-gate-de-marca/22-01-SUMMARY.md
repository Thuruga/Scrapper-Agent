---
phase: 22-gate-de-marca
plan: "01"
subsystem: relevance-pipeline
tags: [brand-gate, nlp, filtering, precision, tdd]
dependency_graph:
  requires: []
  provides:
    - RelevanceSettings.BRAND_GATE_ENABLED
    - NLPService.brand_is_present
    - passes_brand_gate (module-level predicate)
    - produtos_filtrados brand filter in compare_product
  affects:
    - services/cross_marketplace_service.py (compare_product pipeline)
    - config.py (RelevanceSettings)
    - services/nlp_service.py (NLPService)
tech_stack:
  added: []
  patterns:
    - pure module-level predicate importable by both production and tests (anti-tautology HIGH-1)
    - fail-closed for empty marketplace title with known brand in query (T-22-02)
    - flag read inline from relevance_settings, passed as argument — no hardcode (BRAND-03)
key_files:
  created:
    - tests/test_brand_gate.py
  modified:
    - config.py
    - services/nlp_service.py
    - services/cross_marketplace_service.py
decisions:
  - "passes_brand_gate is a pure module-level function (not a method) so production and tests import the same object — reimplementing the predicate in tests would allow a mis-positioned filter in production to pass green"
  - "brand_is_present applies only _clean_text (no remove_colors): known_brands_for_detection ∩ colors == ∅, so the step is provably superfluous for the brand verdict"
  - "nlp_service import moved to module scope in cross_marketplace_service.py so passes_brand_gate is importable without side effects; local import inside compare_product kept for zero-diff in existing code"
metrics:
  duration: "3 minutes"
  completed: "2026-06-13"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 4
---

# Phase 22 Plan 01: Gate de Marca Summary

**One-liner:** Filtro binário pós-score de marca via `passes_brand_gate` + `NLPService.brand_is_present`, fechando o vazamento onde o resgate visual do Gate 1 (text=40.9 → final=85) exibia polos Hering em buscas por SKU Aramis.

## What Was Built

### Task 1 — BRAND_GATE_ENABLED config flag (commit `71593b7`)

Added `BRAND_GATE_ENABLED: bool = Field(default=True, ...)` to `RelevanceSettings` in `config.py`, positioned in the cutoff-thresholds block (after `CROSS_MAX_RESULTS_PER_PLATFORM_FINAL`). Default `True` (gate active). Overridable via `.env` without code changes (`BRAND_GATE_ENABLED=false`). No other field was touched.

### Task 2 — NLPService.brand_is_present (commit `6513f5a`)

Added public method `brand_is_present(self, official_title: str, marketplace_title: str) -> bool` to `NLPService` in `services/nlp_service.py`. Accepts raw titles, cleans internally with `_clean_text` only (no `remove_colors` — intentional; `known_brands_for_detection ∩ colors == ∅`). Uses `self._vocab.known_brands_for_detection` as single source of truth (frozenset from `data/nlp_vocabulary.json`). Fail-closed for empty marketplace title (returns `False` when brand in query). Fail-open for empty official title (returns `True`, no-op). Docstring documents why `remove_colors` is omitted.

### Task 3 — passes_brand_gate + wiring + tests (commit `1842a12`)

**Part A:** Added pure module-level function `passes_brand_gate(titulo, official_title, enabled) -> bool` to `services/cross_marketplace_service.py` returning `(not enabled) or nlp_service.brand_is_present(official_title, titulo)`. Import of `nlp_service` elevated to module scope for importability.

**Part B:** Updated `produtos_filtrados` comprehension in `compare_product` to include `passes_brand_gate(p.get("titulo", ""), official_title, relevance_settings.BRAND_GATE_ENABLED)` as a third predicate (alongside score ≥ cutoff and preco > 0). Flag read inline, passed as argument — no hardcode.

**Part C:** Created `tests/test_brand_gate.py` with 8 tests in 2 classes:
- `TestBrandGate` (5 tests): anchor (Hering discarded), non-regression (Aramis passes), no-op, color-token guard (HIGH-2), visual rescue independence (BRAND-02).
- `TestBrandGatePredicate` (3 tests): `passes_brand_gate(enabled=True)` drops Hering, `passes_brand_gate(enabled=False)` keeps Hering (BRAND-03), integration test with `cutoff=60` fixed explicitly proving 85≥60 and drop is attributable to brand not score.

## Test Results

```
tests/test_brand_gate.py    8 passed
tests/test_relevance_gates.py  22 passed
Total: 30 passed in 0.58s
```

`git diff --quiet -- services/relevance_gates.py` exits 0 — purity preserved (LOCKED).

## Deviations from Plan

### Minor Deviation — 8 tests instead of 7

The plan's artifact list names 7 tests. An eighth test (`test_integration_hering_absent_enabled_present_disabled`) was added to `TestBrandGatePredicate` to cover the MEDIUM integration behavior (cutoff=60, Hering absent/present with enabled=True/False) as a dedicated test rather than embedding it in `test_brand_gate_disabled_keeps_item`. The 7 named behaviors are all covered; the eighth is an additive integration scenario required by the `<behavior>` spec.

## Known Stubs

None.

## Threat Flags

No new trust boundaries introduced beyond those already in the plan's threat model (T-22-01 through T-22-04).

## Self-Check: PASSED

- [x] `config.py` contains `BRAND_GATE_ENABLED` field — FOUND
- [x] `services/nlp_service.py` contains `def brand_is_present` — FOUND
- [x] `services/cross_marketplace_service.py` contains `def passes_brand_gate` at module level — FOUND
- [x] `tests/test_brand_gate.py` exists — FOUND
- [x] Commit `71593b7` (Task 1) — FOUND
- [x] Commit `6513f5a` (Task 2) — FOUND
- [x] Commit `1842a12` (Task 3) — FOUND
- [x] `services/relevance_gates.py` unchanged — VERIFIED
- [x] 30 tests pass (8 new + 22 existing) — VERIFIED
