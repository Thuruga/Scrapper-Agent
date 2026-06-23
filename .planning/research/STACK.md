# Stack Research — v2.0 New-Feature Stack

**Domain:** Fashion price-scraping SPA (Python/FastAPI backend + React/Vite frontend)
**Researched:** 2026-06-18
**Confidence:** HIGH (brands), HIGH (frontend state), MEDIUM (Shopify shipping), HIGH (diagnostics)

---

## 1. Brand Platform Table (COMP-01)

Each brand was investigated via direct page fetch, CDN asset domain analysis, and/or cross-referenced with agency case studies and platform detection services. Confidence is noted per brand.

| Brand | Brazilian URL | Platform | Supported Engine | Status | Confidence | Evidence |
|-------|--------------|----------|-----------------|--------|------------|----------|
| Levi's | levi.com.br | VTEX | VTEXEngine | READY | HIGH | Asset CDN `lojalevis.vtexassets.com` visible on page; VTEX logo in footer |
| Calvin Klein | calvinklein.com.br | VTEX | VTEXEngine | READY | HIGH | Asset CDN `calvinklein.vtexassets.com` and `calvinklein.vtex.com.br` visible; `vtex.file-manager-graphql` in image URLs |
| Zapalla | zapalla.com.br | VTEX IO | VTEXEngine | READY | HIGH | Agency case study (Wicomm) documents full VTEX IO migration; project delivered 2024 |
| Austral | austral.com.br | VTEX + Deco.cx frontend | VTEXEngine | READY | HIGH | Asset CDN `austral.vtexassets.com`; Deco.cx footer link (Deco.cx is a VTEX-native headless layer, backend is still VTEX) |
| Track & Field | tf.com.br | VTEX | VTEXEngine | READY | HIGH | AfterShip brand tech stack confirms VTEX; `trackfield.vtexcrm.com.br` and `trackfield.ds.vtexcrm.com.br` in public DNS records |
| Richards | richards.com.br | Wake Commerce | — | DEFERRED | HIGH | Footer attribution `logo-wake-footer.svg` linking to `wake.tech`; subdomain `richardswake.troquefacil.com.br` |
| Lacoste | lacoste.com/br | Salesforce Commerce Cloud (SFCC/Demandware) | — | DEFERRED | MEDIUM | Global Lacoste runs SFCC (confirmed via Salesforce blog and agency case Itelios); Brazilian subdomain is on the same global platform (site blocked 403 for direct inspection — inferred from global implementation) |
| Hugo Boss | hugoboss.com/br | Salesforce Commerce Cloud (SFCC/Demandware) | — | DEFERRED | MEDIUM | Hugo Boss confirmed as Salesforce Commerce Cloud customer across multiple sources (RocketReach tech stack, SAP/Salesforce industry reports); Brazilian country section is the same global storefront; site returned 403 — platform inferred from global evidence |
| Zara | zara.com/br | Custom Inditex (IOP — Inditex Open Platform) | — | DEFERRED | HIGH | Inditex built and uses their proprietary Inditex Open Platform (IOP) launched 2018; completely custom, no standard scraping API; 403 on direct fetch confirms active bot blocking |

### Summary by Outcome

**READY — VTEX (4 brands):** Levi's, Calvin Klein, Zapalla, Austral, Track & Field
(5 brands total — all use `VTEXEngine`, zero new engine work required)

**DEFERRED — Wake Commerce (1 brand):** Richards
- Wake Commerce engine is explicitly out of scope for this milestone.
- Richards is flagged in the brand registry with `is_active: false` and a note "platform: wake_commerce — engine not yet built."

**DEFERRED — Non-standard platforms (3 brands):** Lacoste (SFCC), Hugo Boss (SFCC), Zara (Custom/IOP)
- No scraping support exists for SFCC or IOP.
- Building SFCC or Inditex scrapers is out of scope.
- These brands are flagged as `is_active: false` with a note indicating platform.

### Risk Assessment

