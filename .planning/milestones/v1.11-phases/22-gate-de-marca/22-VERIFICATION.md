---
phase: 22-gate-de-marca
verified: 2026-06-13T00:00:00Z
status: passed
score: 7/7 must-haves verified
overrides_applied: 0
re_verification: false
---

# Phase 22: Gate de Marca Verification Report

**Phase Goal:** Quando a query por SKU especifica uma marca conhecida, garantir que produtos sem essa marca no título sejam descartados do resultado final — fechando o vazamento onde o gate de resgate visual (`if img>=85 and text>=40: max(img,text)` em services/relevance_gates.py) reabilita um concorrente parecido cujo texto já foi penalizado.
**Verified:** 2026-06-13
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Busca por SKU Aramis NÃO exibe polo Hering (marca ausente), mesmo com image_match_score >= 85 (BRAND-01, BRAND-02) | VERIFIED | `passes_brand_gate("...Piquet Hering", "...aramis", True) is False` confirmed live; `test_hering_polo_discarded_against_aramis_query` passes |
| 2 | Resgate visual Gate 1 `compute_final_match_score(40.9, 85) == 85` deixa de reabilitar item de marca ausente — filtro de marca é independente do score (BRAND-02) | VERIFIED | Live: `compute_final_match_score(40.9, 85.0) == 85.0` confirmed; `brand_is_present(official_Aramis, title_Hering) is False` confirmed; `test_independent_of_visual_rescue` and `test_integration_hering_absent_enabled_present_disabled` (cutoff=60 fixed, 85>=60 asserted) both pass |
| 3 | O predicado `passes_brand_gate` é o MESMO objeto de código usado em produção E nos testes (anti-tautologia HIGH-1) | VERIFIED | Test file contains `from services.cross_marketplace_service import passes_brand_gate` — imports the production object. No re-implementation of brand predicate in test body (only in comments). `TestBrandGatePredicate` exercises the imported predicate directly. |
| 4 | Títulos do marketplace que contêm a marca (~95% legítimos) continuam exibidos (BRAND-01) | VERIFIED | `passes_brand_gate("...Aramis Masculina Piquet", "...aramis", True) is True` confirmed live; `test_aramis_title_passes` passes |
| 5 | Query sem marca conhecida não remove nada — o gate é no-op (BRAND-01) | VERIFIED | `nlp_service.brand_is_present("Camisa Polo Masculina Piquet", "Camisa Polo Hering") is True` confirmed; `test_noop_when_query_has_no_known_brand` passes |
| 6 | Veredito de marca não muda quando token de cor é adicionado/removido — marcas ∉ colors por construção (BRAND-01, HIGH-2) | VERIFIED | `test_brand_detection_unaffected_by_color_tokens` passes: result_with_color == result_without_color; docstring of `brand_is_present` explicitly documents that `remove_colors` is omitted because `known_brands_for_detection ∩ colors == ∅` |
| 7 | `BRAND_GATE_ENABLED=False` desativa o filtro via .env, sem hardcode no fluxo de decisão (BRAND-03) | VERIFIED | `BRAND_GATE_ENABLED: bool = Field(default=True, ...)` in `RelevanceSettings`; production call reads `relevance_settings.BRAND_GATE_ENABLED` inline; `passes_brand_gate(..., False) is True` confirmed live; `test_brand_gate_disabled_keeps_item` passes |

**Score:** 7/7 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `config.py` | `RelevanceSettings.BRAND_GATE_ENABLED bool Field(default=True)` | VERIFIED | Lines 215-224: `BRAND_GATE_ENABLED: bool = Field(default=True, ...)` in cutoff-thresholds block |
| `services/nlp_service.py` | `NLPService.brand_is_present(official_title, marketplace_title) -> bool` | VERIFIED | Lines 307-344: public method, uses `_clean_text` + `known_brands_for_detection`, no `remove_colors` in body, returns pure bool |
| `services/cross_marketplace_service.py` | `passes_brand_gate(titulo, official_title, enabled) -> bool` at module level | VERIFIED | Lines 16-38: module-level function (only entry in `module_level_funcs` AST scan), body: `return (not enabled) or nlp_service.brand_is_present(official_title, titulo)` |
| `services/cross_marketplace_service.py` | `passes_brand_gate` wired into `produtos_filtrados` comprehension | VERIFIED | Lines 244-250: third predicate `and passes_brand_gate(p.get("titulo", ""), official_title, relevance_settings.BRAND_GATE_ENABLED)` |
| `tests/test_brand_gate.py` | 8 tests covering anchor/non-regression/no-op/color-guard/config-off/independence | VERIFIED | 8 tests pass: 5 in `TestBrandGate`, 3 in `TestBrandGatePredicate` (including integration) |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `produtos_filtrados` comprehension (L244-250) | `passes_brand_gate` | third predicate in list comprehension passing `p.get("titulo","")`, `official_title`, `relevance_settings.BRAND_GATE_ENABLED` | VERIFIED | Confirmed in source: line 249 |
| `tests/test_brand_gate.py` | `services/cross_marketplace_service.passes_brand_gate` | `from services.cross_marketplace_service import passes_brand_gate` | VERIFIED | Line 21 of test file |
| `passes_brand_gate` | `nlp_service.brand_is_present` | `return (not enabled) or nlp_service.brand_is_present(official_title, titulo)` | VERIFIED | Implementation line 38 |
| `brand_is_present` | `NLPVocabulary.known_brands_for_detection` | `brands_in_query = official_words.intersection(self._vocab.known_brands_for_detection)` | VERIFIED | Line 341 |
| `passes_brand_gate` call site | `relevance_settings.BRAND_GATE_ENABLED` | flag read inline at comprehension, passed as `enabled` argument | VERIFIED | Line 249; no hardcoded True/False in production call |

