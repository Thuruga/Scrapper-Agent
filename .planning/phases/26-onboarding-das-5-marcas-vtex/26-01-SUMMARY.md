---
phase: 26-onboarding-das-5-marcas-vtex
plan: "01"
subsystem: tests
tags: [vtex, onboarding, contract-test, tdd, offline]
dependency_graph:
  requires: []
  provides:
    - "tests/test_vtex_brand_onboarding_contract.py → COMP-01 automated contract (D-10b)"
  affects:
    - "scripts/onboard_vtex_brands.py (26-02) — must satisfy this contract"
tech_stack:
  added: []
  patterns:
    - "BrandManagerService.__new__ in-memory factory (mirrors test_brand_active.py)"
    - "unittest.mock.patch.object for _save and brand_service monkeypatching"
    - "VALID_SLUGS derived from _RAW_CATEGORIES for source-of-truth sync (D-04)"
key_files:
  created:
    - tests/test_vtex_brand_onboarding_contract.py
  modified: []
decisions:
  - "Derived VALID_SLUGS from _RAW_CATEGORIES (not hardcoded set) to stay in sync with the canonical source (D-04 anchor)"
  - "Used unittest.mock.patch.object(category_mapping_module, 'brand_service', svc) to inject in-memory service into resolve_category_for_brands without touching real module state"
metrics:
  duration: "8m"
  completed: "2026-06-19"
  tasks: 1
  files: 1
---

# Phase 26 Plan 01: VTEX Brand Onboarding Contract Test Summary

Offline deterministic contract test that pins the post-onboarding state COMP-01 requires: JWT-free BrandManagerService in-memory factory + 6 test methods covering engine, is_active, mappings persistence, active list visibility, relative vtex_fq_path guard, and valid URL generation via resolve_category_for_brands.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Create offline contract test scaffold (COMP-01, D-10b) | 0e86617 | tests/test_vtex_brand_onboarding_contract.py |

## Verification Results

- `python -m pytest tests/test_vtex_brand_onboarding_contract.py -q` → **6 passed, 0 errors**
- Full suite: 162 passed, 1 pre-existing failure in test_ocr_service.py (cv2/easyocr env incompatibility — unrelated to this plan)

## Deviations from Plan

None — plan executed exactly as written. VALID_SLUGS derived from `_RAW_CATEGORIES` as instructed (not from non-existent `CANONICAL_SLUGS` export).

## Known Stubs

None — all test assertions are wired against real production code (BrandManagerService, CategoryMapping, resolve_category_for_brands). No placeholder data flows to any rendering path.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced. Test file only (I/O fully mocked).

## Self-Check: PASSED

- tests/test_vtex_brand_onboarding_contract.py — FOUND
- Commit 0e86617 — FOUND (git log confirms)
- 6 test methods collected and passing — CONFIRMED
