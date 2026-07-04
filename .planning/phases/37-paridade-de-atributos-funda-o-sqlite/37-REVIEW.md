---
phase: 37-paridade-de-atributos-fundacao-sqlite
reviewed: 2026-07-03T14:20:19Z
status: passed
depth: standard
files_reviewed: 10
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
---

# Phase 37 Code Review

## Summary

Re-reviewed Phase 37 after applying the two previously reported export/parity fixes. The comparative export now preserves sparse search-card rows when PDP enrichment is partial or absent, and Shopify PDP mapping now emits a truthful category value or leaves it blank.

## Findings

No remaining Critical, Warning, or Info findings were identified in the Phase 37 surface after the fixes and regression pass.

## Fixes Verified

- `backend/api/routes_search.py` now seeds each export row from the original `SearchProductResult` payload and layers PDP enrichment only when it adds meaningful fields, preserving Wake and marketplace rows even when `get_product_details()` returns `None` or seller-only data.
- `backend/services/shopify_api_client.py` now uses `product_type` for Shopify PDP category mapping and leaves `category` as `None` when Shopify does not expose a truthful source value.
- `backend/tests/test_export_search_contract.py` now covers partial and missing PDP enrichment so sparse comparative rows cannot silently disappear again.
- `backend/tests/test_shopify_variation_stock.py` now locks both the truthful `product_type` path and the blank-category fallback for Shopify PDP fetches.

## Verification

- `python -m pytest tests/test_export_search_contract.py -q` -> 4 passed
- `python -m pytest tests/test_shopify_variation_stock.py -q` -> 6 passed
- `python -m pytest tests/test_product_contract.py tests/test_phase37_engine_contract.py tests/test_export_search_contract.py tests/test_shopify_variation_stock.py -q` -> 19 passed
- `python -m pytest -q` -> 527 passed, 1 existing warning

## Residual Risk

- The backend test suite still reports one pre-existing runtime warning in `backend/tests/test_sfcc_lacoste_search.py` about an unawaited `PriceMonitorService._monitor_loop` coroutine. It is unrelated to Phase 37 but remains worth cleaning up.