---

### Pipeline Order Verification (Critical for Phase Goal)

The brand gate must fire AFTER scoring (including visual rescue) and BEFORE per-platform cap, PDP fetch, dedup, and buybox selection. Verified from source line numbers in `compare_product`:

| Step | Lines | Order |
|------|-------|-------|
| `official_title = strict_query` | L125 | 1 — brand string in scope before scoring |
| Text scoring (NLP) | L152-159 | 2 |
| Vision scoring + `compute_final_match_score` (Gate 1 visual rescue fires here) | L187-230 | 3 |
| `produtos_filtrados` comprehension — **BRAND GATE HERE** | L244-250 | 4 — after all scoring incl. visual rescue |
| Per-platform cap (`CROSS_MAX_RESULTS_PER_PLATFORM_FINAL`) | L261-267 | 5 |
| PDP fetch (`fetch_pdp_seller_and_shipping`) | L299 | 6 |
| `dedup_results` | L332 | 7 |
| `mark_buybox_winner` | L335 | 8 |

**VERIFIED:** A brand-absent item with `final_match_score=85` (Gate 1 visual rescue applied) cannot reach the per-platform cap, PDP enrichment, dedup, or buybox selection. It is filtered at step 4.

---

### Data-Flow Trace (Level 4)

| Variable | Assignment | Used in brand gate | Status |
|----------|-----------|-------------------|--------|
| `official_title` | L125: `official_title = strict_query` (the brand-bearing query string) | L249: passed as second arg to `passes_brand_gate` | FLOWING |
| `p.get("titulo", "")` | marketplace product dict field | L249: passed as first arg to `passes_brand_gate` | FLOWING |
| `relevance_settings.BRAND_GATE_ENABLED` | `config.py` Field(default=True) | L249: passed as third arg `enabled` | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Result | Status |
|----------|--------|--------|
| `passes_brand_gate(Hering_title, Aramis_official, True) is False` | False | PASS |
| `passes_brand_gate(Hering_title, Aramis_official, False) is True` | True | PASS |
| `passes_brand_gate(Aramis_title, Aramis_official, True) is True` | True | PASS |
| `compute_final_match_score(40.9, 85) == 85.0` (Gate 1 rescue active) | 85.0 | PASS |
| `brand_is_present(Aramis_official, Hering_title) is False` (independence) | False | PASS |
| `BRAND_GATE_ENABLED` default True | True | PASS |
| Full test suite (65 tests) | 65 passed | PASS |

---

### Probe Execution

Step 7c: SKIPPED (no probe scripts found; phase produces a library module, not a CLI/script).

---

### Requirements Coverage

| Requirement | Plan | Description | Status | Evidence |
|-------------|------|-------------|--------|---------|
| BRAND-01 | 22-01-PLAN.md | Produtos sem marca conhecida da query descartados independentemente do score visual | SATISFIED | `passes_brand_gate` in `produtos_filtrados` comprehension; tests 1, 2, 3, 4 pass |
| BRAND-02 | 22-01-PLAN.md | Gate de marca independente do gate visual (resgate Gate 1 não promove item brand-absent) | SATISFIED | `test_independent_of_visual_rescue` proves `compute_final_match_score(40.9,85)==85` AND `brand_is_present` returns False; integration test cutoff=60 proves drop attributable to brand not score |
| BRAND-03 | 22-01-PLAN.md | Comportamento do gate configurável via config/.env, sem hardcode | SATISFIED | `BRAND_GATE_ENABLED: bool = Field(default=True)` in `RelevanceSettings`; production call reads flag from `relevance_settings` at runtime; `test_brand_gate_disabled_keeps_item` passes |

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None found | — | — | — |

Scanned `config.py`, `services/nlp_service.py`, `services/cross_marketplace_service.py`, `tests/test_brand_gate.py` for TBD/FIXME/XXX/placeholders/empty returns/hardcoded empty props. None found. No spike-002 visual rescue valve (no score/threshold comparison) in `passes_brand_gate` implementation body.

---

### Purity Check (LOCKED Constraint)

`git diff --quiet -- services/relevance_gates.py` exits with code 0. `services/relevance_gates.py` is byte-identical to before Phase 22. No brand/title arguments were added to its functions. No `nlp_service` import was added to it.

---

### Human Verification Required

None. All must-haves are mechanically verifiable and have been verified.

---

## Gaps Summary

No gaps. All 7 must-have truths are verified. All 5 required artifacts exist, are substantive, and are correctly wired. All 3 key links are confirmed. All 3 BRAND requirements are satisfied. The full test suite (65 tests) passes. `services/relevance_gates.py` is untouched.

---

_Verified: 2026-06-13_
_Verifier: Claude (gsd-verifier)_
