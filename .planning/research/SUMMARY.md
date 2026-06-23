# Project Research Summary

**Project:** Intelligence Scraper — v2.0 Cobertura de Concorrentes & Confiabilidade
**Domain:** Multi-engine fashion price/catalog scraping (Python backend + React/Vite SPA)
**Researched:** 2026-06-18
**Confidence:** HIGH (codebase-grounded), MEDIUM (external platform detection for 2 brands)

## Executive Summary

This is a subsequent milestone (v2.0) adding competitor coverage and platform reliability to an already-shipped multi-engine scraper. Research was grounded in direct codebase inspection plus external platform investigation of the 9 proposed brands.

**The single most important finding is a scope correction:** only **5 of the 9** proposed competitor brands run on a currently-supported platform (VTEX) and are actionable in v2.0 — **Levi's, Calvin Klein, Zapalla, Austral, Track & Field**. The other 4 run on platforms with no existing engine: **Richards (Wake Commerce), Lacoste (Salesforce Commerce Cloud), Hugo Boss (Salesforce Commerce Cloud), Zara (custom Inditex IOP)** — they must be registered as deferred/unsupported, not silently onboarded. Platform confidence is HIGH for 7 brands and MEDIUM for Lacoste/Hugo Boss (their sites returned 403; platform inferred from global evidence), so onboarding must empirically re-confirm each brand's engine via the existing `detect_engine` before committing.

The recommended approach is mostly **wiring up infrastructure that already exists**: the `is_active` flag, the `preloadedJobId` prop, the `SearchHistory.type` discriminator, and the VTEX checkout simulation are all present but not connected. The only genuinely new code is a frontend global store (one new dependency, `zustand`), a category-diagnostics service, and a per-engine shipping generalization. The highest regression risk is the frontend state lift (PERS-01).

## Key Findings

### Recommended Stack

Backend needs **no new libraries** — all work reuses existing patterns (Pydantic models, engine factory, checkout simulation, `aiohttp`/`curl_cffi`). Frontend needs exactly **one** new dependency for cross-tab persistence.

**Core technologies:**
- **zustand@^5.0.14** (frontend): module-level singleton store that survives React component unmount by design (~1 KB gzipped, no Provider). The correct minimal fix for in-flight search state lost on tab switch. Do NOT add TanStack Query or persist middleware.
- **VTEX checkout simulation** (`POST /api/checkout/pub/orderForms/simulation`) — already used; extend to VTEX brand sites that currently return `None` for shipping.
- **Shopify AJAX Cart API** (`/cart/add.json` → `/cart/prepare_shipping_rates.json` → `/cart/async_shipping_rates.json`) — for Shopify shipping; needs a session cookie + empirical validation; no new Python lib. **Defer if costly** (researchers split: may need Playwright).
- **Pure Python** for category diagnostics — a `CategoryDiagnosticResult` model + a runner wrapping `run_bulk_scrape`. No monitoring library.

### Expected Features

**Must have (table stakes):**
- Onboard the supported (VTEX) brands with verified scraping + category mappings; gracefully flag unsupported-platform brands instead of silent 0-product failures.
- Deactivate/reactivate a brand and have it excluded **everywhere** (search, monitoring, export, scheduler); reversible.
- In-flight search survives leaving and returning to a tab (progress/results preserved); completion notification.
- Complete search history: save **comparative** searches too (today only SKU is saved) and re-open any saved search.
- Category diagnostics distinguishing **empty vs error** (not just a product count).
- Per-result shipping price + delivery time + free-shipping detection where the engine supports it.

**Should have (competitive):**
- Brand-management field (add/remove/deactivate) in one place.
- Diagnostics surfaced per brand/engine, actionable.

**Defer (future / out of scope):**
- Wake Commerce engine (Richards / Shop2gether) — v3.0 candidate (custom GraphQL + per-store token).
- Salesforce Commerce Cloud brands (Lacoste, Hugo Boss) — future research spike.
- Zara (Inditex IOP) — no standard API.
- Shopify checkout shipping if empirical validation proves fragile.
- Per-user access profiles / auth overhaul; banners→SharePoint (already out of scope for this milestone).

### Architecture Approach

Almost every change is a **single chokepoint** plus a small UI surface. `is_active` enforcement belongs in `BrandManagerService.list_brands(active_only=True)` (one source of truth → propagates to all 3 search routes + factory + scheduler). The frontend state lift is a new `frontend/src/store/searchStore.ts` replacing component `useState`, plus fixing `App.tsx renderTab()` to pass the dangling `historyJobId`/`preloadedJobId` prop. Comparative-search history is ~4 lines added to `search_products()`.

**Major components:**
1. **Brand activation chokepoint** — `brand_service.list_brands(active_only)` + `PATCH /brands/{key}/active` + Settings toggle.
2. **Engine-detection hardening** — `detect_engine` must return `"unknown"` (not fall through to `"vtex"`) and add a Wake probe; brands with unknown engines kept inactive/excluded.
3. **Frontend search store (zustand)** — holds loading/results across tab unmount; wire `preloadedJobId`.
4. **Comparative history save** — `routes_search.py` calls `SearchHistoryService.create_job/update_job`.
5. **Category diagnostics service** — three-state (`ok|empty|error`) runner + endpoint + UI panel.
6. **Per-engine shipping** — generalize `BaseEngine.calculate_shipping` (VTEX brand sites, then Shopify) with a documented unit contract.

### Critical Pitfalls

