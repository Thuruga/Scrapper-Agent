# Feature Research — v2.0

**Domain:** Fashion-price intelligence scraping platform (multi-brand, multi-engine)
**Researched:** 2026-06-18
**Confidence:** HIGH (based on direct codebase inspection + domain reasoning; no external sources needed)

---

## Context: What Already Exists

The following features are SHIPPED and must not be re-implemented:

- Brand registry (`BrandManagerService`, `DynamicBrand` with `is_active: bool = True` field present but ignored by search)
- Multi-engine scraping: VTEX, Shopify, Mercado Livre, Netshoes, Amazon
- Engine auto-detection (`detect_engine()` in `routes_brands.py`: tries `collections.json` → VTEX category tree → HTML fingerprint)
- Comparative search (`POST /search`) and cross-marketplace SKU search (`POST /search/cross-marketplace`)
- Category mapping per brand (`CategoryMapping`, `update_mappings` endpoint)
- Relevance engine (brand gate + model discrimination + CLIP visual)
- Excel export for both search types
- Search history (`SearchHistoryService`, `GET /history`) — but only SKU search is saved; comparative (`/search`) is NOT saved
- Shipping: `ShippingInfo` model, `calculate_shipping` on ML (API-based), Amazon+Netshoes (Playwright), VTEX shell (`return None` — not implemented)
- Shared API-key auth

---

## Feature Areas for v2.0

### Area 1: Multi-Brand Competitor Onboarding (COMP-01)

