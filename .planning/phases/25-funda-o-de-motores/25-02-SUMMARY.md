---
phase: 25-funda-o-de-motores
plan: "02"
subsystem: brand-service
tags: [mgmt, brand-activation, service-layer, chokepoint]
dependency_graph:
  requires: ["25-00"]
  provides: ["list_brands(active_only)", "set_active"]
  affects: ["services/brand_service.py"]
tech_stack:
  added: []
  patterns: ["single-chokepoint filter", "idempotent flag setter", "dual-backend persistence"]
key_files:
  modified:
    - services/brand_service.py
decisions:
  - "D-07: active_only default stays False — preserves all existing call-site behavior (Pitfall 6)"
  - "D-05: set_active only sets is_active flag and persists; no monitor cancellation"
  - "D-06: set_active is idempotent set, not toggle — calling twice with same value is a no-op semantically"
metrics:
  duration: "8m"
  completed: "2026-06-18"
  tasks: 2
  files: 1
---

# Phase 25 Plan 02: Brand Service Active-Only Chokepoint Summary

**One-liner:** Service-layer chokepoint `list_brands(active_only=False)` + idempotent `set_active` flag setter with dual-backend persistence via existing `_save`.

## What Was Built

Two methods added/evolved on `BrandManagerService` in `services/brand_service.py`:

1. **`list_brands(self, active_only: bool = False) -> List[DynamicBrand]`** — evolved from zero-arg signature. Default `False` preserves all existing call-site behavior. When `True`, filters out any brand with `is_active=False`. This is the single exclusion point for inactive brands across search, scheduler, monitoring and export — no per-call-site filtering needed.

2. **`set_active(self, brand_key: str, is_active: bool) -> Optional[DynamicBrand]`** — new method. Normalizes `brand_key` via `.lower()`, returns `None` for unknown keys (zero mutation, drives 404 at route), sets `is_active` on the in-memory record and persists via `self._save(brand)`. Works in both Supabase and JSON backends. Does NOT cancel active monitors (D-05).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add active_only filter to list_brands chokepoint (D-07) | 839a915 | services/brand_service.py |
| 2 | Add set_active idempotent flag setter with persistence (D-05/D-06) | 54f1b9a | services/brand_service.py |

## Test Results

All 7 tests in `tests/test_brand_active.py` GREEN after implementation:
- `TestListBrandsActiveOnly::test_default_returns_all_brands` — PASS
- `TestListBrandsActiveOnly::test_active_only_excludes_inactive` — PASS (was RED in Wave 0)
- `TestListBrandsActiveOnly::test_active_only_false_returns_all` — PASS (was RED in Wave 0)
- `TestSetActive::test_deactivate_brand` — PASS (was RED in Wave 0)
- `TestSetActive::test_reactivate_brand` — PASS (was RED in Wave 0)
- `TestSetActive::test_set_active_unknown_key_returns_none` — PASS (was RED in Wave 0)
- `TestBrandRouteReturnsInactive::test_route_includes_inactive_brand` — PASS

## Threat Mitigations Applied

| Threat ID | Mitigation | Status |
|-----------|-----------|--------|
| T-25-02-KEY | `.lower()` normalization + unknown key returns None (no mutation) | Applied in Task 2 |
| T-25-02-DEF | Default `active_only=False` preserved (Pitfall 6) | Applied in Task 1 |

## Deviations from Plan

None — plan executed exactly as written.

Pre-existing RED test `test_engine_detection.py::test_wake_commerce_returns_unknown` was failing before and after our changes (scope of Plan 25-01, not this plan). Confirmed pre-existing via `git stash` check.

## Known Stubs

None — both methods are fully implemented and wired.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced.

## Self-Check: PASSED

- `services/brand_service.py` modified with both methods — FOUND
- Commit 839a915 (Task 1) — FOUND
- Commit 54f1b9a (Task 2) — FOUND
- All 7 tests in test_brand_active.py GREEN — VERIFIED
