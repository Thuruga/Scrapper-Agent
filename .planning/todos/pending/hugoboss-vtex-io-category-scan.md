---
created: 2026-06-29
area: backend (engine / vtex scraper)
source: 39-01 checkpoint (operator decision: persist mappings + defer monitoring)
priority: high
resolves_phase:
---

# Hugo Boss category-scan strategy for VTEX-IO / Intelligent Search storefronts

Phase 39-01 persisted Hugo Boss's category mappings (resolution works), but the
**10-min category monitor returns 0 products** for Hugo Boss because the existing
VTEX scraper (`VtexApiClient.scrape_category_paged` / `run_bulk_scrape`) drives the
legacy `catalog_system` category APIs, which Hugo Boss's storefront no longer serves.

## Evidence (probe matrix, 2026-06-29, live)

| Method | Result |
|--------|--------|
| `search("camisa")` full-text (catalog_system) | ✅ real products (title + `/p` URL + price) |
| `catalog_system /products/search/{path}` (no map) | 0 products |
| `catalog_system /products/search/{path}?map=c,c,c` | 3 **generic** products, identical across camisas/polos/calcas (NOT leaf-filtered) |
| `catalog_system /products/search?fq=C:/{categoryId}/` | 0 products (ids resolve fine: camisas=54, polos=52, calcas=56) |
| Intelligent Search `/api/io/_v/api/intelligent-search/product_search/{path}` | `records=0` |
| existing browser fallback (`ROOT_QUERY` regex) | 0 (regex doesn't match HB's render) |
| **storefront ground truth (Playwright network capture)** | products load via **VTEX IO GraphQL** (`/_v/public/graphql/v1`, persistedQuery); DOM renders **36 `vtex-product-summary` tiles** |

**Conclusion:** Hugo Boss is a VTEX-IO / Intelligent-Search storefront. Category
listings come from GraphQL `productSearch` persisted queries, not the legacy
`catalog_system` category navigation. Products exist and render — the engine just
can't read them with its current strategy. This is a NEW category-scan strategy,
not a parameter tweak (the `map=c,c,c` shortcut returns generic, non-filtered data
and must NOT be used).

## Proposed approaches (pick during the spike)

1. **Playwright DOM-render + tile-parse** — render the category page, parse
   `vtex-product-summary` tiles (title / `/p` URL / price). Feasible today
   (chromium installed; 36 tiles render). Extends the existing browser fallback.
2. **VTEX IO GraphQL `productSearch`** — call `/_v/public/graphql/v1` with the
   storefront's persistedQuery hash + segment token. More robust but the persisted
   hash changes on storefront deploys; needs hash discovery + pagination handling.

Mirror the Zara gate (Phase 39-02 spike): validate viability with a spike BEFORE
wiring into `run_bulk_scrape`, and add a hermetic test proving leaf filtering
(camisas ≠ polos) and `price_full > 0`.

## Secondary: auto_match accent collision

`auto_match` (onboard_vtex_brands.py) mismatched canonical `calcas` →
`/masculino/calcados` (footwear) because "calça" fuzzy-matches "calçados". The
39-01 human-review gate corrected it to `/masculino/roupas/calcas`, but re-running
`onboard_hugoboss_categories.py` would re-propose the wrong path. Add accent/word-
boundary-aware matching (or a per-brand correction) so discovery is reproducible.
