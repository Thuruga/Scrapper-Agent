# Phase 33: Frete via Checkout nos Sites VTEX - Research

**Researched:** 2026-06-24
**Requirement:** FRET-05
**Status:** Complete

## Executive Summary

The repository already has a working VTEX cart-simulation call and five characterization tests. The phase is not a greenfield integration: it is a contract expansion and reliability pass around `VtexApiClient._fetch_shipping`.

The recommended shape is to keep the existing internal `VtexApiClient` path, add a pure SLA parser, expose all valid home-delivery options through an additive `shipping_options` field, and preserve the legacy primary `shipping`/`shipping_price` fields using the cheapest valid option. This avoids breaking existing consumers while allowing the UI to render every delivery option.

The main hidden gaps are:

1. `_fetch_shipping` currently chooses one cheapest SLA without filtering pickup.
2. The request hardcodes seller `"1"` even though VTEX requires the seller responsible for the selected SKU.
3. The result model has only one `ShippingInfo` and no explicit list of options.
4. All failures collapse into `Indisponível`, so a valid “no delivery for this CEP” response cannot be distinguished from a timeout.
5. `DEFAULT_CEP` exists only in backend settings; the frontend has no safe way to display it.
6. The UI can render one quote but not a list, and it currently labels every parsed estimate as generic days.

## Official VTEX Contract

### Cart simulation request

`POST /api/checkout/pub/orderForms/simulation` accepts an `items` array with SKU `id`, `quantity`, and `seller`, plus `country` and `postalCode`. The official schema states that this public endpoint does not require authentication.

The seller ID is required by contract. The search path should therefore select a SKU and seller from the same available commercial offer and pass both to simulation; hardcoding seller `"1"` is only a fallback for legacy first-party catalogs.

### Cart simulation response

The useful path is `logisticsInfo[].slas[]`. Each SLA can contain:

- `deliveryChannel`: use exact value `delivery` for home delivery; exclude `pickup-in-point`.
- `price` and `listPrice`: integer values in cents.
- `shippingEstimate`: number plus unit.
- `name` / `id`: displayable service identity.
- `pickupStoreInfo.isPickupStore` and `pickupPointId`: defensive pickup signals.

The official orderForm documentation lists four estimate units: `m` (minutes), `h` (hours), `bd` (business days), and `d` (days). The user decision “Até X dias úteis” is exact for `bd`. Other official units must be rendered faithfully (`Até X dias`, `Até X horas`, `Até X minutos`) rather than mislabeled as business days.

### Pickup filtering

Primary rule: retain only SLAs whose `deliveryChannel == "delivery"`.

Defensive exclusion when payloads are incomplete:

- exclude when `pickupStoreInfo.isPickupStore is true`;
- exclude when `pickupPointId` is non-empty;
- never infer “free shipping” from a zero-priced pickup SLA.

### Response states

Recommended state matrix:

| Condition | Product remains? | Retry? | User state |
|-----------|------------------|--------|------------|
| 200 with one or more valid delivery SLAs | Yes | No | Options available |
| 200 with no valid home-delivery SLA | Yes | No | `Entrega indisponível para este CEP` |
| Timeout, connection error, 408, 429, or 5xx | Yes | Once | `Frete temporariamente indisponível` after second failure |
| Non-retryable malformed/4xx response | Yes | No | Temporary-unavailable state with diagnostic logging |
| Mixed valid and malformed SLAs | Yes | No | Keep valid options, discard malformed entries |

Do not retry a valid 200 response with no delivery: that is a business result, not a transient transport failure.

## Recommended Data Contract

Use an additive contract to avoid breaking current consumers:

- Extend `ShippingInfo` with service identity and parsed estimate metadata, or introduce a dedicated `ShippingOption` model.
- Add `shipping_options: List[ShippingInfo] = []` to `SearchProductResult` (and only add it to `RawProductBronze` if category/bulk output actually needs it).
- Preserve `shipping` as the primary cheapest option when options exist.
- Preserve `shipping_price` and `is_free_shipping` from the primary option to satisfy FRET-05 and existing export/history consumers.
- For errors/no-delivery, keep `shipping_options=[]` and put the explicit state in the existing `shipping.status` or an additive product-level status field.
- Do not remove `landed_price` globally in this phase. The Phase 33 VTEX UI must simply not display or use the sum; global SKU/marketplace standardization is deferred.

