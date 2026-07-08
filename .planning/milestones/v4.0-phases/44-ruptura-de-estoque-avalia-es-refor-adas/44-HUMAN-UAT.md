---
status: complete
phase: 44-ruptura-de-estoque-avalia-es-refor-adas
source: [44-VERIFICATION.md]
started: 2026-06-30T20:50:16.9007969-03:00
updated: 2026-07-01T09:59:58.6355093-03:00
---

## Current Test

[retest stock-depth and review comment actions after UAT fix]

## Tests

### 1. Monitor Modal Stock Summary

expected: Verified, unknown, out-of-stock, and rupture percentage appear when a persisted summary exists; if summary is missing/404, products still show.
result: passed - user confirmed the first flow worked.

### 2. Live Stock-Depth Cart-Probe

expected: Only one selected persisted scan product is probed and updated; result label identifies the provider evidence source; failures/block/unsupported do not become quantity zero; normal search remains untouched.
result: passed via local live probe; pending user visual retest. Aramis product `74291` returned `stock_depth_state='estimated'`, `stock_depth_estimate=100`, `stock_depth_source='vtex-product-api'`, and label `Estimativa pelo AvailableQuantity da VTEX API publica.`.

### 3. Live Review Comment Provider

expected: Supported provider returns compact comments or an explicit temporary failure; unsupported brand returns `reviews_state='unsupported'`; normal search stays rating/review_count only.
result: passed via local live probe; pending user visual retest. Aramis product `74291` returned `reviews_state='available'`, rating `5.0`, `review_count=3`, and 3 Trustvox opinion entries.

## Summary

total: 3
passed: 3
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

### 2026-06-30 Stock-Depth and Review Actions UAT Feedback

status: fixed_pending_retest
symptoms: Stock-depth returned browser-visible 400 errors for repeated/guarded probe attempts; review actions returned 200 but the modal did not clearly surface `temporary_failure`/persisted `review_comments`.
fix: Stock-depth throttle/limit now returns persisted `blocked` state instead of HTTP 400, and the modal renders persisted `review_comments` plus state-specific feedback for stock-depth and reviews.
verification: `cd backend; python -m pytest tests/ -q` -> 454 passed, 1 existing warning; `cd frontend; npm run build` -> passed with existing Vite chunk warning.

### 2026-07-01 Stock Quantity and Trustvox Collection UAT Feedback

status: fixed_pending_user_visual_retest
symptoms: User retest showed product cards still rendering `Profundidade: - (falha temporaria)` and `Avaliacoes: 0 (falha temporaria)` after the first flow succeeded.
root_cause: VTEX stock-depth depended on rendered PDP scripts and missed Aramis' public product API `AvailableQuantity`; Aramis Trustvox configuration used stale `store_id=78800`, while the live PDP publishes `store_id=114327`, and Trustvox comments are returned by `/widget/opinions` rather than the summary-only root payload.
fix: VTEX stock-depth now probes the public product API by product id before falling back to browser probing; Aramis Trustvox config uses store `114327`; Trustvox reviews fetch opinion items and normalize nested `user.name`; UI renders author/date for ratings that do not include free text.
verification: `cd backend; python -m pytest tests/test_stock_depth_service.py tests/test_review_comments_service.py tests/test_wake_token.py -q` -> 37 passed; `cd backend; python -m pytest -q` -> 463 passed, 1 existing warning; `cd frontend; npm run build` -> passed with existing Vite chunk warning; local live probe updated the reported Aramis card to stock estimate 100 and 3 Trustvox reviews.
