---
phase: 44-ruptura-de-estoque-avalia-es-refor-adas
plan: 01
subsystem: backend-analytics
tags: [python, pydantic, pytest, stock-rupture, shopify, vtex, json-persistence]

requires:
  - phase: 40-onboarding-por-url-workflows-de-adi-o-ao-monitoramento
    provides: active brand registry and monitor/search foundations
provides:
  - Shared additive Phase 44 product contracts for rupture, stock-depth, and review comments
  - Deterministic stock rupture summary math over product-level stock_availability
  - Local JSON artifact helpers for monitor and manual category scan summaries
  - VTEX and Shopify regression coverage for product-level variation aggregation
affects: [44-02, 44-03, 44-04, category-monitor, review-comments, stock-depth]

tech-stack:
  added: []
  patterns:
    - Pure summary service returning Pydantic StockRuptureSummary
    - Local JSON artifact helpers under backend/data
    - Product-level availability aggregation before analytics summaries

key-files:
  created:
    - backend/services/stock_summary_service.py
    - backend/tests/test_shopify_variation_stock.py
  modified:
    - backend/core/models.py
    - backend/config.py
    - backend/services/shopify_api_client.py
    - backend/tests/test_stock_summary_service.py
    - backend/tests/test_vtex_api_client.py

key-decisions:
  - "44-01/persistence-reality: backend/data/analytics.db, backend/services/*analytics*.py, and Phase 37 artifacts were absent; Plan 44-01 used JSON/local helpers and did not create SQLite schema."
  - "44-01/stock-summary-input: compute_stock_summary consumes only normalized product-level stock_availability; SKU/item/variant arrays are intentionally ignored."
  - "44-01/shopify-d04: Shopify availability now derives from variants[].available when variants are exposed; suggest.json without variants preserves the prior default available=True."
  - "44-01/non-vtex-variation-audit: Wake, SFCC, and Zara scan paths currently expose scalar/text stock signals rather than variation arrays; no D-04 parser change was made for those engines."

patterns-established:
  - "Stock rupture percentage: out_of_stock_count / verified_stock_count, where verified_stock_count counts only literal True/False stock_availability values."
  - "Unknown stock semantics: stock_availability=None or any non-bool value increments unknown_stock_count and never affects rupture_pct."
  - "Scan product identity: ensure_scan_product_ids adds deterministic IDs from scan_id, brand, URL, and title/name without mutating input products."

requirements-completed: [STOCK-01, STOCK-02, REVW-01]

duration: 9 min
completed: 2026-06-30
---

# Phase 44 Plan 01: Shared Stock Rupture and Review Contracts Summary

**Additive Phase 44 contracts plus deterministic stock rupture math and JSON scan summary helpers**

## Performance

- **Duration:** 9 min
- **Started:** 2026-06-30T17:57:06Z
- **Completed:** 2026-06-30T18:06:02Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- Added `StockRuptureSummary`, `StockDepthResult`, `ReviewComment`, and `ReviewCommentsResult` plus optional Phase 44 fields on `RawProductBronze` and `SearchProductResult`.
- Added conservative settings defaults for review pagination and controlled stock-depth probes.
- Added `stock_summary_service.py` with pure rupture math, deterministic scan product IDs, and JSON/local summary persistence.
- Added VTEX and Shopify D-04 regression tests; fixed Shopify `suggest.json` availability to read exposed variants.

## Task Commits

1. **Task 1: Add additive Phase 44 model and config contracts**
   - `eaba2b3` test(44-01): add failing tests for phase 44 contracts
   - `83fc8ea` feat(44-01): add phase 44 product contracts
2. **Task 2: Enforce D-04 variation-level stock aggregation before summaries**
   - `25d3d1b` test(44-01): add variation stock aggregation regressions
   - `9121358` fix(44-01): aggregate Shopify variant availability
3. **Task 3: Implement pure rupture summary and scan artifact helpers**
   - `d48dc33` test(44-01): add failing tests for stock summary helpers
   - `815e342` feat(44-01): implement stock rupture summary helpers

## Files Created/Modified

