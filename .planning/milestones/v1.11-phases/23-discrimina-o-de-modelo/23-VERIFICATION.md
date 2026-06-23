---
phase: 23-discrimina-o-de-modelo
verified: 2026-06-13T00:00:00Z
status: passed
score: 8/8 must-haves verified
overrides_applied: 0
re_verification: null
gaps: []
deferred: []
human_verification: []
---

# Phase 23: Discriminação de Modelo — Verification Report

**Phase Goal:** Entre produtos da marca correta, garantir que o topo do resultado é o modelo/linha específico buscado — e não um modelo Aramis adjacente — usando model-words decisivas e o sinal visual CLIP como desempate quando o texto está ambíguo.
**Verified:** 2026-06-13
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Um candidato com model_ratio < 0.50 e mesma marca tem texto penalizado por HEAVY_WITH_BRAND=0.40, caindo abaixo de MED_TEXT_FLOOR(40), defeatando o Gate 1 e ficando abaixo do cutoff 60 (MODEL-01 criterion 3) | ✓ VERIFIED | `config.py:288` `default=0.40`; `compute_final_match_score(88*0.40, 85.0)=55.12 < 60`, `(90*0.40, 90.0)=57.60 < 60` — ambas confirmadas via Python |
| 2 | Um candidato na faixa MED (0.50 <= ratio < 0.75) é penalizado por MED_WITH_BRAND=0.75 (mais discriminante que o antigo 0.90) (MODEL-01 setup faixa MED) | ✓ VERIFIED | `config.py:301` `default=0.75`; `relevance_settings.NLP_MODEL_PENALTY_MED_WITH_BRAND == 0.75` confirmado via Python |
| 3 | Candidato de modelo+marca corretos (ratio >= 0.75) NÃO recebe penalidade — seu score permanece intacto (criterion 4, não-regressão) | ✓ VERIFIED | `test_correct_model_unaffected_by_penalty` passes; `TestModelPenalty` verde (13/13) |
| 4 | VISUAL_TIEBREAK_ENABLED (bool, default True) e VISUAL_TIEBREAK_TEXT_WINDOW (float, default 10.0) presentes em RelevanceSettings e overridáveis via .env (MODEL-02 knobs) | ✓ VERIFIED | `config.py:227-246`; assertions `r.VISUAL_TIEBREAK_ENABLED is True`, `r.VISUAL_TIEBREAK_TEXT_WINDOW == 10.0` passaram |
| 5 | Entre candidatos da mesma marca dentro de VISUAL_TIEBREAK_TEXT_WINDOW, o de maior image_match_score fica no topo — visual atua como desempate explícito (MODEL-02) | ✓ VERIFIED | `apply_visual_tiebreak` usa chave de duas faixas sem flooring: `(0, -top, -img, preco)` para in-window; `test_promotes_higher_image_within_window` e `test_text_leader_overtaken_by_visual_within_window` passam |
| 6 | CR-01 corrigido: chave de ordenação não usa bucket-flooring — candidato in-window de maior final não cai abaixo de out-of-window de final menor (sem inversão por linha de grade) | ✓ VERIFIED | `math.floor` ausente em `apply_visual_tiebreak`; two-tier key `(0,-top,-img,preco)` / `(1,-final,0.0,preco)` confirmada; `TestVisualTiebreakBoundary` (2 testes) passam |
| 7 | apply_visual_tiebreak é função pura de nível de módulo que recebe window/enabled como argumentos (não lê relevance_settings internamente), retorna nova lista, e está fiada em compare_product substituindo o .sort() in-place | ✓ VERIFIED | Assinatura `(candidates, window, enabled)` sem `official_title`; `relevance_settings.` ausente no corpo da função; `produtos_filtrados = apply_visual_tiebreak(...)` na linha 367 (antes do cap por plataforma na linha 382); antigo `.sort()` ausente |
| 8 | services/relevance_gates.py e services/nlp_service.py permanecem byte-idênticos (pureza LOCKED Phase 22) | ✓ VERIFIED | `git diff --quiet -- services/relevance_gates.py` → exit 0; `git diff --quiet -- services/nlp_service.py` → exit 0 |

