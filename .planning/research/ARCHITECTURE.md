# Architecture Research — v4.0 Integration

**Researched:** 2026-06-26 (inline; subagents rate-limited)
**Grounding:** `backend/core/models.py`, `backend/core/base_scraper.py`, `backend/services/*`, `backend/api/*`, `backend/data/*.json`.

## Existing architecture (verified)

- **Canonical schema:** `RawProductBronze` (full product, incl. `specifications: Dict[str,str]` attribute bag, `shipping: ShippingInfo`, `rating`/`review_count`). `SearchProductResult` (lean search result, incl. `shipping_options: List[ShippingInfo]`, `sku_id`, `seller_id`, `seller`). `ShippingInfo` (price/status/estimate/service_name/is_free_shipping).
- **Engine contract:** `BaseScraper` ABC → `get_product_by_url`, `scrape_category_paged`, `search`. Engines selected via `EngineFactory` + `detect_engine` (vtex/shopify/wake/sfcc/unknown).
- **Services:** `brand_service`, `category_mapping`, `category_monitor_service`, `category_resolver`, `cross_marketplace_service` (ML/Netshoes/Amazon), `price_monitor_service`, `review_service`, `vtex_shipping`, `vtex_api_scraper`/`vtex_catalog`/`vtex_parsing`, `shopify_api_client`, `nlp_service`, `relevance_gates`, `image_ai_service`, `ocr_service`, `orchestrator`/`orchestrator_multi`.
- **API routes:** auth, brands, category, history, jobs, monitor, product, search (+ banners).
- **Persistence:** JSON files in `backend/data/` (brands, monitored_categories, price_monitors, search_history, monitored_products_*, nlp_vocabulary).
- **Frontend:** single `App.tsx` (pages inlined), zustand store, ApiClient, WebSocket job updates.
- **Scheduler:** 10-min category-monitor scheduler.

## Integration points by category

### A. Attribute parity
- **New:** a normalization layer — `services/attribute_normalizer.py` (canonical vocabulary + alias map source→canonical). Each engine's product extractor calls it before populating `RawProductBronze.specifications`/typed fields.
- **Modified:** per-engine extractors (VTEX parsing, Wake, SFCC, cross_marketplace) to emit canonical keys; possibly `models.py` if we promote frequently-used spec keys to typed Optional fields.
- **Build order:** foundational — do first; E5 (assortment) depends on it.

### B. Coverage
- **Hugo Boss:** add VTEX category mappings (`category_mapping`/`category_resolver` + `backend/data`); no new engine. Verify scan/monitor paths.
- **Zara:** new `ZaraEngine`/Inditex extractor implementing `BaseScraper` + a `detect_engine` label (or browser-rendered fallback). Plug into `EngineFactory`. Highest unknown — gate with a spike (validate product+price extraction publicly) before full build.
- **Lacoste removal:** filter at the brand-selection chokepoint (`brand_service.list_brands(active_only=True)` already excludes inactive — verify Lacoste is inactive everywhere and not special-cased into any selector).

### C. UX
- **URL-only onboarding:** new route (e.g. `POST /brands/identify`) → `detect_engine(url)` + brand-name inference (domain/title/JSON-LD) → returns a prefilled `DynamicBrandCreate` draft. Frontend collapses the two-step form.
- **Add-to-monitoring:** new `POST /monitor` action reusable from search/SKU/category; builds a `PriceMonitorConfig` from a result; dedup by url+brand. Wire buttons in `App.tsx`.
- **Promo in monitoring list:** ensure `price_discount` is persisted in `PriceMonitorConfig`/history and rendered.
- **Auto-trigger category monitor:** frontend triggers first scan on category select; backend already supports the scan.
- **Marketplace toggles:** give virtual marketplaces a brand-like record (or a parallel `marketplaces.json` with `is_active`) so the toggle has a backend target; `cross_marketplace_service` honors it.
- **Responsiveness / history relocation / SKU pattern:** frontend-only (`App.tsx`, CSS).

### D. Shipping
- **New abstraction:** `services/shipping/` strategy — `base_shipping.py` interface + per-engine implementations (`vtex_shipping` already exists; add `wake_shipping`, `shopify_shipping`, marketplace shippers). Keep VTEX on `VtexApiClient` (D-03). A resolver picks the strategy by engine/marketplace.
- **Multi-regional matrix:** a fan-out helper over a configured list of key CEPs (`backend/data/cep_matrix.json`); on-demand/batched, not at search time. Results attach as `shipping_options` per region or a dedicated matrix payload.
- **Modified:** `ShippingInfo` may gain a `region`/`cep` field; product/search flow gains an opt-in shipping-matrix call.

### E. Intelligence
- **MAP:** new fields (floor price per product/brand/category, persisted as `map_rules.json`); comparison at result time flags violations + `seller`; a violations view/endpoint.
- **Promotions/payment:** per-engine parsers → structured `promotions: List[...]` on the product model; reuse `nlp_service` for free-text seal normalization.
- **Stock rupture:** category-scan aggregation (% out-of-stock) + a guarded cart-probe helper (per engine) for depth; new fields on the scan result.
- **Reviews:** extend `review_service` per-brand extractors; ensure `rating`/`review_count` + comment corpus populated.
- **Assortment cron:** a new scheduled job (alongside category scheduler) that scrapes a category fully and counts by canonical attribute; stores counts (`assortment_*.json` or SQLite); depends on Category A.

## Persistence decision
JSON files are fine for config-shaped data (brands, monitors, MAP rules, CEP matrix). **Assortment counts, review corpora, and historical price/stock series** will grow and have concurrent writers (cron + scheduler) — recommend introducing **SQLite** (stdlib, zero-dep) for these analytical/time-series datasets while keeping JSON for config. Flag as an architecture decision for the roadmap.

## Suggested build order (dependency-aware)
1. **A — Attribute parity** (foundational; unblocks E5, improves E1/E2).
2. **C — UX quick wins** (promo-in-list, history relocation, SKU pattern, auto-trigger, responsiveness, marketplace toggles) — independent, high user value, low risk.
3. **B — Coverage** (Hugo Boss category fix first; Zara behind a spike gate; Lacoste removal).
4. **C — URL-only onboarding + add-to-monitoring** (moderate, cross-cutting).
5. **D — Shipping abstraction → non-VTEX → marketplaces → multi-regional matrix** (layered).
6. **E — Intelligence** (MAP, promos, reviews, stock rupture, assortment) — assortment last (depends on A + persistence).
