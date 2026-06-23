# Architecture Research — v2.0 Integration

**Domain:** Python/FastAPI + React scraper — subsequent milestone integration
**Researched:** 2026-06-18
**Confidence:** HIGH (all findings drawn from direct code inspection of the live codebase)

---

## System Overview (Current v1.x State)

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (React SPA — frontend/src/App.tsx)                    │
│  AnimatePresence key={activeTab} → tabs UNMOUNT on switch       │
│  All search state in local useState — lost on navigation        │
│  brands[] loaded once in App(), passed as prop to all pages     │
│  preloadedJobId prop exists on SearchPage/CrossMarketplacePage  │
│  BUT App.renderTab() never passes it → history wiring broken    │
└──────────────────────┬──────────────────────────────────────────┘
                       │ HTTP (synchronous, no streaming)
┌──────────────────────▼──────────────────────────────────────────┐
│  FastAPI API Layer                                               │
│  routes_brands.py  routes_search.py  routes_history.py          │
│  /search  POST (sync, returns full ComparisonResult)            │
│  /search/cross-marketplace  POST (sync, saves to history)       │
│  /history  GET / GET /{id} / DELETE /{id}                       │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│  Service Layer                                                   │
│  EngineFactory → BaseEngine (abstract)                          │
│    VTEXEngine / ShopifyEngine / MercadoLivreEngine              │
│    NetshoesEngine / AmazonEngine                                │
│  BrandManagerService (dual JSON/Supabase backend)               │
│  SearchHistoryService (JSON file, 30-day retention)             │
│  CrossMarketplaceService / NLPService                           │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│  Data Layer                                                      │
│  data/brands.json (DynamicBrand; is_active field present)       │
│  data/search_history.json (SearchHistory records)               │
│  Supabase brands table (optional, env-gated)                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Feature Integration Map

### Feature 1 — is_active Enforcement (MGMT-01)

**Problem:** `DynamicBrand.is_active` is defined in `core/models.py:232` and persisted in `data/brands.json`, but is never read anywhere. `BrandManagerService.list_brands()` returns all brands unconditionally. `EngineFactory.search_all_brands()` calls `brand_service.list_brands()` without filtering.

**Chokepoint decision: single chokepoint in `brand_service.list_brands()`.**

Reason: `list_brands()` is the only source-of-truth reader used by every downstream caller. Filtering there means no call-site changes in routes, factory, or monitoring. Adding `active_only=True` as a keyword argument (defaulting to False for backward compat) lets the Settings page continue to show inactive brands in the management UI.

**Files MODIFIED:**

| File | Function | Change |
|------|----------|--------|
| `services/brand_service.py` | `list_brands()` | Add `active_only: bool = False` param; filter `self.brands.values()` by `v.is_active` when True |
| `services/brand_service.py` | NEW `toggle_active(brand_key, active: bool)` | Set `brand.is_active`, call `_save()` — reused by the API route |
| `api/routes_brands.py` | NEW `PATCH /brands/{brand_key}/active` | Accepts `{"active": bool}`, calls `toggle_active`, returns updated `DynamicBrand` |

**Files with passive ripple (no code change needed if chokepoint is correct):**

- `services/engines/factory.py` — `search_all_brands()` line 70: calls `brand_service.list_brands()`. Once `list_brands(active_only=True)` is the default for search, inactive brands are automatically excluded.
- `api/routes_search.py` — `search_products()` lines 144-145: builds `all_brands` from `brand_service.list_brands()` + virtual marketplaces. Same fix flows here automatically.
- `api/routes_search.py` — `export_search_products()` lines 229-230: same list construction. Same fix.
- `api/routes_search.py` — `search_products_get()` line 209: same.

**Active vs inactive default:** The most defensible approach is:
- `list_brands(active_only=False)` — current signature, used by SettingsPage GET /brands/ to show all brands including inactive ones (so they can be reactivated).
- `list_brands(active_only=True)` — used by `search_all_brands()` and all search routes.

This makes the chokepoint unambiguous: the factory and routes explicitly ask for active-only, the management route asks for all.

