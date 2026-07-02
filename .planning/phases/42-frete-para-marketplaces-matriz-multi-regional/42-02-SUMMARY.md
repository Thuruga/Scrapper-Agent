---
phase: 42-frete-para-marketplaces-matriz-multi-regional
plan: 02
subsystem: shipping
tags: [shipping, regional-matrix, cep-matrix, ttl-cache, fastapi]

# Dependency graph
requires:
  - phase: 42-frete-para-marketplaces-matriz-multi-regional (plan 01)
    provides: resolve_shipping_provider dispatch for mercadolivre/amazon/netshoes, SHIPPING_MATRIX_THROTTLE_SECONDS/SHIPPING_MATRIX_CACHE_TTL_SECONDS config settings
provides:
  - calculate_regional_matrix orchestrator (backend/services/shipping/regional_matrix.py) — resolves provider once, iterates 5 curated capital CEPs with throttle + TTL cache + batch error isolation + inline-execution guard
  - backend/data/cep_matrix.json (5 curated capital CEPs, operator-editable) and backend/data/shipping_matrix_cache.json (seed cache file)
  - POST /search/calculate-shipping-matrix route + Pydantic request/response models
  - /search/calculate-shipping-brand description updated to name all 5 supported engines (dispatch itself required no changes — D-04)
affects: [42-03-frontend]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Matrix orchestrator composition: resolver chokepoint (call provider once) + JSON local-storage load/save (category_monitor_service.py shape) + sequential throttle loop + try/except batch error isolation per region"
    - "triggered_by keyword-only guard parameter: only the literal string 'on_demand_matrix_button' passes; any other value raises RuntimeError before any provider call — enforced further by a static ast-based regression test on the two live-scan/search call sites"

key-files:
  created:
    - backend/services/shipping/regional_matrix.py
    - backend/data/cep_matrix.json
    - backend/data/shipping_matrix_cache.json
    - backend/tests/test_shipping_regional_matrix.py
  modified:
    - backend/api/routes_search.py
    - backend/tests/test_non_vtex_shipping_route.py
    - .gitignore

key-decisions:
  - "cep_matrix.json and shipping_matrix_cache.json added to the .gitignore allowlist (mirroring the existing brands.json/nlp_vocabulary.json exceptions to the blanket *.json ignore rule) — both are required tracked artifacts per the plan's must_haves, not throwaway data."
  - "Product identity for the cache key uses normalize_url(product.url) exclusively (Pitfall 6) — sku_id is VTEX-only and unpopulated for marketplace engines, so URL is the only identifier that works across all 5 supported engines."
  - "TTL comparisons use time.time() epoch floats (Pitfall 5), never datetime, avoiding timezone-ambiguity bugs."
  - "The guard is enforced as a first-line RuntimeError check inside calculate_regional_matrix (before resolve_shipping_provider is even called), plus a static ast-based test asserting neither cross_marketplace_search nor run_category_scan references the matrix module/function by name (Pitfall 4)."

patterns-established:
  - "New matrix response entries carry cached: bool alongside region/capital/cep/state/shipping/message so callers (and the frontend in Plan 03) can distinguish a fresh provider call from a cache hit without extra round trips."

requirements-completed: [FRET-08, FRET-09]

# Metrics
duration: 35min
completed: 2026-07-02
---

# Phase 42 Plan 02: Multi-Regional Shipping Matrix (FRET-09) + Marketplace Route Coverage (FRET-08) Summary

**On-demand `calculate_regional_matrix` orchestrator that resolves the shipping provider once and fetches cost/prazo for 5 curated capital CEPs (throttle + TTL cache + batch isolation), exposed via a new guarded `POST /search/calculate-shipping-matrix` route, with `/calculate-shipping-brand` now documented to cover all 3 marketplace engines.**

## Performance

- **Duration:** 35 min
- **Tasks:** 2
- **Files modified:** 7 (4 created, 3 modified)

## Accomplishments
- `calculate_regional_matrix(product, brand, cep_list, *, triggered_by, cache_path=None)` resolves the shipping provider exactly once per matrix request, then loops the 5 curated CEPs: cache hit skips the provider entirely (`cached=True`), a cache miss on any CEP after the first awaits `SHIPPING_MATRIX_THROTTLE_SECONDS` before calling the provider, and one CEP's exception yields a `temporary_failure` entry for that region only without aborting the other 4.
- Inline-execution guard (D-10): the function's first action raises `RuntimeError` unless `triggered_by == "on_demand_matrix_button"` — no provider call happens beforehand. A dedicated `ast`-based static test (`test_matrix_guard_no_inline_import`) walks the source of `cross_marketplace_search` and `run_category_scan` and asserts neither references `regional_matrix`/`calculate_regional_matrix` by any AST node type (name, attribute, import, or string constant).
- `backend/data/cep_matrix.json` ships the 5 curated capitals (São Paulo-SP, Porto Alegre-RS, Brasília-DF, Salvador-BA, Manaus-AM) in the fixed Sudeste/Sul/Centro-Oeste/Nordeste/Norte order; `backend/data/shipping_matrix_cache.json` seeds as `{}`.
- `POST /search/calculate-shipping-matrix` mirrors `calculate_shipping_brand`'s guard order (404 unknown brand → 400 SSRF host-mismatch via `is_url_allowed_for_brand` → matrix call), takes no `zipcode` field (the 5 CEPs come from `cep_matrix.json` per D-08), and lives under the existing `/search` prefix so `X-API-Key`/`INTERNAL_API_KEY` middleware coverage applies automatically with no new bypass (T-42-03).
- `/search/calculate-shipping-brand`'s description now explicitly names Wake/Shopify/Mercado Livre/Amazon/Netshoes; no new branching logic was added to the handler — Plan 01's resolver extension is what already makes the 3 marketplace engines work (D-04), confirmed by parametrized route tests.

