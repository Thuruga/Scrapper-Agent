---
phase: 33-frete-via-checkout-nos-sites-vtex
verified: 2026-06-26T14:00:00Z
status: passed
score: 18/18 must-haves verified
overrides_applied: 0
human_verification_confirmed: "All 8 items below were confirmed via 33-HUMAN-UAT.md (8/8 passed, operator confirmed 2026-06-26)."
human_verification:
  - test: "Default CEP is visible in the field on page load and editable"
    expected: "Field shows the DEFAULT_CEP from backend (e.g. '01415-000'), can be cleared/edited, resets to default on page reload"
    why_human: "Requires a running stack; cannot verify live HTTP initialization via grep"
  - test: "Editing CEP to fewer than 8 digits blocks Comparar and Excel"
    expected: "Inline error 'Informe um CEP válido com 8 dígitos.' appears with AlertTriangle icon, focus moves to CEP field, neither request is sent"
    why_human: "Browser interaction and focus behavior cannot be verified via static analysis"
  - test: "A late getSearchConfig response never overwrites a user-edited CEP"
    expected: "If user edits CEP while config is loading (simulate with network throttle), the edit is preserved and the config result is discarded"
    why_human: "Race condition with async network request; requires DevTools throttling"
  - test: "VTEX brand search returns >=1 home-delivery option with correct price/estimate"
    expected: "Truck header + 'Entrega para {CEP}', at least one option row with price in reais (e.g. R$ 19,90) and estimate (e.g. Até 5 dias úteis); pickup options absent"
    why_human: "Requires live VTEX checkout simulation against an onboarded brand"
  - test: "Free shipping option shows 'Frete Grátis' (green, CheckCircle2) alongside paid alternatives"
    expected: "Free option renders with CheckCircle2 and green '--success' color, not 'R$ 0,00'; paid options show R$ X,XX with tabular-nums"
    why_human: "Requires a brand/CEP combination that actually returns a free SLA"
  - test: "No-delivery CEP shows 'Entrega indisponível para este CEP' (muted, not red)"
    expected: "MapPin icon + muted text color (--text-muted), NOT red/--error"
    why_human: "Requires a CEP that yields a valid 200 with zero delivery SLAs from VTEX"
  - test: "Failed simulation shows 'Frete temporariamente indisponível' (amber AlertTriangle)"
    expected: "AlertTriangle with --warning color; the product card remains usable; other products unaffected"
    why_human: "Requires simulating a transport failure (e.g. network block for one brand)"
  - test: "Old history records (no shipping_options) render via legacy fallback without crashing"
    expected: "History items from before Phase 33 show the legacy p.shipping block (single shipping row), not an error or blank"
    why_human: "Requires history data predating this phase in the running application"
---

# Phase 33: Frete via Checkout nos Sites VTEX — Verification Report

**Phase Goal:** Deliver VTEX checkout-based shipping — fetch real freight options via the VTEX checkout simulation API, surface them in the search results UI, and expose a configurable default CEP.
**Verified:** 2026-06-26T14:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Roadmap Success Criteria

The ROADMAP.md defines three success criteria for Phase 33 (FRET-05):

1. A search on any onboarded VTEX brand returns `shipping_cost` in reais (not centavos) and `shipping_time` — fields that are currently empty/null.
2. When shipping is free, `is_free_shipping` is `true` and `shipping_cost` is `0.0` — distinguishable from an uncalculated shipping (which stays null, not `0.0`).
3. The unit contract (centavos→reais, divide by 100) is documented in the VTEX shipping path and covered by at least one range test that detects unit regression (e.g. value above R$1,000 without free shipping is suspicious).

### Observable Truths