- `backend/services/stock_summary_service.py` - Pure rupture summary math, scan product ID generation, and local JSON artifact helpers.
- `backend/tests/test_stock_summary_service.py` - TDD coverage for model/config contracts, rupture denominator semantics, scan IDs, and JSON round trips.
- `backend/tests/test_shopify_variation_stock.py` - Shopify parser/search D-04 regression coverage.
- `backend/tests/test_vtex_api_client.py` - VTEX parser/search D-04 regression coverage.
- `backend/core/models.py` - Additive Phase 44 Pydantic contracts and product fields.
- `backend/config.py` - Conservative review/probe defaults.
- `backend/services/shopify_api_client.py` - Shared Shopify variant availability aggregation in product and search mapping.

## Decisions Made

- Used JSON/local summary helpers because Phase 37 SQLite artifacts are absent in this workspace.
- Kept rupture math independent of SKU/item/variant arrays; parser/scan paths own product-level aggregation first.
- Preserved Shopify `suggest.json` default availability when no variants are exposed, while using variants when present.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Shopify suggest search ignored exposed variant availability**
- **Found during:** Task 2 (variation aggregation regressions)
- **Issue:** Shopify `suggest.json` results were always mapped as `available=True`, so products with exposed variants all unavailable could be counted as in stock.
- **Fix:** Added `_variants_available()` and used it in `_map_to_bronze`, `suggest.json`, and `search.json` mapping; `only_in_stock` now uses the same aggregate.
- **Files modified:** `backend/services/shopify_api_client.py`
- **Verification:** `python -m pytest backend/tests/test_stock_summary_service.py backend/tests/test_vtex_api_client.py backend/tests/test_shopify_variation_stock.py -q` -> 31 passed.
- **Committed in:** `9121358`

**Total deviations:** 1 auto-fixed (Rule 1 bug)
**Impact on plan:** Required for D-04 correctness; no scope expansion beyond Shopify variation aggregation.

## Issues Encountered

- Backstage standards MCP was unavailable in this Codex session; continued with in-repo Phase 33/41 patterns as required by the plan.
- Phase 37 persistence artifacts were absent (`backend/data/analytics.db`, `backend/services/*analytics*.py`, and Phase 37 artifacts not found), so no SQLite schema or migration was created.

## Known Stubs

None in production code. Empty lists in tests are intentional fixtures.

## Threat Flags

None. New local artifact helpers match the plan threat model; no new endpoint, auth path, external network call, or schema boundary was introduced.

## Verification

- `python -m pytest backend/tests/test_stock_summary_service.py -q` -> 8 passed.
- `python -m pytest backend/tests/test_stock_summary_service.py backend/tests/test_vtex_api_client.py backend/tests/test_shopify_variation_stock.py -q` -> 31 passed.
- `git diff -- backend/core/models.py backend/config.py backend/services/stock_summary_service.py backend/services/vtex_api_scraper.py backend/services/shopify_api_client.py backend/tests/test_stock_summary_service.py backend/tests/test_vtex_api_client.py backend/tests/test_shopify_variation_stock.py` -> no uncommitted diff after task commits.
- Schema/migration scan for this plan -> no ORM migration or schema-push file added.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for Plan 44-02 to wire rupture summaries into category scan/monitor flows. Downstream plans should consume `StockRuptureSummary` and `compute_stock_summary()` instead of recomputing D-01/D-04 semantics.

## Self-Check: PASSED

- Found created files: `backend/services/stock_summary_service.py`, `backend/tests/test_shopify_variation_stock.py`, `backend/tests/test_stock_summary_service.py`, and this SUMMARY.
- Found commits: `eaba2b3`, `83fc8ea`, `25d3d1b`, `9121358`, `d48dc33`, `815e342`.
- Re-ran plan verification: `python -m pytest backend/tests/test_stock_summary_service.py backend/tests/test_vtex_api_client.py backend/tests/test_shopify_variation_stock.py -q` -> 31 passed.

---
*Phase: 44-ruptura-de-estoque-avalia-es-refor-adas*
*Completed: 2026-06-30*