## Task Commits

Each task was committed atomically:

1. **Task 1: Regional matrix module — throttle, TTL cache, inline-execution guard, cep_matrix.json** - `1718c18` (feat)
2. **Task 2: POST /search/calculate-shipping-matrix route + extend /calculate-shipping-brand for marketplaces** - `199f8d5` (feat)

_Note: each task followed RED (tests written first, confirmed failing via `pytest`) then GREEN (implementation, confirmed passing) inline within a single commit per task, matching the plan's task-level `tdd="true"` structure._

## Files Created/Modified
- `backend/services/shipping/regional_matrix.py` - New orchestrator: `calculate_regional_matrix`, `_stable_product_identity`, `_cache_key`, `_load_cache`/`_save_cache`, `_read_matrix_cache`/`_write_matrix_cache`, `load_cep_matrix`
- `backend/data/cep_matrix.json` - 5-element curated capital-CEP array (Sudeste/Sul/Centro-Oeste/Nordeste/Norte order)
- `backend/data/shipping_matrix_cache.json` - Seed cache file (`{}`)
- `backend/tests/test_shipping_regional_matrix.py` - New test file: 5-region result, cache hit, throttle, guard (bad trigger), static no-inline-import guard, batch error isolation, TTL expiry (7 tests)
- `backend/api/routes_search.py` - Added `CalculateShippingMatrixRequest`/`ShippingMatrixRegionResult`/`CalculateShippingMatrixResponse` models + `calculate_shipping_matrix` handler; updated `/calculate-shipping-brand` description
- `backend/tests/test_non_vtex_shipping_route.py` - Added marketplace-engine acceptance tests (mercadolivre/amazon/netshoes), matrix route tests (5-region response, host-mismatch 400, unknown-brand 404, on-demand trigger spy, route registration)
- `.gitignore` - Allowlisted `backend/data/cep_matrix.json` and `backend/data/shipping_matrix_cache.json` against the blanket `*.json` ignore rule (mirrors existing `brands.json`/`nlp_vocabulary.json` exceptions)

## Decisions Made
- Cache key uses `normalize_url(product.url)` as the sole product-identity half (never `sku_id`) so the same cache logic works uniformly across VTEX, Wake, Shopify, and all 3 marketplace engines (Pitfall 6).
- TTL uses `time.time()` epoch floats exclusively (Pitfall 5) — no `datetime` objects anywhere in the cache read/write path.
- Data files (`cep_matrix.json`, `shipping_matrix_cache.json`) required an explicit `.gitignore` allowlist addition since the repo's blanket `*.json` rule would otherwise have silently excluded them from every future commit — this was caught immediately via `git status --short` after Task 1's initial file creation, before the first commit.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added `.gitignore` allowlist entries for the two new data files**
- **Found during:** Task 1 (writing `cep_matrix.json`/`shipping_matrix_cache.json`)
- **Issue:** The repo's `.gitignore` has a blanket `*.json` rule with explicit exceptions only for `brands.json` and `nlp_vocabulary.json`. The two new plan-required data files were silently excluded from `git status`/`git add`, which would have made Task 1's commit incomplete (missing the `must_haves.artifacts` for `cep_matrix.json`/`shipping_matrix_cache.json`).
- **Fix:** Added `!/backend/data/cep_matrix.json` and `!/backend/data/shipping_matrix_cache.json` to `.gitignore`, immediately following the existing `brands.json`/`nlp_vocabulary.json` allowlist pattern.
- **Files modified:** `.gitignore`
- **Verification:** `git status --short` confirmed both files as new/trackable (`??`) after the edit; both are present in Task 1's commit tree (`git show --stat 1718c18`).
- **Committed in:** `1718c18` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking — gitignore allowlist)
**Impact on plan:** Necessary for the plan's own `must_haves.artifacts` to actually be committed; no scope creep, no behavior change.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `POST /search/calculate-shipping-matrix` is live, guarded, and tested — ready for Plan 03's frontend wiring (a "Ver matriz regional" button calling this endpoint and rendering 5 region rows).
- `calculate_regional_matrix` and `load_cep_matrix` are importable from `services.shipping.regional_matrix` for any future consumer that needs the same guard rails.
- Full backend suite (505 tests, up from 490 at Plan 01 baseline) green — no regression to Phase 41 VTEX/Wake/Shopify/marketplace shipping paths or any other subsystem.
- Manual/UAT verification (one live ML delivery-time field shape + a live 5-region matrix smoke test) remains deferred per `42-VALIDATION.md` Manual-Only Verifications — not a CI gate, noted here for Plan 03/UAT follow-up.

---
*Phase: 42-frete-para-marketplaces-matriz-multi-regional*
*Completed: 2026-07-02*
