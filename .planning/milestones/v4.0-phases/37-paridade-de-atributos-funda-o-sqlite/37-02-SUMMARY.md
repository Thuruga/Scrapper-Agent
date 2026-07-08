---
phase: 37-paridade-de-atributos-fundacao-sqlite
plan: 02
subsystem: backend-engines
tags: [python, pytest, vtex, shopify, wake, sfcc, zara, marketplace, attribute-parity]

requires:
  - phase: 37-paridade-de-atributos-fundacao-sqlite
    plan: 01
    provides: shared canonical contract and projector
provides:
  - VTEX additive spec normalization with visible `product_code` support
  - Shopify category/color/size signals promoted into the canonical seam without inventing `product_code`
  - Characterization coverage proving rich and sparse engines obey the same blanks semantics
affects: [37-03, comparative-export, category-export]

tech-stack:
  added: []
  patterns:
    - Real mapper/parser characterization tests against the canonical row contract
    - Sparse engines remain truthful by returning blanks instead of synthetic attributes

key-files:
  created:
    - backend/tests/test_phase37_engine_contract.py
  modified:
    - backend/services/vtex_api_scraper.py
    - backend/services/shopify_api_client.py
    - backend/tests/test_vtex_api_client.py

key-decisions:
  - VTEX now normalizes additive specification aliases before building `RawProductBronze`
  - Shopify promotes available colors/sizes from real option names and keeps `product_code` blank
  - Sparse Wake/SFCC/Zara/Amazon paths are verified through characterization tests rather than forced into fabricated fields

requirements-completed: [PARID-02, PARID-03]
completed: 2026-07-03
---

# Phase 37 Plan 02 Summary

**Engine and parser parity now flows through the shared contract, with rich sources filling real fields and sparse sources keeping blanks semantics.**

## Accomplishments

- VTEX now carries additive canonical aliases in `specifications`, including visible `product_code` when present.
- Shopify now promotes available colors and sizes from option metadata and keeps its canonical shape aligned with the shared projector.
- Added `backend/tests/test_phase37_engine_contract.py` covering VTEX, Shopify, Wake, SFCC, Zara, and a marketplace PDP path.
- Updated the existing VTEX characterization expectation to the new additive-spec contract.

## Task Results

1. **Wave 0 characterization tests**
   - `backend/tests/test_phase37_engine_contract.py`
   - Result: completed
2. **Rich-engine parity improvements**
   - `backend/services/vtex_api_scraper.py`
   - `backend/services/shopify_api_client.py`
   - Result: completed
3. **Sparse-engine and marketplace alignment**
   - Verified via characterization coverage; no synthetic `product_code` or `composition` fallback introduced
   - Result: completed

## Task Commits

No git commits were created in this workspace run.

## Verification

- `python -m pytest backend/tests/test_phase37_engine_contract.py -q` -> 6 passed
- `python -m pytest backend/tests/test_vtex_api_client.py backend/tests/test_shopify.py backend/tests/test_wake_engine.py backend/tests/test_sfcc_engine.py backend/tests/test_zara_engine.py backend/tests/test_amazon_engine.py -q` -> passed within the phase regression bundle

## Deviations from Plan

None.

## Self-Check: PASSED

- Rich engines populate only truthful canonical fields.
- Sparse paths keep blanks/nulls instead of inventing product codes.
- Characterization tests are green.