**Score:** 8/8 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `config.py` | `NLP_MODEL_PENALTY_HEAVY_WITH_BRAND=0.40`, `NLP_MODEL_PENALTY_MED_WITH_BRAND=0.75`, `VISUAL_TIEBREAK_ENABLED=True`, `VISUAL_TIEBREAK_TEXT_WINDOW=10.0` | ✓ VERIFIED | Lines 227-246, 287-310; all four values confirmed via Python assertion |
| `services/cross_marketplace_service.py` | `apply_visual_tiebreak` + `_detect_candidate_brand` as module-level pure functions; calling site wiring | ✓ VERIFIED | Both functions present at module level (confirmed via AST); two-tier non-floored sort key; `brand_by_id` cache (WR-03); `sorted(vocab_brands)` (WR-02) |
| `tests/test_model_discrimination.py` | 13 tests covering MODEL-01/MODEL-02 anchors + CR-01 boundary regressions + robustness | ✓ VERIFIED | 4 test classes: `TestModelPenalty` (2), `TestVisualTiebreak` (4), `TestVisualTiebreakBoundary` (2), `TestVisualTiebreakRobustness` (5) = 13 total; all pass |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `services/nlp_service.py _apply_model_word_penalty` | `relevance_settings.NLP_MODEL_PENALTY_HEAVY_WITH_BRAND` | existing consumer reads cfg at runtime | ✓ WIRED | No structural change to `nlp_service.py` needed — default changed in `config.py` is consumed by existing code |
| `compare_product` (line 367) | `apply_visual_tiebreak` | `produtos_filtrados = apply_visual_tiebreak(produtos_filtrados, window=relevance_settings.VISUAL_TIEBREAK_TEXT_WINDOW, enabled=relevance_settings.VISUAL_TIEBREAK_ENABLED)` | ✓ WIRED | Flags read inline from `relevance_settings`; confirmed by source grep and AST parse |
| `apply_visual_tiebreak` | `_detect_candidate_brand` | `_detect_candidate_brand(c.get("titulo",""), vocab_brands)` inside function body | ✓ WIRED | Confirmed in source at line ~130; brand cached via `brand_by_id` |
| `_detect_candidate_brand` | `nlp_service._clean_text` + `known_brands_for_detection` | `nlp_service._clean_text(titulo)` + iteration over `vocab_brands` (frozenset from `nlp_service._vocab.known_brands_for_detection`) | ✓ WIRED | Source confirmed; no literal brand list; WR-02 fixed with `sorted(vocab_brands)` |
| `tests/test_model_discrimination.py` | production `apply_visual_tiebreak` | `from services.cross_marketplace_service import apply_visual_tiebreak` | ✓ WIRED | Import confirmed; no local reimplementation of sort/bucket logic in test file |

---

### Data-Flow Trace (Level 4)

Not applicable — this is a backend relevance pipeline (pure Python functions and config). No UI rendering or dynamic data sources to trace. The data flowing through `apply_visual_tiebreak` comes from the product dicts already scored by NLP + CLIP in `compare_product`; the tiebreak operates on those scores and returns a reordered list that feeds the cap and final formatting steps.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Config defaults correct | `python -c "from config import relevance_settings as r; assert r.NLP_MODEL_PENALTY_HEAVY_WITH_BRAND == 0.40 ..."` | All 8 assertions passed | ✓ PASS |
| Gate 1 defeated by HEAVY=0.40 | `compute_final_match_score(88*0.40, 85.0)` → 55.12; `(90*0.40, 90.0)` → 57.60 | Both < 60.0 | ✓ PASS |
| MODEL-02 visual tiebreak | `apply_visual_tiebreak([a,c], 10.0, True)` → c (img=92) ranks above a (img=72) | `r[0] is c` | ✓ PASS |
| Fallback enabled=False | `apply_visual_tiebreak([a,c], 10.0, False)` → order by -final | `r2[0] is c(86) before a(85)` | ✓ PASS |
| Fallback all image==0 | `apply_visual_tiebreak([...all img=0...], 10.0, True)` → text order | `r3[0]['final_match_score']==88.0` | ✓ PASS |
| CR-01(a) regression: in-window above out-of-window | `apply_visual_tiebreak([a_out(81), b_in(89), top(92)], 10.0, True)` | `b_in` before `a_out` | ✓ PASS |
| Full test suite | `python -m pytest tests/ -q` | 78 passed | ✓ PASS |
| Model discrimination tests | `python -m pytest tests/test_model_discrimination.py -q` | 13 passed | ✓ PASS |
| LOCKED files unchanged | `git diff --quiet -- services/relevance_gates.py services/nlp_service.py` | exit 0 | ✓ PASS |

