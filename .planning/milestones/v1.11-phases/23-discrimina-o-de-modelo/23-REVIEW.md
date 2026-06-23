---
phase: 23-discrimina-o-de-modelo
reviewed: 2026-06-13T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - config.py
  - services/cross_marketplace_service.py
  - tests/test_model_discrimination.py
findings:
  critical: 1
  warning: 4
  info: 3
  total: 8
status: issues_found
---

# Phase 23: Code Review Report

**Reviewed:** 2026-06-13
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed the MODEL-01/MODEL-02 implementation: the `VISUAL_TIEBREAK_*` config
knobs, the reinforced penalty multipliers, the new `apply_visual_tiebreak` /
`_detect_candidate_brand` functions, and their tests.

LOCKED constraint **honored**: `git diff HEAD~5..HEAD` touches only
`services/cross_marketplace_service.py` and `tests/test_model_discrimination.py`.
`services/relevance_gates.py` was NOT modified and remains pure.

The headline concern is the bucket-flooring `sort_key` in `apply_visual_tiebreak`.
It contains a genuine, reproducible mis-ordering bug at bucket boundaries — and
the existing tests do not catch it because every fixture lives inside a single
`[80,90)` bucket. The defect is exactly the "candidate straddling a bucket
boundary sorting incorrectly" pitfall the phase brief flagged, and it manifests
in two distinct ways (in-window vs out-of-window, and in-window vs in-window).

The config changes are values-only and correct. The fallback path reproduces the
prior `(-final, preco)` behavior exactly.

## Critical Issues

### CR-01: Bucket-flooring sort key mis-orders candidates at bucket boundaries

**File:** `services/cross_marketplace_service.py:115-128`

**Issue:** `_sort_key` floors `final_match_score` into `safe_window`-wide buckets
(`math.floor(final / safe_window) * safe_window`) for in-window candidates, but
keys out-of-window candidates on the **exact** `-final`. Mixing a *floored* value
and an *exact* value in the same sort tuple position produces two reproducible
inversions:

**(a) Out-of-window beats higher in-window (lower score ranks higher).**
With a brand top-score of 92, `window=10`:
- Out-of-window A: `final=81` (92-81=11 > 10) → key `(0, -81.0, 0.0, preco)`
- In-window B: `final=89` (92-89=3 ≤ 10), `img=20` → `bucket=floor(89/10)*10=80` →
  key `(0, -80.0, -20.0, preco)`

Since `-81.0 < -80.0`, **A (final=81) sorts ABOVE B (final=89)** — a candidate
with a strictly lower final score is promoted above a higher one. Verified by
direct computation. The phase's own `test_out_of_window_candidate_not_demoted`
passes only because it uses final=92 vs final=86 (a gap large enough that the
floored 80 still loses to -92); it never exercises a boundary where the floored
bucket overtakes the out-of-window exact score.

**(b) In-window vs in-window: visual tiebreak silently disabled at every bucket edge.**
Two same-brand candidates with near-identical text scores that fall on opposite
sides of a bucket boundary are never compared by image:
- G: `final=80.0`, `img=10` → `bucket=80` → key `(0, -80.0, -10.0, …)`
- H: `final=79.9`, `img=99` → `bucket=70` → key `(0, -70.0, -99.0, …)`

`-80.0 < -70.0` so **G wins despite img=10 vs H's img=99**, even though their text
scores are 0.1 apart. This defeats the entire purpose of MODEL-02 (let the visual
signal break text ties) for any pair straddling a `…0`-point boundary. The window
is anchored to each brand's top score, but the bucket grid is anchored to absolute
zero — the two are unrelated, so a boundary can fall anywhere inside the window.

