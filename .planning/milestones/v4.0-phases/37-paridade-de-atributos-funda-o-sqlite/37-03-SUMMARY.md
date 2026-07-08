---
phase: 37-paridade-de-atributos-fundacao-sqlite
plan: 03
subsystem: backend-export
tags: [python, pandas, fastapi, pytest, excel, export-contract]

requires:
  - phase: 37-paridade-de-atributos-fundacao-sqlite
    plan: 01
    provides: shared canonical projector
  - phase: 37-paridade-de-atributos-fundacao-sqlite
    plan: 02
    provides: engine and parser parity signals
provides:
  - Comparative export uses the shared canonical leading column block
  - Single-brand category export uses the same canonical leading columns
  - Multi-brand category export uses the same canonical leading columns
  - Regression tests that lock all three export surfaces to one contract
affects: [search-export, orchestrator, orchestrator-multi]

tech-stack:
  added: []
  patterns:
    - One shared export DataFrame builder across all Excel surfaces
    - Canonical block first, extra raw/spec columns appended after it

key-files:
  created:
    - backend/tests/test_export_search_contract.py
  modified:
    - backend/api/routes_search.py
    - backend/services/orchestrator.py
    - backend/services/orchestrator_multi.py

key-decisions:
  - The three Excel-producing paths now share `build_canonical_export_dataframe(...)`
  - Existing sort behavior is preserved where it already existed (`brand`, `price_full`)
  - No new route or UI surface was introduced

requirements-completed: [PARID-01, PARID-02]
completed: 2026-07-03
---

# Phase 37 Plan 03 Summary

**All Excel-producing Phase 37 surfaces now lead with the same canonical English column block.**

## Accomplishments

- Replaced route-local/category-local export flattening with the shared canonical export builder.
- Added `backend/tests/test_export_search_contract.py` to prove `/search/export`, the single-brand orchestrator, and the multi-brand consolidator all emit the same leading contract.
- Kept sparse-row behavior additive: products remain present and blanks/nulls stay blanks/nulls.

## Task Results

1. **Wave 0 export contract tests**
   - `backend/tests/test_export_search_contract.py`
   - Result: completed
2. **Comparative export consumes the shared projector**
   - `backend/api/routes_search.py`
   - Result: completed
3. **Category orchestrators consume the same projector**
   - `backend/services/orchestrator.py`
   - `backend/services/orchestrator_multi.py`
   - Result: completed

## Task Commits

No git commits were created in this workspace run.

## Verification

- `python -m pytest backend/tests/test_export_search_contract.py -q` -> 3 passed
- `python -m pytest -q` -> 525 passed, 1 existing warning

## Deviations from Plan

None.

## Self-Check: PASSED

- Comparative export, single-brand export, and multi-brand export share one canonical leading contract.
- Sparse products are still exported.
- No new endpoint or UI surface was introduced.

