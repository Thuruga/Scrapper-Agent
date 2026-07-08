---
phase: 38-ux-de-busca-monitoramento-quick-wins
plan: 01
subsystem: api
tags: [pydantic, fastapi, websocket, price-monitor, tdd]

# Dependency graph
requires:
  - phase: 25-gest-o-de-marcas
    provides: "list_brands(active_only=True) chokepoint enforcement (D-07/25-02)"
provides:
  - "PriceMonitorConfig.last_price_discount and PriceHistoryEntry.last_price_discount fields (Optional[float], default None)"
  - "Discount-aware change detection in _monitor_loop: promo-only price changes now register in history and WS payload"
  - "price_update WS payload includes price_discount and price_full keys (D-03)"
  - "COMP-08 regression guard: TestLacosteExcludedFromActiveOnly locks the active_only chokepoint"
  - "UX-08 backend contract test proving run_category_scan writes last_scraped_at"
affects: ["38-02", "38-03"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Discount delta convention: price_discount/last_price_discount hold a positive discount AMOUNT, not a final discounted price (mirrors RawProductBronze.price_discount and App.tsx price_full + price_discount render)"

key-files:
  created:
    - backend/tests/test_category_monitor.py
  modified:
    - backend/core/models.py
    - backend/services/price_monitor_service.py
    - backend/tests/test_price_monitor.py
    - backend/tests/test_brand_active.py

key-decisions:
  - "last_price_discount is a single delta field added to both PriceMonitorConfig and PriceHistoryEntry; last_price keeps meaning effective/current price for frontend back-compat (D-04)"
  - "Default None (not 0.0) preserves backward compatibility with existing price_monitors.json records lacking the field (D-02)"
  - "has_change now also fires on config.last_price_discount != current_discount, so a promo-only change (price_full unchanged, discount added) is no longer silently dropped (D-01)"

patterns-established:
  - "Test jitter-sleep race fix: when config.last_price is not None, _monitor_loop performs an initial jitter asyncio.sleep BEFORE the while loop; hermetic tests must count sleep() calls and only flip config.active=False on the 2nd call (end-of-cycle sleep), not the 1st (jitter)."

requirements-completed: [UX-02, UX-08, COMP-08]

# Metrics
duration: 25min
completed: 2026-07-01
---

# Phase 38 Plan 01: Backend Discount-Aware Monitoring + Wave-0 Regression Tests Summary

**Promo-only price changes (price_full unchanged, discount added) now register in price monitor history and the `price_update` WebSocket payload via a new `last_price_discount` delta field on both monitor models.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-07-01T16:11:00Z
- **Completed:** 2026-07-01T16:36:38Z
- **Tasks:** 3 completed
- **Files modified:** 5 (1 created, 4 modified)

## Accomplishments
- UX-02 backend: `PriceMonitorConfig`/`PriceHistoryEntry` gained `last_price_discount: Optional[float] = None`; `_monitor_loop` change-detection now treats a discount-only delta as a trigger, appending history and notifying via WS with `price_discount`/`price_full` keys
- UX-08 backend proof: new `test_category_monitor.py` confirms `run_category_scan` writes `last_scraped_at` on the monitor row (the frontend's poll signal) — no production code change needed, trigger already existed
- COMP-08: `TestLacosteExcludedFromActiveOnly` locks the `list_brands(active_only=True)` chokepoint so Lacoste (inactive due to anti-bot) can never leak into an active-brands selector
- Full backend suite (473 tests) green, no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 — create the three failing baseline tests (COMP-08, UX-02, UX-08 backend)** - `553be88` (test)
2. **Task 2: Add last_price_discount field to PriceMonitorConfig and PriceHistoryEntry (D-04)** - `78ec352` (feat)
3. **Task 3: Discount-aware change detection + WS payload in _monitor_loop (D-01, D-03)** - `e3bbac2` (feat)

**Plan metadata:** (pending — recorded below)

_Note: This is a `type: tdd` plan. Task 1 established RED for the price-monitor test (Task 2/3 made it GREEN); COMP-08 and UX-08 tests were regression guards that passed immediately by design (no production code required)._

## Files Created/Modified
- `backend/tests/test_category_monitor.py` - New hermetic test proving `run_category_scan` writes `last_scraped_at` (UX-08 backend contract)
- `backend/tests/test_brand_active.py` - Added `TestLacosteExcludedFromActiveOnly` regression guard (COMP-08)
- `backend/tests/test_price_monitor.py` - Added `test_price_monitor_promo_only_change_triggers_history` (D-01/D-03 RED→GREEN)
- `backend/core/models.py` - Added `last_price_discount: Optional[float] = None` to `PriceHistoryEntry` and `PriceMonitorConfig`
- `backend/services/price_monitor_service.py` - Discount-aware `has_change` detection; `price_discount`/`price_full` added to WS payload; `current_discount` computed from `product.price_discount` delta convention

## Decisions Made
- `last_price_discount` is a single delta field (not a redundant `last_price_full`) added to both models, per RESEARCH.md D-04 recommendation — `last_price` continues to mean the effective/current price so the existing frontend stays compatible.
- Default `None` (not `0.0`) so existing `price_monitors.json` records without the key still validate (D-02, confirmed by loading all 4 real persisted records through `PriceMonitorConfig.model_validate`).
- `current_discount = product.price_discount if product.price_discount and product.price_discount > 0 else None` — normalizes falsy/zero discounts to `None`, matching the delta convention (not a final discounted price).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test jitter-sleep race caused the loop body to never execute**
- **Found during:** Task 3 (making the Task-1 RED test GREEN)
- **Issue:** The Task 1 test set `config.last_price=100.0` and used a single-call `asyncio.sleep` side effect (`config.active = False`) to stop the loop after "one iteration," mirroring the plan's instructions. But `_monitor_loop` performs an initial jitter `asyncio.sleep` call BEFORE the `while config.active:` loop whenever `config.last_price is not None`. That first sleep call consumed the stop signal, so the loop body (and all change-detection logic) never ran — the test failed with `history == 0` even after Task 2/3 model and service changes were correctly implemented.
- **Fix:** Changed the test's `asyncio.sleep` mock to a call counter that only sets `config.active = False` on the 2nd invocation (the first is jitter, pre-loop; the second is the end-of-cycle sleep, inside the loop, after one full iteration executed).
- **Files modified:** `backend/tests/test_price_monitor.py`
- **Verification:** `pytest tests/test_price_monitor.py -q` — all 7 tests pass, including the new promo-only test.
- **Committed in:** `e3bbac2` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix in test harness)
**Impact on plan:** Necessary for correctness — the plan's literal single-sleep-call stop trick does not account for the pre-loop jitter path taken whenever `last_price` is not `None`. No scope creep; fix is scoped entirely to the new test's mock setup.

## Issues Encountered
None beyond the deviation documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- UX-02 backend contract (discount field + change detection + WS payload) is ready for Plan 03's frontend render work (`App.tsx` already expects `price_full + price_discount`, per existing pattern referenced in the plan).
- UX-08 backend polling signal (`last_scraped_at`) is proven and ready for Plan 03's frontend poll implementation.
- COMP-08 is fully closed (test-only, no production code) — no further backend work needed.
- No blockers for Plan 02/03.

---
*Phase: 38-ux-de-busca-monitoramento-quick-wins*
*Completed: 2026-07-01*

## Self-Check: PASSED

All created/modified files confirmed present on disk; all three task commit hashes (553be88, 78ec352, e3bbac2) confirmed present in git log.
