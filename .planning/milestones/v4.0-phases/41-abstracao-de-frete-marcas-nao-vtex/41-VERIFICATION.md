---
phase: 41-abstracao-de-frete-marcas-nao-vtex
verified: 2026-07-02T01:39:39Z
status: automated_passed
score: automated must-haves verified
human_verification:
  - test: "Search Buckman/BCK with a valid CEP and inspect returned shipping options"
    expected: "At least one option from Shopify/Buckman appears; explicit free shipping is shown only when provider returns 0.0"
    why_human: "Requires running stack/browser to inspect UX"
  - test: "Search Richards with a valid CEP and inspect Wake shipping options"
    expected: "PAC/SEDEX-like Wake options appear with price and deadline"
    why_human: "Requires running stack/browser to inspect UX"
  - test: "VTEX on-demand shipping still works from existing VTEX button"
    expected: "/search/calculate-shipping-vtex path remains available and unchanged in UI behavior"
    why_human: "Requires running stack/browser and a VTEX product result"
---

# Phase 41: Verification Report

## Goal Achievement

Phase 41 delivered non-VTEX shipping abstraction and support for Shopify/Buckman and Wake/Richards, while keeping VTEX on the existing `VtexApiClient` path.

## Automated Evidence

| Area | Command | Result |
|------|---------|--------|
| Spike script | `python -m py_compile .planning/spikes/011-non-vtex-shipping/experiment.py` | pass |
| Live spike | `python .planning/spikes/011-non-vtex-shipping/experiment.py --provider all --write-report` | Shopify GO, Wake GO |
| Provider/backend focused | `cd backend && python -m pytest tests/test_shipping_resolver.py tests/test_shopify_shipping.py tests/test_wake_shipping.py tests/test_non_vtex_shipping_integration.py tests/test_non_vtex_shipping_route.py tests/test_vtex_api_client.py tests/test_vtex_shipping.py tests/test_search_shipping_contract.py -x -q` | 86 passed on 2026-07-02 |
| Full backend suite | `cd backend && python -m pytest tests/ -x -q` | 339 passed |
| Frontend build | `cd frontend && npm run build` | pass on 2026-07-02 |

## Must-Haves

- `backend/services/shipping/` exists with base, resolver, unsupported fallback, Shopify and Wake providers.
- Shopify/Buckman uses real Ajax Cart shipping rates.
- Wake/Richards uses real Storefront GraphQL `shippingQuotes`.
- VTEX is not routed through `BaseShipping`; existing VTEX route and tests remain green.
- SFCC/unknown engines remain unsupported, with no false free shipping.
- Inline search and on-demand route share the same providers.
- Frontend reuses existing `shipping_options` UI for VTEX, Shopify and Wake.

## Remaining Manual UAT

Run the app and verify one Buckman and one Richards product card with a valid CEP. The automated spike already verified the live provider endpoints, but visual UAT still needs the running frontend.

