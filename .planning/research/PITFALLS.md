# Pitfalls Research

**Domain:** Multi-engine fashion scraper — adding v2.0 features to existing Python/React system
**Researched:** 2026-06-18
**Confidence:** HIGH (derived from direct codebase inspection, not speculation)

---

## Critical Pitfalls

### Pitfall 1: `is_active` is stored in the model but never read anywhere in the search path

**What goes wrong:**
`DynamicBrand.is_active` exists in `core/models.py:232` with `default=True`. However, every call site that builds the brand list — `routes_search.py:144`, `factory.py:70`, `routes_brands.py:72` — calls `brand_service.list_brands()` without filtering on `is_active`. A deactivated brand will still appear in comparative searches, export, category scraping target list, the scheduler's `run_category_scan`, and the brand dropdown in the frontend. The field is purely decorative today.

**Why it happens:**
The field was added to the model in anticipation of this feature but the enforcement layer was never built. When adding a toggle in the settings UI, developers will flip the flag and assume the system respects it — it does not.

**How to avoid:**
Add filtering at the single authoritative layer: `BrandManagerService.list_brands()` must filter `is_active=True` by default, with an optional `include_inactive=True` param for the management UI. Every other call site already goes through `list_brands()` or `get_brand()`, so one change propagates everywhere. Do not filter per-callsite — that approach guarantees a missed path.

Audit all four code paths before shipping:
1. `factory.py:70` — `search_all_brands` default brand list
2. `routes_search.py:144,228` — comparative search and export endpoints
3. `category_monitor_service.py` — scheduler job (does not check brand status at all)
4. `routes_brands.py:72` — `list_brands` API used by frontend brand filter

**Warning signs:**
- Deactivated brand still returns results in search
- Deactivated brand still appears in the brand chip filter in `SearchPage`
- Category monitor `run_category_scan` runs for a deactivated brand's registered category

**Phase to address:** Brand management phase (MGMT-01). Must be the first thing implemented — no UI toggle should be wired up until enforcement is confirmed in all four paths.

---

### Pitfall 2: Wake Commerce looks like VTEX to `detect_engine` and silently scrapes nothing

**What goes wrong:**
`detect_engine` in `routes_brands.py:14-53` has three probes: Shopify via `/collections.json`, VTEX via `/api/catalog_system/pub/category/tree/1`, and then HTML parsing for VTEX/Shopify strings. Wake Commerce is a VTEX white-label headless platform: the storefronts (e.g. Shop2gether, and potentially some of the 9 new brands) serve HTML that contains `vtexassets.com` or similar CDN references because the theme layer is still VTEX-based, but the catalog/search API is not the standard VTEX `catalog_system` — it is Wake's own GraphQL layer. The HTML probe at step 3 will return `"vtex"`. The brand gets registered as VTEX engine. Every search returns 0 results or an HTTP error, silently absorbed by the `BrandSearchResult(error=str(e))` catch in `factory.py:88`.

**Why it happens:**
Wake Commerce uses VTEX infrastructure under the hood (CDN, checkout token) but replaces the catalog API. A surface-level HTML scan cannot distinguish the two. There is no Wake-specific probe in `detect_engine`.

**How to avoid:**
Add a Wake Commerce detection probe to `detect_engine` before the VTEX HTML fallback:

```python
# Try Wake-specific GraphQL endpoint
try:
    async with session.post(
        f"{base_url}/graphql",
        json={"query": "{ shop { name } }"},
        timeout=aiohttp.ClientTimeout(total=5),
        headers=headers
    ) as resp:
        if resp.status == 200:
            data = await resp.json()
            if "data" in data and "shop" in data.get("data", {}):
                return "wake"  # unsupported — flag for deferral
except Exception:
    pass
```

Alternatively, maintain a static allowlist of known-Wake domains (shop2gether.com.br, etc.) checked before auto-detect. The system must return `"wake"` (or `"unsupported"`) and the brand registration endpoint must reject it with a clear 422 explaining the platform is not yet supported.

For the 9 new brands: manually verify each brand's platform before onboarding. Signs a site is Wake: GraphQL endpoint responds at `/graphql`, product listing pages use Apollo or urql client-side fetching, and the standard VTEX search API (`/api/catalog_system/pub/products/search`) returns 404 or empty.

