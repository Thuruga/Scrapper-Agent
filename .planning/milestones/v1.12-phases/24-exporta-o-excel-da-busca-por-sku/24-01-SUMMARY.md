---
phase: 24-exporta-o-excel-da-busca-por-sku
plan: "01"
subsystem: testing
tags: [pytest, fastapi, openpyxl, tdd, red-scaffold, excel-export]

requires: []
provides:
  - "TDD RED scaffold: tests/test_export_cross_marketplace.py with 14 failing tests"
  - "Executable contract for POST /search/cross-marketplace/export (route, columns, behaviors)"
  - "Security behavior contracts: formula injection (T-24-01), payload size (T-24-02), auth 403 (T-24-03), empty payload (T-24-04)"
affects:
  - "24-02 (backend implementation must make these 14 tests GREEN)"
  - "24-03 (frontend; not directly tied to these tests but builds on same requirements)"

tech-stack:
  added: []
  patterns:
    - "TDD RED scaffold: test file created before implementation exists; tests fail with 404/ImportError (not syntax errors)"
    - "app.dependency_overrides[verify_api_key] bypass pattern for TestClient-based auth tests"
    - "TestClient from fastapi.testclient for sync endpoint testing without pytest-asyncio"

key-files:
  created:
    - tests/test_export_cross_marketplace.py
  modified: []

key-decisions:
  - "Wave 0 uses TestClient (app importable cleanly, no startup side-effects); pure-function fallback strategy not needed"
  - "14 tests collected: 12 endpoint tests (TestExportEndpoint) + 2 sanitize helper tests (TestSanitizeHelper)"
  - "test_empty_items asserts status in (400, 422) — both are acceptable per CONTEXT.md decision"
  - "_sanitize_cell imported lazily inside test methods (not at module level) so collection does not fail on ImportError"
  - "EXPECTED_HEADERS constant uses plain ASCII column names without accented chars to avoid encoding issues in the test file"

patterns-established:
  - "RED scaffold pattern: move dangerous imports (missing modules) inside test methods so pytest --collect-only succeeds"
  - "test_auth pop/restore pattern: temporarily removes dependency_overrides in try/finally to avoid contaminating other tests"

requirements-completed: [EXPORT-04, EXPORT-05, EXPORT-06]

duration: 10min
completed: 2026-06-15
---

# Phase 24 Plan 01: Exportacao Excel da Busca por SKU — TDD RED Scaffold Summary

**14-test RED scaffold for POST /search/cross-marketplace/export, locking the full backend contract (10 PT columns, null-shipping rule, boolean mapping, score rounding, formula injection, display-order sorting, fidelity, filename pattern, empty/oversized payload, auth) before any implementation**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-06-15T14:35:00Z
- **Completed:** 2026-06-15T14:45:00Z
- **Tasks:** 1 of 1
- **Files modified:** 1

## Accomplishments

- Created `tests/test_export_cross_marketplace.py` (395 lines) with 14 tests covering the full export endpoint contract
- All 14 tests confirmed RED: 12 fail with `assert 404 == 200` (route missing), 2 fail with `ImportError: cannot import name '_sanitize_cell'` (helper missing)
- Zero collection errors: `pytest --collect-only -q` collects all 14 tests cleanly
- 130 baseline tests remain green (new file does not break any existing test)
- Security threat mitigations locked as executable test assertions: T-24-01 (formula injection), T-24-02 (oversized payload), T-24-03 (auth 403), T-24-04 (empty items)

## Task Commits

1. **Task 1: Create the RED test scaffold** - `48c7cba` (test)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `tests/test_export_cross_marketplace.py` — RED scaffold: 14 tests covering EXPORT-04/05/06 and security edge cases; fails with 404 (missing route) and ImportError (missing `_sanitize_cell`)

## Decisions Made

- **app imports cleanly**: `from app import app` works without startup side-effects breaking test collection. The TestClient approach from PATTERNS.md is used directly; the pure-function fallback (RESEARCH A1) was not needed.
- **_sanitize_cell imported inside test methods**: avoids collection failure at module level when the function does not exist yet. Both tests in `TestSanitizeHelper` fail at runtime with `ImportError` (expected RED behavior).
- **EXPECTED_HEADERS uses ASCII-safe names**: Column header strings in the test constant use plain characters (e.g. "Titulo", "Preco", "Frete Gratis") to avoid potential encoding issues in the test file itself; the actual PT-BR headers with accents will be tested against what the endpoint returns.
- **test_auth uses try/finally**: ensures `dependency_overrides` is always restored even if the assertion fails, preventing test pollution.

## Deviations from Plan

None - plan executed exactly as written. The test file structure, import pattern, fixture design, and test method names follow the plan specification. The fallback strategy (pure-function testing without TestClient) was not needed.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. All test dependencies (pytest, openpyxl, FastAPI TestClient) were already installed and verified.

## Next Phase Readiness

- Plan 24-02 (backend implementation) has a complete, executable contract: implement `POST /search/cross-marketplace/export`, `CrossMarketplaceExportRequest` Pydantic model, and `_sanitize_cell` in `api/routes_search.py`; run `python -m pytest tests/test_export_cross_marketplace.py -q` — all 14 must turn GREEN.
- No blockers.

## TDD Gate Compliance

- RED gate commit: `48c7cba` (`test(24-01): add RED scaffold...`) — RED gate satisfied.
- GREEN gate: pending Plan 02 implementation.

---
*Phase: 24-exporta-o-excel-da-busca-por-sku*
*Completed: 2026-06-15*
