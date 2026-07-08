---
phase: 38-ux-de-busca-monitoramento-quick-wins
plan: 02
subsystem: ui
tags: [react, css-media-query, lucide-react, zustand-free-local-state]

# Dependency graph
requires:
  - phase: 38-ux-de-busca-monitoramento-quick-wins
    provides: "38-01 backend discount-aware monitoring (unrelated, ran in parallel — no shared files)"
provides:
  - "@media (max-width: 768px) rule collapsing .grid-category to a single column, fixing overflow on both MonitoredCategoriesPage and CategoryPage (UX-01)"
  - "Top-right icon-only History button on SearchPage and CrossMarketplacePage, controlling the existing HistoryList panel via new optional controlled props (collapsed/onToggleCollapsed/onCountChange) without duplicating ApiClient.getHistoryList() (UX-06)"
affects: ["38-03"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "HistoryList controlled-prop pattern: collapsed/onToggleCollapsed are optional — when omitted, HistoryList keeps its original internal useState(true) toggle behavior (backward-compatible dual-mode controlled/uncontrolled component)"
    - "Count-lifting via onCountChange callback: exposes the internal type-filtered items.length upward for an external badge, avoiding a second fetch or duplicated filter logic"

key-files:
  created: []
  modified:
    - frontend/src/App.css
    - frontend/src/App.tsx

key-decisions:
  - "Icon placed as a page-local top-right row (flex justify-content: flex-end) inside each page's own .page-content, rather than lifting state into the shared app-shell content-header — avoids threading toggle/badge state through App() for a two-tab feature, matches plan's 'executor's discretion' allowance"
  - "HistoryList made dual-mode (controlled or uncontrolled) instead of forcing a breaking prop change, so the collapsed prop defaults to the component's own state when not supplied by a future caller"
  - "Products-modal grid (repeat(auto-fill, minmax(250px, 1fr))) verified as already responsive at 768px (auto-fill wraps columns without overflow) — no CSS override added, per plan's conditional instruction"

patterns-established:
  - "Dual-mode controlled/uncontrolled component prop pattern for React state lifting without breaking existing internal-toggle callers"

requirements-completed: [UX-01, UX-06]

# Metrics
duration: 20min
completed: 2026-07-01
---

# Phase 38 Plan 02: Responsive category grid + top-right search-history icon Summary

**Added a 768px breakpoint collapsing `.grid-category` to one column, and a top-right History icon button on both search tabs that toggles the existing `HistoryList` panel with a type-scoped badge count.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2 completed
- **Files modified:** 2 (`frontend/src/App.css`, `frontend/src/App.tsx`)

## Accomplishments
- `.grid-category` (shared by `MonitoredCategoriesPage` and `CategoryPage`) now stacks to a single column at `max-width: 768px`, matching the app's existing `@media (max-width: Npx)` convention (no container queries introduced).
- Both search tabs (comparativa `SearchPage`, SKU `CrossMarketplacePage`) now show a top-right icon-only History button (`title="Ver histórico de buscas"`) that toggles the pre-existing `HistoryList` panel instead of relying on its internal collapsed header.
- The icon's corner badge mirrors `HistoryList`'s own type-filtered count (via a new `onCountChange` callback) — no duplicated fetch, no raw/unfiltered count leak between tabs.

## Task Commits

Each task was committed atomically:

1. **Task 1: Responsive .grid-category breakpoint at 768px (UX-01)** - `ed2e482` (feat)
2. **Task 2: Top-right History icon toggling the HistoryList panel on both search tabs (UX-06)** - `fb4b94f` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified
- `frontend/src/App.css` - Added `.grid-category { grid-template-columns: 1fr; }` inside the existing `@media (max-width: 768px)` block (colocated with the mobile-sidebar rules).
- `frontend/src/App.tsx` - `HistoryList` gained optional `collapsed`/`onToggleCollapsed`/`onCountChange` props (backward-compatible with its prior uncontrolled internal toggle); `SearchPage` and `CrossMarketplacePage` each render a new top-right `.btn-icon` History button with a `.monitor-badge` count pill, wired to the (now controlled) `HistoryList` instance; the old inline `HistoryList` render calls (previously below the search form) were removed since the component moved to the top of each page.

## Decisions Made
- Kept the icon button page-local (inside `SearchPage`/`CrossMarketplacePage`'s own `.page-content`) rather than lifting state to the shared `content-header` in the app shell — simpler, avoids new cross-component plumbing, and the plan explicitly allowed either location.
- Made `HistoryList`'s `collapsed` prop optional/dual-mode so the component still works standalone (internal `useState(true)`) if a future caller doesn't pass the controlled props — avoids a breaking API change.
- Confirmed via code inspection that the products-modal grid (`repeat(auto-fill, minmax(250px, 1fr))` at `App.tsx:2983`) does not need a 768px override — `auto-fill` already reflows columns to fit the 95%-width modal without horizontal overflow, so the plan's conditional scoped-class fallback was not needed.

## Deviations from Plan

None - plan executed exactly as written. The one conditional branch in Task 1's `<action>` (add a scoped CSS override for the products-modal grid "if overflow observed") was evaluated and found not applicable — `minmax(250px, 1fr)` with `auto-fill` is inherently responsive, confirmed by code reading of the grid definition and container width, no override added.

## Issues Encountered

The working tree contained unrelated in-progress changes to `frontend/src/App.tsx` (stock-depth `availability_only` state handling, from other work outside this plan's scope) mixed into the same file. Used `git add -p` to stage only the hunks belonging to this plan's Task 2 (HistoryList controlled props + both pages' icon buttons), leaving the unrelated stock-depth hunks uncommitted in the working tree exactly as found.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- UX-01 and UX-06 are code-complete and build-verified; final visual/interaction confirmation is deferred to `38-HUMAN-UAT.md` Tests 1-2, which run after Wave 2 (Plan 03) per the UAT file's own note.
- No blockers for Plan 03 (UX-07/UX-08), which touches different sections of the same files (`App.tsx` SKU form, `MonitoredCategoriesPage` submit handler) with no expected overlap with this plan's edits.

---
*Phase: 38-ux-de-busca-monitoramento-quick-wins*
*Completed: 2026-07-01*

## Self-Check: PASSED

- FOUND: frontend/src/App.css
- FOUND: frontend/src/App.tsx
- FOUND: .planning/phases/38-ux-de-busca-monitoramento-quick-wins/38-02-SUMMARY.md
- FOUND commit: ed2e482
- FOUND commit: fb4b94f