**Warning signs:**
- Brand registered, search returns 0 products consistently with no logged error
- `BrandSearchResult.error` is non-null for the brand on every search
- Visiting `{brand_domain}/api/catalog_system/pub/category/tree/1` returns 404

**Phase to address:** Brand onboarding phase (COMP-01). The Wake detection gate must be built before adding any of the 9 new brands. A brand with `engine="wake"` or `engine="unsupported"` must be excluded from all search and monitoring operations — treat it like a deactivated brand until the engine is built.

---

### Pitfall 3: Frontend WebSocket in `CategoryPage` has no cleanup on unmount

**What goes wrong:**
In `App.tsx`, `renderTab()` returns a fresh component for the active tab. When the user switches away from the "Categorias" tab while a scrape is running, `CategoryPage` unmounts. The `wsRef.current` WebSocket is never closed on unmount because there is no `useEffect` cleanup returning `ws.close()`. The WebSocket connection stays open. The backend job continues running. If the user returns to the tab, `startScrape` can create a second WebSocket for a new job while the old one is still open. Two simultaneous connections receive messages and both call `setLogs`, causing interleaved log output from two different jobs.

The `isScraping` state is lost on unmount (local `useState`), so the "Iniciar Varredura" button becomes enabled again when the user returns, even though a scrape is running on the backend.

**Why it happens:**
WebSocket lifetime is tied to component mount. Tabs unmount on switch (`AnimatePresence mode="wait"` replaces the component). There is no global scrape state.

**How to avoid:**
Short-term (safe, non-breaking): Add a cleanup effect to `CategoryPage`:
```typescript
useEffect(() => {
  return () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.close();
    }
  };
}, []);
```
This at minimum prevents dangling connections.

Long-term (required for PERS-01): Move scrape job state to a global store (Zustand or React context) so `isScraping`, `logs`, and `wsRef` survive tab switches. This is the same refactor needed for search state — do them together.

**Warning signs:**
- Browser DevTools Network tab shows `ws://` connections accumulating after tab switches
- Log console shows duplicate/interleaved messages after returning to the Categorias tab
- Backend `asyncio.gather` reports two concurrent bulk scrape tasks for the same job

**Phase to address:** Frontend state refactor phase (PERS-01). The WebSocket cleanup fix is a prerequisite that should be done even if the full global store is deferred.

---

### Pitfall 4: Lifting search state to a global store without guarding the existing synchronous fetch pattern will cause double-fetches and stale-closure bugs

**What goes wrong:**
`SearchPage` and `CrossMarketplacePage` currently manage all state locally (`useState`). When lifting to a global store (Zustand, Context, or Redux), the most common mistake is:

1. The component reads from the store on mount and triggers a fetch if `results === null` — but the results are already being fetched from the previous mount. Two concurrent `ApiClient.search()` calls run in parallel. The second one resolves and overwrites the first with identical or stale data.

2. The `handleSearch` closure captures `query`, `sort`, and `selectedBrands` from the render at submit time. If these are now derived from the store, a stale closure can fire `setResults` using a query string from a previous render after the user has already changed the query and started a new search.

3. `preloadedJobId` prop in the current `SearchPage` triggers a history reload via `useEffect`. After lifting state, if `preloadedJobId` is no longer cleared correctly (the `onClearPreloadedJob` callback pattern), switching from history to a fresh search will re-apply the history load on every remount.

**Why it happens:**
Lifting state without auditing every `useEffect` dependency array and every in-flight request cancellation. The current code has no `AbortController` on `ApiClient` calls.

**How to avoid:**
- Use an AbortController for every search fetch, cancel it on re-fetch or on component unmount.
- Add a `searchId` (monotonic counter or uuid) to every search. Discard `setResults` calls where the resolved `searchId` does not match the current one.
- When migrating to global store, keep a `status: idle | loading | done | error` field next to `results`. The component mounts, checks `status`. If `loading`, it renders the spinner and does not re-fetch. If `done`, it renders results immediately. Only if `idle` does it auto-fetch.
- The `preloadedJobId` mechanism must be replaced by a dedicated `historyLoad(jobId)` action that sets status explicitly — not a prop-driven `useEffect`.