**What it is:** Adding 9 new brands (Lacoste, Levi's, Richards, HugoBoss, Calvin Klein, Track&Field, Austral, Zapalla, Zara) with correct engine detection and category mapping; handling brands whose platform is not yet supported (Wake Commerce).

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Brand registered and scraping returns products | Adding a brand without verifiable results is meaningless | MEDIUM | Requires mapping at least the primary categories (polos, camisas, camisetas, calças) per brand; auto-detection handles engine field |
| Engine correctly auto-detected per brand | Users assume the system knows how to talk to each site | LOW | `detect_engine()` already exists; just needs to run per brand on onboard |
| Unsupported platform surfaced as a clear status, not a silent failure | Users need to know WHY a brand is not returning results | LOW | Wake Commerce brands (e.g., Shop2gether) — show `engine: "unsupported"` or `status: "pending_engine"` with explanation |
| Category mappings added to canonical set | Brands with zero mappings show zero products in category scans | MEDIUM | Each new brand needs its VTEX `fq` paths (or Shopify collection handles) mapped to canonical slugs (camisas, polos, camisetas, calças, shorts, acessórios) |
| Brand appears in search results immediately after onboarding | User expects new brand to show in comparative and SKU searches | LOW | `engine_factory.search_all_brands` already picks up all registered brands; no extra wiring needed |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Validation smoke-test on onboard: fetch first page of one category and confirm N products returned | Catches bad domains, wrong engine, 403s before brand is "green" | MEDIUM | POST `/brands/` could trigger a quick probe; result stored on brand record as `last_probe_status` |
| Unsupported-platform brands visible in dashboard with "Aguardando motor Wake Commerce" label | Transparency over silent exclusion | LOW | UI-only change; brand exists in registry, engine field = "unsupported", excluded from scraping |
| Auto-discovery of categories runs after engine detection and proposes a mapping draft | Saves operator time; VTEX `discover_categories()` and Shopify `discover_categories()` already exist | MEDIUM | UI wizard: detect engine → discover categories → pick canonical mappings → save |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Auto-mapping all discovered categories to canonical slugs without human review | "Less work" | VTEX category trees have noise (outlet, sale, "Todos", "Hidden"); wrong mappings produce garbage in category scans | Show discovered categories for operator to manually assign to canonical slugs; default = unmapped |
| Building a Wake Commerce engine in this milestone | 2 brands depend on it (Shop2gether) | Scope blowout; Wake Commerce has no public JSON API, requires full Playwright reverse-engineering | Register brands with `engine: "unsupported"`, defer engine to next milestone |
| Scraping all categories on onboard (full sync) | "Why not index everything now?" | 9 brands × N categories = hours of Playwright; blocks user; fails silently on rate limits | Onboard registers the brand and mappings; scraping is triggered manually per category or via scheduler |

---

### Area 2: Brand Activation / Deactivation (MGMT-01, MGMT-02)

**What it is:** Toggle `is_active` on a brand; inactive brands are excluded from all search, monitoring, and exports. A brand-management UI panel supports add / remove / deactivate actions.

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| `PATCH /brands/{brand_key}` endpoint to toggle `is_active` | `is_active` field already exists in `DynamicBrand` but is never read by search or factory | LOW | Add endpoint; `BrandManagerService._save()` handles persistence |
| `engine_factory.search_all_brands` filters out inactive brands | Core promise: disabled brand disappears from results | LOW | One-line filter in `EngineFactory.search_all_brands`: skip brands where `brand.is_active == False` |
| `POST /search` and `POST /search/cross-marketplace` both respect `is_active` | Both search paths call `engine_factory` — one fix covers both | LOW | Covered by the factory filter above |
| Category monitor excludes inactive brands | Users expect "disabled" to mean disabled everywhere, including background jobs | LOW | `load_monitored_categories` / `run_category_scan` should check `is_active` before running |
| Deactivation is reversible (reactivate restores brand to all results) | Standard toggle UX; soft-delete, not hard-delete | LOW | Already possible since the field is a bool; just expose PATCH endpoint |
| UI toggle visible per brand in the brand management panel | Users assume a UI control exists | LOW | Toggle switch in SettingsPage brand list |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Visual distinction in brand list: active vs inactive brands | Prevents confusion about why a brand returns no results | LOW | Grey out or badge "Inativo" in sidebar brand filter and settings panel |
| Inactive brands still visible in history (past searches retain their data) | Deactivation should not erase historical records | LOW | History records `brands: List[str]` — the list is a snapshot; no change needed to history service |
| Confirmation dialog before deactivating a brand | Prevents accidental deactivation during routine UI interaction | LOW | Single-step toast confirmation |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Hard-delete via deactivation button | "Remove from system" feels complete | Loses category mappings, history associations, config; hard to recover | Keep delete as a separate destructive action (`DELETE /brands/{key}`), deactivate is just the toggle |
| Deactivation retroactively purging brand from history records | "Clean slate" feeling | Breaks audit trail; re-activating brand would show inconsistent history | Inactive only affects FUTURE searches; history is immutable |
| Auto-deactivating brands that return errors | "Smart" housekeeping | Error may be transient (site down); auto-disable surprises users and hides real scraping failures | Show error status in diagnostics (DIAG-01) without touching `is_active` |

---

### Area 3: Search Robustness — In-Flight Persistence + Complete History (PERS-01, HIST-01)

**What it is:** (a) A running search survives navigating to another tab — state is not lost on component unmount. (b) Both search types (comparative `/search` and SKU `/search/cross-marketplace`) are saved to history and can be re-opened.

#### Table Stakes

**PERS-01 — In-flight search survives tab navigation:**

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Switching to another sidebar tab does not cancel an in-progress search | Users navigate while waiting; losing results after 30+ seconds is unacceptable | MEDIUM | Root cause: `loading`/`results` state lives in `CrossMarketplacePage` and `SearchPage` components, which unmount on tab switch. Fix: lift state to a global store (React Context or Zustand at root `App` level) |
| Returning to the search tab shows the result (or spinner if still loading) | Natural expectation of in-progress work | LOW | Once state is global, the component reads from store on mount |
| No duplicate request when returning to a tab with an in-progress search | Prevents double-billing API calls and race conditions | LOW | Guard: if `loading === true` in store, do not re-fire on tab switch |
| Notification (toast) when search completes while user is on another tab | User doesn't have to poll | LOW | Already exists as a pattern in `MonitorPage`; replicate for search completion |

**HIST-01 — Complete search history:**

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Comparative search (`/search`) creates a history record on execution | SKU search is saved; comparative not saving is an obvious gap | LOW | `SearchHistoryService.create_job()` exists; `routes_search.py` `search_products()` just needs to call it with `type="search"` |
| Comparative search results are saved to history (not just metadata) | Re-opening a historical comparative search should show the actual results | MEDIUM | `SearchHistory.results: Optional[Any]` field already exists; `update_job(results=...)` needs to be called after the search completes — same pattern as SKU search |
| History list shows both search types with visual distinction | Users can tell comparative vs SKU searches apart | LOW | `type` field already in `SearchHistory` model ("search" vs "cross"); UI needs icon/label per type |
| Clicking a history item re-displays that search's results without re-running | Fast restore; no extra API call | LOW | Already implemented for SKU search via `onClearPreloadedJob`/`onPreloadedJob` pattern; needs same wiring for comparative search |
| History list is sorted newest-first | Standard list UX | LOW | Already implemented in `SearchHistoryService.list_jobs()` |
| 30-day retention (auto-cleanup on load) | Prevents unbounded disk growth | LOW | Already implemented in `cleanup_old_records()` |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| History item shows result count + brands searched | Preview before re-opening | LOW | `brands: List[str]` and `results` length derivable from stored data |
| Manual delete of individual history items | User housekeeping | LOW | `DELETE /history/{job_id}` already exists; needs UI button |
| "Re-run" action on a history item (fresh search with same params) | Repeat a past search with current prices | LOW | Extract query + brands from history record, fire new search |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Persisting in-flight state to `localStorage`/`sessionStorage` | "Survive browser refresh" | Cross-marketplace search can take 30-60 seconds; storing partial streaming results in localStorage creates stale/incomplete data bugs | Global React state is sufficient; page refresh losing state is acceptable. Full persistence belongs to a server-side job model (out of scope) |
| Background search that continues after browser tab is closed | "Fire and forget" | Requires WebWorker or server-side async job queue — architectural change; not aligned with current synchronous request model | In-flight survives tab switches within the SPA only |
| Infinite history retention | "Keep everything" | Disk grows unbounded on dev machine / small VPS; 30-day window covers all operational needs | Keep 30-day cleanup; add manual delete for individual items |
| Auto-re-running searches on history open | "Show fresh data" | Defeats the purpose of history (re-run is a separate explicit action) | Keep history as snapshot; offer explicit "Re-run" button |

---

### Area 4: Engine Diagnostics — Category Health Report (DIAG-01)

**What it is:** The system identifies, per brand and engine, which configured categories return zero products and which return errors during scraping — presented in a trackable, actionable report.

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Per-brand list of categories with their last scrape status (ok / empty / error) | Users need to know which categories are broken before trusting the data | MEDIUM | Requires augmenting `CategoryMapping` or `monitored_categories` with `last_status`, `last_scraped_at`, `product_count` fields |
| "Empty" category detected and flagged (0 products returned, no error) | Empty ≠ error; both need tracking | MEDIUM | `run_bulk_scrape` already yields products; count yielded items, if 0 → status = "empty" |
| "Error" category detected and flagged (exception during scrape) | Silent failures are the worst kind of empty | MEDIUM | Wrap `engine.run_bulk_scrape` in try/catch within the diagnostic runner; store exception message |
| Report accessible in UI (not just backend logs) | Operational usefulness | MEDIUM | New panel in dashboard or expandable section in brand settings |
| Report shows: brand, category name/path, status, last-checked timestamp | Minimum actionable data | LOW | Data model fields |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| One-click "re-probe" per category from diagnostic panel | Operator can retry a flaky category without re-running everything | MEDIUM | Reuses existing `/scrape-category` endpoint; diagnostic panel triggers single-category probe |
| Summary dashboard widget: "X of Y categories healthy" per brand | At-a-glance operational status | LOW | Derived count from diagnostic data |
| Error message shown in diagnostic (not just "error" status) | Operators can distinguish 403, timeout, zero-results, parsing error | LOW | Store `error_message: Optional[str]` on diagnostic record |
| Historical status changes tracked (was OK, now empty — NEW flag) | Catches regressions | HIGH | Requires time-series log of status per category; likely overkill for v2.0 |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Auto-disabling categories that are empty/errored | "Smart" maintenance | A category may be empty legitimately (seasonal, sold out) or transiently; auto-disable hides the real issue | Flag with status; let operator decide to remove the mapping |
| Running diagnostics continuously (polling every N minutes per category) | "Always fresh" | Duplicates category monitor functionality; burns resources on all categories equally | Diagnostic probe is triggered manually or on a separate low-frequency schedule distinct from the monitoring job |
| Per-product-level error tracking in diagnostics | "Granular debugging" | Too much data; diagnostic is about category health, not product-level quality gates | Quality gate rejections already logged per scrape session; not stored in diagnostic records |

---

### Area 5: Checkout-Based Shipping (FRET-05)

**What it is:** Extract shipping price and delivery time via checkout simulation across more engines beyond VTEX. Currently: ML has API-based shipping (`_fetch_shipping_options`); Amazon + Netshoes have Playwright-based checkout (`calculate_shipping_advanced`); VTEX `calculate_shipping` returns `None`.

**Current state by engine:**
- Mercado Livre: WORKING (API `/shipping_options`)
- Amazon: WORKING (Playwright, `calculate_shipping_advanced`)
- Netshoes: WORKING (Playwright, `calculate_shipping_advanced`)
- VTEX (brand sites): NOT WORKING — `calculate_shipping()` returns `None`
- Shopify (brand sites): NOT WORKING — not implemented

The primary gap for FRET-05 is **VTEX brand sites** (Lacoste, Levi's, Richards, Aramis self-check, etc.) and **Shopify brand sites**.

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Shipping price displayed per product in cross-marketplace and comparative results | `ShippingInfo` model and `shipping_price`/`landed_price` fields already defined; users see them for ML/Amazon/Netshoes; brand site cards show nothing | HIGH | VTEX shipping requires a CEP-specific API call: `POST /api/checkout/pub/orderForms/simulation` with SKU items — this is the standard VTEX checkout simulation endpoint |
| Free-shipping detection (`is_free_shipping: True`) | Users make buying decisions on total landed cost | LOW | VTEX simulation response includes `logisticsInfo[].slas[].price` = 0 means free |
| Delivery time (ETA in days) extracted alongside price | Price without ETA is only half the picture | MEDIUM | VTEX simulation response includes `slas[].deliveryWindow` or `deliveryIds[].estimatedDate`; normalize to integer days |
| CEP passed from search form to all engines consistently | User provides CEP once; all engines should use it | LOW | Already plumbed through `zipcode` parameter in `search_all_brands`; VTEX engine just needs to act on it |
| Per-product "Calcular frete" button falls back to on-demand calculation if not pre-fetched | Not all searches include shipping; on-demand path needed | LOW | Already exists for ML/Amazon/Netshoes via `POST /search/calculate-shipping`; needs VTEX implementation |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Shipping fetched in parallel with product search (not sequential) | Adds minimal latency vs separate call per product | MEDIUM | VTEX simulation can batch multiple SKUs in one call; structure `run_bulk_scrape` to batch-fetch shipping at end of page scrape |
| Shopify shipping calculation (brand sites on Shopify) | Closes the gap for Shopify brands in v2 (Austral, Zapalla if on Shopify) | HIGH | Shopify checkout simulation requires product variant ID + shipping address; no standard public API — needs Playwright or unofficial storefront API |
| "Frete grátis acima de R$X" inference from free-shipping threshold text | Some VTEX stores show "free shipping over R$299" on PDP | MEDIUM | Parse `raw_text` in ShippingInfo; flag `is_free_shipping: True` when product price >= threshold |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Pre-fetching shipping for ALL products in ALL categories during bulk scrape | "Complete data" | VTEX checkout simulation is one request per SKU; 500 products = 500 extra HTTP calls; multiplied by N brands = rate-limit bans and 10x slower scrapes | Shipping on bulk scrape is opt-in (`include_shipping: bool = False`); on-demand per-product button remains the default UX |
| Shipping calculation without a CEP configured | Appears to work but returns national flat rate, not user-relevant | Misleads users making location-specific decisions | Require CEP field; show "configure CEP to see shipping" placeholder when not set |
| Playwright-based VTEX shipping (headless browser on every product) | "Works for sites that block API" | VTEX checkout simulation API is public and reliable; Playwright is heavyweight, fragile, and banned by some CDN configs | Use VTEX REST checkout simulation API (`/api/checkout/pub/orderForms/simulation`); only fall back to Playwright if API returns 403/404 |
| Storing historical shipping prices (price timeline for freight) | "Trend analysis" | Shipping price volatility is low; adds storage cost without proportional value in v2 | Ship current-price only; trend is a future backlog item |

---

## Feature Dependencies

```
COMP-01 (9 new brands onboarded)
    └──enables──> MGMT-01 (more brands to manage = deactivation becomes useful)
    └──enables──> DIAG-01 (more engines/categories = more to diagnose)
    └──enables──> FRET-05 (new VTEX/Shopify brands need shipping coverage)

MGMT-01 (is_active toggle backend)
    └──requires──> MGMT-02 (UI panel must expose the toggle)

PERS-01 (global search state store)
    └──enables──> HIST-01 (comparative search results can be captured to save to history)

HIST-01 (comparative search saved to history)
    └──requires──> existing SearchHistoryService (already built)
    └──requires──> routes_search.py calling create_job/update_job (not yet called for /search)

FRET-05 (VTEX shipping)
    └──requires──> existing ShippingInfo model (already built)
    └──requires──> existing zipcode plumbing in search_all_brands (already built)
    └──requires──> VTEX checkout simulation API call (new code in VTEXEngine.calculate_shipping)

DIAG-01 (category diagnostics)
    └──requires──> COMP-01 partial (new brands' mappings are the primary source of new diagnostic coverage)
    └──enhances──> existing CategoryMonitorService (diagnostic can reuse scrape infrastructure)
```

### Dependency Notes

- **PERS-01 must precede HIST-01 in implementation:** Lifting search state to global store is the prerequisite for reliably capturing comparative results before they vanish on tab switch. Technically HIST-01 can be done independently (just call `create_job` in the route), but the full user story (re-open shows results) requires the state to survive navigation.
- **COMP-01 is independent of all other areas:** Can be done first (data work: domains, category paths, brand_key registration). Does not block MGMT or DIAG.
- **FRET-05 VTEX implementation is independent of Shopify:** VTEX checkout simulation is achievable with existing HTTP client; Shopify shipping is higher complexity and can be deferred.
- **MGMT-01 backend and MGMT-02 frontend are tightly coupled:** The backend PATCH endpoint is trivial (5 lines); UI work is the bulk of MGMT-02.

---

## MVP Definition

### Launch With (v2.0)

- [x] **COMP-01** — 9 brands registered with correct engine + primary category mappings; unsupported-platform brands flagged, not silently broken
- [x] **MGMT-01** — `is_active` respected by engine factory and search routes
- [x] **MGMT-02** — Toggle in UI + brand management panel
- [x] **PERS-01** — Global state store for in-flight search survival
- [x] **HIST-01** — Comparative search saved and re-displayable; history list shows type distinction
- [x] **DIAG-01** — Per-brand category health report with ok/empty/error status
- [x] **FRET-05 (VTEX)** — VTEX checkout simulation for shipping price + ETA on brand sites

### Add After Validation (v2.x)

- [ ] FRET-05 (Shopify) — Shipping for Shopify brand sites; harder due to no standard API
- [ ] DIAG-01 historical tracking — Time-series of category status changes
- [ ] Brand onboard wizard — Auto-discover + draft category mapping flow

### Future Consideration (v3+)

- [ ] Wake Commerce engine — Enables Shop2gether and other Wake-based brands
- [ ] Per-user access profiles — ARAMIS/URBAN/NEXT/MARKETPLACE login tiers
- [ ] Server-side search jobs — Background execution that survives browser close

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| COMP-01: 9 brands onboarded | HIGH (direct coverage expansion) | MEDIUM (data work + category mapping) | P1 |
| MGMT-01: is_active backend | HIGH (controls what appears in all searches) | LOW (1 endpoint + 1 filter line) | P1 |
| MGMT-02: brand management UI | HIGH (makes MGMT-01 usable) | LOW-MEDIUM (toggle + panel) | P1 |
| PERS-01: global search state | HIGH (stops losing work in progress) | MEDIUM (React Context/Zustand lift) | P1 |
| HIST-01: comparative search history | MEDIUM (parity gap, users notice it's missing) | LOW (route calls `create_job`; model already exists) | P1 |
| DIAG-01: category health report | HIGH (ops cannot trust data without it) | MEDIUM (new status fields + UI panel) | P1 |
| FRET-05 (VTEX): checkout shipping | MEDIUM (fills a gap; VTEX brands show no shipping today) | MEDIUM (checkout simulation API) | P2 |
| FRET-05 (Shopify): checkout shipping | LOW (few Shopify brands with new onboarding) | HIGH (no public API; Playwright) | P3 |
| Brand onboard wizard UI | LOW (CLI/API onboard is sufficient for now) | HIGH (full wizard UX) | P3 |

**Priority key:**
- P1: Must have for v2.0 launch
- P2: Should have, ship if implementation is clean
- P3: Nice to have, defer to v2.x

---

## Complexity and Dependency Summary by Area

| Area | Backend Complexity | Frontend Complexity | Key Dependency | Risk |
|------|--------------------|---------------------|----------------|------|
| COMP-01 Onboarding | LOW (data entry + auto-detect exists) | LOW (brands already render) | None | MEDIUM — category paths require manual research per brand |
| MGMT-01/02 Activation | LOW backend | LOW frontend | `is_active` field already in model | LOW |
| PERS-01 Search persistence | LOW-MEDIUM (no backend change needed) | MEDIUM (React state lift) | None | LOW-MEDIUM — need to verify no memory leak on long-running searches |
| HIST-01 Complete history | LOW (route calls existing service) | LOW (type distinction in list UI) | PERS-01 (for full re-display) | LOW |
| DIAG-01 Category diagnostics | MEDIUM (new fields + diagnostic runner) | MEDIUM (new UI panel) | COMP-01 partial | MEDIUM — defining "empty" vs "error" boundary cases |
| FRET-05 VTEX shipping | MEDIUM (checkout simulation API) | LOW (field already in UI card) | Zipcode plumbing (exists) | MEDIUM — VTEX stores vary in checkout API responses |

---

## Sources

- Direct codebase inspection: `services/brand_service.py`, `services/search_history_service.py`, `services/engines/factory.py`, `services/engines/vtex_engine.py`, `services/engines/mercado_livre_engine.py`, `services/engines/amazon_engine.py`, `services/engines/netshoes_engine.py`, `api/routes_brands.py`, `api/routes_search.py`, `api/routes_history.py`, `frontend/src/App.tsx`, `frontend/src/api/client.ts`, `core/models.py`
- Project context: `.planning/PROJECT.md` (v2.0 requirements COMP-01, MGMT-01/02, PERS-01, HIST-01, DIAG-01, FRET-05)
- VTEX Checkout Simulation API: standard VTEX public endpoint `POST /api/checkout/pub/orderForms/simulation` (HIGH confidence — well-known VTEX developer pattern)

---

*Feature research for: Intelligence Scraper v2.0 — Cobertura de Concorrentes & Confiabilidade*
*Researched: 2026-06-18*
