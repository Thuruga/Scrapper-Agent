---
phase: 42-frete-para-marketplaces-matriz-multi-regional
plan: 03
subsystem: ui
tags: [shipping, mercado-livre, react, frontend, cross-marketplace, delivery-time]

# Dependency graph
requires:
  - phase: 42-01
    provides: MercadoLivreShipping/AmazonShipping/NetshoesShipping adapters, ShippingState.BLOCKED, delivery-time extraction in engine layer
  - phase: 42-02
    provides: /search/calculate-shipping-matrix regional matrix endpoint + (product, cep) cache
provides:
  - Cross-marketplace enrichment (_enrich_pdp_and_shipping) surfaces estimated_delivery_days / shipping_raw_text / _shipping_state=blocked onto product dicts
  - App.tsx blocked-state rendering ("Bloqueado (anti-bot)") replacing "Calcular Frete" for blocked marketplace items
  - Always-visible "Matriz Regional" button + "Frete por região" 5-region modal at both insertion points (comparativa/SKU and cross-marketplace)
  - isBrandShippingSupported extended to mercadolivre/amazon/netshoes
  - MercadoLivreEngine._parse_delivery_time computes estimated_delivery_days from the live API's absolute ISO-8601 date field (live-verification fix)
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "delivery_raw_text is a defensive fallback only — never populated when estimated_delivery_days was successfully derived, so the frontend's raw_text-before-estimated_delivery_days precedence never surfaces a machine-formatted value"

key-files:
  created: []
  modified:
    - backend/services/cross_marketplace_service.py
    - backend/services/relevance_gates.py
    - backend/services/engines/mercado_livre_engine.py
    - backend/tests/test_cross_marketplace_service.py
    - backend/tests/test_marketplace_shipping.py
    - frontend/src/App.tsx
    - frontend/src/App.css
    - frontend/src/api/client.ts

key-decisions:
  - "Netshoes blocked-state and delivery-time surfacing added additively to _enrich_pdp_and_shipping without ever setting a fake shipping_price=0.0 for a blocked result (T-42-03)."
  - "Matriz Regional button rendered unconditionally (no isBrandShippingSupported/sku_id gate), per D-07 — every product row gets the action regardless of engine support."
  - "Live verification (orchestrator-run, API-level, real ML/Amazon/Netshoes network calls) found the real ML /shipping_options response shape does not match RESEARCH.md's MEDIUM-confidence assumption (time_frame.to / unit+time); it returns an absolute ISO-8601 date instead. Fixed _parse_delivery_time to compute estimated_delivery_days from that date via day-difference-from-now (math.ceil), never raising on malformed input."
  - "delivery_raw_text is now ONLY set when the date could not be parsed into a day-count, preventing the raw ISO timestamp from winning App.tsx's raw_text-before-estimated_delivery_days fallback precedence and rendering verbatim to the operator."

patterns-established:
  - "Blocked shipping state is a static labeled state (mirrors .monitor-price-blocked), never a retryable button — distinguishes 'permanent-for-now anti-bot block' from temporary_failure's retry affordance."

requirements-completed: [FRET-08, FRET-09]