**Warning signs:**
- Search result flickers (shows old results briefly before new ones)
- Two `POST /search` requests visible in Network panel for a single search action
- History results appear when user navigates away and back without clicking a history entry

**Phase to address:** Frontend state refactor phase (PERS-01). Design the store schema before writing any code. Must be reviewed against all three pages that use search state: `SearchPage`, `CrossMarketplacePage`, and `HistoryPage`.

---

### Pitfall 5: VTEX vs. Wake confusion during manual category mapping — VTEX `fq=C:/` paths do not work on Wake storefronts

**What goes wrong:**
`category_resolver.py` builds VTEX-style `fq=C:/dept/cat/` paths hardcoded for aramis, reserva, and tommy. If a new brand is registered as VTEX but is actually Wake (or a VTEX store with a non-standard category ID scheme), `resolve_query_to_vtex_category_path` will return a malformed path. The VTEX engine will send a search request with that `fq` parameter and receive either 0 results or an HTTP 400, silently caught and returned as an empty `BrandSearchResult`. The user sees an empty column and assumes no products exist.

Additionally, the `_BRAND_CATEGORY_PATHS` dict in `category_resolver.py` is static. When adding 9 new brands, developers may be tempted to hardcode their category IDs without verifying them against the live VTEX API (`/api/catalog_system/pub/category/tree/1`). Category IDs in VTEX are store-specific integers — they cannot be guessed or reused across accounts.

**Why it happens:**
Static category ID mapping is a shortcut that works for the first three brands but does not scale. New brand onboarding requires running `discover_categories()` per brand and mapping the returned IDs — not copying from another brand.

**How to avoid:**
- Never add a new brand's category IDs to `_BRAND_CATEGORY_PATHS` without fetching the live category tree first.
- Use the `/brands/{brand_key}/discover` endpoint (backed by `VTEXEngine.discover_categories()`) to confirm the IDs are valid before saving mappings.
- Add a validation step in the onboarding flow: after registration, auto-run discovery and surface the result count. Zero categories = signal for investigation.

**Warning signs:**
- `discover_categories()` returns an empty list for a newly registered brand
- Category filter returns 0 results where the live site shows products
- `fq` parameter in requests contains IDs that return HTTP 404

**Phase to address:** Brand onboarding phase (COMP-01), specifically the category mapping sub-step for each new brand.

---

### Pitfall 6: `detect_engine` returns `"vtex"` as the final fallback for any unrecognized platform

**What goes wrong:**
The last line of `detect_engine` is `return "vtex"` with no sentinel. This means any site that does not match Shopify or VTEX probes — including Wake Commerce, custom platforms, sites behind Cloudflare that block the probes, or sites with strict CSP — registers as VTEX engine. The brand is created, searches silently fail, and there is no indication to the operator that the engine assignment is wrong.

**Why it happens:**
A fallback was needed to avoid returning `None`. The VTEX assumption was reasonable when all initial brands were VTEX.

**How to avoid:**
Change the fallback to return `"unknown"` instead of `"vtex"`. In `EngineFactory.get_engine()`, add a guard: if `engine_type == "unknown"`, raise a descriptive exception rather than falling through to `VTEXEngine`. In the brand registration endpoint, return a warning to the frontend: "Engine could not be auto-detected. Please select manually." Do not allow a brand with `engine="unknown"` to participate in searches until it is manually corrected.

**Warning signs:**
- Brand registered, engine shows as VTEX in settings, all searches return 0
- `detect_engine` logs show all three probes failing for the domain

**Phase to address:** Brand onboarding phase (COMP-01). This is a one-line change with high leverage — implement it before registering any of the 9 new brands.

---

### Pitfall 7: New brands behind aggressive WAF/anti-bot blocking initial bulk scrape and discovery

**What goes wrong:**
`detect_engine` sends a plain `aiohttp` GET with a static Chrome User-Agent. Fashion brand sites with Cloudflare or Imperva WAF block this fingerprint immediately and return a 403 or a Cloudflare challenge page (HTML with no VTEX/Shopify markers). The probe fails, the brand registers as VTEX by default (see Pitfall 6), and category discovery subsequently fails with the same 403. Sites like Zara, Lacoste, and Hugo Boss are known to operate Cloudflare Enterprise.