#### Wave 1 (Plan 33-01) — Pure Parser + Model Contract

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | VTEX-only boundary: no SFCC/Wake/Shopify path touches vtex_shipping.py (D-03) | VERIFIED | `vtex_shipping.py` docstring explicitly states "Escopo: somente sites de marca VTEX (D-03)"; no SFCC/Wake/Shopify imports or references found |
| 2 | Pickup/retirada SLAs excluded; only `deliveryChannel=='delivery'` survives (D-09) | VERIFIED | `filter_and_sort_slas` lines 121-131 of `vtex_shipping.py` filters `channel != 'delivery'`, `isPickupStore is True`, and non-empty `pickupPointId` |
| 3 | Cents→reais via /100; `0.0` is free, `None` is not-calculated — never interchangeable (D-02) | VERIFIED | `price_reais = raw_price / 100` at line 162; `is_free = price_reais == 0.0` explicit check; test `test_free_shipping_null_contract` at line 223 asserts this distinction |
| 4 | All four estimate units (bd/d/h/m) parsed and rendered faithfully (D-11) | VERIFIED | `_UNIT_CONFIG` and `parse_estimate` produce exact PT strings; test file lines 30-42 assert `"Até 5 dias úteis"`, `"Até 2 dias"`, `"Até 12 horas"`, `"Até 30 minutos"` |
| 5 | Valid delivery options ordered by price asc, then estimate duration asc (D-10) | VERIFIED | `valid_options.sort(key=lambda o: (o["price_reais"], o["estimate_sort_seconds"]))` at line 176 |
| 6 | Free option alongside paid alternatives, flagged `is_free_shipping` (D-12) | VERIFIED | Tested in `test_free_and_paid_coexistence`; `is_free_shipping=True` in the normalized dict |
| 7 | Malformed SLA entries discarded individually; valid options survive (D-16) | VERIFIED | Each guard in `filter_and_sort_slas` uses `continue` individually; test `test_malformed_entries_discarded` covers valid+malformed input |
| 8 | `SearchProductResult` exposes `shipping_options: List[ShippingInfo]` additively; `shipping`/`shipping_price`/`is_free_shipping`/`landed_price` preserved (D-08, D-14) | VERIFIED | `grep -c 'shipping_options' models.py` returns 1; `landed_price` has 10 occurrences; `calculate_landed_price` has 2 occurrences — all preserved |
| 9 | Untrusted SLA payload cannot corrupt prices/states: validated before Pydantic construction (T-33-04) | VERIFIED | `filter_and_sort_slas` validates `raw_price` is non-negative int, `shippingEstimate` matches `_ESTIMATE_RE`, `deliveryChannel == 'delivery'` before constructing any `ShippingInfo` |
| 10 | R$1,000 unit-regression guard asserted in tests (FRET-05 SC-3) | VERIFIED | `test_unit_regression_guard_below_1000` at line 155: `assert all(o["price_reais"] < 1000 for o in result)` |

**Wave 1 score: 10/10 truths verified**

#### Wave 2 (Plan 33-02) — HTTP Wiring + Config Endpoint

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 11 | `_fetch_shipping` pairs SKU with its own seller (not hardcoded "1") (D-01) | VERIFIED | `select_candidate(items)` called at line 842 of `vtex_api_scraper.py`; `seller_id = "1"` appears only as fallback comment at line 848 |
| 12 | Simulation URL built only from persisted brand domain, never from caller-supplied host (T-33-01) | VERIFIED | `url = f"https://{domain}/api/checkout/pub/orderForms/simulation"` where `domain` is a parameter derived from the persisted brand — not from request body |
| 13 | Exactly one bounded retry for transient failures; valid 200-with-no-delivery NOT retried (D-15, D-13) | VERIFIED | `for attempt in range(2)` loop; 200 with no SLAs hits `return` immediately on line ~501; retry only on transport exceptions and HTTP 408/429/5xx |
| 14 | Failing store keeps product with 'Frete temporariamente indisponível'; siblings unaffected (D-13) | VERIFIED | Outer `except Exception` at line 540 absorbs all exceptions; `asyncio.gather` siblings isolated; test `test_sibling_isolation` in `test_vtex_api_client.py` |
| 15 | Valid 200 with no home-delivery SLA shows 'Entrega indisponível para este CEP', distinct from failure (D-14) | VERIFIED | `ShippingInfo(status="Entrega indisponível para este CEP", ...)` at line ~502; test `test_no_logistics_info_yields_unavailable_for_cep` asserts this exact state |
| 16 | `_fetch_shipping` populates `shipping_options` (all valid options) + primary `shipping`/`shipping_price`/`is_free_shipping` from cheapest (D-04, FRET-05) | VERIFIED | `prod_result.shipping_options = shipping_options` at line ~492; `primary = shipping_options[0]` sets primary fields |
| 17 | Read-only `GET /search/config` exposes `DEFAULT_CEP` and no secret (D-04) | VERIFIED | `SearchConfigResponse(BaseModel)` with `default_cep: str` only; handler returns `SearchConfigResponse(default_cep=settings.DEFAULT_CEP)` at line 277; test confirms no extra keys |
| 18 | `shipping_options` serializes automatically via Pydantic — verified by contract test (D-07) | VERIFIED | `test_search_shipping_contract.py` uses `model_dump(mode='json')` and asserts `shipping_options` list is present and ordered; 9 tests green |
| 19 | CEP/payload never logged at info/error; only brand/status/attempt (T-33-02) | VERIFIED | All `logger.warning` calls in `_fetch_shipping` log only `domain`, `resp.status`, and `type(exc).__name__` — no CEP or payload string |

