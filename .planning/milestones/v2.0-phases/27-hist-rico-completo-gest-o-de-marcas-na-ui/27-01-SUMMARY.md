---
phase: 27-hist-rico-completo-gest-o-de-marcas-na-ui
plan: "01"
subsystem: backend
tags: [history, persistence, search, fastapi]
dependency_graph:
  requires: ["27-00"]
  provides: ["HIST-01-backend"]
  affects: ["api/routes_search.py", "services/search_history_service.py"]
tech_stack:
  added: []
  patterns: ["job persistence (create_job/update_job)", "inner-list shape contract (Resolution A)"]
key_files:
  created: []
  modified:
    - api/routes_search.py
decisions:
  - "Module-level import of search_history_service (not lazy inside function) — required for test monkeypatching pattern used in test_search_history_comparative.py"
  - "Removed redundant lazy import from cross_marketplace_search after hoisting to module top"
metrics:
  duration: "5m"
  completed: "2026-06-20"
  tasks: 1
  files: 1
---

# Phase 27 Plan 01: Persist Comparative Search History (HIST-01 Backend) Summary

**One-liner:** POST /search now persists type='search' history with inner-list results and raw query using create_job/update_job, mirroring the cross-marketplace pattern with two mandatory deviations (Resolution A).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Persist comparative search in POST /search | 0422be3 | api/routes_search.py |

## What Was Built

Modified `search_products` in `api/routes_search.py` to persist search history on every `POST /search` call:

1. Added module-level import: `from services.search_history_service import search_history_service`
2. After `target_brands` computation, generates `job_id = str(uuid.uuid4())` and calls `search_history_service.create_job(job_id, query=request.query, brands=target_brands, type="search")`
3. Wrapped the engine call and result construction in `try/except Exception`
4. On success: calls `update_job(COMPLETED, results=result.model_dump(mode="json")["results"])` then returns
5. On exception: calls `update_job(FAILED, error=str(e))` then re-raises
6. Removed the now-redundant lazy `from services.search_history_service import search_history_service` line from `cross_marketplace_search` (hoisted to module top)

## Deviations from Plan

### Auto-fixed Issues

None from deviation rules. Two **planned deviations** from the analog (cross-marketplace block) were applied as specified:

**Deviation 1 (Pitfall 2):** `query=request.query` (raw term), NOT a composed display label. The reopen handler (App.tsx:656) dumps `res.query` back into the search box; a label would corrupt it.

**Deviation 2 (Pitfall 1 / Resolution A):** `result.model_dump(mode="json")["results"]` (inner `List[BrandSearchResult]`), NOT the whole `ComparisonResult` wrapper. `SearchPage` reopen sets `setResults({ results: res.results, ... })` expecting `res.results` to be the array directly.

**Implementation note — module-level vs lazy import:** The plan permitted either lazy (mirroring the analog) or module-level import. Module-level was chosen because the test's monkeypatching pattern (`routes_search.search_history_service = history_svc`) requires the name to exist as a module attribute. A lazy `from services... import search_history_service` inside the function would shadow the injected singleton and break the tests.

## Verification Results

```
python -m pytest tests/test_search_history_comparative.py -x -v
4 passed in 1.03s

python -m pytest tests/ --ignore=tests/test_ocr_service.py
166 passed in 1.68s
```

**OCR test note:** `test_ocr_service.py::test_compare_image_texts` fails when run as part of the full suite (cv2/easyocr `AttributeError: module 'cv2.dnn' has no attribute 'DictValue'`) but passes in isolation. This is a pre-existing test-isolation / Python 3.14 + opencv incompatibility — present in the baseline (before this plan's changes). Not introduced by this plan.

## Known Stubs

None. All persistence paths are wired end-to-end with real service calls.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes beyond what the plan's threat model covers. T-27-01-01 (Pydantic validation) and T-27-01-02 (disk size) dispositions honored — no new surface introduced.

## Self-Check: PASSED
