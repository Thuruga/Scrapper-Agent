---
phase: 41-abstracao-de-frete-marcas-nao-vtex
plan: 02
subsystem: backend
tags: [shipping, shopify, wake, providers, pytest]

provides:
  - "backend/services/shipping package with BaseShipping, resolver and providers"
  - "ShopifyShipping using Ajax Cart prepare/async shipping rates"
  - "WakeShipping using Storefront GraphQL shippingQuotes"
  - "Inline shipping wired into ShopifyEngine and WakeEngine"
  - "Non-VTEX shipping identity fields on SearchProductResult"

requirements-completed: [FRET-07]
completed: 2026-06-29T21:55:00Z
---

# Phase 41 Plan 02: Backend Shipping Providers Summary

Implemented the non-VTEX backend shipping layer without moving VTEX out of `VtexApiClient`.

## Accomplishments

- Added `backend/services/shipping/`:
  - `base.py` with `ShippingCalculation`, states, URL/domain guard and `apply_shipping_calculation`.
  - `resolver.py` mapping Shopify/Wake to real providers and VTEX/SFCC/unknown to unsupported.
  - `shopify.py` using product `.json`, cart add, prepare rates and async rates.
  - `wake.py` using Wake product identity and `shippingQuotes`.
  - `unsupported.py` preserving explicit unsupported state.
- Added additive non-VTEX identity fields to `SearchProductResult`: `shipping_product_id`, `shipping_variant_id`, `shipping_sku`.
- Wired inline shipping into `ShopifyEngine.search` and `WakeEngine.search` only when `include_shipping=true` and CEP exists.
- Updated the old Wake test expectation from `None` to explicit non-free state for invalid product identity.

## Verification

```powershell
cd backend
python -m pytest tests/test_shipping_resolver.py tests/test_shopify_shipping.py tests/test_wake_shipping.py tests/test_non_vtex_shipping_integration.py -x -q
python -m pytest tests/test_wake_engine.py -q
```

Result: 15 focused provider tests passed; 27 Wake regression tests passed.

