---
phase: 44-ruptura-de-estoque-avalia-es-refor-adas
plan: 02
subsystem: backend-analytics
tags: [python, fastapi, pytest, stock-rupture, category-monitor, json-persistence]

requires:
  - phase: 44-ruptura-de-estoque-avalia-es-refor-adas
    provides: Plan 44-01 shared StockRuptureSummary, compute_stock_summary, scan product IDs, and JSON artifact helpers
provides:
  - Scheduled category monitor stock summaries persisted by monitor_id
  - Manual single-brand and multi-brand category scan summaries persisted by job_id
  - Read endpoints for monitor and manual scan stock summaries
  - Regression coverage for scheduled/manual STOCK-01 wiring
affects: [44-03, 44-05, category-monitor, manual-category-scan, stock-rupture]

tech-stack:
  added: []
  patterns:
    - Shared compute_stock_summary used from all category scan surfaces
    - Read routes load persisted summary artifacts instead of recomputing from request data
    - Manual scan summaries use per-brand scan_id values under one shared job_id artifact

key-files:
  created:
    - backend/tests/test_phase44_routes.py
  modified:
    - backend/services/category_monitor_service.py
    - backend/api/routes_monitor.py
    - backend/services/orchestrator.py
    - backend/services/orchestrator_multi.py
    - backend/api/routes_category.py

key-decisions:
  - "44-02/summary-source: scheduled and manual summary wiring consumes product-level stock_availability only through compute_stock_summary; routes never recompute summary math."
  - "44-02/manual-scan-id: manual category summaries use scan_id='{job_id}:{brand_key}' and persist all brand summaries under category_scan_summaries_{job_id}.json."
  - "44-02/hugo-boss-risk: automated STOCK-01 proof uses synthetic/working-brand fixtures; Hugo Boss zero-product scans remain a UAT dependency risk until the pending VTEX-IO category-scan todo is resolved."

patterns-established:
  - "Scheduled monitor products are normalized through ensure_scan_product_ids before monitored_products_{monitor_id}.json is written."
  - "GET summary endpoints are read-only wrappers around load_monitor_stock_summary/load_category_job_stock_summaries."
  - "Manual category scan response keys remain unchanged while background work receives job_id for summary persistence."

requirements-completed: [STOCK-01]

duration: 11 min
completed: 2026-06-30
---

# Phase 44 Plan 02: Scheduled and Manual Category Scan Rupture Summary Wiring

**Shared STOCK-01 rupture summaries wired into scheduled monitors and manual category scan jobs**

## Performance

- **Duration:** 11 min
- **Started:** 2026-06-30T18:11:08Z
- **Completed:** 2026-06-30T18:22:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Scheduled category monitor runs now enrich persisted products with `scan_product_id`, persist `stock_summary_{monitor_id}.json`, and store a compact `last_stock_summary` on the monitor row.
- Added `GET /monitor/category/{monitor_id}/stock-summary` as a read-only endpoint backed by `load_monitor_stock_summary`.
- Manual single-brand scans now accept optional `job_id`, persist one `category_scan_summaries_{job_id}.json` entry, and include `stock_summary` in the completion log payload.
- Multi-brand manual scans now persist one summary per brand under the shared `job_id` and include `stock_summaries` in final log payloads.
- Added `GET /scrape-category/{job_id}/stock-summary` to return all persisted manual summaries for a job.

## Task Commits

1. **Task 1: Persist scheduled monitor rupture summaries beside monitored products**
   - `02abf48` test(44-02): add failing tests for scheduled stock summaries
   - `14e1569` feat(44-02): persist scheduled stock summaries
2. **Task 2: Persist manual category scan rupture summaries by job_id**
   - `82f1842` test(44-02): add failing tests for manual stock summaries
   - `15b4265` feat(44-02): persist manual stock summaries

## Files Created/Modified

- `backend/tests/test_phase44_routes.py` - TDD coverage for scheduled monitor summaries, manual job summaries, job_id propagation, and read endpoints.
- `backend/services/category_monitor_service.py` - Enriches scheduled scan products, persists monitor summary artifacts, and updates monitor metadata.
- `backend/api/routes_monitor.py` - Adds read-only monitor stock summary endpoint.
- `backend/services/orchestrator.py` - Adds optional `job_id` support and persists single-brand manual summaries.
- `backend/services/orchestrator_multi.py` - Persists per-brand manual summaries under the shared job artifact.
- `backend/api/routes_category.py` - Passes generated `job_id` into manual scans and exposes manual summary endpoint.

## Decisions Made

- Manual summaries use `scan_id="{job_id}:{brand_key}"` so multi-brand jobs remain auditable while sharing one job-level artifact.
- API endpoints are read-only loaders over persisted JSON artifacts; no route recomputes summary math from caller-provided products.
- Hugo Boss remains excluded from automated success proof for STOCK-01 because zero products would mask the known VTEX-IO category dependency.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Backstage standards MCP was unavailable in this Codex session. The implementation followed the Phase 44 pattern map and existing FastAPI/service conventions instead.
- The RED fixture for manual scan orchestration initially omitted the existing `run_bulk_scrape(..., log_callback, cancel_event)` kwargs. The fixture was corrected during GREEN to match the established engine interface.

## Known Stubs

None in production code. Empty dict/list values in tests are intentional fixtures and accumulators.

## Threat Flags

None. The new network/API surfaces are the read-only endpoints explicitly listed in the plan and use persisted summary loaders.

## Verification

- `python -m pytest backend/tests/test_stock_summary_service.py backend/tests/test_phase44_routes.py -q` -> 16 passed.
- `python - <<'PY' ... inspect.signature(run_orchestrator) ... PY` -> PASS, `job_id` remains optional with default `None`.
- Acceptance grep: `routes_monitor.py` uses `load_monitor_stock_summary`; `routes_category.py` uses `load_category_job_stock_summaries`; no route recomputes summary math.
- Acceptance grep: scheduled/manual summary wiring does not inspect SKU/seller/variant arrays; product-level `stock_availability` remains the only summary input.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for Plan 44-03 to add explicit stock-depth actions against persisted scan products. Downstream code can rely on `scan_product_id` being present in scheduled monitor products and on manual summary artifacts being addressable by `job_id`.

## Self-Check: PASSED

- Found created/modified files: `backend/tests/test_phase44_routes.py`, `backend/services/category_monitor_service.py`, `backend/api/routes_monitor.py`, `backend/services/orchestrator.py`, `backend/services/orchestrator_multi.py`, `backend/api/routes_category.py`, and this SUMMARY.
- Found commits: `02abf48`, `14e1569`, `82f1842`, `15b4265`.
- Re-ran plan verification: `python -m pytest backend/tests/test_stock_summary_service.py backend/tests/test_phase44_routes.py -q` -> 16 passed.

---
*Phase: 44-ruptura-de-estoque-avalia-es-refor-adas*
*Completed: 2026-06-30*