**Wave 2 score: 9/9 truths verified**

#### Wave 3 (Plan 33-03) — Frontend UI

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 20 | CEP field labeled 'CEP de entrega', prefixed with MapPin, initializes once from backend DEFAULT_CEP (D-04) | VERIFIED | App.tsx line 1267: `<label ... >CEP de entrega</label>`; line 1269: `<MapPin ... aria-hidden="true">`; one-time `useEffect` at line 1140 calls `getSearchConfig` with `cepInitialized` guard |
| 21 | Invalid/incomplete CEP blocks both search and export with inline error 'Informe um CEP válido com 8 dígitos.' (D-05) | VERIFIED | `handleSearch` lines 1198 and `handleExport` line 1224 both contain `setCepError('Informe um CEP válido com 8 dígitos.')` with early return + focus |
| 22 | Valid edited CEP remembered for session, shared across tabs, resets on reload (D-06) | VERIFIED | `searchStore.ts`: `cepInitialized` has no `persist` middleware (confirmed at lines 22/39/74); reload resets to `cepInitialized: false`; `setSearch` patch writes to Zustand memory store |
| 23 | Every search with valid CEP sends `include_shipping` automatically (D-07) | VERIFIED | `include_shipping: cepDigits.length === 8 ? true : undefined` at App.tsx lines 1210 and 1237 |
| 24 | Late `getSearchConfig` response never overwrites an edited CEP (D-04, D-06) | VERIFIED | Two-stage guard: check `cepInitialized` at effect entry (line 1141) AND after async response (line 1154); user edits set `cepInitialized: true` at line 1288 |
| 25 | All `shipping_options` render in backend price-then-estimate order; pickup never appears (D-09, D-10, D-12) | VERIFIED | `p.shipping_options.map(...)` at line 1448 renders options in backend order; no client-side `.sort()` applied; pickup was already excluded by the backend parser |
| 26 | Each estimate shows its faithful unit copy (D-11) | VERIFIED | `estimate_display` field from backend is rendered directly; backend produces exact strings ("Até X dias úteis" / "Até X dias" / etc.) |
| 27 | Free option shows 'Frete Grátis' (success green, CheckCircle2) alongside paid alternatives (D-12) | VERIFIED | App.tsx line 1463: `Frete Grátis` with `.shipping-free` (--success); paid path uses `.shipping-paid` with tabular-nums |
| 28 | Product price and freight visually separate; no total/landed_price on brand-search surface (D-08) | VERIFIED | `grep` for `landed_price`, `Preço total`, `Valor final`, `Produto + Frete` in the shipping section found zero matches in the brand-search card; occurrences found only in `CrossMarketplacePage` |
| 29 | Old history records without `shipping_options` fall back to legacy single shipping display (D-08 compat) | VERIFIED | Lines 1506-1512: `if (!Array.isArray(p.shipping_options) && p.shipping)` renders legacy `p.shipping` block |

**Wave 3 automated score: 10/10 truths verified (visual/behavioral items require human verification)**

