---
phase: 26-onboarding-das-5-marcas-vtex
fixed_at: 2026-06-19T14:55:00Z
review_path: .planning/phases/26-onboarding-das-5-marcas-vtex/26-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 26: Code Review Fix Report

**Fixed at:** 2026-06-19T14:55:00Z
**Source review:** .planning/phases/26-onboarding-das-5-marcas-vtex/26-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope (Critical + Warning): 6
- Fixed: 6
- Skipped: 0
- Info findings (IN-01..IN-04): out of scope (fix_scope=critical_warning); not addressed.

## Fixed Issues

### CR-01: `test_mappings_persisted` validates a tautology, not the persistence contract

**Files modified:** `tests/test_vtex_brand_onboarding_contract.py`
**Commit:** adaf17c
**Status:** fixed
**Applied fix:** Imported the real `auto_match` from `scripts/onboard_vtex_brands.py` and rewrote `test_mappings_persisted` to build the `CategoryMapping` list from `auto_match`'s output (driving the production slug producer as the SUT) instead of author-hardcoded slugs. A regression in `auto_match` that emits an off-vocabulary slug now fails the `m.canonical_slug in VALID_SLUGS` assertion. Added an assertion that `auto_match` produced at least one proposal. The test remains fully offline/deterministic — only the pure `auto_match` function is exercised; `main()` (network/stdin) is never called. Test categories supply `rel_path` (the key `auto_match` reads), matching the post-`urlparse` shape produced by `discover_and_match`.

### WR-01: `auto_match` silently drops/mis-routes a category when its best-fit slug was already claimed

**Files modified:** `scripts/onboard_vtex_brands.py`
**Commit:** e5fa84d
**Status:** fixed
**Applied fix:** Restructured the inner loop so the keyword match is evaluated first; when the matched slug is already in `seen_slugs`, the loop now `break`s (decision is made at the category level) instead of `continue`ing onto a later, broader slug. This guarantees each canonical slug is proposed at most once AND that a category whose best match is already claimed is dropped rather than mis-routed to an inferior slug. Verified with an in-process check: two categories both best-matching `calcas` yield a single `calcas` proposal and the second is not re-routed.

### WR-02: `discover_and_match` crashes on categories with a missing/None `path`

**Files modified:** `scripts/onboard_vtex_brands.py`
**Commit:** e5fa84d
**Status:** fixed
**Applied fix:** Changed `urlparse(item["path"])` to `urlparse(item.get("path") or "")`, so a malformed node defaults to an empty path instead of raising `TypeError` and aborting the onboarding loop mid-run. An empty `rel_path` is then safely dropped by the existing `persist_mappings` relative-path guard.

### WR-03: `discover_categories()` failure (empty list) indistinguishable from "site has no categories"

**Files modified:** `scripts/onboard_vtex_brands.py`
**Commit:** e5fa84d
**Status:** fixed
**Applied fix:** `discover_and_match` now returns `(discovered_count, proposals)`. `main` distinguishes three cases: `discovered_count == 0` (probable discovery/network failure) routes the brand to a new `partial` bucket and does NOT mark it `onboarded`; categories discovered but no keyword match also go to `partial`; only a confirmed-and-persisted brand is added to `onboarded`. The final summary now prints a `Parciais` line so a failed/empty discovery is no longer reported as a misleading success.

### WR-04: Idempotency "[s/N]" prompt re-runs discovery even when operator declined to overwrite

**Files modified:** `scripts/onboard_vtex_brands.py`
**Commit:** e5fa84d
**Status:** fixed
**Applied fix:** Replaced `onboard_brand`'s loose return contract with an explicit `OnboardResult` `NamedTuple` (`brand`, `skip_mappings`) — preferred over a dunder attribute on the Pydantic model, per the review. When the operator declines to overwrite existing mappings, `onboard_brand` returns `OnboardResult(brand, skip_mappings=True)`; `main` honors it by keeping existing mappings (logs `[KEEP]`, marks `onboarded`) and skipping discovery/persist entirely, so the second overwrite prompt no longer reopens the D-06 idempotency gate.

### WR-05: `engine="auto"` stale-state hazard after `add_brand`

**Files modified:** `scripts/onboard_vtex_brands.py`
**Commit:** e5fa84d
**Status:** fixed
**Applied fix:** Added `svc.set_active(brand_key, False)` immediately after `add_brand`, before `detect_engine` reconfirmation. If the script aborts between `add_brand` and engine confirmation, the brand stays inactive rather than active with an unconfirmed `engine="auto"`. The brand is only re-activated at step 5 once `detect_engine` confirms `vtex`. This is fail-safe deactivation only — no manual `engine="vtex"` override is introduced, so D-11 is preserved.

## Skipped Issues

None — all in-scope (Critical + Warning) findings were fixed.

(Info findings IN-01 through IN-04 were out of scope under `fix_scope=critical_warning`. IN-01 requires no action; IN-02/IN-03/IN-04 are cosmetic/latent and deliberately left for manual discretion.)

## Verification

- `python -c "import ast; ast.parse(...)"` on both files → parse-ok.
- `python -m pytest tests/test_vtex_brand_onboarding_contract.py -q` → 6 passed.
- `python -m pytest tests/ -q` → 156 passed, 7 failed. The 7 failures
  (`test_brand_gate.py` x4, `test_model_discrimination.py` x2,
  `test_ocr_service.py::test_compare_image_texts`) are PRE-EXISTING and
  environment-driven (cv2 `cv2.dnn.DictValue` AttributeError under the local
  OpenCV/typing build, cascading via test-order state). Confirmed identical
  (156 passed / 7 failed) on the pristine committed baseline by stashing the
  fixes and re-running. They occur even in isolation and do not import any
  phase-26 module — NOT a regression introduced by these fixes. (The
  guardrail's reference baseline of "162 passed, 1 failed" reflects a
  different environment; relative to the actual local baseline, zero new
  failures were introduced.)
- `git diff --quiet -- services/category_mapping.py` → unchanged (D-07 preserved).
- Locked decisions preserved: no manual `engine="vtex"` override (D-11); no
  edit to `services/category_mapping.py` (D-07); `vtex_fq_path` kept relative;
  `CANONICAL_KEYWORDS` keys unchanged (still the 7 `_RAW_CATEGORIES` slugs, D-04).

---

_Fixed: 2026-06-19T14:55:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
