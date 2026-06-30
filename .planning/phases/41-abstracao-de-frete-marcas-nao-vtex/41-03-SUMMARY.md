---
phase: 41-abstracao-de-frete-marcas-nao-vtex
plan: 03
subsystem: api-frontend
tags: [shipping, fastapi, react, on-demand]

provides:
  - "POST /search/calculate-shipping-brand for non-VTEX on-demand shipping"
  - "Frontend ApiClient.calculateShippingBrand"
  - "Search UI supports Wake/Shopify on-demand shipping with existing shipping_options renderer"

requirements-completed: [FRET-07]
completed: 2026-06-29T22:00:00Z
---

# Phase 41 Plan 03: On-Demand API and UI Summary

Added on-demand non-VTEX shipping while preserving `/search/calculate-shipping-vtex`.

## Accomplishments

- Added `CalculateBrandShippingRequest` and `CalculateBrandShippingResponse`.
- Added `POST /search/calculate-shipping-brand`:
  - rejects unknown brands;
  - rejects VTEX and directs callers to the VTEX endpoint;
  - validates product URL host against the persisted brand domain before provider calls;
  - returns `state`, `shipping_options`, primary `shipping`, `shipping_price`, `is_free_shipping` and `message`.
- Added frontend `ApiClient.calculateShippingBrand`.
- Updated Search UI:
  - "Calcular frete de todos" includes VTEX with SKU plus Wake/Shopify products;
  - product-level button uses VTEX endpoint for VTEX and brand endpoint for Wake/Shopify;
  - existing multi-option renderer remains the single UI path;
  - unsupported/temporary states never display as free shipping.

## Verification

```powershell
cd backend
python -m pytest tests/test_non_vtex_shipping_route.py tests/test_search_shipping_contract.py -x -q
cd ..\frontend
npm run build
```

Result: 15 route/contract tests passed; frontend build passed.