Recommended pure helpers in `backend/services/vtex_shipping.py` (exact names are planner discretion):

- parse one `shippingEstimate` into numeric value, unit, sortable duration, and display text;
- parse/filter/sort `logisticsInfo[].slas` into canonical options;
- select a shipping candidate `(sku_id, seller_id)` from VTEX search items;
- classify the simulation result into available, unavailable-for-CEP, or temporary failure.

Pure helpers keep unit conversion, pickup filtering, estimate parsing, ordering, and malformed-entry handling deterministic and easy to test without HTTP.

## Existing Code Integration

### Backend

- `backend/services/vtex_api_scraper.py:431-470` already posts cart simulation, converts cents with `/ 100`, and stores a single `ShippingInfo`.
- `backend/services/vtex_api_scraper.py:758-810` selects `items[0].itemId`, scans sellers for price, then schedules `_fetch_shipping`; it should select SKU and seller together.
- `backend/services/engines/vtex_engine.py` already delegates search to `VtexApiClient` with `zipcode` and `include_shipping`. Keep `calculate_shipping()` untouched as required by the architectural decision.
- `backend/core/models.py` already carries `shipping`, `shipping_price`, `is_free_shipping`, and `landed_price`; the multiple-option contract should be additive.
- `backend/config.py` already defines `DEFAULT_CEP` but no frontend endpoint exposes it. A small authenticated/read-only search-config endpoint is the cleanest source for a visible default.
- `backend/api/routes_search.py` already validates CEP shape and serializes search results.

### Frontend

- `frontend/src/stores/searchStore.ts` is module-scoped and intentionally non-persistent, which matches “remember during the session, reset on reload.” Add an initialization flag so a late config fetch never overwrites a user-edited CEP.
- `frontend/src/App.tsx` currently sends shipping only when the CEP has eight digits and renders one `shipping` object.
- Add an `ApiClient` method to load the non-sensitive search configuration, initialize the search CEP once, and block submit/export when the edited CEP is incomplete.
- Render `shipping_options` in price order; fall back to legacy `shipping` for old history records.
- Keep product price and freight visually separate. Do not render the `landed_price` sum in the VTEX brand-search surface.

### Compatibility

History files may contain old results without `shipping_options`; frontend fallback is mandatory. Existing marketplace/SKU flows use flat `shipping_price` fields and must not be changed by this phase.

## Retry and Concurrency

Use exactly two total attempts for transient failures (initial call plus one retry), isolated inside each product quote. Retry only network/timeout errors and explicitly retryable HTTP statuses. Keep the existing per-client semaphore so the second attempt does not bypass concurrency limits.

The delay can be short and deterministic (for example 250–500 ms) because the user asked for one retry, not a general exponential-retry subsystem. Inject or patch the sleep in tests.

`asyncio.gather` already isolates scheduling at the batch level only if `_fetch_shipping` absorbs its own errors. Preserve that behavior: no quote exception may escape and cancel sibling products.

## Security Threat Model Notes

- **SSRF boundary:** build the simulation URL only from the persisted VTEX brand domain already selected by `brand_service`; do not accept an arbitrary checkout host from the request body.
- **Input validation:** normalize CEP to eight digits and rely on the existing Pydantic pattern at the API boundary. Do not interpolate CEP into a URL; send it only in JSON.
- **Logging/privacy:** do not log full simulation payloads or user-entered CEPs at info/error level. Diagnostic logs may include brand key, HTTP status, and attempt count.
- **Response trust:** validate SLA types, non-negative integer cents, recognized estimate format, and delivery channel before constructing Pydantic models.
- **Availability:** bound timeout, retry count, response parsing, and concurrency so a failing store cannot stall the whole search.

No new authentication secret or database schema is required.

## Pitfalls to Avoid

