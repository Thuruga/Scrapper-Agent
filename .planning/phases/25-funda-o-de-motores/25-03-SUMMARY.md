---
phase: 25-funda-o-de-motores
plan: "03"
subsystem: brand-management-api
tags: [mgmt, brand-activation, api-route, chokepoint, active-only]
dependency_graph:
  requires: ["25-01", "25-02"]
  provides: ["PATCH /brands/{brand_key}/active", "active_only=True call sites"]
  affects:
    - api/routes_brands.py
    - api/routes_search.py
    - services/engines/factory.py
    - api/routes_category.py
    - core/models.py
tech_stack:
  added: []
  patterns: ["thin route", "Pydantic input validation (V5)", "idempotent PATCH", "single-chokepoint opt-in"]
key_files:
  created: []
  modified:
    - core/models.py
    - api/routes_brands.py
    - api/routes_search.py
    - services/engines/factory.py
    - api/routes_category.py
decisions:
  - "OQ2 YES: routes_category.py scrape_category_multi enforces active_only=True — inactive brands are not valid scan targets (consistency with search)"
  - "BrandActiveUpdate placed in core/models.py near DynamicBrand for colocation with the domain model"
  - "Pre-existing test_ocr_service cv2/Python3.14 env failure confirmed unrelated and out of scope"
metrics:
  duration: "15m"
  completed: "2026-06-18"
  tasks: 2
  files: 4
---

# Phase 25 Plan 03: PATCH /brands/{brand_key}/active + active_only Wiring Summary

**One-liner:** PATCH endpoint for idempotent brand activation/deactivation wired to `brand_service.set_active`, plus `active_only=True` chokepoint adoption at all five consumer call sites.

## What Was Built

### Task 1: PATCH /brands/{brand_key}/active + BrandActiveUpdate (D-06)

**`core/models.py`** — Added `BrandActiveUpdate(BaseModel)` with a single field `is_active: bool`. Placement near `DynamicBrand` for domain model colocation. The `bool` type is the V5 Input Validation mitigation (T-25-03-BODY): Pydantic/FastAPI returns HTTP 422 automatically for any non-bool body.

**`api/routes_brands.py`** — Added `@router.patch("/brands/{brand_key}/active", response_model=DynamicBrand)` handler `set_brand_active(brand_key: str, payload: BrandActiveUpdate)`. Thin route: delegates entirely to `brand_service.set_active(brand_key, payload.is_active)`. Returns `None` → HTTP 404 (T-25-03-KEY mitigation: unknown/arbitrary keys cannot corrupt state). `GET /brands/` route unchanged — still calls `list_brands()` with no args (SC-4, Pitfall 6 guard).

### Task 2: active_only=True at consumer call sites (D-08)

Five call sites switched from `brand_service.list_brands()` to `brand_service.list_brands(active_only=True)`:

| File | Function | Purpose |
|------|----------|---------|
| `api/routes_search.py` L144 | `search_products` | Validation list for brands filter |
| `api/routes_search.py` L209 | `search_products_get` | Response brands_searched list |
| `api/routes_search.py` L228 | `export_search_products` | Validation list for export |
| `services/engines/factory.py` L70 | `search_all_brands` | Default target_brands when none specified |
| `api/routes_category.py` L176 | `scrape_category_multi` | Brand validator for multi-scan |

Virtual marketplace appends (`.extend(["mercado_livre", "netshoes", "amazon"])`) left untouched at every search site — they are always active and appended after the list call.

**Intentionally unchanged (per D-08):**
- `api/routes_brands.py` L100 `GET /brands/` — `list_brands()` with no args (SC-4: inactive brands must stay visible/reactivatable)
- `services/category_mapping.py` L161 — `list_brands()` with no args (gate is at search time; revisit Phase 29)

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add PATCH /brands/{brand_key}/active + BrandActiveUpdate model (D-06) | f93c4b4 | core/models.py, api/routes_brands.py |
| 2 | Adopt active_only=True at search/scheduler/category-scan call sites (D-08) | e0b5862 | api/routes_search.py, services/engines/factory.py, api/routes_category.py |

## Test Results

- `python -m pytest tests/test_brand_active.py -x -q` — **7 passed** (Task 1 gate)
- `python -m pytest tests/ -q` — **156 passed, 1 pre-existing failure** (test_ocr_service cv2/Python3.14 env issue, confirmed pre-existing before this plan's changes)

## Threat Mitigations Applied

| Threat ID | Mitigation | Status |
|-----------|-----------|--------|
| T-25-03-BODY | `BrandActiveUpdate.is_active: bool` → FastAPI 422 for non-bool input | Applied in Task 1 |
| T-25-03-KEY | `set_active` returns None → route raises 404; no corruption from arbitrary keys | Applied in Task 1 |
| T-25-03-VAL | `active_only=True` at all search validation lists (Pitfall 4) — inactive brands not valid filter targets | Applied in Task 2 |

## Deviations from Plan

None — plan executed exactly as written.

**Open Question 2 Decision (RESEARCH):** `routes_category.py` L176 `scrape_category_multi` DOES enforce `active_only=True` — inactive brands should not be valid scan targets (consistency with search). This was a deliberate YES decision matching the plan's stated resolution.

**Pre-existing failure:** `test_ocr_service.py::test_compare_image_texts` fails in full suite run due to `cv2.dnn.DictValue` missing (Python 3.14 incompatibility with easyocr/cv2). Confirmed pre-existing via git stash verification — same failure count (1 failed, 156 passed) before and after our changes. Out of scope per deviation rules.

## Known Stubs

None — all five call sites are fully wired; PATCH route delegates to the real service.

## Threat Flags

None — no new network endpoints beyond the planned PATCH route, no new auth paths, no new file access patterns, no schema changes at trust boundaries beyond what the plan's threat model covers.

## Self-Check: PASSED

- `core/models.py` contains `BrandActiveUpdate` — FOUND
- `api/routes_brands.py` contains `@router.patch("/brands/{brand_key}/active"` — FOUND
- `api/routes_search.py` contains `list_brands(active_only=True)` × 3 — FOUND
- `services/engines/factory.py` contains `list_brands(active_only=True)` — FOUND
- `api/routes_category.py` contains `list_brands(active_only=True)` — FOUND
- `api/routes_brands.py` GET /brands/ still calls `list_brands()` no args — FOUND
- Commit f93c4b4 (Task 1) — FOUND
- Commit e0b5862 (Task 2) — FOUND
- All 7 tests in test_brand_active.py GREEN — VERIFIED