**Monitoring ripple:** `MonitorPage` in App.tsx calls `ApiClient.getBrands()` which hits `GET /brands/`. The response already flows into the brand selector dropdown. If `GET /brands/` continues to return all brands (including inactive), the monitor brand selector will show inactive brands — which is probably acceptable (the user might want to stop monitoring an inactive brand). If the requirement is stricter, add `active_only=True` to `GET /brands/` and add a separate `GET /brands/all` for management. Recommend keeping the current `GET /brands/` returning all brands and filtering only in search.

**Data-flow change:**
```
Before: list_brands() → all brands → factory → all searched
After:  list_brands(active_only=True) → active only → factory → filtered
        list_brands() → all brands → SettingsPage API → shown with active toggle
```

**NEW model field needed:** None — `is_active: bool = True` already in `DynamicBrand`.

**NEW API endpoint:** `PATCH /brands/{brand_key}/active` — body `{"active": bool}`.

**Frontend changes (MGMT-02):**
- `SettingsPage` in App.tsx lines 1319-1428: add toggle button per brand row (reactivate/deactivate). Currently shows only Trash2 icon. Add a power/toggle icon that calls the new PATCH endpoint and refreshes brands.
- The brand list card (lines 1396-1425) renders `b.is_active` to show a dim/badge state for inactive brands.

---

### Feature 2 — In-flight Search State Survival (PERS-01 + HIST-01)

**Problem:** `App.tsx` renders tabs via `AnimatePresence key={activeTab}` with `renderTab()` inside a `motion.div`. When `activeTab` changes, the old component unmounts and all `useState` is destroyed. `SearchPage` and `CrossMarketplacePage` hold query, results, loading, selectedBrands entirely in local state. The `preloadedJobId` prop is defined in both component signatures but `renderTab()` at lines 1770-1779 passes no props to either — the prop wires are dangling.

**Recommended approach: global React context/store holding job state per tab.**

Rationale vs alternatives:
- **Keep components mounted (CSS `display:none`):** Would work but conflicts with `AnimatePresence`'s exit animations which require unmount. Would require removing animations or CSS-hiding only the content inside the animated wrapper — fragile.
- **Backend job + polling:** The backend `/search` is synchronous and returns data inline. Converting to async job+polling requires a Celery/background task layer. That is a large change not justified by the requirement. The history service already provides the storage half.
- **Global store (Zustand or React context):** Lifts state out of components into a module-scoped store that survives tab switches. Components read from and write to the store. Cost: one new file, no backend changes. Fits the synchronous search model perfectly.

**Recommended store shape:**

```typescript
// NEW: frontend/src/store/searchStore.ts
interface SearchTabState {
  query: string;
  results: ComparisonResult | null;
  loading: boolean;
  selectedBrands: string[];
  sort: string;
  inStock: boolean;
  zipcode: string;
}

interface CrossTabState {
  targetSku: string;
  zipcode: string;
  results: any | null;
  loading: boolean;
  selectionMode: boolean;
  selectedItems: Set<string>;
}

interface SearchStore {
  search: SearchTabState;
  cross: CrossTabState;
  setSearch: (partial: Partial<SearchTabState>) => void;
  setCross: (partial: Partial<CrossTabState>) => void;
}
```

Use Zustand (already a common pattern in React; very lightweight) or a React `useReducer` + Context approach if no new dependency is desired.

**Files MODIFIED:**

| File | Change |
|------|--------|
| `frontend/src/App.tsx` | Remove `key={activeTab}` from `motion.div` OR keep animation but lift state. Pass `preloadedJobId` and `onClearPreloadedJob` from `App` state down to `SearchPage` and `CrossMarketplacePage` in `renderTab()`. Add `historyJobId` state in App. |
| `frontend/src/pages/SearchPage.tsx` (or in App.tsx) | Replace all `useState` for query/results/loading/selectedBrands with store reads/writes |
| `frontend/src/pages/CrossMarketplacePage.tsx` (or in App.tsx) | Same |

**NEW files:**
- `frontend/src/store/searchStore.ts` — Zustand store (or context module)

**History wiring for comparative searches (HIST-01):**

Currently `routes_search.py POST /search` runs synchronously and returns `ComparisonResult` directly — it never calls `search_history_service.create_job()` or `update_job()`. `POST /search/cross-marketplace` does save to history (lines 414-449). So the gap is only on the comparative side.