1. Choosing `min(price)` before filtering pickup can produce a false “Frete Grátis”.
2. Hardcoding seller `"1"` can make simulation fail when the selected SKU offer belongs to another seller.
3. Treating `0` as missing destroys free-shipping semantics; use explicit `is None` checks.
4. Labeling `d`, `h`, or `m` as business days is incorrect according to VTEX's official unit contract.
5. Retrying a valid empty-SLA response wastes time and misclassifies a business result as an outage.
6. Replacing the existing `shipping` field outright would break old history and current UI consumers; use additive evolution.
7. Removing `landed_price` globally would spill into the deferred SKU/marketplace standardization.
8. A config fetch that writes CEP after the user has typed can clobber their input; initialize once only.

## Validation Architecture

### Test layers

| Layer | Scope | Command |
|-------|-------|---------|
| Pure unit | SLA filtering, cents→reais, four estimate units, ordering, malformed entries | `python -m pytest backend/tests/test_vtex_shipping.py -q` |
| Client characterization | request payload SKU+seller, retry matrix, response states, sibling isolation | `python -m pytest backend/tests/test_vtex_api_client.py -q` |
| API contract | default CEP endpoint and search serialization | `python -m pytest backend/tests/test_search_shipping_contract.py -q` |
| Backend regression | all backend tests | `python -m pytest backend/tests -q` |
| Frontend static | TypeScript and production build | `npm run build --prefix frontend` |
| Frontend lint | changed React/store/client code | `npm run lint --prefix frontend` |

### Required deterministic cases

1. Two delivery SLAs plus one free pickup: output contains only the two delivery SLAs.
2. Prices `3990` and `1990`: output is ordered `19.90`, `39.90`; both are below the R$1,000 unit-regression threshold.
3. Free delivery plus paid express: both remain; free is first and `is_free_shipping=true`.
4. `5bd`, `2d`, `12h`, and `30m`: display preserves each official unit.
5. Timeout then success: exactly two calls, no error state.
6. Timeout twice: product remains with temporary-unavailable status.
7. 200 with only pickup/no delivery: unavailable-for-CEP status, no retry.
8. One malformed and one valid SLA: valid option survives.
9. Search result with no `shipping_options` still renders legacy history safely.
10. Edited CEP is not overwritten by delayed default-config response.

### Wave gates

- Backend contract/parser tests must be green before wiring UI rendering.
- Existing baseline `backend/tests/test_vtex_api_client.py` must remain green throughout (current baseline: 5 passed).
- Final phase gate runs backend regression, frontend build/lint, and a live smoke against at least one onboarded VTEX brand using a non-sensitive test CEP.

### Manual/live verification

Live checkout responses are store- and CEP-dependent, so deterministic tests must use fixtures/fakes. The live smoke verifies only integration shape: at least one product returns one or more home-delivery options, pickup is absent, cents are converted, and a failed store does not break other results.

## Suggested Plan Decomposition

1. **Backend shipping contract and parser:** additive models, pure parsing, SKU+seller selection, retry/state semantics, unit/range tests.
2. **API/default CEP wiring:** expose visible default configuration and verify serialized multi-option results.
3. **Frontend experience:** one-time session initialization, blocking CEP validation, all-option rendering, legacy-history fallback, and separate product/freight presentation.

Plans 1 and 2 can share Wave 1 only if they modify disjoint files; the frontend plan depends on the finalized backend contract.

## Sources

- [VTEX Checkout API OpenAPI schema](https://github.com/vtex/openapi-schemas/blob/master/VTEX%20-%20Checkout%20API.json) — cart simulation request/response, cents, SLAs, delivery channels, pickup fields.
- [VTEX orderForm fields](https://developers.vtex.com/docs/guides/orderform-fields) — estimate units (`m`, `h`, `bd`, `d`) and logistics field semantics.
- [Adding shipping address and delivery options](https://developers.vtex.com/docs/guides/add-shipping-address-and-delivery-option-to-the-cart) — delivery vs. pickup channel selection and checkout error examples.
- `backend/services/vtex_api_scraper.py`, `backend/core/models.py`, `backend/api/routes_search.py`, `frontend/src/App.tsx`, and `frontend/src/stores/searchStore.ts` — current repository contract and integration seams.

---

*Research complete: 2026-06-24*
