---
phase: 27-hist-rico-completo-gest-o-de-marcas-na-ui
plan: "00"
subsystem: backend/tests
tags: [tdd, red-scaffold, history, hist-01, pytest]
requirements: [HIST-01]
dependency_graph:
  requires: []
  provides: [tests/test_search_history_comparative.py]
  affects: [27-01]
tech_stack:
  added: []
  patterns:
    - in-memory service via __new__ (mirrors test_brand_active.py)
    - monkeypatched module singletons in try/finally
    - asyncio.run for direct async route calls in tests
key_files:
  created:
    - tests/test_search_history_comparative.py
  modified: []
decisions:
  - "Resolution A (shape contract): stored results for comparative search MUST be the inner List[BrandSearchResult] array (ComparisonResult.model_dump(mode='json')['results']), NOT the ComparisonResult wrapper dict — locked by test_persisted_results_shape_is_inner_list"
metrics:
  duration: 2m
  completed: 2026-06-20
  tasks_completed: 1
  files_changed: 1
---

# Phase 27 Plan 00: RED Test Scaffold for HIST-01 Summary

Wave 0 RED pytest scaffold encoding the HIST-01 persistence contract — 4 test functions locking the stored-result-shape contract (inner list, not ComparisonResult wrapper), persistence, FAILED path, and service round-trip before 27-01 writes any implementation.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create tests/test_search_history_comparative.py | 2245e37 | tests/test_search_history_comparative.py |

## What Was Built

Created `tests/test_search_history_comparative.py` with 4 test functions following the `tests/test_brand_active.py` project idiom exactly:

- **`test_history_service_search_type`** (unit) — in-memory `SearchHistoryService` via `__new__`, `_save_history` patched to no-op; verifies `create_job(type="search")` + `update_job` round-trip: `type`, `status`, `results`. PASSES today (service already correct).

- **`test_post_search_persists_history`** (integration RED) — injects history service, engine mock, brand service mock via try/finally; calls `asyncio.run(routes_search.search_products(req))`; asserts exactly 1 record with `type="search"`, `status="COMPLETED"`, `query="polo"` (raw term, not composed label). Fails RED — route has no persistence.

- **`test_persisted_results_shape_is_inner_list`** (integration RED) — same setup; asserts `stored.results` is `list` AND each element has `brand_key`; explicit negative assertion: `not (isinstance(stored.results, dict) and "brands_searched" in stored.results)`. Locks Resolution A (shape contract). Fails RED.

- **`test_search_failure_marks_failed`** (integration RED) — engine mock raises `RuntimeError("boom")`; wraps route call in `pytest.raises(RuntimeError)`; asserts `status="FAILED"`, `error` contains "boom". Locks Pitfall 5. Fails RED.

## Verification Results

- `python -m pytest tests/test_search_history_comparative.py --collect-only -q` → **4 tests, 0 collection errors** (acceptance criteria met)
- `python -m pytest tests/test_search_history_comparative.py -x` → **RED** (1 passed / 3 failed) — expected; 27-01 makes them green
- `python -m pytest tests/ --collect-only -q` → **168 tests, 0 import errors** — no breakage introduced

## Deviations from Plan

None — plan executed exactly as written.

## Threat Surface Scan

No new runtime surface introduced. Test-only file with no-op I/O (T-27-00-01 mitigated: `_save_history` patched; tests never touch `data/search_history.json`).

## Self-Check: PASSED

- `tests/test_search_history_comparative.py` exists and contains `def test_persisted_results_shape_is_inner_list`
- Commit `2245e37` exists: `test(27-00): add RED scaffold for HIST-01 persistence contract`
- 4 tests collected, 0 import errors
- File exceeds 80 lines minimum (contains 299 lines)
- Uses `SearchHistoryService.__new__`, `_save_history` patch, `asyncio.run`, singletons in try/finally