**Why it happens:**
`aiohttp` with a static User-Agent has a trivially detectable TLS fingerprint and no browser-like behavior. These sites require either a real browser (Playwright) or `curl_cffi` for TLS impersonation. The existing hybrid scraping pipeline has this capability for product pages but `detect_engine` uses raw `aiohttp` in the session manager.

**How to avoid:**
- For domain detection specifically, use `curl_cffi` or Playwright rather than `aiohttp` if the `aiohttp` probe returns a non-2xx status.
- For discovery (`/api/catalog_system/pub/category/tree/1`), the API itself is usually unprotected even when the storefront is behind WAF. Test it directly with `curl` before assuming a block.
- For the initial bulk scrape of new brands, start with a small sample (single page, 10 products). If the rate exceeds what the brand site allows, add a configurable delay between pages in `VtexApiClient.scrape_category_paged`.
- Do not scrape all 9 brands in the same session simultaneously on first onboarding — stagger them.

**Warning signs:**
- `detect_engine` log shows probe returning status 403, 429, or 503
- Discovery returns an empty list even though the brand is known to be on VTEX
- Bulk scrape yields 0 products after the first page

**Phase to address:** Brand onboarding phase (COMP-01). Create a per-brand onboarding checklist that includes a manual WAF probe before automated detection.

---

### Pitfall 8: Checkout shipping `calculate_shipping` generalization breaks VTEX price unit assumptions

**What goes wrong:**
VTEX returns shipping costs in centavos (integer, e.g. `1990` = R$ 19.90). The existing `VtexApiClient` already performs the `/100` conversion, as verified in `test_vtex_api_client.py:174` (`assert prod.shipping.price == pytest.approx(19.90)  # 1990 / 100`). When implementing `calculate_shipping` for Shopify engine and potentially Wake Commerce, the new engine may return prices already in reais (float). If the shared `ShippingInfo` normalization layer applies `/100` unconditionally, Shopify prices become 1% of their real value. If it does not apply it at all, VTEX centavo values appear 100x inflated.

**Why it happens:**
Different platforms use different monetary units. There is no documented contract in `BaseEngine.calculate_shipping` specifying whether the return dict's `shipping_price` key should be in reais or centavos.

**How to avoid:**
Add an explicit docstring to `BaseEngine.calculate_shipping` stating: "Return `shipping_price` in BRL reais (float), not centavos. Each engine is responsible for its own unit conversion before returning." This makes the contract clear. Add a unit test for each new engine implementation that asserts `shipping_price < 500` for a typical shipping cost (values above 500 in BRL for domestic shipping are almost certainly a unit error).

Also add a sanity check in `ShippingInfo` validation: if `shipping_price > 500.0`, emit a warning log — this should not be the norm for domestic fashion shipping.

**Warning signs:**
- Shipping cost displayed as R$ 1990.00 (centavos not divided)
- Shipping cost displayed as R$ 0.19 (divided twice)
- `is_free_shipping: True` when the actual calculated cost is 0.0 (division of 0 centavos)

**Phase to address:** Checkout shipping phase (FRET-05). Add the unit contract docstring and the unit test before writing any new `calculate_shipping` implementation.

---

### Pitfall 9: Free-shipping false positive when `shipping_price` is `0.0` but not actually free

**What goes wrong:**
In `cross_marketplace_service.py:480`, after calling `engine.calculate_shipping`, the code stores `shipping_price` from the result. In `CrossMarketplacePage` in the frontend (`App.tsx:1260`), `is_free_shipping` is a separate boolean. If a new engine returns `{"shipping_price": 0.0, "is_free_shipping": False}` because the checkout simulator returned a zero-cost SLA (e.g. a promo SLA, an error that resolved to 0, or a region with no courier configured), the frontend will display `R$ 0.00 (Frete)` rather than `Frete Grátis` — but the `landed_price` calculation will also add 0 to the product price, which is correct. The reverse bug is worse: if an engine returns `{"is_free_shipping": True}` erroneously (e.g. the simulator API returned a 200 with a 0-cost SLA due to a CEP that has no coverage), the UI shows "Frete Grátis" badge and the landed price calculation excludes shipping. The actual order would have shipping cost.