1. **`is_active` is a ghost field** — exists but never read. Fix at the single `list_brands()` source, not per-callsite, or deactivation silently does nothing and erodes trust.
2. **Wake Commerce is undetectable today and falls through to VTEX** — Wake sites carry VTEX CDN refs (HTML probe says "vtex") but expose no catalog REST API → silent 0-product results. Change the fallback to `"unknown"` and add a Wake probe; reject unknown-engine brands from search.
3. **`CategoryPage` WebSocket has no unmount cleanup** — dangling connections + interleaved logs; a 5-line `useEffect` cleanup. Prerequisite for PERS-01, not part of it.
4. **Shipping unit bug (centavos vs reais)** — VTEX is centavos (`/100`); `BaseEngine.calculate_shipping` has no unit contract. Add a docstring + range-assertion test **before** writing any new engine shipping.
5. **Category diagnostics conflate three states** — empty vs wrong-id vs error all yield "0 products" today. DIAG-01 must return `status` + `http_status` + `error_detail`. Don't auto-disable on "empty" (seasonal gaps are legitimate).
6. **PERS-01 state lift is the highest regression risk** — touches SearchPage + CrossMarketplacePage + history at once. Plan explicit regression tests (no double-fetch, correct cancellation, preloaded-history handling).

## Implications for Roadmap

Suggested dependency-aware phase structure (continues numbering from **Phase 25**):

### Phase 25: Engine-detection hardening + `is_active` enforcement (backend foundation)
**Rationale:** Prerequisite for safely onboarding brands and for the deactivation feature to mean anything. Wake/unknown fallback must exist before registering new brands.
**Delivers:** `detect_engine` returns `unknown` (+ Wake probe); `list_brands(active_only)`; `PATCH /brands/{key}/active`; disabled brands excluded from search/monitoring/export/scheduler.
**Avoids:** ghost-field pitfall, silent Wake-as-VTEX failures.

### Phase 26: Onboard supported competitor brands (data) + flag deferred
**Rationale:** Needs Phase 25 so bad/unknown brands can't pollute search.
**Delivers:** 5 VTEX brands onboarded with verified engine + category mappings; Richards/Lacoste/Hugo Boss/Zara registered as deferred/unsupported (inactive). Each engine re-confirmed via `detect_engine` at onboarding.
**Addresses:** COMP-01.

### Phase 27: Complete search history + brand-management UI
**Rationale:** Comparative-history save is a tiny backend change; brand toggle/management UI consumes Phase 25's endpoint.
**Delivers:** comparative searches saved to history; `preloadedJobId` prop wired in `App.tsx`; Settings brand add/remove/deactivate field.
**Addresses:** HIST-01, MGMT-01, MGMT-02.

### Phase 28: Search persistence across tabs (frontend store)
**Rationale:** Highest regression risk — isolate it. Includes the WebSocket-cleanup prerequisite.
**Delivers:** `searchStore.ts` (zustand); in-flight search survives tab switch; completion notification; regression tests.
**Addresses:** PERS-01.

### Phase 29: Category diagnostics (empty/error)
**Rationale:** Independent; needs brands from Phase 26 for coverage.
**Delivers:** three-state diagnostic service + endpoint + UI panel.
**Addresses:** DIAG-01.

### Phase 30: Checkout shipping across more engines
**Rationale:** Independent of 28/29; define unit contract first.
**Delivers:** VTEX brand-site shipping; Shopify shipping (if empirically viable, else deferred).
**Addresses:** FRET-05.

### Phase Ordering Rationale
- **Backend foundation (25) before onboarding (26)**: deactivation + unknown-engine gate must exist before new brands are registered.
- **MGMT UI (27) after enforcement (25)**: a toggle that does nothing erodes trust.
- **PERS-01 (28) isolated**: highest regression surface; bundle the WS-cleanup prerequisite.
- **DIAG (29) and FRET (30) are parallelizable** and independent of the frontend work.

### Research Flags
- **Phase 30 (Shopify shipping):** empirical — needs a smoke test of the AJAX Cart shipping-rates workflow against a real BR Shopify store before committing; may require Playwright.
- **Phase 26 (Lacoste/Hugo Boss platform):** MEDIUM confidence (403 blocked); re-confirm engine at onboarding; expect to defer.
- Phases 25, 27, 29 use established/in-repo patterns — skip deep research.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | zustand verified; backend reuses existing patterns; Shopify shipping MEDIUM (session-cookie workflow unproven) |
| Features | HIGH | All grounded in direct codebase inspection |
| Architecture | HIGH | Exact chokepoints/file refs traced |
| Pitfalls | HIGH | Each pitfall tied to a specific code location |
| Brand platforms | MEDIUM | 7/9 HIGH; Lacoste/Hugo Boss inferred (403) — verify at onboarding |

**Overall confidence:** HIGH

### Gaps to Address
- **Per-brand engine confirmation:** run `detect_engine` against each of the 5 "ready" brands at onboarding; don't trust the research table blindly.
- **Shopify shipping viability:** smoke-test before committing the full FRET-05 Shopify path.
- **Category-mapping data:** the VTEX `fq` paths / collection handles per new brand are data work to be done at onboarding.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `services/engines/factory.py`, `base_engine.py`, `services/brand_service.py`, `core/models.py`, `api/routes_search.py`, `routes_brands.py`, `frontend/src/App.tsx`, `frontend/src/api/client.ts`.
- Detailed research docs: `.planning/research/STACK.md`, `FEATURES.md`, `ARCHITECTURE.md`, `PITFALLS.md`.
- zustand npm/GitHub/Context7 (v5 API + footprint).

### Secondary (MEDIUM confidence)
- External brand-site platform detection (CDN asset domains, footer attributions, Salesforce/Inditex public material).

### Tertiary (LOW confidence)
- Lacoste/Hugo Boss BR platform inferred (sites returned 403) — needs onboarding-time confirmation.

---
*Research completed: 2026-06-18*
*Ready for roadmap: yes*
