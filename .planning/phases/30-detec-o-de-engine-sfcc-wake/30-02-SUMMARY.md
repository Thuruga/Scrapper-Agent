---
phase: 30-detec-o-de-engine-sfcc-wake
plan: "02"
subsystem: engine-factory
tags: [sfcc, wake, engine-factory, guard, not-implemented]
dependency_graph:
  requires: []
  provides: [engine_factory_sfcc_wake_guard]
  affects: [backend/services/engines/factory.py]
tech_stack:
  added: []
  patterns: [explicit-guard-before-fallback, raise-not-implemented-error]
key_files:
  modified:
    - backend/services/engines/factory.py
decisions:
  - "D-09: explicit sfcc/wake guard raises NotImplementedError before the VTEXEngine fallback, removing the silent wrong-engine path for active-but-engineless brands"
  - "D-10: a single guard covers both 'sfcc' and 'wake'; NotImplementedError is an Exception subclass already caught by _search_one's except Exception, so one brand's failure becomes BrandSearchResult.error without downing the asyncio.gather"
metrics:
  duration: "5m"
  completed_date: "2026-06-23"
  tasks_completed: 1
  files_modified: 1
---

# Phase 30 Plan 02: EngineFactory sfcc/wake Guard Summary

**One-liner:** `EngineFactory.get_engine` now fails loudly with `NotImplementedError` for `engine_type in ("sfcc", "wake")` instead of silently falling through to `VTEXEngine`, so active-but-engineless SFCC/Wake brands surface a diagnosable error per search instead of mis-running VTEX.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Guard sfcc/wake in EngineFactory.get_engine | cdb3788 | backend/services/engines/factory.py |

## What Was Built

Inserted a guard in `get_engine` immediately after the `if engine_type == "shopify": return ShopifyEngine(brand_key)` branch and **before** the final `return VTEXEngine(brand_key)`:

```python
if engine_type in ("sfcc", "wake"):
    raise NotImplementedError(
        f"Engine '{engine_type}' para '{brand_key}' ainda não disponível (Phase 31/32 pendente)."
    )
```

A multi-line inline comment cites D-09 (why the guard exists — closes the active-without-engine window opened by Phase 30) and D-10 (single guard for both engines; `NotImplementedError` is caught downstream). The virtual-marketplace branches, the `engine_type` resolution, the `shopify` branch, and the `VTEXEngine` fallback are byte-for-byte unchanged — `vtex` and any unrecognized legacy string still resolve to `VTEXEngine`. `_search_one` / `search_all_brands` were not touched.

## Verification

- `grep -nE 'sfcc|wake' backend/services/engines/factory.py` → guard at line 51 ✓
- `grep -nF 'NotImplementedError' backend/services/engines/factory.py` → line 52 ✓
- `python -c "import ast; ast.parse(open('backend/services/engines/factory.py').read())"` → Syntax OK ✓
- Existing engine paths (vtex/shopify/mercado_livre/netshoes/amazon) preserved — confirmed by diff (1 file changed, 12 insertions, 1 deletion: only the blank-line + guard block added) ✓
- `_search_one`'s `except Exception` (L86-88) unchanged → `NotImplementedError` is captured as `BrandSearchResult.error` and `asyncio.gather` keeps running (D-10 / T-30-05) ✓

## Deviations from Plan

None — plan executed exactly as written. Behavioral proof (active brand stays active AND search surfaces a diagnosable error) is exercised by plan 30-03 (SC-3), per the plan's verification note.

## Threat Surface Scan

No new network endpoints, auth paths, or dependencies introduced. Threat IDs from the plan's model are covered:
- T-30-05 (DoS): `NotImplementedError` is caught by `_search_one`; one sfcc/wake brand yields a single `BrandSearchResult.error` and the gather completes for all other brands ✓
- T-30-06 (Tampering/Elevation): the explicit guard removes the silent VTEX-fallback masking for sfcc/wake, replacing a silent wrong-engine run with a surfaced error ✓
- T-30-07 (Info Disclosure): the message contains only the engine type and operator-supplied `brand_key` (no secrets/PII); accepted ✓

## Known Stubs

The downstream SFCC engine (Phase 31) and Wake engine (Phase 32) are intentionally deferred. Until they ship, the guard is the intended terminal behavior for sfcc/wake brands in search.

## Self-Check: PASSED

- `backend/services/engines/factory.py` exists and contains the guard ✓
- Commit `cdb3788` exists (Task 1 — sfcc/wake guard) ✓
- AST parse clean; existing engine resolutions preserved ✓