**Fix:** Do not floor for ordering. The intent ("within the window, the higher
image_score wins; otherwise rank by final") is expressed directly without bucket
arithmetic, and is comparable across in/out-of-window because both branches key on
exact `final`:

```python
def _sort_key(c):
    final = c.get("final_match_score", 0.0)
    img = c.get("image_match_score", 0.0)
    preco = c.get("preco", 0.0)
    bk = _detect_candidate_brand(c.get("titulo", ""), vocab_brands)
    top = brand_top.get(bk, 0.0) if bk else 0.0
    in_window = bk is not None and img > 0 and (top - final) <= window
    if in_window:
        # Within the brand's ambiguity window: anchor all in-window members of
        # the same brand to the brand top, then let image_score decide.
        return (0, -top, -img, preco)
    return (1, -final, 0.0, preco)
```

Here every in-window member of a brand shares the same `-top` primary key, so they
compete purely on `-img` (the MODEL-02 intent) with no boundary discontinuity, and
out-of-window candidates are keyed on exact `-final`. If a different anchoring is
desired, the key insight is the same: **never compare a floored value against an
exact value in the same tuple slot, and never let an arbitrary grid line cut
through the ambiguity window.** Add regression tests at the boundary
(final=89 vs 81 across buckets; final=80.0/img=10 vs 79.9/img=99) — the current
suite would still pass the buggy code.

## Warnings

### WR-01: Tests are confined to a single bucket — boundary regressions invisible

**File:** `tests/test_model_discrimination.py:30-44, 110-221`

**Issue:** Every fixture `final_match_score` is in `[82, 92]`, i.e. the single
`[80,90)`/`[90,100)` region. No test crosses a `floor(final/window)*window`
boundary, so CR-01's mis-orderings (final=89 vs 81; 80.0 vs 79.9) are completely
untested. The suite gives false confidence that the sort key is correct.

**Fix:** Add the two boundary cases from CR-01 as explicit anchor tests. They will
fail against the current implementation and pass against the suggested fix,
locking in the correct behavior.

### WR-02: `_detect_candidate_brand` returns first match from non-deterministic frozenset iteration

**File:** `services/cross_marketplace_service.py:59-62`

**Issue:** The loop `for brand in vocab_brands` iterates a `frozenset`, whose order
is not guaranteed stable across processes (hash randomization / set internals).
When a title contains two known brands (e.g. a co-branded or comparison title
"Polo Aramis vs Tommy"), the detected brand — and therefore the `brand_top` anchor
and bucket grouping in `apply_visual_tiebreak` — can differ between runs. This
makes the final ordering non-deterministic for such titles. Rare in practice, but
it undermines reproducibility and is hard to debug if it surfaces.

**Fix:** Make selection deterministic, e.g. iterate a sorted snapshot and prefer a
defined precedence (longest match, or sorted order):

```python
for brand in sorted(vocab_brands):
    if brand in words:
        return brand
```

Document that the first brand by sort order wins when multiple are present, or
return all matches and let the caller decide.

### WR-03: `_sort_key` re-runs `_detect_candidate_brand` for every comparison

**File:** `services/cross_marketplace_service.py:115-120`

**Issue:** `_sort_key` calls `_detect_candidate_brand(c.get("titulo", ""), …)` on
every key evaluation, which itself calls `nlp_service._clean_text` (HTML unescape,
regex, unicode normalization). `sorted` invokes the key once per element, but the
brand was *already* computed for every candidate in the `brand_top` loop
(lines 108-111). The work is duplicated and the result is recomputed. Beyond the
cost, recomputation is a correctness hazard if `_detect_candidate_brand` is ever
non-deterministic (see WR-02): the brand used to build `brand_top` could differ
from the brand used in the key for the same candidate, corrupting the `top` lookup.

**Fix:** Compute the brand once per candidate and cache it (e.g. annotate a local
dict `brand_by_id = {id(c): bk}` or precompute a list of `(candidate, brand)`
tuples) so `brand_top` construction and the sort key read the same value.

### WR-04: Reliance on private `nlp_service._vocab` / `_clean_text` across module boundary

**File:** `services/cross_marketplace_service.py:57, 104`

**Issue:** `apply_visual_tiebreak` / `_detect_candidate_brand` reach into
`nlp_service._vocab.known_brands_for_detection` and `nlp_service._clean_text` —
both underscore-private. This couples the cross-marketplace module to NLPService
internals; a refactor of NLPService (renaming `_vocab` or `_clean_text`) silently
breaks the tiebreak with no type/interface contract to catch it. `nlp_service`
already exposes the public `brand_is_present`; brand detection deserves a public
accessor too.

**Fix:** Add a public method/property on `NLPService` (e.g.
`detect_brand(title) -> str | None` and `known_brands` property) and call those.
Keeps the single-source-of-truth intent without depending on private members.

## Info

### IN-01: `in_window` uses `window` while bucket uses `safe_window`

**File:** `services/cross_marketplace_service.py:121, 125`

**Issue:** The window membership test uses raw `window` (`(top - final) <= window`)
while the bucket uses the guarded `safe_window`. When `window <= 0`, membership
collapses to `top - final <= 0` (only the exact top qualifies) yet the bucket still
divides by `safe_window=0.1`, producing huge bucket values. Behavior is defensible
(window<=0 ≈ tiebreak off) but the two values diverging is a latent footgun once
CR-01 is refactored. Prefer using `safe_window` consistently, or guard
`window <= 0` by short-circuiting to the fallback sort.

### IN-02: Out-of-window key third slot is a float `0.0` placeholder

**File:** `services/cross_marketplace_service.py:128`

**Issue:** Out-of-window returns `(0, -final, 0.0, preco)` where `0.0` pads the
`-img` slot used by in-window keys. It works because the first/second elements
already separate the groups in the intended fix, but a literal `0.0` placeholder
in a tuple compared against real `-img` values is fragile and unexplained. Add a
comment or, after the CR-01 fix, use a distinct leading group flag (`0` vs `1`) so
in-window and out-of-window tuples never compete on heterogeneous slots.

### IN-03: `official_title` parameter is unused

**File:** `services/cross_marketplace_service.py:69, 91`

**Issue:** `apply_visual_tiebreak` accepts `official_title` (documented as "used
only for brand vocabulary lookup via nlp_service") but never references it — the
vocabulary comes from `nlp_service._vocab.known_brands_for_detection`
(line 104), independent of the official title. The parameter is dead. Either use
it (e.g. restrict tiebreak to the brand(s) present in the query, mirroring
`passes_brand_gate`) or drop it from the signature and the call site
(line 352) to avoid misleading future readers.

---

_Reviewed: 2026-06-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
