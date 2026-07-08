---
phase: 37-paridade-de-atributos-fundacao-sqlite
plan: 01
subsystem: backend-contract
tags: [python, pydantic, pandas, pytest, export-contract, attribute-parity]

provides:
  - Shared canonical Phase 37 product contract with fixed English leading columns
  - Additive `product_code` support on `RawProductBronze`
  - Pure alias normalization and canonical row projection helpers
  - Wave-0 contract coverage for fallback semantics and additive aliases
affects: [37-02, 37-03, search-export, category-export]

tech-stack:
  added: []
  patterns:
    - Pure helper service for canonical product/export projection
    - Additive aliasing that preserves raw specification keys

key-files:
  created:
    - backend/services/product_contract.py
    - backend/tests/test_product_contract.py
  modified:
    - backend/core/models.py

key-decisions:
  - Canonical export order is fixed in one shared constant: `CANONICAL_PRODUCT_COLUMNS`
  - `product_name` and `product_description` fall back from `raw_title` and `raw_description` instead of renaming the bronze model
  - `product_code` only comes from visible product/specification signals; no internal ID fallback was introduced

requirements-completed: [PARID-01, PARID-03]
completed: 2026-07-03
---

# Phase 37 Plan 01 Summary

**Shared canonical product/export contract added with additive alias normalization and pure contract tests.**

## Accomplishments

- Added `product_code: Optional[str] = None` to `RawProductBronze`.
- Created `backend/services/product_contract.py` with the fixed canonical column block, additive specification normalization, canonical row projection, and canonical export DataFrame builder.
- Added `backend/tests/test_product_contract.py` to lock canonical column order, fallback semantics, and alias preservation.

## Task Results

1. **Wave 0 contract tests**
   - `backend/tests/test_product_contract.py`
   - Result: RED-to-GREEN completed in this workspace run
2. **Additive model field for `product_code`**
   - `backend/core/models.py`
   - Result: completed
3. **Shared canonical projector**
   - `backend/services/product_contract.py`
   - Result: completed

## Task Commits

No git commits were created in this workspace run.

## Verification

- `python -m pytest backend/tests/test_product_contract.py -q` -> 3 passed

## Deviations from Plan

None.

## Self-Check: PASSED

- Required files exist on disk.
- Canonical contract tests pass.
- The helper stays pure and does not add I/O or route behavior.