Fix: In `routes_search.py search_products()`, wrap the existing logic:
1. Generate `job_id = str(uuid.uuid4())` before calling `search_all_brands`.
2. Call `search_history_service.create_job(job_id, query, brands, type="search")`.
3. After results: `search_history_service.update_job(job_id, "COMPLETED", results=brand_results_serialized)`.
4. Return `ComparisonResult` with `job_id` field added (or return it in a wrapper).

**preloadedJobId wiring:**

In `App.tsx renderTab()`, the switch statement currently passes no props to SearchPage or CrossMarketplacePage. The fix:

```typescript
// In App.tsx state
const [historyJobId, setHistoryJobId] = useState<string|null>(null);
const [historyTabTarget, setHistoryTabTarget] = useState<string|null>(null);

// When user clicks a history item (needs HistoryPage or sidebar hook):
const handleHistoryClick = (job: SearchHistory) => {
  setHistoryJobId(job.job_id);
  setHistoryTabTarget(job.type === 'cross' ? 'cross' : 'search');
  setActiveTab(job.type === 'cross' ? 'cross' : 'search');
};

// In renderTab():
case 'search': return <SearchPage brands={brands}
  preloadedJobId={historyTabTarget === 'search' ? historyJobId : null}
  onClearPreloadedJob={() => { setHistoryJobId(null); setHistoryTabTarget(null); }} />;
case 'cross': return <CrossMarketplacePage
  preloadedJobId={historyTabTarget === 'cross' ? historyJobId : null}
  onClearPreloadedJob={() => { setHistoryJobId(null); setHistoryTabTarget(null); }} />;
```

Both `SearchPage` and `CrossMarketplacePage` already have a `useEffect` on `preloadedJobId` that calls `ApiClient.getHistoryDetail()` and sets results — so the consumption side is wired; only the passing side in `App.tsx` was missing.

**Data-flow change:**
```
Before: Tab switch → AnimatePresence unmounts component → useState lost
After:  Tab switch → AnimatePresence still animates → but state lives in store
        History click → App sets historyJobId+tab → renderTab passes prop → component loads from /history/{id}
        POST /search → now also saves to history before returning
```

---

### Feature 3 — Engine/Category Diagnostics (DIAG-01)

**Problem:** There is no service that aggregates per-engine category health. `VTEXEngine.discover_categories()` and `ShopifyEngine.discover_categories()` return lists but do not report empty/failed categories in a structured way. `BaseEngine` has no concept of a category health result. Logs go to the websocket during bulk scrape but are not persisted as diagnostic records.

**Recommended architecture: new `CategoryDiagnosticsService` that wraps per-engine discovery and stores structured results.**

**NEW file:** `services/category_diagnostics_service.py`

```python
# services/category_diagnostics_service.py
class CategoryHealthRecord(BaseModel):
    brand_key: str
    category_name: str
    category_path: str
    status: str  # "ok" | "empty" | "error"
    product_count: int = 0
    error_message: Optional[str] = None
    checked_at: str  # ISO timestamp

class CategoryDiagnosticsService:
    async def run_diagnostics(self, brand_key: str) -> List[CategoryHealthRecord]: ...
    def get_last_run(self, brand_key: str) -> List[CategoryHealthRecord]: ...
    def get_all(self) -> Dict[str, List[CategoryHealthRecord]]: ...
```

