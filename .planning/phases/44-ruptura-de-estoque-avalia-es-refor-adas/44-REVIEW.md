---
phase: 44-ruptura-de-estoque-avalia-es-refor-adas
reviewed: 2026-07-01T13:01:36Z
resolved: 2026-07-01T13:09:41Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - backend/services/stock_depth/vtex.py
  - backend/services/stock_depth_service.py
  - backend/services/review_service.py
  - backend/services/wake_token.py
  - backend/services/engines/wake_engine.py
  - backend/services/shipping/wake.py
  - backend/data/brands.json
  - backend/.env.example
  - .planning/debug/resolved/richards-sem-categorias.md
  - backend/tests/test_stock_depth_service.py
  - backend/tests/test_review_comments_service.py
  - backend/tests/test_wake_token.py
  - frontend/src/App.tsx
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
original_findings:
  critical: 2
  warning: 3
  info: 0
  total: 5
status: fixed
---

# Phase 44: Code Review Report

**Reviewed:** 2026-07-01T13:01:36Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** fixed

## Summary

Reviewed the focused UAT-fix files for the Aramis stock-depth and Trustvox review regressions. The initial review found 2 blockers and 3 warnings; all findings below were fixed in this turn and the remaining findings count is zero.

## Resolution Summary

- CR-01 fixed: stock-depth guard is now keyed by brand, with a cross-monitor regression test.
- CR-02 fixed in code: the committed Wake token was removed from `brands.json` and masked in the historical debug note; Wake search/shipping can resolve brand-specific tokens from env vars such as `WAKE_ACCESS_TOKEN_RICHARDS`. The exposed token still must be revoked/rotated outside the repo.
- WR-01 fixed: provider-specific stock-depth labels are preserved.
- WR-02 fixed: Trustvox opinion fetch returns structured success/failure, and products with summary count but failed/unparseable opinions remain `temporary_failure`.
- WR-03 fixed: service-level tests now cover Trustvox root summary plus `/widget/opinions`, and opinion failure behavior.

## Critical Issues

### CR-01: Stock-depth probe cap is bypassable across monitors

**Classification:** BLOCKER
**Resolution:** fixed
**File:** `backend/services/stock_depth_service.py:119`
**Issue:** `_enforce_probe_guard` keys the throttle/cap by `(brand_key, monitor_id)`, while the setting is explicitly `MAX_STOCK_DEPTH_PROBES_PER_BRAND`. A user can create or use multiple Aramis monitors and get a fresh counter for each one, bypassing the intended per-brand execution guard. This violates the Phase 44 controlled/on-demand probe limit and can multiply live VTEX requests.
**Fix:** Key the guard by brand only, or maintain both a per-brand cap and a separate per-monitor UI throttle if needed.

```python
def _enforce_probe_guard(brand_key: str, monitor_id: str) -> StockDepthResult | None:
    key = brand_key
    now = _now_monotonic()
    guard = _PROBE_GUARDS.get(key)
    ...
```

Add a test that probes two products under different monitor IDs for the same brand and asserts the second/third call still observes the brand-wide throttle/cap.

### CR-02: Hardcoded Wake access token is committed in brand data

**Classification:** BLOCKER
**Resolution:** fixed in code; token rotation required operationally
**File:** `backend/data/brands.json:415`
**Issue:** `wake_access_token` contains a literal token value. This is a credential in repository-managed configuration, so anyone with repo access or build artifacts can reuse it. Even if pre-existing, the reviewed file is in scope and this remains a security defect.
**Fix:** Revoke/rotate the exposed token, remove it from `brands.json`, and load it from an environment variable or local secrets file that is not committed.

```json
"wake_access_token": null
```

Then resolve the token at runtime from a configured secret source for the `richards` brand.

## Warnings

### WR-01: Product API stock estimates are mislabeled as cart-probe evidence

