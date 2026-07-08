---
phase: 44-ruptura-de-estoque-avalia-es-refor-adas
plan: 03
subsystem: backend-stock-depth
tags: [python, fastapi, pytest, playwright, stock-depth, json-persistence, vtex]

requires:
  - phase: 44-ruptura-de-estoque-avalia-es-refor-adas
    provides: Plan 44-01/44-02 scan product IDs, monitor product artifacts, and rupture summary foundations
provides:
  - Explicit stock-depth provider contract with five non-false states
  - VTEX-only stock-depth provider with ephemeral Playwright lifecycle and cleanup tests
  - Unsupported provider for non-VTEX engines
  - Persisted monitor scan-product stock-depth orchestration with domain validation, throttle, and per-run cap
  - POST /monitor/category/{monitor_id}/products/{scan_product_id}/stock-depth
affects: [44-05, monitor-products, stock-depth, category-monitor]

tech-stack:
  added: []
  patterns:
    - Provider resolver returns VTEX implementation only; every other engine is explicit unsupported
    - Stock-depth service trusts persisted monitor/product identity, never caller-supplied URL/domain/quantity
    - Non-estimated provider states persist without numeric estimates

key-files:
  created:
    - backend/services/stock_depth/__init__.py
    - backend/services/stock_depth/base.py
    - backend/services/stock_depth/unsupported.py
    - backend/services/stock_depth/resolver.py
    - backend/services/stock_depth/vtex.py
    - backend/services/stock_depth_service.py
    - backend/tests/test_stock_depth_service.py
  modified:
    - backend/api/routes_monitor.py
    - backend/tests/test_phase44_routes.py

key-decisions:
  - "44-03/provider-scope: stock-depth resolver returns a real provider only for engine='vtex'; wake/shopify/sfcc/marketplace/unknown engines return explicit unsupported."
  - "44-03/identity-boundary: stock-depth API accepts only monitor_id and scan_product_id; product URL, brand domain, quantity, and provider are resolved from persisted artifacts/settings."
  - "44-03/non-false-states: blocked, temporary_failure, and unsupported persist stock_depth_estimate=None; unavailable may persist zero only when provider evidence is reliable."

patterns-established:
  - "StockDepthState has exactly estimated, unavailable, unsupported, blocked, and temporary_failure."
  - "Provider cleanup is tested with fake Playwright success and exception paths."
  - "Stock-depth route is isolated under monitor products and normal search paths do not import or call stock-depth."

requirements-completed: [STOCK-02]

duration: 9 min
completed: 2026-06-30
---

# Phase 44 Plan 03: Explicit Monitor Product Stock-Depth Cart-Probe Action Summary

**Controlled stock-depth probes for one persisted monitor scan product with VTEX provider isolation and explicit non-false states**

## Performance

- **Duration:** 9 min
- **Started:** 2026-06-30T18:27:30Z
- **Completed:** 2026-06-30T18:36:44Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments

- Added `services.stock_depth` provider package with `StockDepthState`, `BaseStockDepthProvider`, domain guard helper, VTEX provider, unsupported provider, and resolver.
- Added `probe_scan_product_stock_depth(monitor_id, scan_product_id)` to load persisted monitor artifacts, validate brand/domain identity, enforce throttle/cap, call the provider, and rewrite only the matching scan product.
- Added `POST /monitor/category/{monitor_id}/products/{scan_product_id}/stock-depth` as the explicit authenticated monitor-product action.
- Added hermetic tests for resolver/provider states, Playwright cleanup, service persistence semantics, throttle/cap, route behavior, and search-path isolation.

## Task Commits

1. **Task 1: Create stock-depth provider contract, resolver, and VTEX provider**
   - `73c8958` test(44-03): add failing tests for stock-depth providers
   - `1014761` feat(44-03): add stock-depth provider contract
2. **Task 2: Implement scan-product stock-depth orchestration and persistence**
   - `183e782` test(44-03): add failing tests for stock-depth orchestration
   - `166f28d` feat(44-03): persist stock-depth scan product results