**How it works:** `run_diagnostics(brand_key)` calls `engine.discover_categories()` to get the category list, then for each category attempts a lightweight probe (e.g., call `engine.search(query="", max_results=1)` against that category URL or use VTEX's category product count endpoint). It records empty vs error vs ok.

**BaseEngine change:** Add a non-abstract method `probe_category(category_path: str) -> dict` with a default implementation that calls `discover_categories()` and filters. Each engine can override to use a cheaper endpoint (e.g., VTEX has `?fq=C:/X/&_from=0&_to=0` which returns total count cheaply).

**Storage:** `data/category_diagnostics.json` — same pattern as `search_history.json`. Key: `brand_key`, value: list of `CategoryHealthRecord`. Overwritten on each run.

**NEW API endpoint:** `GET /diagnostics/categories` — returns all stored results. `POST /diagnostics/categories/{brand_key}/run` — triggers a new diagnostic run for one brand (async, returns job_id or waits inline given current sync pattern).

**Files MODIFIED:**

| File | Change |
|------|--------|
| `services/engines/base_engine.py` | Add optional `probe_category(path)` method with default stub |
| `services/engines/vtex_engine.py` | Override `probe_category` with VTEX count endpoint |
| `services/engines/shopify_engine.py` | Override `probe_category` with collections product count |

**NEW files:**
- `services/category_diagnostics_service.py`
- `api/routes_diagnostics.py`

**Frontend surface (DiagnosticsPage or panel inside CategoryPage):** A new sidebar tab "Diagnóstico" or a sub-panel in `MonitoredCategoriesPage` showing a table per brand with category rows and status badges (ok/empty/error).

---

### Feature 4 — Checkout Shipping Across More Engines (FRET-05)

**Current state:**
- `BaseEngine` declares `calculate_shipping(product, zipcode)` as abstract and `calculate_shipping_advanced(url, zipcode)` as non-abstract raising `NotImplementedError`.
- `VTEXEngine.calculate_shipping` — returns `None` (comment: "not implemented for now"). VTEX shipping is actually done in `VtexApiClient` via checkout simulation, called from within the search flow when `include_shipping=True`.
- `ShopifyEngine.calculate_shipping` — returns `None` (explicit stub).
- `MercadoLivreEngine.calculate_shipping` — implemented via ML's shipping API.
- `NetshoesEngine.calculate_shipping` — delegates to `calculate_shipping_advanced` which uses Playwright.
- `AmazonEngine.calculate_shipping` — partially implemented (lines 269, 319).

**Problem:** `ShopifyEngine.search()` sets `shipping = ShippingInfo(status="Calculado no checkout")` when `include_shipping=True`, but never actually calculates anything. The Shopify Storefront API has a `/cart/shipping_rates.json` endpoint that accepts destination and returns rates — this is the correct implementation target.

**Recommended approach: implement `calculate_shipping` in ShopifyEngine using Shopify's shipping rates API without breaking VTEX.**

VTEX shipping is correctly working via the existing checkout simulation path in `VtexApiClient`. The `VTEXEngine.calculate_shipping` returning `None` is a dead method — VTEX shipping goes through `VtexApiClient.search()` internally, not through the engine's `calculate_shipping` hook. This is a design inconsistency but must not be changed to avoid regression.

**Shopify shipping implementation path:**

Shopify exposes `POST /cart/shipping_rates.json` (unauthenticated, requires a session cart) or the Storefront API's `checkoutCreate` mutation. The simpler path: use `GET /api/2023-01/checkouts/{token}/shipping_rates.json` via a synthetic checkout. This requires creating a cart first. A simpler fallback: call `GET /products/{handle}.json` to get variant IDs, create a checkout via `POST /checkouts.json`, then call shipping rates. This is an async multi-step flow suitable for the existing aiohttp session.

**Files MODIFIED:**

| File | Function | Change |
|------|----------|--------|
| `services/engines/shopify_engine.py` | `calculate_shipping()` | Implement Shopify checkout + shipping_rates sequence. Accept `product: Any` (must contain `url` and ideally a variant_id). Return `{"is_free_shipping": bool, "shipping_price": float, "raw_text": str}` matching existing ShippingInfo contract. |
| `services/engines/shopify_engine.py` | `search()` | When `include_shipping=True`, call `calculate_shipping` per product (or a batch if possible) after search returns |
| `services/engines/base_engine.py` | `calculate_shipping_advanced` | Document that VTEX uses a different path; add docstring clarifying the split |

**No change to VTEXEngine** — shipping already works through `VtexApiClient`'s checkout simulation flow that is called from inside `VtexApiClient.search()` when `include_shipping=True`.

**Amazon/Netshoes:** Both already have `calculate_shipping_advanced` implemented via Playwright. The `/search/calculate-shipping` endpoint already dispatches to them. No new wiring needed unless the goal is to make them work during the bulk search flow (currently they're on-demand only). For v2.0, leave on-demand and document clearly.

**Extending to new competitor brands (COMP-01):** When onboarding VTEX brands, shipping works automatically since `VTEXEngine` delegates to `VtexApiClient`'s checkout simulation. When onboarding Shopify brands, shipping will work once the ShopifyEngine implementation above is complete. No per-brand code needed.

---

### Feature 5 — 9 New Competitor Brands (COMP-01)

**No new files needed.** The `routes_brands.py` `detect_engine()` function already probes for VTEX vs Shopify automatically. The `BrandManagerService.add_brand()` persists to JSON/Supabase. The `EngineFactory.get_engine()` routes by `engine` field.

**Files MODIFIED:**
- `data/brands.json` — add 9 brand entries. Each entry needs: `brand_key`, `brand_name`, `domain`, `engine` (auto-detected or manually set), `is_active: true`.
- `services/category_resolver.py` — add category paths for brands that are VTEX (if category-scoped search is needed). Shopify brands do not need entries here (they use collections).

**Brands and their likely engines (to verify via `detect_engine` during onboarding):**

| Brand | Domain | Expected Engine | Risk |
|-------|--------|-----------------|------|
| Lacoste | lacoste.com/pt-br | VTEX (confirmed publicly) | Low |
| Levi's | loja.levis.com.br | VTEX | Low |
| Richards | loja.richards.com.br | VTEX | Low |
| Hugo Boss | hugoboss.com/br | Likely Shopify or proprietary | Medium |
| Calvin Klein | calvinklein.com.br | Likely Shopify | Medium |
| Track&Field | trackefeld.com.br | VTEX | Low |
| Austral | — | Unknown | High — may need manual check |
| Zapalla | — | Unknown | High |
| Zara | zara.com/br | Proprietary (Inditex) | HIGH — may be neither VTEX nor Shopify; could require Wake Commerce or custom |

**Zara/Wake Commerce risk:** Zara and similar Inditex brands use their own platform. If `detect_engine` returns neither vtex nor shopify, the system currently falls back to `VTEXEngine` (factory.py line 45), which will silently fail. The correct handling is to mark the brand `is_active: false` with an `engine: "unsupported"` value and surface this in the UI. Add a guard in `EngineFactory.get_engine()` to raise a clear `UnsupportedEngineError` rather than silently instantiating a wrong engine.

---

## Component Boundaries — New vs Modified

```
┌─────────────────────────────────────────────────────────────────┐
│ NEW                          MODIFIED                           │
├──────────────────────────────┬──────────────────────────────────┤
│ frontend/src/store/          │ frontend/src/App.tsx             │
│   searchStore.ts             │   - renderTab() passes props     │
│                              │   - historyJobId state in App    │
│ services/                    │   - AnimatePresence key removed  │
│   category_diagnostics_      │     or state lifted              │
│   service.py                 │                                  │
│                              │ services/brand_service.py        │
│ api/routes_diagnostics.py    │   - list_brands(active_only)     │
│                              │   - toggle_active()              │
│ api/routes_brands.py         │                                  │
│   PATCH /brands/{k}/active   │ services/engines/                │
│                              │   shopify_engine.py              │
│ data/brands.json entries     │   - calculate_shipping() impl    │
│   (9 new brands)             │                                  │
│                              │ services/engines/base_engine.py  │
│                              │   - probe_category() stub        │
│                              │                                  │
│                              │ api/routes_search.py             │
│                              │   - search_products() saves to   │
│                              │     history                      │
│                              │                                  │
│                              │ services/category_resolver.py    │
│                              │   - new brand paths              │
└──────────────────────────────┴──────────────────────────────────┘
```

---

## Data Flow Changes

### is_active Flow
```
PATCH /brands/{key}/active
  → brand_service.toggle_active(key, active)
  → DynamicBrand.is_active = active
  → _save() → JSON or Supabase

GET /search (or factory.search_all_brands)
  → brand_service.list_brands(active_only=True)  [CHANGED default for search callers]
  → only active brands reach EngineFactory
  → inactive brands never searched
```

### Search State Persistence Flow
```
User types in SearchPage (query, brands, etc.)
  → searchStore.setSearch({query, ...})  [NEW]
  → localStorage/memory persists across tab switch

Tab switch → AnimatePresence unmounts SearchPage
  → state LIVES in searchStore, not in component

User returns to Search tab → SearchPage mounts
  → reads from searchStore → restores last query + results

User clicks History item
  → App.handleHistoryClick(job) [NEW]
  → sets historyJobId + activeTab
  → renderTab() passes preloadedJobId to SearchPage/CrossMarketplacePage
  → component useEffect fires → loads from /history/{id}
```

### Comparative Search History Flow
```
Before: POST /search → execute → return ComparisonResult (no history)
After:  POST /search → create_job(uuid, query, "search")
                     → execute search_all_brands
                     → update_job(uuid, "COMPLETED", results)
                     → return ComparisonResult + job_id
```

### Category Diagnostics Flow
```
POST /diagnostics/categories/{brand_key}/run
  → CategoryDiagnosticsService.run_diagnostics(brand_key)
  → engine.discover_categories()  [existing]
  → for each category: engine.probe_category(path)  [NEW]
  → write CategoryHealthRecord[] to data/category_diagnostics.json
  → return summary

GET /diagnostics/categories
  → read from data/category_diagnostics.json
  → return Dict[brand_key, List[CategoryHealthRecord]]
```

---

## Architectural Patterns

### Pattern 1: Single-Chokepoint Active Filtering

**What:** Filter inactive brands in exactly one place (`brand_service.list_brands(active_only=True)`) rather than at each call site.

**When to use:** When a cross-cutting constraint (like is_active) must apply uniformly to all consumers. Prevents the bug where a new call site forgets the filter.

**Trade-off:** The management UI needs to call `list_brands(active_only=False)`. This requires explicit `active_only=False` in the brands route rather than relying on the default. If the default is changed to True for safety, the brands route must opt out — slightly surprising but safer.

### Pattern 2: Module-Scoped Store for Search State

**What:** Replace component-local `useState` for search session data with a module-scoped store (Zustand or React Context). The store module is imported by both the component and App.tsx.

**When to use:** When state must survive component unmount (tab switch in a keyed AnimatePresence) without converting to URL state or adding a backend job layer.

**Trade-off:** Module-scoped stores don't reset on page refresh (which is desirable here). But they also don't reset on browser tab close unless explicitly cleared. This is acceptable for a scraper dashboard.

### Pattern 3: Lightweight Probe for Category Health

**What:** Rather than running a full bulk scrape to test a category, issue a minimal API call (e.g., VTEX `&_from=0&_to=0` query returning only the total count, Shopify `/products.json?collection_id=X&limit=1&fields=id`). Store result as a structured `CategoryHealthRecord`.

**When to use:** When diagnostic value must not incur the full cost of the operation being diagnosed.

**Trade-off:** Probe may succeed (category URL responds) but actual bulk scrape fails due to WAF/rate limiting. A "ok" probe does not guarantee a successful scrape. This is acceptable for v2.0 — the goal is catching genuinely empty/404 categories, not WAF failures.

### Pattern 4: Engine-Internal Shipping (VTEX) vs Hook-Based Shipping (Others)

**What:** VTEX shipping goes through `VtexApiClient`'s checkout simulation inside `search()`. Other engines use the `calculate_shipping` abstract method called after search. These are two different patterns in the same codebase.

**Implication for v2.0:** Do not try to unify them. VTEX's approach is correct and complete. Shopify's `calculate_shipping` stub needs implementation. The important constraint is: do not break VTEX by attempting to route its shipping through the `calculate_shipping` hook.

---

## Build Order (Dependency-Aware)

The dependency graph drives the phase sequence:

```
Phase A: Brand data + is_active enforcement (backend only)
  → required before: brand-management UI, any search correctness

Phase B: 9 competitor brands onboarded
  → requires: Phase A (is_active gate prevents untested brands
    from polluting search; can be marked inactive until verified)

Phase C: Comparative search history save + preloadedJobId wiring in App
  → requires: nothing new on the backend beyond Phase A
  → required before: Phase D (state store needs to know what to preload)

Phase D: Frontend global search state store (tab-switch survival)
  → requires: Phase C (preloadedJobId must flow through App before store makes sense)
  → brand-management toggle UI comes here too (reads is_active from API)

Phase E: Category diagnostics service + endpoint + UI panel
  → requires: Phase B (needs all brands registered to be useful)
  → no frontend blocker from A-D

Phase F: Shopify checkout shipping implementation
  → requires: Phase B (Shopify brands must be registered to test)
  → independent from C/D/E
```

**Recommended phase sequence:**

| Phase | Feature(s) | Key files touched |
|-------|-----------|-------------------|
| 1 | is_active enforcement backend | brand_service.py, routes_brands.py (new PATCH endpoint) |
| 2 | 9 competitor brand data + engine detection | data/brands.json, category_resolver.py |
| 3 | Comparative search history + preloadedJobId wiring | routes_search.py, App.tsx (prop passing only) |
| 4 | Frontend global store (tab-switch survival) + brand toggle UI | searchStore.ts, App.tsx (AnimatePresence key), SettingsPage |
| 5 | Category diagnostics | category_diagnostics_service.py, routes_diagnostics.py, UI panel |
| 6 | Shopify checkout shipping | shopify_engine.py, ShopifyApiClient |

Phases 5 and 6 are independent of each other and can be swapped or parallelized.

---

## Anti-Patterns

### Anti-Pattern 1: Per-Call is_active Filtering

**What:** Adding `if not brand.is_active: continue` in `search_all_brands`, `search_products`, and `export_search_products` separately.

**Why wrong:** Any new call site (e.g., future monitoring routes) will miss the filter. The bug will recur silently.

**Do instead:** Filter once in `brand_service.list_brands(active_only=True)` and trust the chokepoint.

### Anti-Pattern 2: Converting Synchronous Search to Async Job for State Survival

**What:** Making `POST /search` return a job_id immediately and polling for results to avoid the frontend state-loss problem.

**Why wrong:** Requires Celery or background tasks, Redis, and a polling loop on the frontend. The actual problem (state lost on tab switch) is solved entirely in the frontend with a store — no backend change needed for PERS-01.

**Do instead:** Use a module-scoped frontend store. The backend change needed for HIST-01 (saving comparative searches to history) is a small addition to the existing synchronous handler, not an architectural overhaul.

### Anti-Pattern 3: Routing VTEX Shipping Through `calculate_shipping` Hook

**What:** Implementing `VTEXEngine.calculate_shipping()` to call the VTEX checkout simulation, replacing the current in-client shipping flow.

**Why wrong:** VTEX shipping already works correctly inside `VtexApiClient.search()` when `include_shipping=True`. Moving it to the engine hook would duplicate the logic and risk breaking the existing working flow.

**Do instead:** Leave VTEX shipping in `VtexApiClient`. Document the split clearly. Only implement `calculate_shipping` for engines where it is genuinely missing (Shopify).

### Anti-Pattern 4: Removing AnimatePresence to Fix State Loss

**What:** Deleting the `AnimatePresence` wrapper and `motion.div key={activeTab}` to prevent unmounting.

**Why wrong:** Removes all tab-transition animations, which is a UX regression. The real fix (module-scoped store) preserves animations while solving state persistence.

**Do instead:** Keep `AnimatePresence`. The store holds state; components read from it on mount.

---

## Integration Points

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `brand_service` → `engine_factory` | Direct import, `list_brands()` call | Add `active_only=True` parameter here |
| `routes_search.py` → `search_history_service` | Direct import, `create_job`/`update_job` | Already wired for cross; add for comparative |
| `App.tsx` → `SearchPage`/`CrossMarketplacePage` | Props | `preloadedJobId` prop already defined, wiring in `renderTab()` missing |
| `App.tsx` → `searchStore` | Module import | New; replaces local `useState` |
| `CategoryDiagnosticsService` → `BaseEngine` | `discover_categories()` + new `probe_category()` | probe_category is a new optional method |

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Shopify shipping rates API | `POST /checkouts.json` → `GET /checkouts/{token}/shipping_rates.json` | Unauthenticated; session-based cart required |
| VTEX category count | `GET /api/catalog_system/pub/products/search?fq=C:/X/&_from=0&_to=0` | Returns `resources: "0-0/N"` header; cheap probe for diagnostics |
| Supabase brands table | Already wired via `_upsert_to_supabase()` | `is_active` field must be in the Supabase schema if not already |

---

## Sources

- Direct code inspection: `services/engines/factory.py`, `services/engines/base_engine.py`, `services/engines/shopify_engine.py`, `services/engines/vtex_engine.py`
- Direct code inspection: `services/brand_service.py`, `core/models.py`, `services/search_history_service.py`
- Direct code inspection: `api/routes_search.py`, `api/routes_brands.py`, `api/routes_history.py`
- Direct code inspection: `frontend/src/App.tsx` (all 1875 lines)
- Confidence: HIGH — all findings are from live codebase, no inference from external sources required

---

*Architecture research for: Intelligence Scraper v2.0 — integration of MGMT-01/02, PERS-01, HIST-01, DIAG-01, FRET-05, COMP-01*
*Researched: 2026-06-18*