---

### Probe Execution

No conventional `scripts/*/tests/probe-*.sh` probes found. The PLAN verification blocks used inline Python commands — all executed and confirmed above.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| MODEL-01 | 23-01-PLAN (config changes), 23-02-PLAN (tests + wiring) | Entre produtos da marca correta, o topo corresponde ao modelo buscado, não a um adjacente | ✓ SATISFIED | `HEAVY_WITH_BRAND=0.40` defeats Gate 1 for divergent models; `apply_visual_tiebreak` promotes correct model by image within window; `test_correct_model_ranks_above_adjacent` (anchor 1) and `test_model_ratio_zero_below_cutoff_with_high_image` (anchor 3) pass |
| MODEL-02 | 23-02-PLAN | O sinal visual (CLIP) atua como desempate entre candidatos da mesma marca quando o score de texto é ambíguo | ✓ SATISFIED | `apply_visual_tiebreak` two-tier comparator promotes highest `image_match_score` within `VISUAL_TIEBREAK_TEXT_WINDOW`; wired in `compare_product`; `test_promotes_higher_image_within_window` (anchor 2) and `test_text_leader_overtaken_by_visual_within_window` (Criterion 2 sharp test) pass |

**REQUIREMENTS.md traceability note:** REQUIREMENTS.md marks MODEL-02 as `[ ]` (Pending) in the checkbox column but lists it as "Phase 23: Pending" in the traceability table — this is a pre-existing documentation state reflecting that MODEL-02 was not yet implemented when REQUIREMENTS.md was written. The implementation is now complete and verified.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `config.py` | 294 | `"todo blend bruto realista..."` | ℹ️ Info | Portuguese word "todo" (meaning "every"), not an English TODO action marker. No debt. |
| `services/cross_marketplace_service.py` | 93 | `"Como todo membro in-window..."` | ℹ️ Info | Portuguese word "todo" (meaning "every") in a docstring comment. Not a debt marker. |

No TBD, FIXME, or XXX markers found. No placeholder implementations or stub returns in any phase file. No orphaned artifacts.

**WR-04 (deferred by code review):** Reliance on private `nlp_service._vocab` / `_clean_text` across module boundary is explicitly deferred in `23-REVIEW-FIX.md` — requires structural change to `nlp_service.py` which Phase 23 locked as config-only. Low severity; private members are stable. Recommend a follow-up phase to expose `NLPService.known_brands` / `detect_brand(title)`.

---

### Human Verification Required

None. This is a backend relevance-engine phase verifiable entirely by unit tests and source assertions. All behavioral checks are deterministic and confirmed programmatically.

---

### Gaps Summary

No gaps. All 8 must-have truths are verified, all artifacts exist and are substantive and wired, all key links are confirmed, both requirement IDs (MODEL-01, MODEL-02) are satisfied, all 78 tests pass (13 model discrimination + 65 pre-existing), and LOCKED files are byte-identical.

The CR-01 critical bug (bucket-flooring sort key) reported in `23-REVIEW.md` was fully resolved before this verification: the live `apply_visual_tiebreak` uses the two-tier non-floored comparator `(0, -top, -img, preco) / (1, -final, 0.0, preco)`, confirmed by AST inspection and by the two `TestVisualTiebreakBoundary` regression tests that were added specifically to prevent this class of bug from re-emerging.

---

_Verified: 2026-06-13T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
