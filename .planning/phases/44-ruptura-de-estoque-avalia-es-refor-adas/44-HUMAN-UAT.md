---
status: partial
phase: 44-ruptura-de-estoque-avalia-es-refor-adas
source: [44-VERIFICATION.md]
started: 2026-06-30T20:50:16.9007969-03:00
updated: 2026-06-30T21:10:58.9195044-03:00
---

## Current Test

[retest stock-depth and review comment actions after UAT fix]

## Tests

### 1. Monitor Modal Stock Summary

expected: Verified, unknown, out-of-stock, and rupture percentage appear when a persisted summary exists; if summary is missing/404, products still show.
result: passed - user confirmed the first flow worked.

### 2. Live Stock-Depth Cart-Probe

expected: Only one selected persisted scan product is probed and updated; result label is `maximo observado/estimativa via cart-probe`; failures/block/unsupported do not become quantity zero; normal search remains untouched.
result: [pending retest after fix]

### 3. Live Review Comment Provider

expected: Supported provider returns compact comments or an explicit temporary failure; unsupported brand returns `reviews_state='unsupported'`; normal search stays rating/review_count only.
result: [pending retest after fix]

## Summary

total: 3
passed: 1
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps

### 2026-06-30 Stock-Depth and Review Actions UAT Feedback

status: fixed_pending_retest
symptoms: Stock-depth returned browser-visible 400 errors for repeated/guarded probe attempts; review actions returned 200 but the modal did not clearly surface `temporary_failure`/persisted `review_comments`.
fix: Stock-depth throttle/limit now returns persisted `blocked` state instead of HTTP 400, and the modal renders persisted `review_comments` plus state-specific feedback for stock-depth and reviews.
verification: `cd backend; python -m pytest tests/ -q` -> 454 passed, 1 existing warning; `cd frontend; npm run build` -> passed with existing Vite chunk warning.
