---
phase: 41
slug: abstracao-de-frete-marcas-nao-vtex
status: verified
threats_open: 0
asvs_level: 1
created: 2026-07-02
verified: 2026-07-02
---

# Phase 41 - Security

Phase 41 introduced non-VTEX shipping providers for Shopify/Buckman and Wake/Richards while keeping VTEX on the existing `VtexApiClient` path. The plan-time threat register was reviewed against the implementation and focused tests on 2026-07-02.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Browser -> API | User triggers inline or on-demand shipping calculation. | Brand key, product URL, CEP. |
| API -> persisted brand config | Shipping route resolves the trusted brand/domain from storage. | Brand metadata, engine, domain, Wake token override. |
| API/providers -> external storefronts | Shopify Ajax Cart and Wake Storefront GraphQL calls. | Product identity, CEP, bounded request payloads. |
| Non-VTEX resolver -> legacy VTEX path | Resolver must not route VTEX through `BaseShipping`. | Engine selection and unsupported states. |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-41-01 | Denial of Service | Shopify/Wake live probes | mitigate | Spike uses one product at a time; Shopify provider uses 15s request timeout, five bounded async-rate polls, and cart cleanup. | closed |
| T-41-02 | Information Disclosure | Spike output/logging | mitigate | Provider warnings log brand/status only, not CEP or full payload; spike report records signatures/options instead of private credentials. | closed |
| T-41-03 | Authorization boundary | Wake quote endpoint | mitigate | Wake provider uses stored/public storefront token path only; missing token returns unsupported instead of private fallback. | closed |
| T-41-04 | Data integrity | Spike verdict criteria | mitigate | GO evidence requires real price/options; `apply_shipping_calculation` only marks free shipping for explicit 0.0/free provider result. | closed |
| T-41-05 | SSRF | Provider product URL | mitigate | `is_url_allowed_for_brand` requires product URL host to match the persisted brand domain or subdomain before provider calls. | closed |
| T-41-06 | Information Disclosure | Provider logging | mitigate | Shopify/Wake exception logs include brand key and exception type, not CEP or raw provider payload. | closed |
| T-41-07 | Denial of Service | Inline freight fan-out | mitigate | Inline shipping runs only when `include_shipping` and CEP are present; Shopify/Wake populate with semaphore concurrency 3 and provider timeouts. | closed |
| T-41-08 | Tampering/Data Integrity | Rate normalization | mitigate | Prices parse to `float | None`, options are sorted deterministically, and unavailable/unsupported states never become free shipping. | closed |
| T-41-09 | Regression | VTEX path | mitigate | Resolver returns unsupported for VTEX; `/search/calculate-shipping-vtex` remains registered and covered by regression tests. | closed |
| T-41-10 | SSRF | `/calculate-shipping-brand` product URL | mitigate | Route resolves brand from storage and rejects host mismatch before calling the provider; route test asserts provider is not called. | closed |
| T-41-11 | Information Disclosure | API logs/errors | mitigate | Route returns client-safe errors; provider logs avoid CEP and raw payload. | closed |
| T-41-12 | Data integrity | Unsupported UI state | mitigate | Backend returns `is_free_shipping=false` for unsupported/temporary states; frontend uses the shared `shipping_options` renderer. | closed |
| T-41-13 | Regression | VTEX endpoint | mitigate | VTEX endpoint remains separate; focused VTEX/search contract tests passed on 2026-07-02. | closed |
| T-41-14 | UX confusion | Mixed product/freight price | mitigate | Freight remains separate in `shipping_options`, `shipping_price`, and `landed_price`; no mandatory total-price override was introduced. | closed |

---

## Accepted Risks Log

No accepted risks.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-07-02 | 14 | 14 | 0 | Codex |

## Verification Evidence

| Area | Evidence |
|------|----------|
| URL/domain guard | `backend/services/shipping/base.py::is_url_allowed_for_brand`; `backend/api/routes_search.py::calculate_shipping_brand`; `backend/tests/test_non_vtex_shipping_route.py::test_calculate_shipping_brand_rejects_host_mismatch_before_provider`. |
| Non-free failure states | `backend/services/shipping/base.py::apply_shipping_calculation`; `backend/tests/test_non_vtex_shipping_integration.py`. |
| Resolver/VTEX boundary | `backend/services/shipping/resolver.py`; `backend/tests/test_shipping_resolver.py`; `backend/tests/test_non_vtex_shipping_route.py::test_existing_vtex_endpoint_still_registered`. |
| Provider DoS bounds | Shopify/Wake provider timeouts; inline populate semaphores in `shopify_engine.py` and `wake_engine.py`. |
| Current verification run | `cd backend && python -m pytest tests/test_shipping_resolver.py tests/test_shopify_shipping.py tests/test_wake_shipping.py tests/test_non_vtex_shipping_integration.py tests/test_non_vtex_shipping_route.py tests/test_vtex_api_client.py tests/test_vtex_shipping.py tests/test_search_shipping_contract.py -x -q` -> 86 passed; `cd frontend && npm run build` -> passed. |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-07-02