**Why it happens:**
Checkout simulators on VTEX, Shopify, and others return their cheapest or fastest SLA, not necessarily the correct one for the customer's CEP. An unconfigured CEP can silently return a 0-cost placeholder.

**How to avoid:**
- When `shipping_price == 0.0 and is_free_shipping == False`, treat it as uncalculated rather than zero-cost: set `shipping_price = None` and surface the "Calcular Frete" button.
- Validate the returned CEP coverage: if the simulate endpoint explicitly returns a free-shipping SLA with a label like "Frete Grátis" in the SLA name, trust it. If it returns a 0.0 numeric cost with no such label, treat it as suspect.
- Add a regression test: POST the shipping calculate endpoint with a clearly rural CEP (00000-001 or similar) that has no courier coverage and assert that the response is `null` or `unknown`, not `{"shipping_price": 0.0}`.

**Warning signs:**
- "Frete Grátis" badge appears for brands that never offer free shipping
- Landed price is lower than expected and matches product price exactly
- Shipping calculation for CEP outside São Paulo metro returns 0

**Phase to address:** Checkout shipping phase (FRET-05).

---

### Pitfall 10: Category diagnostics cannot distinguish "legitimately empty" from "scrape error" or "mapped to wrong category ID"

**What goes wrong:**
When implementing DIAG-01 (identify categories with no products or errors), a naive implementation checks `len(products) == 0` and flags the category as problematic. But there are three distinct causes of zero products: (a) the category is genuinely empty on the brand's site, (b) the `fq=C:/...` path is incorrect (wrong category ID), and (c) the scrape request returned an error (WAF block, timeout, network failure). All three produce zero products. Without distinguishing them, operators will investigate empty categories that are legitimately empty and miss real scraping errors.

**Why it happens:**
`run_bulk_scrape` in `VTEXEngine` uses an async generator. When the generator yields nothing, the caller cannot tell if that was because the API returned an empty array or because an exception was raised and caught (the `try/except` in `category_monitor_service.py:72` swallows errors and produces zero products).

**How to avoid:**
Add a status return to the diagnostic: instead of just a product count, emit a structured result per category:
```python
{
    "category_url": url,
    "products_found": 0,
    "status": "empty" | "error" | "ok",
    "error_detail": "HTTP 403" | None,
    "http_status": 403 | None
}
```
At minimum, distinguish HTTP 2xx with empty response (legitimately empty) from non-2xx or exception (scrape error) from HTTP 2xx with non-zero response (ok). The diagnostic endpoint for DIAG-01 should surface this distinction.

A "transient vs. persistent" error check: run the category probe twice with a 30-second gap. A 403 on both runs is persistent. A 503 on the first and 200 on the second is transient. Persistent errors should trigger a flag; transient errors should be logged but not alarmed.

**Warning signs:**
- Diagnostic reports show the same categories as "empty" on every run (likely wrong category ID)
- Diagnostic shows categories as "ok" even when the site is blocking all requests (error being swallowed)

**Phase to address:** Engine diagnostics phase (DIAG-01).

---

### Pitfall 11: `SettingsPage` brand list shows inactive brands with no visual distinction and no toggle

**What goes wrong:**
The current `SettingsPage` (`App.tsx:1319+`) shows all brands from `list_brands()` with only a delete button. When `is_active` enforcement is added to the backend `list_brands()`, brands added from the UI and then deactivated will disappear from the list, with no indication of what happened. Operators will not know the brand still exists in the registry but is deactivated. The management UI needs to show inactive brands with a visual state difference and a reactivate button.

**Why it happens:**
The UI was built before deactivation was a concept. The API `GET /brands/` today returns all brands regardless of status. If the backend filter is added without updating the API to have an `include_inactive` param, the management page loses visibility into deactivated brands entirely.

**How to avoid:**
The management-facing `GET /brands/` endpoint must accept `?include_inactive=true` and the `SettingsPage` must always pass this flag. The search-facing `GET /brands/` (used to populate search filters) must default to `is_active=True`. These are the same endpoint today — either add the query param or create a separate management endpoint.

