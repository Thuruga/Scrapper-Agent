---
phase: 23-discrimina-o-de-modelo
source_review: 23-REVIEW.md
fixed: 2026-06-13
status: fixed
findings_total: 8
findings_fixed: 7
findings_deferred: 1
---

# Phase 23: Code Review Fix Report

Fixes applied to the findings in [23-REVIEW.md](23-REVIEW.md). Source files changed:
`services/cross_marketplace_service.py`, `tests/test_model_discrimination.py`.
LOCKED purity preserved: `services/relevance_gates.py` and `services/nlp_service.py` both
unchanged (`git diff --quiet` exits 0).

## Fixed

### CR-01 (Critical) — bucket-flooring mis-orders at boundaries — FIXED
Replaced the floored `_sort_key` with a **two-tier, non-floored** comparator:
- **Faixa 0 (cohort de ambiguidade):** in-window members (image>0, `final` within `window`
  of the brand's top-score) all anchor on `(0, -brand_top, -image, preco)` — a *shared*
  primary key — so they compete purely on `-image`. No floored value is ever compared
  against an exact value, and no arbitrary grid line cuts through the window.
- **Faixa 1 (fora da janela / sem marca / sem imagem):** `(1, -final, 0.0, preco)`.

Because every in-window member has `final ≥ top − window > ` any out-of-window member's
`final` (same brand), the faixa separation is consistent with text ordering — and the
two reviewer-verified inversions are eliminated:
- Inversion (a): in-window `final=89` now ranks above out-of-window `final=81`.
- Inversion (b): two in-window candidates straddling a `…0` boundary now resolve by
  image (the MODEL-02 intent), not by the grid line.

**Semantic decision (recorded):** Criterion 2 ("scores de texto próximos → o de maior
similaridade visual fica acima — desempate, não confirmação") is taken literally: within
the ambiguity window a lower-text candidate **may overtake the text-leader** on image.
This is now asserted by `test_text_leader_overtaken_by_visual_within_window`.

### WR-01 — boundary regressions invisible — FIXED
Added two regression tests (`TestVisualTiebreakBoundary`) encoding CR-01's exact inversions.
Empirically verified they **fail against the old floored code** and **pass against the fix**
(proven by reconstructing the old comparator), so the bug can no longer regress silently.

### WR-02 — non-deterministic brand detection — FIXED
`_detect_candidate_brand` now iterates `sorted(vocab_brands)`; documented tie-break
(first brand alphabetically) for the rare dual-brand title.

### WR-03 — brand recomputed per comparison — FIXED
Each candidate's brand is detected once and cached in `brand_by_id` (keyed by `id(c)`);
both `brand_top` construction and `_sort_key` read the same cached value. Removes the
duplicated `_clean_text` work and the consistency hazard.

### IN-01 — window vs safe_window divergence — FIXED
The flooring (and its `safe_window` divisor) is gone, so there is a single `window` value.
`window <= 0` degrades cleanly: only the exact brand top qualifies as in-window
(no division, no crash). Covered by `test_window_zero_degrades_to_text_order`.

### IN-02 — heterogeneous tuple slot — FIXED
The leading faixa flag (`0` vs `1`) guarantees in-window and out-of-window keys never
compare their 3rd slot (`-image` vs `0.0`) against each other.

### IN-03 — unused `official_title` param — FIXED
Removed from the signature, docstring, the `compare_product` call site, and all test calls.

## Deferred

### WR-04 — reliance on private `nlp_service._vocab` / `_clean_text` — DEFERRED
Adding public `NLPService` accessors is a **structural change to `services/nlp_service.py`**,
which Phase 23's CONTEXT locked as config-only ("no structural change"). Applying it here
would breach that boundary. Recommend a small follow-up: expose
`NLPService.known_brands` / `detect_brand(title)` and switch the two private references over.
Low severity — the private members are stable and already the single source of truth.

## Verification
- `pytest tests/test_model_discrimination.py -q` → 13 passed (5 original anchors + Criterion-2
  sharp test + 2 CR-01 boundary guards + 5 robustness/edge tests).
- `pytest tests/ -q` → 78 passed (no regression; +7 over the pre-fix 71).
- `git diff --quiet -- services/relevance_gates.py services/nlp_service.py` → exit 0.
- `apply_visual_tiebreak` reads no `relevance_settings` in its logic (anti-tautology HIGH-1).
