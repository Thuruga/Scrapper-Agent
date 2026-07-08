---
phase: 40-onboarding-por-url-workflows-de-adi-o-ao-monitoramento
plan: "04"
subsystem: marketplace-toggle
tags: [marketplace, brand-service, cross-marketplace, factory, toggle, ux-05]
dependency_graph:
  requires: ["40-02"]
  provides: ["brands.json marketplace entries", "per-request engine enforcement"]
  affects: ["cross_marketplace_service", "factory.search_all_brands", "brand toggle UI"]
tech_stack:
  added: []
  patterns: ["module-level _ENGINE_MAP singleton", "per-request active filter via brand_service", "_by_display display-name lookup"]
key_files:
  created: []
  modified:
    - backend/data/brands.json
    - backend/services/cross_marketplace_service.py
    - backend/services/engines/factory.py
    - backend/tests/test_brand_active.py
    - backend/tests/test_cross_marketplace_service.py
decisions:
  - "[40-04/marketplace-brand-keys]: Preserved brand_keys mercado_livre/netshoes/amazon from Plan 02 runtime injection — engine values are mercadolivre/netshoes/amazon (no underscore) matching existing engine class naming"
  - "[40-04/_inject_engines-helper]: Tests use _inject_engines(service, engines_dict) helper instead of direct service.engines assignment; helper sets _by_display and monkey-patches _active_engines() — hermetic, does not touch brands.json"
  - "[40-04/brand_service-import]: brand_service imported at module level in cross_marketplace_service (not lazy) — safe because brand_service singleton is initialized at import time with no async calls"
metrics:
  duration: "~25 min"
  completed: "2026-06-30T14:27:37Z"
  tasks: 2
  files: 5
---

# Phase 40 Plan 04: Marketplace Toggles — brands.json Promotion + Per-Request Engine Enforcement

Marketplace toggles (UX-05) delivered: `mercado_livre`, `netshoes`, `amazon` promoted to real `brands.json` entries with `is_active` (D-10); `CrossMarketplaceService` rebuilt to select engines per-request from `brand_service.list_brands(active_only=True)` (D-11); hardcoded `extend` bypass removed from `factory.search_all_brands` (T-40-06).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Promote marketplaces to brands.json + guard test | 55cfa0c | brands.json, test_brand_active.py |
| 2 | Per-request engine enforcement + factory bypass removed | fe6ba93 | cross_marketplace_service.py, factory.py, test_cross_marketplace_service.py |

## What Was Built

### Task 1 — brands.json marketplace entries (D-10)

Added three real `DynamicBrand` entries to `backend/data/brands.json`:

- `mercado_livre` — engine `mercadolivre`, domain `mercadolivre.com.br`, `is_active: true`
- `netshoes` — engine `netshoes`, domain `netshoes.com.br`, `is_active: true`
- `amazon` — engine `amazon`, domain `amazon.com.br`, `is_active: true`

Each entry carries the full `DynamicBrand` field set (all optional fields null/empty). All three validate correctly against the Pydantic model.

Extended `test_brand_active.py` with `TestMarketplacesInBrandsJson` (3 tests):
- `test_marketplaces_in_brands_json` — asserts 3 keys exist with correct engine and `is_active=True`
- `test_marketplaces_returned_by_active_only_filter` — confirms `list_brands(active_only=True)` includes them
- `test_no_runtime_injection_in_list_brands_route` — inspects `list_brands()` source for absence of `brands.append` (regression guard against Plan 02 removal)

Confirmed `routes_brands.py` has 0 `brands.append` references (Plan 02 clean).

### Task 2 — CrossMarketplaceService refactor + factory.search_all_brands fix (D-11 / T-40-06)

`cross_marketplace_service.py`:
- Added module-level `_ENGINE_MAP: Dict[str, tuple]` mapping `engine_key → (display_name, EngineClass)` for the 3 marketplace engines
- Replaced hardcoded `self.engines = {…}` in `__init__` with:
  - `self._engine_instances` — singleton engine objects (stateless, race-free — T-40-07)
  - `self._by_display` — `display_name → engine` map for `_enrich_pdp_and_shipping` lookup
- Added `_active_engines() -> Dict[str, Any]` — reads `brand_service.list_brands(active_only=True)` per call; returns only engines whose `brand_key` appears in the active set
- `_fetch_all_engines`: `self.engines.items()` → `self._active_engines().items()`
- `_enrich_pdp_and_shipping`: `self.engines[plat]` → `self._by_display[plat]`
- Verified: 0 remaining `self.engines` references in the file

`factory.py`:
- Removed `target_brands.extend(["mercado_livre","netshoes","amazon"])` (l.85 old)
- `list_brands(active_only=True)` now returns marketplaces from brands.json — single source of truth

`test_cross_marketplace_service.py`:
- Added `_inject_engines(service, engines_dict)` helper: sets `_by_display` and monkey-patches `_active_engines()` — allows existing characterization tests to remain hermetic without touching brands.json
- Adapted all `service.engines = {…}` assignments to `_inject_engines(service, {…})`
- Added `TestInactiveMarketplaceExcluded` with 2 tests:
  - `test_inactive_marketplace_excluded` — patches `brand_service.list_brands` to omit Amazon; asserts `_active_engines()` excludes `"Amazon"` and `compare_product` returns no Amazon results
  - `test_active_marketplace_included` — positive case: all 3 active → `_active_engines()` returns 3 engines

## Deviations from Plan

None — plan executed exactly as written.

## Test Results

```
tests/test_brand_active.py: 10 passed (7 pre-existing + 3 new)
tests/test_cross_marketplace_service.py: 9 passed (7 adapted + 2 new)
Full suite: 347 passed, 0 failures, 1 pre-existing warning (unrelated coroutine)
```

## Acceptance Criteria Verification

| Criterion | Status |
|-----------|--------|
| `brands.json` contains `mercado_livre`, `netshoes`, `amazon` with `is_active: true` | PASS |
| Engine values: `mercadolivre` / `netshoes` / `amazon` (D-10 preserved brand_keys) | PASS |
| `self.engines` removed from `cross_marketplace_service.py` (grep count == 0) | PASS |
| `_active_engines` present (count >= 2) | PASS (count = 2) |
| `_by_display` present (count >= 2) | PASS (count = 3) |
| `factory.search_all_brands` hardcoded extend removed | PASS |
| `test_inactive_marketplace_excluded` passes | PASS |
| `routes_brands.list_brands` has 0 `brands.append` | PASS |
| Full suite green | PASS (347 passed) |

## Known Stubs

None — all functionality is fully wired. The marketplace entries in `brands.json` are real data; `_active_engines()` reads live data from `brand_service` per request.

## Threat Flags

None — no new network endpoints, auth paths, or file access patterns introduced beyond what the plan's threat model covers (T-40-05, T-40-06, T-40-07 addressed).

## Self-Check: PASSED

- `backend/data/brands.json` — exists, valid JSON, contains `mercado_livre`/`netshoes`/`amazon`
- `backend/services/cross_marketplace_service.py` — contains `_active_engines`, `_by_display`, `_ENGINE_MAP`
- `backend/services/engines/factory.py` — no `extend` line with marketplace list
- `backend/tests/test_brand_active.py` — `TestMarketplacesInBrandsJson` present
- `backend/tests/test_cross_marketplace_service.py` — `TestInactiveMarketplaceExcluded` present
- Commits `55cfa0c` and `fe6ba93` verified in git log