**Overall automated score: 29/29 (18 unique truths per PLAN frontmatter merge, 29 across all must-haves)**

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/services/vtex_shipping.py` | Pure HTTP-free SLA parser/filter/sort; ≥60 lines | VERIFIED | 230 lines; 4 pure helpers (`parse_estimate`, `filter_and_sort_slas`, `select_candidate`, `classify_result`); no `async def`, no `aiohttp`, no `self` |
| `backend/core/models.py` | Extended `ShippingInfo` + additive `shipping_options` on `SearchProductResult` | VERIFIED | `shipping_options` field present (1 occurrence); 5 new `ShippingInfo` fields (`service_name`, `service_id`, `estimate_display`, `estimate_unit`, `is_free_shipping`); `landed_price` / `calculate_landed_price` preserved |
| `backend/tests/test_vtex_shipping.py` | Pure unit tests for all contract behaviors; ≥60 lines | VERIFIED | 345 lines; 37 passing tests covering pickup filter, cents→reais, 4 estimate units, ordering, malformed entries, R$1,000 guard, None≠0.0 |
| `backend/services/vtex_api_scraper.py` | Rewired `_fetch_shipping` using pure parser; contains `shipping_options` | VERIFIED | `from services.vtex_shipping import filter_and_sort_slas, classify_result, select_candidate` at line 18; `shipping_options` populated; SKU+seller resolved via `select_candidate` |
| `backend/api/routes_search.py` | `GET /search/config` returning `{default_cep}` | VERIFIED | `SearchConfigResponse(BaseModel)` at line 87; handler at line 271 returns `settings.DEFAULT_CEP` |
| `backend/tests/test_search_shipping_contract.py` | Config endpoint + serialized options contract tests; ≥60 lines | VERIFIED | 195 lines; 9 passing tests (4 config endpoint + 5 Pydantic serialization) |
| `frontend/src/api/client.ts` | `static getSearchConfig()` loading default CEP | VERIFIED | Line 90: `static getSearchConfig()` returning `this.request<any>('/search/config')` |
| `frontend/src/stores/searchStore.ts` | `cepInitialized` flag; no persist middleware | VERIFIED | `cepInitialized: boolean` at line 24; confirmed memory-only (no `persist(` anywhere in file) |
| `frontend/src/App.tsx` | CEP field relabeled, one-time init, blocking validation, `shipping_options` render, legacy fallback | VERIFIED | All required strings and patterns confirmed present (see truth table) |
| `frontend/src/App.css` | Shipping options list styles using existing semantic tokens | VERIFIED | `.cep-input-error`, `.shipping-section`, `.shipping-header`, `.shipping-free`, `.shipping-paid` etc. confirmed present; all reference `--border`, `--success`, `--text-main`, `--text-muted` tokens |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `vtex_shipping.py` | `backend/core/models.py` | constructs `ShippingInfo` from filtered SLAs | VERIFIED | `_fetch_shipping` in `vtex_api_scraper.py` constructs `ShippingInfo(...)` using fields from `filter_and_sort_slas` output |
| `test_vtex_shipping.py` | `vtex_shipping.py` | imports and tests pure helpers | VERIFIED | `from services.vtex_shipping import ...` pattern confirmed; 37 pure-unit tests green |
| `vtex_api_scraper.py` | `vtex_shipping.py` | imports parser helpers | VERIFIED | `from services.vtex_shipping import filter_and_sort_slas, classify_result, select_candidate` at line 18 |
| `routes_search.py` | `settings.DEFAULT_CEP` | read-only config endpoint | VERIFIED | `return SearchConfigResponse(default_cep=settings.DEFAULT_CEP)` at line 277 |
| `test_search_shipping_contract.py` | `vtex_api_scraper.py` | fake-session drives `_fetch_shipping` | VERIFIED | `_fetch_shipping` referenced in 10 tests; retry/state matrix covered |
| `App.tsx` | `ApiClient.getSearchConfig` | one-time effect initializes CEP | VERIFIED | `getSearchConfig` called in `useEffect` at line 1151 |
| `App.tsx` | `p.shipping_options` | maps options in backend order with legacy fallback | VERIFIED | `p.shipping_options.map(...)` at line 1448; legacy `p.shipping` fallback at line 1507 |
| `searchStore.ts` | `cepInitialized` flag | guards one-time CEP initialization | VERIFIED | Flag set at initialization (line 83) and updated in `setSearch` patch at lines 1145, 1156, 1162, 1288 |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `App.tsx` shipping section | `p.shipping_options` | `_fetch_shipping` populates `prod_result.shipping_options` from VTEX checkout simulation API; flows via Pydantic serialization through `/search` response | Yes — VTEX checkout simulation via `session.post(url, json=payload)`; not static/hardcoded | FLOWING |
| `App.tsx` CEP field | `zipcode` in `searchStore` | `getSearchConfig()` fetches from `GET /search/config` → `settings.DEFAULT_CEP`; one-time init effect | Yes — reads from live settings; not hardcoded in frontend | FLOWING |
| `routes_search.py` `/search/config` | `default_cep` | `settings.DEFAULT_CEP` from backend config | Yes — runtime config value | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 37 pure shipping parser tests pass | `python -m pytest backend/tests/test_vtex_shipping.py -q` | 37 passed in 0.09s | PASS |
| 10 vtex_api_client tests pass (retry matrix + 3 baseline) | `python -m pytest backend/tests/test_vtex_api_client.py -q` | 10 passed in 0.54s | PASS |
| 9 search shipping contract tests pass (config + Pydantic) | `python -m pytest backend/tests/test_search_shipping_contract.py -q` | 9 passed in 1.42s | PASS |
| Full backend suite (310 tests, no regression) | `python -m pytest backend/tests -q` | 310 passed in 13.75s | PASS |
| Frontend lint clean | `npm run lint --prefix frontend` | No errors | PASS |
| Frontend build clean (tsc + vite) | `npm run build --prefix frontend` | Built in 768ms, no errors | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| FRET-05 | 33-01, 33-02, 33-03 | VTEX checkout shipping: price/estimate in reais, free shipping detection, unit contract | SATISFIED | SC-1: `shipping_options` populated with price in reais per `_fetch_shipping`; SC-2: `is_free_shipping=True` when `price_reais == 0.0`, `None` != `0.0` contract enforced; SC-3: `test_unit_regression_guard_below_1000` assertion present and green |

No orphaned requirements: REQUIREMENTS.md Traceability confirms FRET-05 maps to Phase 33 and is marked Complete.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | No TBD/FIXME/XXX markers found in any phase-33 modified file; no placeholder strings; no hardcoded empty returns in production paths |

No anti-patterns were found. The `placeholder` grep hits in App.tsx are all HTML `placeholder=` attributes (input field hint text), not stub implementation patterns.

---

### Human Verification Required

All automated checks pass. The following items require a running stack to verify:

### 1. Default CEP Visible and Editable on Load

**Test:** Open the frontend, navigate to the search page, observe the CEP field.
**Expected:** Field displays the backend `DEFAULT_CEP` (e.g. `01415-000`), is editable. Refreshing the browser resets it to the default (not to a blank field if the default is non-empty).
**Why human:** Requires a running stack; `getSearchConfig` makes a live HTTP call that cannot be simulated via grep.

### 2. Invalid CEP Blocks Both Search and Export

**Test:** Clear the CEP field, type 5 digits (e.g. `01415`), then click "Comparar" and then "Excel".
**Expected:** For both buttons: inline error `Informe um CEP válido com 8 dígitos.` appears with AlertTriangle icon, focus moves to the CEP field, no network request is made.
**Why human:** Browser interaction and focus behavior cannot be verified via static analysis.

### 3. Late Config Response Does Not Overwrite Edited CEP

**Test:** Open DevTools > Network, throttle to Slow 3G, edit the CEP field immediately on load before the config response arrives, wait for the response.
**Expected:** The user-edited value is preserved; the default CEP from the response is discarded.
**Why human:** Race condition with async network request; requires DevTools throttling simulation.

### 4. VTEX Brand Search Returns Real Shipping Options

**Test:** With at least one VTEX brand onboarded (e.g. Aramis, Richards if applicable), run a product search with a valid CEP.
**Expected:** At least one product card shows the shipping section with `Entrega para {CEP}` header, one or more option rows with real prices in reais (e.g. `R$ 19,90`) and estimate strings (e.g. `Até 5 dias úteis`). No pickup options appear.
**Why human:** Requires live VTEX checkout simulation against an onboarded brand.

### 5. Free Shipping Shows 'Frete Grátis' Not 'R$ 0,00'

**Test:** Find a VTEX brand/product/CEP combination that returns a free shipping option.
**Expected:** The free option renders with a `CheckCircle2` icon and `Frete Grátis` in green (not `R$ 0,00`).
**Why human:** Requires a brand/CEP that actually returns a free SLA from the VTEX checkout.

### 6. No-Delivery CEP Shows Correct State (Muted, Not Red)

**Test:** Search with a valid CEP for which the VTEX brand has no home-delivery option configured.
**Expected:** Product card shows `Entrega indisponível para este CEP` with `MapPin` icon and muted text (`--text-muted` color, NOT red/error color).
**Why human:** Requires a CEP that yields a valid 200 with zero delivery SLAs.

### 7. Temporary Failure Shows Amber Warning

**Test:** Block the VTEX checkout simulation endpoint for one brand (e.g. add a network rule via browser DevTools to fail `orderForms/simulation`), run a search.
**Expected:** That brand's products show `Frete temporariamente indisponível` with `AlertTriangle` in amber; other brands/products still load their shipping.
**Why human:** Requires simulating a transport failure and verifying sibling isolation visually.

### 8. Legacy History Records Render Without Crashing

**Test:** Open the search history, navigate to a result from before Phase 33 (a record without `shipping_options` in the stored JSON).
**Expected:** The history item renders without a JS crash or blank card, showing the legacy single shipping row (whatever `p.shipping` contained).
**Why human:** Requires history data predating this phase in the running application.

---

### Gaps Summary

No automated gaps found. All 29 observable truths are VERIFIED by codebase evidence (files exist, are substantive, are wired, and data flows through the wiring). The 310-test backend suite and the frontend lint/build are all green.

The `human_needed` status reflects 8 behavioral items that require a running stack for full acceptance — per ROADMAP.md Phase 33 success criteria, the live behavior (SC-1: real shipping values appear) is the final gate.

---

_Verified: 2026-06-26T14:00:00Z_
_Verifier: Claude (gsd-verifier)_
