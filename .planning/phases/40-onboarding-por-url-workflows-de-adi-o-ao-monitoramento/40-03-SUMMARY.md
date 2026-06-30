---
phase: 40-onboarding-por-url-workflows-de-adi-o-ao-monitoramento
plan: "03"
subsystem: backend-service
tags: [dedup, idempotent-monitor, price-monitor, url-normalization, tdd]
dependency_graph:
  requires: ["40-01"]
  provides: ["dedup-aware start_monitor", "status-returning POST /monitor/start"]
  affects:
    - backend/services/price_monitor_service.py
    - backend/api/routes_product.py
    - backend/tests/test_price_monitor.py
tech_stack:
  added: []
  patterns:
    - lazy import of normalize_url inside start_monitor to avoid circular risk
    - tuple return (config, status) from service method
    - dedup scan before creation: iterate monitors.items(), normalize+compare
key_files:
  created: []
  modified:
    - backend/services/price_monitor_service.py
    - backend/api/routes_product.py
    - backend/tests/test_price_monitor.py
decisions:
  - "[40-03/dedup-return]: start_monitor now returns (PriceMonitorConfig, status_str) on all paths; status in {created, already_active, reactivated}; caller unpacks tuple"
  - "[40-03/job_id-surface]: POST /monitor/start returns config.job_id (existing for already_active/reactivated, new uuid for created) so frontend always sees the canonical id"
  - "[40-03/lazy-import]: normalize_url imported inside start_monitor body to avoid any import-cycle risk; matches PATTERNS.md recommendation"
metrics:
  duration: "~17 minutes"
  completed_date: "2026-06-30"
  tasks_completed: 2
  files_modified: 3
  commits: 3
---

# Phase 40 Plan 03: Dedup-Aware start_monitor & Idempotent POST /monitor/start Summary

**One-liner:** Dedup scan in `start_monitor` using `normalize_url + brand.lower()` returns `(config, status)` in `{created, already_active, reactivated}`, making "Adicionar ao monitoramento" idempotent (D-08/D-09/UX-04).

## What Was Built

### Task 1: Dedup scan in `start_monitor` (TDD RED + GREEN)

`PriceMonitorService.start_monitor` now inserts a dedup scan before creating a new `PriceMonitorConfig`:

1. Imports `normalize_url` from `services.url_utils` (Plan 01) lazily inside the method.
2. Computes `norm_url = normalize_url(url)`.
3. Iterates `self.monitors.items()`: if `normalize_url(config.url) == norm_url and config.brand.lower() == brand.lower()`:
   - `config.active` is True → returns `(existing_config, "already_active")` — no new entry, no new task.
   - `config.active` is False → calls `resume_monitor(existing_id)`, returns `(reactivated_config, "reactivated")`.
4. No match → creates `PriceMonitorConfig` (existing logic unchanged), returns `(config, "created")`.
5. `_monitor_loop` is untouched — still only checks `while config.active` (D-06).

### Task 2: Route unpacks tuple + dedup tests

`POST /monitor/start` in `routes_product.py`:
- Changed `config = await monitor_service.start_monitor(...)` to `config, status = await monitor_service.start_monitor(...)`.
- Returns `{"job_id": config.job_id, "status": status, "config": config.model_dump()}`.
- `config.job_id` is the canonical id: for `created` it is the freshly minted uuid (same as before); for `already_active`/`reactivated` it is the existing monitor's id.

Extended `tests/test_price_monitor.py` with two async tests:
- `test_dedup_active`: pre-seeds an active monitor with a URL carrying `utm_source` and `www.`; calls `start_monitor` with the normalized equivalent; asserts `status == "already_active"`, `len(service.monitors) == 1`, no new entry.
- `test_dedup_reactivate`: pre-seeds a stopped monitor; calls `start_monitor` with matching url+brand; asserts `status == "reactivated"`, existing entry's `active` flips to `True`, `len(service.monitors) == 1`.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 9731ee5 | test | add failing dedup tests for start_monitor (RED) |
| 4e88469 | feat | add dedup scan to start_monitor returning (config, status) (GREEN) |
| 059a590 | feat | unpack (config, status) tuple in POST /monitor/start |

## Verification

- `cd backend && python -m pytest tests/test_price_monitor.py -x` — 4 passed (includes `test_dedup_active`, `test_dedup_reactivate`)
- `cd backend && python -m pytest tests/ -x` — 371 passed, 1 warning (pre-existing RuntimeWarning on unrelated test)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — dedup logic is fully wired; no placeholders.

## Threat Flags

No new network endpoints, auth paths, or schema changes introduced beyond what the threat model covers. T-40-03 (DoS via repeated monitor creation) is now mitigated: `test_dedup_active` confirms that a second "add" for an active (normalized url + brand) is a no-op and does not grow `service.monitors`.

## TDD Gate Compliance

- RED gate: commit `9731ee5` — `test(40-03)` with two failing tests before implementation.
- GREEN gate: commit `4e88469` — `feat(40-03)` with minimal implementation making tests pass.
- REFACTOR gate: not required (code is already clean; no dead branches or duplication).

## Self-Check: PASSED

- `backend/services/price_monitor_service.py` — modified, contains `return config, "already_active"`, `return config, "created"`, `resume_monitor` path for reactivated.
- `backend/api/routes_product.py` — modified, contains `config, status = await monitor_service.start_monitor`.
- `backend/tests/test_price_monitor.py` — modified, contains `test_dedup_active` and `test_dedup_reactivate`.
- Commits `9731ee5`, `4e88469`, `059a590` exist in `git log`.
