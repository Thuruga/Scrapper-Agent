---
phase: 43-violacao-de-map-selos-de-promocao
verified: 2026-07-04T00:00:00Z
status: passed_code
score: 4/4 plans + convergence fix automated-verification passed
manual_uat: pending
---

# Phase 43 Verification Report

## Goal Achievement

Phase 43 is implemented at the code and automated-test level:

- Operators can manage MAP rules through protected `/map-rules` CRUD endpoints and the search/monitoring work surfaces, not only Settings.
- The MAP rule form is segmented by rule model: brand, category-by-brand, and product by code/URL.
- MAP verdicts use effective advertised product price, not full/riscado price.
- Rule precedence is centralized as product > category > brand.
- Comparative search and cross-marketplace result rows surface additive MAP metadata.
- Product monitors evaluate MAP on each successful check and expose alerts in the monitor row/history payload.
- Category monitors evaluate MAP during scans, store product-level metadata, re-evaluate on read, and persist the last violation count for list-level alerting.
- Promotion data is additive as `promotions=[]` by default, with structured parser support and low-cost discount-derived seams in engines that already expose price discount evidence.
- Search and cross-marketplace exports preserve legacy contracts when Phase 43 data is absent and add columns only when present.

## Automated Verification

- `cd backend && python -m pytest tests/test_map_rules_service.py tests/test_map_evaluator_service.py -x -q` -> 14 passed
- `cd backend && python -m pytest tests/test_map_rules_routes.py -x -q` -> 4 passed
- `cd backend && python -m pytest tests/test_phase43_search_contract.py tests/test_export_search_contract.py tests/test_export_cross_marketplace.py tests/test_product_contract.py -x -q` -> 28 passed
- `python -m pytest backend/tests/test_price_monitor.py backend/tests/test_category_monitor.py backend/tests/test_map_evaluator_service.py backend/tests/test_map_rules_service.py` -> 24 passed
- `python -m pytest backend/tests/test_export_search_contract.py backend/tests/test_phase43_search_contract.py` -> 9 passed
- `python -m pytest backend/tests` -> 554 passed, 1 warning
- `cd frontend && npm run build` -> succeeded

## Notes

- The full backend-suite warning was a runtime warning about an unawaited coroutine reported from an existing test path; the suite still passed.
- Manual UI UAT was not performed in this execution turn. Recommended checks: create/edit/delete a MAP rule in search, SKU, and monitor tabs; run searches/monitor scans that violate it; confirm badges, category counters, and export columns are readable.