# Metrics
duration: ~70min (prior executor Tasks 1-2 + this continuation's Task 3 fix)
completed: 2026-07-02
---

# Phase 42 Plan 03: Marketplace Prazo, Blocked State, Matriz Regional UI Summary

**Cross-marketplace cards now render marketplace delivery-time and a "Bloqueado (anti-bot)" state without a fake spinner-then-nothing, plus an always-visible "Matriz Regional" button opening a 5-region "Frete por região" modal — backed by a live-verification fix that correctly parses Mercado Livre's real absolute-date delivery-time field instead of the RESEARCH.md-assumed relative shape.**

## Performance

- **Duration:** ~70 min total (Tasks 1-2 by prior executor + this continuation's Task 3 verification/fix)
- **Tasks:** 3 (2 auto + 1 checkpoint:human-verify)
- **Files modified:** 8 (0 created, 8 modified)

## Accomplishments
- `_enrich_pdp_and_shipping` surfaces `estimated_delivery_days` / `shipping_raw_text` onto cross-marketplace product dicts when the engine result carries delivery-time, and sets `_shipping_state = "blocked"` (never a fake `shipping_price = 0.0`) when a marketplace engine (Netshoes) maps to a block.
- App.tsx renders the verbatim "Bloqueado (anti-bot)" state (statically labeled, not retryable) replacing "Calcular Frete" for blocked items, extends `isBrandShippingSupported` to `mercadolivre`/`amazon`/`netshoes`, and adds the always-visible "Matriz Regional" button + "Frete por região" modal (5 fixed-order region rows: Sudeste/Sul/Centro-Oeste/Nordeste/Norte) at both insertion points per the UI-SPEC's copywriting/color/spacing contract.
- **Live-verification fix (this continuation):** `MercadoLivreEngine._parse_delivery_time` now computes `estimated_delivery_days` from the live API's absolute ISO-8601 `estimated_delivery_time.date` field (the real API shape, which differs from RESEARCH.md's MEDIUM-confidence `time_frame.to`/`unit`+`time` assumption). `delivery_raw_text` is now only populated when date-parsing fails (true defensive fallback), preventing the raw ISO timestamp from leaking into the UI via App.tsx's `raw_text`-before-`estimated_delivery_days` fallback precedence.

## Task Commits

Each task was committed atomically:

1. **Task 1: Surface delivery-time + blocked state on cross-marketplace items (backend, D-05)** - `580821f` (feat, by prior executor)
2. **Task 2: App.tsx — blocked-state rendering, Matriz Regional button + modal, extended isBrandShippingSupported** - `1ab4249` (feat, by prior executor)
3. **Task 3 fix: ML absolute delivery-date parsing (live-verification finding)** - `248dce3` (fix, this continuation)

**Plan metadata:** (this commit — SUMMARY.md)

## Files Created/Modified
- `backend/services/cross_marketplace_service.py` - `_enrich_pdp_and_shipping` surfaces delivery-time + blocked state (Task 1)
- `backend/services/relevance_gates.py` - Rule 1 fix during Task 1 (see prior executor's deviations below)
- `backend/tests/test_cross_marketplace_service.py` - New enrichment tests (Task 1)
- `frontend/src/App.tsx` - Blocked-state rendering, Matriz Regional button/modal, extended `isBrandShippingSupported`, `requestMatrix` handler (Task 2)
- `frontend/src/App.css` - `.shipping-state-blocked`, `.shipping-matrix-trigger`, matrix modal row-state classes (Task 2)
- `frontend/src/api/client.ts` - Matrix endpoint client wiring (Task 2)
- `backend/services/engines/mercado_livre_engine.py` - `_parse_delivery_time` now computes `estimated_delivery_days` from an absolute ISO-8601 `date` field; `delivery_raw_text` only set on parse failure (Task 3 fix)
- `backend/tests/test_marketplace_shipping.py` - 4 new regression tests for `_parse_delivery_time` (absolute-date computation, time_frame precedence, malformed-date degradation, no-estimated_delivery_time-at-all degradation)

## Decisions Made
- Blocked state never substitutes a fake free/zero shipping value (T-42-03) — enforced at both the backend enrichment layer and the frontend render branch.
- Matriz Regional button has no eligibility gate (D-07) — rendered for every product row including Netshoes and unsupported engines, since the modal itself communicates the real per-region state.
- `delivery_raw_text` redefined as a strict defensive fallback (only set when a date/time value cannot be converted into a day-count), to keep the existing `estimate_display || raw_text || estimated_delivery_days`-derived fallback chain in App.tsx from ever displaying a raw machine timestamp.

## Deviations from Plan

### Auto-fixed Issues (carried forward from prior executor — Tasks 1-2)

**1. [Rule 1 - Bug] Fix in `relevance_gates.py`** (prior executor, Task 1)
- **Found during:** Task 1 (backend enrichment)
- Carried forward from the prior executor's session per continuation instructions; see commit `580821f` for the exact change (touches `backend/services/relevance_gates.py`, part of the same commit as the enrichment surfacing work).

**2. Netshoes-blocked mapping in `runShipForItem`-equivalent flow** (prior executor, Task 2)
- **Found during:** Task 2 (App.tsx rendering)
- The prior executor's App.tsx changes included wiring the Netshoes blocked state into the existing `handleCalculateShipping` cross-marketplace flow so a block renders the static label instead of leaving the UI in a spinner state indefinitely; see commit `1ab4249`.

### Auto-fixed Issues (this continuation — Task 3)

**3. [Rule 1 - Bug] ML `_parse_delivery_time` did not handle the live API's actual response shape**
- **Found during:** Task 3 (live browser/API smoke, run by the orchestrator prior to this continuation agent)
- **Issue:** The live Mercado Livre `/shipping_options` API returns `estimated_delivery_time.date` as an absolute ISO-8601 timestamp (e.g. `"2026-07-02T00:00:00-03:00"`) rather than the `time_frame.to` / `unit`+`time` shape RESEARCH.md flagged as MEDIUM confidence (Open Question A1). The existing code only stored this into `delivery_raw_text` verbatim, which would render literally as the "prazo" caption in the UI (confirmed live for at least 3 App.tsx call sites) — a genuine UX defect, not cosmetic.
- **Fix:** `_parse_delivery_time` now calls a new `_days_from_iso_date` helper that parses the ISO string with `datetime.fromisoformat`, computes the day-difference from "now" (`math.ceil`, floored at 0), and populates `estimated_delivery_days`. `delivery_raw_text` is now set ONLY when the date cannot be parsed (defensive fallback) or when no day-count could be resolved by any branch — never when `estimated_delivery_days` was successfully derived. This additionally required fixing a discovered second-order bug: even after computing `estimated_delivery_days`, the old code still always set `delivery_raw_text` from the raw ISO string whenever `date_str` was present, which would have kept winning App.tsx's `raw_text`-before-`estimated_delivery_days` fallback precedence and defeated the fix. Both issues fixed together as one coherent Rule 1 fix.
- **Files modified:** `backend/services/engines/mercado_livre_engine.py`, `backend/tests/test_marketplace_shipping.py`
- **Verification:** `pytest tests/test_marketplace_shipping.py -x -q` (17 passed); full suite `pytest -q` (497 passed, up from the 493-test baseline reported by 42-01-SUMMARY.md/42-02 — 4 net-new tests, no regressions).
- **Committed in:** `248dce3`

---

**Total deviations:** 2 carried forward from prior executor (Tasks 1-2, documented in-commit) + 1 auto-fixed in this continuation (Rule 1 — ML delivery-date parsing + raw-text-leak fix).
**Impact on plan:** All fixes necessary for correctness (T-42-03 no-fake-value guarantee, and the plan's own Task 3 instruction to "adjust the ML delivery-time parser accordingly" if the live field shape differs from RESEARCH.md's assumption — which it did). No scope creep.

## Issues Encountered
None beyond the documented live-verification finding above.

## Live Verification Evidence (Task 3 — checkpoint:human-verify)

Per the orchestrator's automation-first checkpoint protocol, live API-level verification was performed against the REAL Mercado Livre, Amazon, and Netshoes sites (not mocks) hitting the actual backend endpoints, combining Plan 42-01 + 42-02 (both merged to `main`) with this plan's Task 1/2 commits:

- **Netshoes** single-item shipping calc -> `state: "blocked"`, message "Bloqueado (anti-bot)" — matches D-01 exactly.
- **Amazon** single-item shipping calc -> `state: "temporary_failure"` (real CAPTCHA/anti-bot encountered this session) — correctly never substitutes a fake price.
- **Mercado Livre** single-item shipping calc -> `state: "available"`, `price: 0.0`, `is_free_shipping: true` — cost side confirmed working.
- **Regional matrix** (`POST /search/calculate-shipping-matrix`) for Mercado Livre -> exactly 5 regions (Sudeste/Sul/Centro-Oeste/Nordeste/Norte) with real per-region CEPs, all `state: "available"`.
- **Regional matrix cache (D-09)** -> first request ~21s (cold), second identical request ~1s with `"cached": true` on every region.
- **Regional matrix for Netshoes** -> all 5 regions correctly `state: "blocked"`, action never hidden (D-07 confirmed).
- **ML delivery-time bug** found and fixed as documented above.

**NOT independently verified (genuine human-only judgment, explicitly out of scope for automation):** pixel-level visual rendering in a real browser — button placement, modal layout, absence of overflow/layout-shift at the ≤640px breakpoint — was NOT checked by the orchestrator (no browser-automation tool available in this session) and was NOT checked by this continuation agent either. This does not block plan completion since none of the underlying rendering logic changed as a result of the Task 3 fix (only the ML backend delivery-time computation changed, and the frontend's existing fallback-chain code was read-verified, not modified). **Recommended manual follow-up:** operator should do a final visual pass per the original checkpoint's `<how-to-verify>` steps 2-6 whenever convenient — not blocking, informational only.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- FRET-08 and FRET-09 UI surfaces are fully wired end-to-end: backend enrichment -> App.tsx rendering -> live-verified against real marketplace APIs.
- The `_parse_delivery_time` fix is defensive (never raises, degrades gracefully when `estimated_delivery_time` is absent entirely, as some regions like Nordeste demonstrated live) — safe for production traffic patterns beyond this session's test product.
- Full backend suite green (497 tests, +4 net-new from this continuation, 0 regressions).
- Outstanding non-blocking item: a manual visual/browser pass of the Matriz Regional modal and blocked-state card layout, whenever convenient for the operator.

---
*Phase: 42-frete-para-marketplaces-matriz-multi-regional*
*Completed: 2026-07-02*

## Self-Check: PASSED

- `42-03-SUMMARY.md` verified present on disk at `.planning/phases/42-frete-para-marketplaces-matriz-multi-regional/`.
- All 3 task commit hashes (`580821f`, `1ab4249`, `248dce3`) verified present in `git log --oneline --all`.
- `pytest tests/test_marketplace_shipping.py -x -q` re-confirmed: 17 passed.
- Full backend suite re-confirmed: `pytest -q` — 497 passed, 0 failed, 1 pre-existing unrelated warning.
- No unexpected file deletions in the Task 3 fix commit (`git diff --diff-filter=D --name-only HEAD~1 HEAD` empty).
