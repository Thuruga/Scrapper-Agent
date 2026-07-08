---
phase: 38-ux-de-busca-monitoramento-quick-wins
plan: 03
subsystem: ui
tags: [react, sku-validation, category-monitor, price-monitor]

# Dependency graph
requires:
  - phase: 38-ux-de-busca-monitoramento-quick-wins
    provides: "38-01 backend last_price_discount field + category scan last_scraped_at signal"
  - phase: 38-ux-de-busca-monitoramento-quick-wins
    provides: "38-02 shared search row layout and history icon groundwork"
provides:
  - "SKU search validates ^ML\\.05\\.\\d{7}$ on blur/submit with reused CEP error UI (UX-07)"
  - "SKU + CEP form migrated to shared .search-main-row/.search-field layout (UX-07)"
  - "Category creation shows row spinner, polls GET /monitor/categories, and auto-opens products modal on last_scraped_at (UX-08)"
  - "Monitor list renders last_price_discount as strikethrough pre-discount price using existing GET /monitors payload (UX-02)"
affects: ["38-HUMAN-UAT", "phase-38-verification"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Frontend SKU regex remains a UX gate only; backend SKU validation is unchanged"
    - "Auto-sweep completion uses bounded polling against the existing category list endpoint; no scan endpoint added"
    - "Promo monitor rendering uses the discount-delta convention: last_price + last_price_discount"

key-files:
  created:
    - .planning/phases/38-ux-de-busca-monitoramento-quick-wins/38-03-SUMMARY.md
  modified:
    - frontend/src/App.tsx

requirements-completed: [UX-02, UX-07, UX-08]

# Metrics
duration: 35min
completed: 2026-07-01
---

# Phase 38 Plan 03: SKU Validation, Auto-Sweep, and Promo Monitor Render Summary

**Completed the remaining Phase 38 frontend wave: SKU validation and shared row layout, automatic first category sweep feedback, and promo price rendering in the monitor list.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 3 completed
- **Files modified:** 1 (`frontend/src/App.tsx`)
- **File created:** 1 (`38-03-SUMMARY.md`)

## Accomplishments

- Added SKU validation for the marketplace search tab using `^ML\.05\.\d{7}$`, with the approved inline error copy and reused `.cep-input-error` / `.cep-helper` styling.
- Migrated the SKU + CEP row to the shared `.search-main-row` / `.search-field` layout so it inherits the same 980px collapse behavior as comparative search.
- Added auto-sweep UI for new monitored categories: after `Salvar`, the modal closes, a success toast appears, the new row shows a spinner, and a bounded poll watches `last_scraped_at` before calling the existing `handleViewProducts` modal loader.
- Rendered monitor promo pricing from `last_price_discount` in `.monitor-pricing`, showing a strikethrough pre-discount price above the current price with no new network call.

## Verification

- `cd frontend && npm run build` - passed
- `cd backend && python -m pytest -q` - passed (`473 passed`, 1 runtime warning about an unawaited coroutine surfaced during an existing SFCC Lacoste test)

## Deviations from Plan

- The working tree already contained a partial uncommitted start on Task 1 (SKU regex/layout). This run completed and polished that related work instead of rewriting it.
- The failure toast for the auto-sweep is wired to poll failures or missing created ids. The backend currently records completion via `last_scraped_at` even for empty scans, so there is no richer scan-failure state to branch on from the frontend.

## Issues Encountered

- `frontend/src/App.tsx` also contains unrelated uncommitted stock-depth display changes from outside this plan. They were preserved and not altered except where already present in the same file.

## Manual UAT

`38-HUMAN-UAT.md` remains pending. Automated checks are green, but the visual/interaction checks still need browser confirmation for UX-01, UX-06, UX-07, and UX-08.

## Next Step

Run Phase 38 verification/UAT, then mark the phase complete if all four manual checks pass.

---
*Phase: 38-ux-de-busca-monitoramento-quick-wins*
*Completed: 2026-07-01*
