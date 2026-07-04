---
phase: 43-violacao-de-map-selos-de-promocao
plan: 02
subsystem: api
tags: [fastapi, map-rules, crud, pytest]
requirements-completed: [MAP-01]
completed: 2026-07-04
---

# Phase 43 Plan 02 Summary

Protected MAP rules CRUD endpoints were added.

## Accomplishments

- Added `backend/api/routes_map_rules.py` with list/create/update/delete endpoints under `/map-rules`.
- Registered the router in the protected API aggregator.
- Added route tests with a temporary `map_rules.json` store for empty list, valid create, invalid scope, update/404, and delete/404.

## Verification

- `cd backend && python -m pytest tests/test_map_rules_routes.py -x -q` -> 4 passed

## Deviations

None.
