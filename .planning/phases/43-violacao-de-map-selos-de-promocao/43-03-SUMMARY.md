---
phase: 43-violacao-de-map-selos-de-promocao
plan: 03
subsystem: backend-search-export
tags: [search, export, marketplace, map, promotions]
requirements-completed: [MAP-01, PROMO-01]
completed: 2026-07-04
---

# Phase 43 Plan 03 Summary

MAP and promotions were wired into comparative search, cross-marketplace rows, and exports.

## Accomplishments

- Comparative search results now load active MAP rules once and merge evaluator metadata into each product.
- Cross-marketplace rows receive MAP metadata after seller/PDP enrichment and de-duplication.
- Canonical search exports gain Phase 43 columns only when MAP/promotion data is present, preserving legacy column contracts.
- Cross-marketplace exports gain optional Phase 43 columns only when submitted items include MAP/promotion fields.
- Low-cost promotion seams were added for engines that already compute discount evidence: VTEX, Shopify, Mercado Livre, and Zara parser output.
- Added integration tests for search response metadata, cross row metadata, search export columns, and cross export serialization.

## Verification

- `cd backend && python -m pytest tests/test_phase43_search_contract.py tests/test_export_search_contract.py tests/test_export_cross_marketplace.py tests/test_product_contract.py -x -q` -> 28 passed

## Deviations

- Promotion extraction remains best-effort and does not introduce new network passes. Engines without cheap badge/payment evidence safely return `promotions=[]`.