- 5 of 9 brands are immediately actionable (VTEX). This is the safe core of COMP-01.
- 1 brand (Richards) is a known risk already called out in PROJECT.md (Wake Commerce).
- 3 brands (Lacoste, Hugo Boss, Zara) are an **undiscovered risk** not mentioned in the original scope. They require either: (a) deferring permanently, (b) a future SFCC engine, or (c) sourcing via marketplace search instead.
- Total v2.0 COMP-01 delivery: **5 VTEX brands onboarded, 4 deferred with flagging**.

---

## 2. Frontend State Management (PERS-01, HIST-01)

### Problem

The app is a single-file `App.tsx` SPA with tab switching via `AnimatePresence key={activeTab}`. Tabs **unmount on switch**, destroying all `useState` in `SearchPage` and `CrossMarketplacePage`. In-flight search results and loading state are lost on tab switch.

### Recommendation: Zustand v5

**Install:** `npm install zustand`
**Current version:** 5.0.14 (as of 2026-06-18, published ~21 days ago)
**Bundle footprint:** ~1 KB gzipped (no Provider, no reducers, no boilerplate)

#### Why Zustand over alternatives

| Option | Verdict | Reason |
|--------|---------|--------|
| **Zustand v5** | USE THIS | No Provider wrapping needed. Hook-based. Module-level singleton survives component unmount by design. TypeScript-native. <1 KB. 32M+ weekly npm downloads. #1 non-Redux state library in State of React 2025 (50% usage). |
| React Context + useReducer | AVOID | Context re-renders every consumer on every state change. For a search result object potentially containing hundreds of products, this causes cascading re-renders across all tabs. Also still inside the component tree — if the Context Provider is inside a tab component it still gets destroyed. |
| TanStack Query (React Query) | DO NOT ADD | Solves server-cache lifecycle, not the cross-tab state problem. The app already does manual fetch + setState. Adding TQ just to solve tab persistence is overengineering — TQ would need to own the entire search lifecycle. Defer to a future milestone if caching becomes a need. |
| Redux Toolkit | DO NOT ADD | Massive boilerplate for a single-file app. Bundle adds 30+ KB vs Zustand's 1 KB. No value here. |
| Jotai | viable alternative | Atomic model is good but slightly more verbose for this use case (need to compose atoms for search state). Zustand's single-store model is simpler for the search + cross-marketplace pair. |

#### Integration Pattern