**Warning signs:**
- Operator deactivates a brand, it disappears from settings page with no trace
- Operator cannot reactivate a brand because the UI cannot list it
- Reactivation requires direct database edit

**Phase to address:** Brand management UI phase (MGMT-02).

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoding category IDs in `_BRAND_CATEGORY_PATHS` for new brands | Fast onboarding | Breaks silently when VTEX store restructures categories; impossible to know if IDs are stale | Only if `discover_categories()` is also run and IDs are cross-validated |
| Using `return "vtex"` as the `detect_engine` fallback | Avoids None handling | Every unrecognized platform silently misroutes; Wake brands get VTEX engine | Never — change to `"unknown"` |
| Per-component `useState` for search results during PERS-01 refactor | Avoids store complexity | Tab switch loses search in progress; violates the milestone requirement | Never for PERS-01; fix is the entire point |
| Absorbing all `BrandSearchResult` errors silently | No crash on search | Impossible to diagnose which brands are failing and why | Acceptable only if error field is surfaced in the UI and logged server-side |
| Running `detect_engine` with `aiohttp` plain session | Simpler code | 403s from WAF-protected brands; auto-detects as wrong engine | Only for brands known to have open VTEX APIs |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| VTEX Checkout Simulator | Using `/api/checkout/pub/orderForms/simulation` with wrong SLA data — returns 0-cost SLA | Verify SLA name contains a real carrier label before trusting the price |
| Shopify `calculate_shipping` | Calling the storefront rates API without a session token — returns 401 or empty | Shopify shipping rates require a checkout token; use the cart API flow |
| Wake Commerce GraphQL | Sending REST-style VTEX requests to a Wake storefront | Use `POST /graphql` with the correct schema; standard VTEX REST endpoints return 404 |
| Supabase `is_active` filter | Filtering in Python after fetching all rows | Add `.eq("is_active", True)` to the Supabase query in `load_from_supabase()` to avoid loading deactivated brands into memory |
| Zustand / global store + WebSocket | Storing the `WebSocket` instance in the global store | Store only serializable state; keep `wsRef` as a `useRef` inside the component that owns the WS, but lift `isRunning`, `logs`, and `jobId` to the store |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Keeping all tabs mounted with their WS connections | Memory grows with each tab visited; multiple pollers run simultaneously | Use `AnimatePresence` correctly; ensure cleanup effects run on unmount | After 4+ tab switches with active scrapes |
| Fetching category trees on every tab visit (`CategoryPage` calls `fetchBrandCategories` on brand toggle) | Category API hit on every toggle; no cache between mounts | Cache category trees in the global store keyed by `brand_key` | After adding 9+ new brands to the selector |
| `asyncio.gather` over 12+ brands simultaneously on comparative search | Backend CPU spike; individual timeouts cascade | Add a semaphore to `search_all_brands` (e.g. max 6 concurrent) | At ~9+ brands in the search list |
| Storing full search results in history JSON on disk | History file grows unbounded; large reads on startup | Paginate history reads; cap per-entry product count before serializing | After ~100 searches with full product sets |

---

## "Looks Done But Isn't" Checklist