3. **Task 3: Expose stock-depth as an authenticated monitor product action**
   - `0a1af86` test(44-03): add failing tests for stock-depth route
   - `9d3f99e` feat(44-03): expose stock-depth monitor product action

## Files Created/Modified

- `backend/services/stock_depth/base.py` - Stock-depth state contract, provider ABC, and brand URL domain guard.
- `backend/services/stock_depth/unsupported.py` - Explicit unsupported provider for non-proved engines.
- `backend/services/stock_depth/resolver.py` - Engine-to-provider resolver; VTEX only for real provider.
- `backend/services/stock_depth/vtex.py` - VTEX provider with ephemeral Playwright browser/context/page lifecycle and conservative state mapping.
- `backend/services/stock_depth_service.py` - Monitor scan-product orchestration, throttle/cap guard, provider invocation, and product artifact persistence.
- `backend/api/routes_monitor.py` - Explicit stock-depth POST route for one persisted monitor product.
- `backend/tests/test_stock_depth_service.py` - Provider and service tests.
- `backend/tests/test_phase44_routes.py` - Route wiring and search isolation tests.

## Decisions Made

- Kept stock-depth support VTEX-only for this plan; all other engines return `unsupported` until a provider is proved.
- Kept endpoint input constrained to path params only; caller cannot provide URL/domain/quantity/provider.
- Persisted the operator-facing label as `maximo observado/estimativa via cart-probe` and kept non-estimated states from becoming false quantities.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Backstage coding standards MCP was not available in this Codex session. Implementation followed the local `CLAUDE.md`, Phase 44 pattern map, and existing shipping/provider conventions.
- Two acceptance-check shell snippets initially used Bash/nested PowerShell quoting and were rerun correctly in PowerShell; implementation and tests were unaffected.

## Known Stubs

None in production code. Empty dict/list values in tests are intentional fixtures and guards.

## Threat Flags

None. The new API/browser-probe surfaces are the planned STOCK-02 surfaces and mitigate the plan threat model through persisted identity validation, no caller-supplied URL/domain/quantity, throttle/cap, timeout, and cleanup tests.

## Verification

- `python -m pytest backend/tests/test_stock_depth_service.py -q` -> 14 passed.
- `python -m pytest backend/tests/test_phase44_routes.py -q` -> 12 passed after route implementation.
- `python -m pytest backend/tests/test_stock_depth_service.py backend/tests/test_phase44_routes.py -q` -> 26 passed.
- `rg -n 'stock_depth_service|probe_scan_product_stock_depth|cart-probe|cart_probe' backend/api/routes_search.py backend/services/vtex_api_scraper.py` guarded by PowerShell exit check -> no matches.
- Acceptance checks: `probe_scan_product_stock_depth` signature is `(monitor_id, scan_product_id)`; route handler signature is `(monitor_id, scan_product_id)`; no real sleeps in service tests; resolver returns VTEX provider only for `engine='vtex'`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for Plan 44-04 and Plan 44-05. The backend now has a persisted, explicit STOCK-02 action that the future monitor modal can call without touching normal search paths.

## Self-Check: PASSED

- Found created/modified files: `backend/services/stock_depth/base.py`, `backend/services/stock_depth/unsupported.py`, `backend/services/stock_depth/resolver.py`, `backend/services/stock_depth/vtex.py`, `backend/services/stock_depth_service.py`, `backend/api/routes_monitor.py`, `backend/tests/test_stock_depth_service.py`, `backend/tests/test_phase44_routes.py`, and this SUMMARY.
- Found commits: `73c8958`, `1014761`, `183e782`, `166f28d`, `0a1af86`, `9d3f99e`.
- Re-ran plan verification: `python -m pytest backend/tests/test_stock_depth_service.py backend/tests/test_phase44_routes.py -q` -> 26 passed.
- Re-ran search-path guard: stock-depth/cart-probe grep in `routes_search.py` and `vtex_api_scraper.py` -> no matches.

---
*Phase: 44-ruptura-de-estoque-avalia-es-refor-adas*
*Completed: 2026-06-30*
