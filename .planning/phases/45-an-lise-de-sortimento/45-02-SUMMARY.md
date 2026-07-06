---
phase: 45-an-lise-de-sortimento
plan: 02
subsystem: backend-analytics
tags: [python, fastapi, apscheduler, pytest, json-persistence, sortiment]

requires:
  - phase: 45-an-lise-de-sortimento
    provides: Plan 45-01 JSON registry, snapshot, and manifest foundations
provides:
  - Sortiment category execution runtime with aggregate-only snapshots and backend delta assembly
  - Dedicated sortiment API routes for registry sync, toggle, manual run, and dashboard reads
  - Independent APScheduler job for enabled sortiment categories with overlap protection
affects: [45-03, sortiment, monitoring, scheduler]

tech-stack:
  added: []
  patterns:
    - Backend-owned latest-versus-previous dashboard payloads
    - Shared async overlap guard for cron and manual sortiment runs
    - Separate FastAPI surface for sortiment registry and dashboard reads

key-files:
  created:
    - backend/services/sortiment_snapshot_service.py
    - backend/api/routes_sortiment.py
    - backend/tests/test_sortiment_snapshot_service.py
    - backend/tests/test_sortiment_routes.py
  modified:
    - backend/services/sortiment_registry_service.py
    - backend/api/__init__.py
    - backend/app.py

key-decisions:
  - "45-02/dashboard-backend-owned: baseline and delta semantics are assembled on the backend from latest/previous manifests, never reconstructed in the browser."
  - "45-02/overlap-guard: cron and manual sortiment runs share one asyncio guard; overlapping manual calls return status='busy' instead of double-running."
  - "45-02/scheduler-isolation: sortiment runs use a dedicated APScheduler job id with max_instances=1 and coalesce=True, leaving the 10-minute category monitor cadence intact."

patterns-established:
  - "Dimension normalization collapses dirty values to 'não informado' only when a product has no usable value for that dimension."
  - "Sortiment routes accept persisted category IDs only; URL and brand stay server-owned registry data."
  - "Enabled-only cron iteration happens through load_sortiment_categories(enabled_only=True), not monitor-category reuse."

requirements-completed: [SORT-01]

duration: 11 min
completed: 2026-07-06
---

# Phase 45 Plan 02: Sortiment Runtime and API Summary

**Guarded sortiment snapshot execution, dedicated API routes, and an independent APScheduler job for latest-versus-previous dashboard payloads**

## Performance

- **Duration:** 11 min
- **Started:** 2026-07-06T02:44:15Z
- **Completed:** 2026-07-06T02:55:06Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Added `sortiment_snapshot_service.py` to execute persisted sortiment categories into immutable aggregate-only snapshots and assemble truthful baseline/delta dashboard payloads.
- Added dedicated `/sortiment/*` routes for registry listing, one-way sync, enable/disable, manual runs, and dashboard reads, all keyed by persisted category ID.
- Registered an independent APScheduler sortiment job with `max_instances=1` and `coalesce=True`, while keeping the existing category-monitor job separate.

## Task Commits

1. **Task 1: Implement snapshot execution, bucket normalization, and dashboard read model**
   - `8721fe7` test(45-02): add failing tests for sortiment snapshots
   - `9e53914` feat(45-02): implement sortiment snapshot runtime
2. **Task 2: Add sortiment API routes and independent overlap-safe scheduler wiring**
   - `dac9d48` test(45-02): add failing tests for sortiment routes
   - `5b1830b` feat(45-02): wire sortiment api and scheduler

## Files Created/Modified

- `backend/services/sortiment_snapshot_service.py` - Runs category snapshots, normalizes buckets, assembles baseline/delta dashboard payloads, and guards cron/manual overlap.
- `backend/api/routes_sortiment.py` - Exposes the dedicated sortiment registry, manual-run, and dashboard API surface.
- `backend/tests/test_sortiment_snapshot_service.py` - TDD coverage for immutable snapshot execution, dimension normalization, baseline/delta semantics, busy guard, and enabled-only cron iteration.
- `backend/tests/test_sortiment_routes.py` - TDD coverage for strict route boundaries, busy manual-run responses, and scheduler registration.
- `backend/services/sortiment_registry_service.py` - Adds server-side lookup/update helpers used by the ID-based runtime and routes.
- `backend/api/__init__.py` - Registers the sortiment router in the protected API aggregate.
- `backend/app.py` - Registers the independent sortiment APScheduler job through a shared scheduler configuration helper.

## Decisions Made

- Built the dashboard response on the backend from persisted manifests so the UI can consume explicit baseline/latest/previous state instead of rebuilding snapshot math.
- Used a shared async guard for cron and manual runs to prevent double-execution while returning a user-visible `busy` status instead of raising a transport error.
- Kept route boundaries server-owned: the browser can toggle or run only by persisted category ID and cannot inject alternate URL/brand/runtime parameters.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added registry lookup/update helpers outside the original file list**
- **Found during:** Task 1 (snapshot execution runtime)
- **Issue:** The Plan 45-01 foundation exposed load/save/sync helpers, but the Phase 45 runtime and routes needed server-side lookup/update by persisted category ID to preserve the route boundary.
- **Fix:** Extended `backend/services/sortiment_registry_service.py` with `get_sortiment_category()` and `update_sortiment_category()` so manual runs and dashboard reads stay ID-driven.
- **Files modified:** `backend/services/sortiment_registry_service.py`
- **Verification:** `.venv/bin/python -m pytest tests/test_sortiment_snapshot_service.py tests/test_sortiment_routes.py -x -q`
- **Committed in:** `9e53914`

---

**Total deviations:** 1 auto-fixed (Rule 2 missing critical)
**Impact on plan:** The helper addition kept the runtime and routes inside the intended server-owned boundary. No new feature scope was introduced.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for Plan 45-03 to consume the dedicated sortiment API from the frontend and render the registry controls plus baseline/delta dashboard without re-deriving snapshot semantics in the browser.

## Self-Check: PASSED

- Found created files: `backend/services/sortiment_snapshot_service.py`, `backend/api/routes_sortiment.py`, `backend/tests/test_sortiment_snapshot_service.py`, `backend/tests/test_sortiment_routes.py`, and this summary.
- Found commits: `8721fe7`, `9e53914`, `dac9d48`, `5b1830b`.
- Re-ran verification: `.venv/bin/python -m pytest tests/test_sortiment_snapshot_service.py tests/test_sortiment_routes.py -x -q` -> 7 passed.
- Re-ran contract grep: `rg -n "max_instances=1|coalesce=True|include_router\\(sortiment_router\\)|baseline" backend/app.py backend/api/__init__.py backend/api/routes_sortiment.py backend/services/sortiment_snapshot_service.py` -> expected scheduler/router/dashboard markers present.

---
*Phase: 45-an-lise-de-sortimento*
*Completed: 2026-07-06*
