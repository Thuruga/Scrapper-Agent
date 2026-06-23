---
phase: 30-detec-o-de-engine-sfcc-wake
plan: "03"
subsystem: engine-detection-tests
tags: [tests, pytest, sfcc, wake, detect-engine, asyncmock, sc-1, sc-2, sc-3, sc-4]
dependency_graph:
  requires: [detect_engine_wake, detect_engine_sfcc, engine_factory_sfcc_wake_guard]
  provides: [phase30_detection_green_suite]
  affects: [backend/tests/test_engine_detection.py]
tech_stack:
  added: []
  patterns: [asyncmock-browser-seam, patch-object-detect-engine, mock-session-substring-router]
key_files:
  modified:
    - backend/tests/test_engine_detection.py
decisions:
  - "D-11: test_engine_detection.py converted from v2.0 RED baseline to the Phase 30 GREEN regression+expansion suite"
  - "SC-3 verified against the EXISTING D-04 logic — sfcc/wake brands stay active because the deactivation branch only fires for 'unknown'; create_brand was NOT modified"
metrics:
  duration: "12m"
  completed_date: "2026-06-23"
  tasks_completed: 2
  files_modified: 1
---

# Phase 30 Plan 03: Engine Detection GREEN Suite Summary

**One-liner:** `test_engine_detection.py` is now the Phase 30 GREEN suite (9 passing tests) proving SC-1 (SFCC via browser), SC-2 (Wake), SC-3 (sfcc/wake brands stay active), and SC-4 (anti-false-positive) against the 30-01/30-02 code, with the regression base (shopify, vtex, D-04 unknown→inactive) intact.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Wake flip + SFCC browser mock seam + new detection cases | 36f8543 | backend/tests/test_engine_detection.py |
| 2 | SC-3 stays-active test (existing D-04 logic, no create_brand change) | 36f8543 | backend/tests/test_engine_detection.py |

(Both tasks landed in a single atomic test-file commit — the file is one coherent unit and Task 2's class sits in the same module; splitting would have produced an intermediate state with an incomplete suite.)

## What Was Built

### Task 1 — detection cases (SC-1, SC-2, SC-4)
- Rewrote the module docstring: no longer a RED baseline; it is the Phase 30 GREEN regression+expansion suite.
- Renamed `test_wake_commerce_returns_unknown` → `test_wake_commerce_detected_returns_wake`; assertion flipped `"unknown"` → `"wake"` (SC-2, D-05). The Wake branch returns before the browser probe, so no browser mock is needed there.
- Added `test_sfcc_detected_via_browser` (SC-1): HTTP probes 403/404, home HTML has no VTEX/Wake/Shopify markers, and `BrowserManager.fetch_html` (AsyncMock) returns HTML containing `/on/demandware.static/...` → asserts `"sfcc"`.
- Added `test_sfcc_anti_false_positive_403_no_demandware` (SC-4, Zara/Inditex case): all HTTP probes 403, rendered HTML has a `static.zara.net` asset but **no** `demandware.static`/`demandware.edgesuite.net` → asserts `"unknown"`.
- Extended `test_all_probes_fail_returns_unknown` (SC-4) to also mock `BrowserManager.fetch_html` with marker-free HTML so the suite stays hermetic (no real Playwright launch, T-30-09).
- Kept `test_shopify_detected_via_collections_json` and `test_vtex_detected_via_category_tree` verbatim as the regression base, plus the `_make_mock_response` / `_make_mock_session` helpers.

### Task 2 — SC-3 stays-active (no production change)
- Added `TestCreateBrandActive` with `test_sfcc_brand_stays_active` and `test_wake_brand_stays_active`, mirroring the existing `TestCreateBrandUnknown` seam (`patch.object(routes_brands_module, "detect_engine", ...)`, `brand_service.add_brand`, `brand_service.set_active`).
- A shared `_run_create_brand_with_detected_engine(engine)` helper drives `create_brand` with `detect_engine` mocked to the engine, `add_brand` returning a fake active `DynamicBrand`, and `set_active` patched as a `MagicMock`.
- Each test asserts `result.engine == <engine>`, `result.is_active is True`, and `set_active.assert_not_called()` — proving the D-04 deactivation branch (which only matches `"unknown"`) does NOT fire for sfcc/wake. `create_brand` is unmodified.

## Verification

- `cd backend && python -m pytest tests/test_engine_detection.py -q` → **9 passed in 2.37s** ✓
- `git diff --name-only HEAD` for `backend/api/routes_brands.py` and `backend/services/engines/factory.py` → empty (no production change in this plan) ✓
- Only `backend/tests/test_engine_detection.py` modified ✓
- SC-1 → `test_sfcc_detected_via_browser`; SC-2 → `test_wake_commerce_detected_returns_wake`; SC-3 → `test_sfcc_brand_stays_active` + `test_wake_brand_stays_active`; SC-4 → `test_sfcc_anti_false_positive_403_no_demandware` + extended `test_all_probes_fail_returns_unknown` ✓

## Deviations from Plan

**Mock seam target changed (justified).** The plan's `must_haves`/`key_links` specify patching `api.routes_brands.BrowserManager.fetch_html`. That target is invalid: plan 30-01 implemented the SFCC probe with a **lazy local import** (`from core.browser_manager import BrowserManager` inside `detect_engine`), so `api.routes_brands` has no module-level `BrowserManager` attribute — `patch("api.routes_brands.BrowserManager.fetch_html")` would raise `AttributeError` at patch setup. The tests instead patch the method on its class of origin, `core.browser_manager.BrowserManager.fetch_html` (a captured constant `_BROWSER_FETCH_TARGET`), which the lazy import resolves to. This satisfies the functional acceptance criteria (AsyncMock seam returning demandware HTML → `"sfcc"`; suite GREEN) and the `contains: "BrowserManager.fetch_html"` artifact check. The `verify.key-links` regex (`api\.routes_brands\.BrowserManager\.fetch_html`) will not match by design — modifying production `routes_brands.py` to add a module-level alias just to satisfy the regex was rejected because this is a tests-only plan ("Do NOT modify production code").

Both Task 1 and Task 2 were committed together (see note in the tasks table). Otherwise executed as written.

## Threat Surface Scan

- T-30-08 (test integrity): the anti-false-positive case and `set_active.assert_not_called()` are negative/behavioral assertions on exact engine strings — they fail loudly if detection over-matches or `create_brand` regresses ✓
- T-30-09 (DoS / accidental real I/O): every case that can reach the SFCC probe mocks `BrowserManager.fetch_html`; no test launches a real browser or hits the network (suite runs in 2.37s) ✓

## Known Stubs

None. The suite exercises real `detect_engine` / `create_brand` code paths with mocked I/O boundaries only.

## Self-Check: PASSED

- `backend/tests/test_engine_detection.py` exists and contains the new cases + `BrowserManager.fetch_html` seam ✓
- Commit `36f8543` exists (Tasks 1+2) ✓
- `pytest tests/test_engine_detection.py -q` → 9 passed ✓
- No production file modified by this plan ✓
