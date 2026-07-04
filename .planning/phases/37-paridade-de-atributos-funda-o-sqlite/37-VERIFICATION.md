---
phase: 37-paridade-de-atributos-fundacao-sqlite
verified: 2026-07-03T15:00:00Z
status: human_needed
score: 4/4 automated truths verified
overrides_applied: 0
human_verification:
  - test: "Run one real comparative export and inspect the first columns of the generated Excel."
    expected: "The sheet starts with `brand`, `url`, `price_full`, `price_discount`, `product_name`, `product_description`, `composition`, `available_colors`, `available_sizes`, `product_code`, `category`, `rating`, `review_count` in that exact order."
    why_human: "This is the final operator-facing Excel surface and should be visually confirmed in a real generated file."
  - test: "Run one real category export and compare its leading columns with the comparative export."
    expected: "The single-brand or multi-brand category sheet uses the same leading canonical English columns in the same order."
    why_human: "Confirms the real orchestrator file output, not only the hermetic DataFrame contract."
  - test: "Check one sparse engine row in a real export."
    expected: "Missing fields stay blank and no synthetic `product_code` appears when the source does not expose one."
    why_human: "Best validated against a real sparse-brand export row."
---

# Phase 37 Verification Report

**Phase Goal:** Deliver one canonical product/export contract across engines so comparative and category exports expose the same fixed English columns while sparse sources keep blanks semantics.

**Verified:** 2026-07-03T15:00:00Z
**Status:** human_needed

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | One shared canonical contract exists with additive aliasing and `product_code` support. | VERIFIED | `backend/services/product_contract.py` defines `CANONICAL_PRODUCT_COLUMNS`, additive alias normalization, canonical row projection, and canonical export DataFrame building; `backend/core/models.py` adds `RawProductBronze.product_code`. |
| 2 | Representative rich and sparse engines obey the canonical row contract without inventing missing values. | VERIFIED | `backend/tests/test_phase37_engine_contract.py` covers VTEX, Shopify, Wake, SFCC, Zara, and Amazon; VTEX/Shopify enrich real signals, sparse engines keep blanks semantics. |
| 3 | Comparative export leads with the canonical English columns. | VERIFIED | `backend/api/routes_search.py` now routes export rows through `build_canonical_export_dataframe(...)`; `backend/tests/test_export_search_contract.py::test_search_export_uses_canonical_leading_columns` is green. |
| 4 | Single-brand and multi-brand category exports use the same canonical leading columns. | VERIFIED | `backend/services/orchestrator.py` and `backend/services/orchestrator_multi.py` now consume the shared export builder; both category export regression tests are green. |

**Score:** 4/4 automated truths verified

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/services/product_contract.py` | Shared canonical projector and fixed column order | VERIFIED | File exists with pure helpers and no I/O. |
| `backend/tests/test_product_contract.py` | Wave-0 contract tests | VERIFIED | 3 tests pass. |
| `backend/tests/test_phase37_engine_contract.py` | Engine characterization coverage | VERIFIED | 6 tests pass. |
| `backend/tests/test_export_search_contract.py` | Cross-surface export contract coverage | VERIFIED | 3 tests pass. |
| `backend/api/routes_search.py` | Comparative export uses shared projector | VERIFIED | Shared export builder imported and used. |
| `backend/services/orchestrator.py` and `backend/services/orchestrator_multi.py` | Category exports use shared projector | VERIFIED | Shared export builder imported and used. |

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Shared contract + engine + export suites | `python -m pytest backend/tests/test_product_contract.py backend/tests/test_phase37_engine_contract.py backend/tests/test_export_search_contract.py backend/tests/test_vtex_api_client.py backend/tests/test_shopify.py backend/tests/test_wake_engine.py backend/tests/test_sfcc_engine.py backend/tests/test_zara_engine.py backend/tests/test_amazon_engine.py backend/tests/test_quality_gates.py -q` | 111 passed | PASS |
| Full backend regression | `python -m pytest -q` | 525 passed, 1 existing warning | PASS |

## Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| PARID-01 | Unique canonical product vocabulary and fixed export columns | SATISFIED | Shared projector + export contract tests. |
| PARID-02 | Engines populate the canonical field set truthfully | SATISFIED | Characterization suite proves rich and sparse behavior. |
| PARID-03 | Divergent source names are normalized additively | SATISFIED | Alias normalization preserves raw keys and adds canonical aliases. |
| PARID-04 | Coverage report wording is reinterpreted and not implemented | SATISFIED | No new report/log/endpoint was introduced; verification focuses on contract parity only. |

## Human Verification Required

### 1. Real Comparative Export

**Test:** Run one comparative export and inspect the sheet.
**Expected:** The canonical English column block appears first in the exact locked order.
**Why human:** Final spreadsheet output should be visually confirmed in a real file.

### 2. Real Category Export

**Test:** Run one category export and compare the leading columns with the comparative export.
**Expected:** The same canonical leading block appears first.
**Why human:** Confirms the live orchestrator file output, not only hermetic DataFrame tests.

### 3. Sparse Row Sanity Check

**Test:** Inspect one sparse-brand row in a real export.
**Expected:** Missing fields are blank and `product_code` is not fabricated.
**Why human:** Best verified against a real sparse engine result.

## Gaps Summary

No automated gaps were found. The phase is `human_needed` only because the validation strategy explicitly calls for real Excel/UAT confirmation on the generated files.