The store lives at module scope (outside React's component tree), so it survives unmount/remount of any tab:

```typescript
// stores/searchStore.ts
import { create } from 'zustand'

interface SearchState {
  // Compare search (SearchPage)
  compareQuery: string
  compareResults: any | null
  compareLoading: boolean

  // Cross-marketplace search (CrossMarketplacePage)
  crossQuery: string
  crossResults: any | null
  crossLoading: boolean

  // Actions
  setCompareState: (patch: Partial<SearchState>) => void
  setCrossState: (patch: Partial<SearchState>) => void
  clearCompare: () => void
  clearCross: () => void
}

export const useSearchStore = create<SearchState>()((set) => ({
  compareQuery: '',
  compareResults: null,
  compareLoading: false,
  crossQuery: '',
  crossResults: null,
  crossLoading: false,
  setCompareState: (patch) => set(patch),
  setCrossState: (patch) => set(patch),
  clearCompare: () => set({ compareQuery: '', compareResults: null, compareLoading: false }),
  clearCross: () => set({ crossQuery: '', crossResults: null, crossLoading: false }),
}))
```

In `SearchPage` and `CrossMarketplacePage`: replace `useState` for `query`, `results`, `loading` with `useSearchStore` selectors. The values persist across tab switches because the module-level store is never garbage-collected.

**No `persist` middleware needed** — results only need to survive tab switches within the session, not across page refreshes. Keep it simple: plain `create()`, no middleware.

#### What NOT to add

- Do NOT add `persist` middleware (sessionStorage/localStorage) — search results can be 1–2 MB of JSON and this degrades UX.
- Do NOT add `immer` middleware — the state shape is flat and actions are simple patches.
- Do NOT add TanStack Query alongside Zustand — they solve different problems and adding both adds complexity.

---

## 3. Checkout Shipping Extension (FRET-05)

### Current state

- **VTEX:** Complete. Checkout simulation via `POST /api/checkout/pub/orderForms/simulation` in `services/vtex_api_scraper.py`. Returns price + estimated_delivery_days. ShippingInfo model is already defined.
- **Amazon:** Partial (Playwright-based `calculate_shipping_advanced`).
- **Shopify / Netshoes:** None.

### Shopify Shipping (MEDIUM confidence)

Shopify exposes an unauthenticated AJAX Cart API for storefront-level shipping rate calculation. No API key required — it operates on session cookies issued by the Shopify CDN.

**Workflow (3 steps):**

1. **Add a product to cart** — `POST /{store}/cart/add.json` with `{"id": <variant_id>, "quantity": 1}`. This creates a session cookie (`_session_id` or similar) that the shipping endpoint reads.
2. **Initiate async calculation** — `POST /{store}/cart/prepare_shipping_rates.json?shipping_address[zip]=01310100&shipping_address[country]=Brazil&shipping_address[province]=SP`. Returns HTTP 202 with empty body.
3. **Poll for rates** — `GET /{store}/cart/async_shipping_rates.json?shipping_address[zip]=01310100&shipping_address[country]=Brazil&shipping_address[province]=SP`. Poll until non-null; returns array of `{name, price, delivery_range, delivery_days}`.

**Caveats:**
- Requires a real product variant ID from the Shopify store (extractable during the search/scrape phase).
- The AJAX API "can only be used by themes hosted by Shopify" per official docs — meaning it requires the Shopify session cookie. `curl_cffi` with session cookie carry-over should work; Playwright is a reliable fallback.
- Throttled — do not call per-product. Call once per search, reuse rate for the same store.
- Response `price` is in the store's currency (BRL for Brazilian stores). Verify `currency` field.
- `delivery_range` gives ISO date strings `["2026-06-22", "2026-06-25"]`; compute delta in days for `estimated_delivery_days`.

**Implementation note:** No new Python library needed. Implement as `ShopifyEngine.calculate_shipping()` using `aiohttp` (already in the project). Use `curl_cffi` with `impersonate="chrome"` if the store blocks plain aiohttp.

### Netshoes Shipping

Netshoes is a marketplace (now owned by Magazine Luiza). Their checkout shipping is not exposed via a stable public API. The existing `NetshoesEngine` uses Playwright for scraping. Extending it to shipping would require Playwright page interaction to type a CEP into the product page's shipping calculator widget. This is:
- Fragile (layout changes break it)
- Slow (full browser render per product)
- Of lower priority (Netshoes carries the same brands as VTEX stores — overlap is high)

**Recommendation:** Do NOT extend Netshoes shipping in this milestone. Mark it `ShippingInfo(status="Calculado no checkout")` — the existing ShippingInfo model already supports this. Add a DIAG-01 diagnostic flag instead.

### SFCC / Wake / Custom platforms

None of the deferred brands (Richards, Lacoste, Hugo Boss, Zara) are reachable by our engines in v2.0, so their shipping is moot for this milestone.

### No new Python libraries needed for shipping

The existing `aiohttp` + `curl_cffi` + `Playwright` stack is sufficient. Use:
- `aiohttp.ClientSession` for non-JS Shopify stores
- `curl_cffi.AsyncSession` for WAF-protected stores
- `Playwright` as last resort

---

## 4. Category Diagnostics (DIAG-01)

### Verdict: Pure Python — No New Library Required

The diagnostics feature tracks which category scrapes return zero products (empty) or raise exceptions (error). This is entirely achievable inside the existing engine infrastructure.

**Implementation approach:**

Add a `CategoryDiagnosticResult` model to `core/models.py`:

```python
class CategoryDiagnosticResult(BaseModel):
    brand_key: str
    category_slug: str
    category_url: str
    engine: str
    status: str  # "ok" | "empty" | "error"
    product_count: int = 0
    error_message: Optional[str] = None
    checked_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
```

The existing `BaseEngine.run_bulk_scrape()` already streams products and has a `log_callback`. Wrap the call to capture: (a) final product count == 0 → `status="empty"`, (b) exception raised → `status="error"`. Persist results to `data/diagnostics.json` or a Supabase `category_diagnostics` table.

No new Python library (no Prometheus, no Sentry, no extra monitoring stack) — this is a CRUD record on top of existing patterns.

---

## 5. Brand Management (MGMT-01, MGMT-02)

### is_active Enforcement

`DynamicBrand.is_active` field already exists in the model. The gap is in `EngineFactory.search_all_brands()`: it calls `brand_service.list_brands()` without filtering `is_active`. Fix: add `filter(lambda b: b.is_active, ...)` in `list_brands()` or in the factory call. No new stack component needed.

### Brand Deactivate/Reactivate Endpoint

Add `PATCH /brands/{brand_key}` endpoint in `api/routes_brands.py` accepting `{"is_active": false}`. Update brand_service to persist the flag. Already within the existing FastAPI + Pydantic + brand_service pattern.

### Frontend Brand Management

Extend `SettingsPage` in `App.tsx` to show a toggle per brand (active/inactive). Uses the existing `ApiClient.request()` pattern. No new UI library needed — the existing Lucide icons + existing button styles cover it.

---

## 6. Search History Completion (HIST-01)

### Problem

Comparative searches (`/search` endpoint) do not save to `search_history.json`. Only the cross-marketplace search saves history. The `SearchHistory` model already has `type: str` with values `"search"` and `"cross"`.

### Fix

In the `/search` route handler, after results are assembled, call `search_history_service.save()` with `type="search"` and serialize the `ComparisonResult` as the `results` field. The model and service already support this.

### Frontend re-display

The `SearchPage` already has a `preloadedJobId` prop pattern (identical to `CrossMarketplacePage`). Extend `HistoryPage` to handle both `type="search"` and `type="cross"` — call `ApiClient.getHistoryDetail()` and route to the correct page based on type.

No new stack components needed.

---

## Full Stack Delta for v2.0

### New Frontend Dependency

| Package | Version | Purpose |
|---------|---------|---------|
| `zustand` | `^5.0.14` | Cross-tab persistent search state |

**Install:**
```bash
cd frontend
npm install zustand
```

### New Backend Dependencies

None. All backend features (is_active enforcement, Shopify shipping via AJAX Cart API, category diagnostics, history fix) are implementable with the existing Python stack (`aiohttp`, `curl_cffi`, `Playwright`, `pydantic`, `fastapi`).

### Changes to Existing Files

| File | Change |
|------|--------|
| `core/models.py` | Add `CategoryDiagnosticResult` model |
| `services/engines/factory.py` | Filter `is_active=False` brands in `search_all_brands` |
| `services/engines/shopify_engine.py` | Implement `calculate_shipping()` via AJAX Cart API |
| `api/routes_brands.py` | Add `PATCH /brands/{brand_key}` endpoint |
| `api/routes_search.py` | Save search history for comparative searches |
| `data/brands.json` (or Supabase) | Add 5 VTEX brands; flag 4 deferred brands as `is_active: false` |
| `frontend/src/App.tsx` | Lift search state to Zustand store; extend SettingsPage |
| `frontend/src/stores/searchStore.ts` | New file — Zustand store definition |

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| Zustand | React Context + useReducer | Provider inside tab component still unmounts; global Context higher up causes full-tree re-renders on every result update |
| Zustand | TanStack Query | Solves server-cache lifecycle, not cross-tab state; adds 13 KB; the app's search is fire-and-forget, not a query-key-based cache |
| Shopify AJAX Cart API | Playwright Shopify page scrape | AJAX Cart API is 10x faster and more reliable; Playwright is the fallback if stores block unauthenticated AJAX |
| Pure Python for diagnostics | Prometheus / OpenTelemetry | Massive overkill for what is a per-category status flag persisted to a JSON file |

---

## What NOT to Add in v2.0

| Avoid | Why |
|-------|-----|
| Wake Commerce engine | Out of scope per milestone; Richards is deferred |
| SFCC (Salesforce Commerce Cloud) engine | Out of scope; Lacoste and Hugo Boss deferred |
| Custom Inditex/IOP engine | Out of scope; Zara deferred — IOP is fully proprietary, no public API |
| TanStack Query | Solves a problem the app does not yet have; adds complexity |
| Redux Toolkit | 30+ KB overhead for a single-file SPA |
| `immer` middleware for Zustand | Not needed — state mutations are simple patch objects |
| `persist` middleware for Zustand | Would write MB-sized search results to localStorage; tab-only survival is sufficient |
| Prometheus / Grafana / OpenTelemetry | Diagnostic requirement is a simple status flag, not a metrics pipeline |
| Per-user auth / JWT | Explicitly out of scope this milestone |

---

## Sources

- **Levi's platform:** Direct page fetch → `lojalevis.vtexassets.com` CDN confirmed (HIGH)
- **Calvin Klein platform:** Direct page fetch → `calvinklein.vtexassets.com` CDN confirmed (HIGH)
- **Zapalla platform:** [Wicomm agency case study](https://wicomm.com.br/como-a-implementacao-da-vtex-io-transformou-o-e-commerce-da-zapalla-impulsionando-vendas/) (HIGH)
- **Austral platform:** Direct page fetch → `austral.vtexassets.com` CDN + Deco.cx footer (HIGH)
- **Track & Field platform:** [AfterShip brand tech stack](https://www.aftership.com/brands/tf.com.br) + VTEX CRM subdomain in DNS (HIGH)
- **Richards platform:** Direct page fetch → `logo-wake-footer.svg` linking `wake.tech` in footer (HIGH)
- **Lacoste platform:** [Salesforce blog (FR)](https://www.salesforce.com/fr/blog/commerce-eres-lacoste-vilebrequin/) + [Salesforce LinkedIn post](https://www.linkedin.com/posts/commercecloud-demandware_lacoste-has-a-salesforce-connection-at-every-activity-6412768985820983296-k0Vw) (MEDIUM — global platform; Brazil inferred)
- **Hugo Boss platform:** RocketReach tech stack profile + SAP/Salesforce industry reports (MEDIUM — direct fetch blocked 403)
- **Zara platform:** [Inditex Open Platform documentation](https://www.inditex.com/itxcomweb/es/en/group/our-approach) + [retail trade press](https://retail-systems.com/rs/Zaraowner_To_Invest_1point8bn_In_Online_Platforms.php) (HIGH — custom IOP confirmed)
- **Zustand v5:** [npmjs.com/package/zustand](https://www.npmjs.com/package/zustand) — v5.0.14 confirmed; [GitHub pmndrs/zustand](https://github.com/pmndrs/zustand) docs via Context7 (`/pmndrs/zustand`) (HIGH)
- **Shopify AJAX Cart API:** [Shopify official AJAX Cart API reference](https://shopify.dev/docs/api/ajax/reference/cart) — `prepare_shipping_rates` and `async_shipping_rates` endpoints confirmed (MEDIUM — session cookie requirement documented but workflow nuances need empirical testing)
- **Wake Commerce API:** [wakecommerce.readme.io](https://wakecommerce.readme.io/docs/storefront-api-visaogeral) — confirmed GraphQL + `TCS-Access-Token` required (HIGH)

---
*Stack research for: Intelligence Scraper v2.0 — new feature stack only*
*Researched: 2026-06-18*