**Classification:** WARNING
**Resolution:** fixed
**File:** `backend/services/stock_depth_service.py:163`
**Issue:** `_normalize_result` preserves `stock_depth_source` but overwrites every provider label with `"maximo observado/estimativa via cart-probe"`. When `VtexStockDepthProvider` returns `source="vtex-product-api"` from `backend/services/stock_depth/vtex.py:159`, the persisted/UI label still says cart-probe. That misrepresents the evidence source and makes product-API estimates look like browser/cart probe results.
**Fix:** Preserve the provider label when present, and only use the generic label as a fallback.

```python
return StockDepthResult(
    stock_depth_estimate=estimate,
    stock_depth_state=state,
    stock_depth_checked_at=checked_at,
    stock_depth_source=result.stock_depth_source or "stock-depth-provider",
    stock_depth_label=result.stock_depth_label or _STOCK_DEPTH_LABEL,
)
```

Update `test_probe_scan_product_updates_only_matching_record` or add a product-API orchestration test to assert the persisted label/source pair stays consistent.

### WR-02: Trustvox opinion failures can be reported as successful empty reviews

**Classification:** WARNING
**Resolution:** fixed
**File:** `backend/services/review_service.py:438`
**Issue:** `_fetch_trustvox_comments` calls `/widget/opinions`, but `_fetch_trustvox_opinion_entries` returns `[]` for both "no opinions" and endpoint errors/non-200 responses. The caller then falls back to `/widget/root` parsing and returns `reviews_state="available"` at line 456 even when root only had summary data and the comments endpoint failed. For products with `review_count > 0`, this is a false success: the UI can show reviews as available without any fetched comments.
**Fix:** Return structured status from `_fetch_trustvox_opinion_entries` so the caller can distinguish empty pages from failures. If page 1 has `review_count > 0` and opinions failed or yielded no parseable entries, return `temporary_failure` instead of `available`.

```python
entries, opinions_ok = await _fetch_trustvox_opinion_entries(...)
if not opinions_ok:
    return ReviewCommentsResult(
        reviews_state=ReviewState.TEMPORARY_FAILURE,
        comments=[],
        rating=rating,
        review_count=review_count,
        review_product_id=product_id,
        source_provider="trustvox",
        max_pages=max_pages,
    )
```

Also avoid falling back to `_extract_comment_entries(data)` for Trustvox root unless there is verified evidence that root contains comment entries.

### WR-03: Tests do not cover the actual Trustvox root-plus-opinions regression path

**Classification:** WARNING
**Resolution:** fixed
**File:** `backend/tests/test_review_comments_service.py:184`
**Issue:** The added Trustvox test only normalizes a prebuilt opinion item. It does not exercise `_fetch_trustvox_comments`, does not assert that `/widget/opinions` is called, and does not cover the root-summary-only case that caused the UAT failure. As a result, the service can regress back to root-only behavior or false-success empty comments while this suite remains green.
**Fix:** Add an async service-level test with a fake `aiohttp.ClientSession` or mocked `_fetch_trustvox_opinion_entries` that verifies:

```python
# root returns summary count > 0
# opinions returns one author/date-only item
# result.reviews_state == "available"
# result.comments contains the normalized opinion
# persisted product uses "review_comments"
```

Add a second test where root has `rate.count > 0` but opinions fails/non-200, and assert the result is `temporary_failure` rather than `available` with `comments=[]`.

## Verification

- `cd backend; python -m pytest tests/test_stock_depth_service.py tests/test_review_comments_service.py tests/test_wake_token.py -q` -> 37 passed.
- `cd backend; python -m pytest -q` -> 463 passed, 1 existing warning.
- `cd frontend; npm run build` -> passed, with existing Vite chunk-size warning.
- Local live probe for monitor `05602c15-62d3-4fd0-bee4-a342002f5212`, product `74291`: stock-depth `estimated`, estimate `100`, source `vtex-product-api`; reviews `available`, rating `5.0`, count `3`, comments `3`.

---

_Reviewed: 2026-07-01T13:01:36Z_
_Reviewer: Codex (gsd-code-reviewer)_
_Depth: standard_