- [ ] **`is_active` enforcement:** Toggle works in UI — verify that search, export, category scan, scheduler, and brand dropdown all exclude the brand. Test by deactivating a brand, running comparative search, and confirming the brand column is absent.
- [ ] **Wake detection:** New brand registered with `engine="wake"` — verify it does not appear in `search_all_brands` target list. Verify the registration endpoint returns a user-facing message, not a silent 200.
- [ ] **WebSocket cleanup:** Category scrape starts, user switches tab — verify in browser DevTools that the WS connection closes (status `101 → closed`). Verify the backend job does not produce a second concurrent log stream on return.
- [ ] **Shipping unit:** New engine `calculate_shipping` returns a value — assert the UI displays a price in the range R$ 5–R$ 50 for a typical product, not R$ 0.05 or R$ 5000.
- [ ] **Category diagnostic status field:** Diagnostic run on a category returning HTTP 403 — verify the result shows `status: "error"` and `error_detail: "HTTP 403"`, not `status: "empty"`.
- [ ] **Management UI visibility of inactive brands:** Deactivate a brand via the toggle — verify it still appears in `SettingsPage` with a visual "inactive" state and a reactivate button.
- [ ] **No double-fetch on tab return:** Start comparative search, switch tab, return — verify exactly one `POST /search` call in Network panel, not two.
- [ ] **History saves comparative searches:** Run a comparative search — verify the entry appears in history with type `"search"`, not just SKU searches (HIST-01 gap).

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Brand registered as VTEX, is actually Wake — searches silently empty | LOW | Update `engine` field in `brands.json` or Supabase to `"unsupported"`, deactivate brand, re-onboard when Wake engine ships |
| `is_active` flag set on wrong brand — unexpected brand disabled | LOW | Direct update to `brands.json` or Supabase `is_active=true`; restart server to reload in-memory cache |
| Category IDs wrong for new brand in `category_resolver.py` — search returns 0 | LOW | Run `discover_categories()` via `/brands/{key}/discover`, identify correct IDs, update `_BRAND_CATEGORY_PATHS` |
| Global store refactor introduces double-fetch regression on production | MEDIUM | Feature flag the new store; keep old `useState` path as fallback; rollback to previous commit if double-fetch confirmed |
| Shipping price displayed as centavos (100x too high) in production | MEDIUM | Hotfix in the engine's `calculate_shipping` with `/100`; no schema migration needed; redeploy |
| WebSocket connections accumulating — browser becomes sluggish | LOW | Add cleanup effect; existing sessions close naturally when browser tab refreshes |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| `is_active` not enforced in search/export/scheduler | MGMT-01 (brand deactivation) | Search with deactivated brand selected — zero results; scheduler skips brand |
| Wake Commerce detected as VTEX | COMP-01 (brand onboarding) | Register a known Wake domain — endpoint returns `engine="unsupported"`, not `"vtex"` |
| `detect_engine` VTEX fallback for unknown platforms | COMP-01 | Register an unrecognized domain — response contains warning, not silent VTEX assignment |
| WAF blocks discovery on new fashion brands | COMP-01 | Run manual `curl` probe on discovery endpoint before relying on auto-detect |
| WebSocket not cleaned up on tab unmount | PERS-01 (state refactor) | Switch tabs during scrape — one WS connection in DevTools, not two |
| Double-fetch / stale closure on global store | PERS-01 | Single search action — exactly one network request in DevTools |
| Inactive brands invisible in management UI | MGMT-02 (management UI) | Deactivate brand — still visible in settings with "inactive" badge and reactivate button |
| Shipping unit (centavos vs reais) | FRET-05 | New engine shipping test asserts price in range 5.0–100.0 BRL |
| Free-shipping false positive from 0.0 cost | FRET-05 | CEP with no courier coverage returns `shipping_price=null`, not `0.0` |
| Category diagnostic conflates empty with error | DIAG-01 | 403 from WAF shows `status="error"`, empty array shows `status="empty"` |
| VTEX category IDs wrong for new brands | COMP-01 (category mapping) | `discover_categories()` run and IDs cross-validated before adding to `_BRAND_CATEGORY_PATHS` |
| Management UI cannot list/reactivate inactive brands | MGMT-02 | `GET /brands/?include_inactive=true` returns all brands including inactive ones |

---

## Sources

- Direct inspection of `services/engines/factory.py`, `api/routes_brands.py`, `services/category_resolver.py`, `services/brand_service.py`, `services/category_monitor_service.py`, `frontend/src/App.tsx`, `core/models.py`, `api/routes_search.py`
- `tests/test_vtex_api_client.py:174` — confirmed centavo unit in VTEX shipping
- `tests/test_netshoes_engine.py:25` — confirms "saleInCents" pattern in at least one engine
- PROJECT.md — milestone context and requirement IDs
- Wake Commerce platform behavior: well-documented in Brazilian e-commerce community (Shop2gether uses Wake; standard VTEX catalog REST not available)

---
*Pitfalls research for: Multi-engine fashion scraper v2.0 — adding new brands, brand management, frontend state refactor, checkout shipping, and category diagnostics*
*Researched: 2026-06-18*
