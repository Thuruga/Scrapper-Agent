---
phase: 25-funda-o-de-motores
plan: "00"
subsystem: tests
tags: [tdd, red, comp-02, mgmt-01, engine-detection, brand-active]
dependency_graph:
  requires: []
  provides:
    - tests/test_engine_detection.py
    - tests/test_brand_active.py
  affects:
    - api/routes_brands.py (Wave 1 implementation target)
    - services/brand_service.py (Wave 2 implementation target)
tech_stack:
  added: []
  patterns:
    - "asyncio.run() for async test execution (no pytest-asyncio)"
    - "unittest.mock.MagicMock with __aenter__/__aexit__ for aiohttp context managers"
    - "BrandManagerService.__new__() + _check_reload no-op for in-memory fixture"
    - "patch.object(svc, '_check_reload') to bypass JSON reload in unit tests"
    - "patch.object(..., create=True) to patch non-existent attributes (Wave 0 RED)"
key_files:
  created:
    - tests/test_engine_detection.py
    - tests/test_brand_active.py
  modified: []
decisions:
  - "Added _check_reload no-op mock to _make_service_with_brands() to prevent JSON file reload overwriting in-memory test data"
  - "Used create=True in patch.object for set_active to allow RED scaffold to work before the method exists in Wave 1"
  - "TestBrandRouteReturnsInactive injects fake_svc directly into routes_brands_module.brand_service (replaces singleton temporarily) — avoids FastAPI TestClient overhead"
metrics:
  duration: "8m"
  completed: "2026-06-18"
  tasks: 2
  files: 2
---

# Phase 25 Plan 00: Wave 0 RED Test Scaffold Summary

**One-liner:** RED test scaffolds for COMP-02 (detect_engine unknown/Wake) and MGMT-01 (list_brands active_only + set_active) using asyncio.run + unittest.mock aiohttp context managers.

## What Was Built

Two new test files establishing the Nyquist feedback loop for Phase 25 Waves 1 and 2:

**`tests/test_engine_detection.py`** (COMP-02 RED scaffold):
- `TestDetectEngine` — 4 cases exercising `detect_engine` with mocked aiohttp sessions:
  - `test_shopify_detected_via_collections_json` — PASSES (Shopify detection already works)
  - `test_vtex_detected_via_category_tree` — PASSES (VTEX API detection already works)
  - `test_wake_commerce_returns_unknown` — FAILS RED (current code returns "vtex", not "unknown")
  - `test_all_probes_fail_returns_unknown` — FAILS RED (current fallback L53 returns "vtex")
- `TestCreateBrandUnknown` — integration test for D-04:
  - `test_unknown_engine_brand_saved_inactive` — FAILS RED (`is_active=True` vs expected `False`)

**`tests/test_brand_active.py`** (MGMT-01 RED scaffold):
- `TestListBrandsActiveOnly` — 3 cases for `list_brands(active_only)` parameter:
  - `test_default_returns_all_brands` — PASSES (no-arg call returns 2 brands)
  - `test_active_only_excludes_inactive` — FAILS RED (TypeError: unexpected keyword)
  - `test_active_only_false_returns_all` — FAILS RED (TypeError: unexpected keyword)
- `TestSetActive` — 3 cases for `set_active()` (doesn't exist yet):
  - `test_deactivate_brand` — FAILS RED (AttributeError: no set_active)
  - `test_reactivate_brand` — FAILS RED (AttributeError: no set_active)
  - `test_set_active_unknown_key_returns_none` — FAILS RED (AttributeError: no set_active)
- `TestBrandRouteReturnsInactive` — SC-4 guard:
  - `test_route_includes_inactive_brand` — PASSES (guard against Pitfall-6 regression)

**Combined result:** 12 tests collected, 4 pass, 8 fail RED. Zero import/collection errors.

## Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | RED scaffold tests/test_engine_detection.py (COMP-02) | 2edc2a6 | tests/test_engine_detection.py |
| 2 | RED scaffold tests/test_brand_active.py (MGMT-01) | b76f9a8 | tests/test_brand_active.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added _check_reload no-op to _make_service_with_brands() fixture**
- **Found during:** Task 2 — first run showed `test_default_returns_all_brands` getting 8 brands instead of 2
- **Issue:** `list_brands()` calls `_check_reload()` which reloads from `data/brands.json`, overwriting the in-memory test fixture with real production data (8 brands from brands.json)
- **Fix:** Added `svc._check_reload = unittest.mock.MagicMock()` to the helper after `__new__` construction — prevents JSON reload while keeping the service in pure in-memory mode
- **Files modified:** tests/test_brand_active.py (helper only, no production code)
- **Commit:** b76f9a8

**2. [Rule 1 - Bug] Used create=True in patch.object for set_active**
- **Found during:** Task 1 — first run of TestCreateBrandUnknown raised AttributeError during patch setup (not during test execution)
- **Issue:** `patch.object` raises AttributeError during `__enter__` when the target attribute doesn't exist, preventing the test body from running
- **Fix:** Added `create=True` kwarg to `patch.object` for `set_active` — allows patching a non-existent attribute, so the test body executes and fails on the assertion (correct RED behavior)
- **Files modified:** tests/test_engine_detection.py
- **Commit:** 2edc2a6

## Known Stubs

None — test files only, no production stubs.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. Test files only; all HTTP mocked via unittest.mock.

## Self-Check: PASSED

- [x] tests/test_engine_detection.py exists and collects
- [x] tests/test_brand_active.py exists and collects
- [x] Commit 2edc2a6 verified in git log
- [x] Commit b76f9a8 verified in git log
- [x] `pytest tests/test_engine_detection.py tests/test_brand_active.py -q` → 8 failed, 4 passed (0 errors)
- [x] All named -k filters from VALIDATION Per-Task Verification Map collect and produce expected RED/PASS state
