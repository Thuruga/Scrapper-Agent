---
phase: 27-hist-rico-completo-gest-o-de-marcas-na-ui
plan: "02"
subsystem: frontend
tags: [brand-management, settings-ui, toggle, active-inactive]
dependency_graph:
  requires: []
  provides: [ApiClient.setBrandActive, SettingsPage brand toggle, inactive visual distinction]
  affects: [frontend/src/api/client.ts, frontend/src/App.tsx]
tech_stack:
  added: []
  patterns: [PATCH via shared request wrapper, conditional className opacity, lucide-react Power icon]
key_files:
  created: []
  modified:
    - frontend/src/api/client.ts
    - frontend/src/App.tsx
decisions:
  - "VIRTUAL guard implemented as a constant array ['mercado_livre','netshoes','amazon'] inside SettingsPage — simple includes() check"
  - "Inactive distinction uses inline style opacity 0.55 on .brand-info instead of a new CSS class — avoids App.css modification while meeting D-09"
  - "Toggle ON/OFF color via inline style using var(--primary)/var(--text-muted) — consistent with existing token usage"
  - "handleToggleActive surfaces errors via setStatus banner (same as handleSubmit) rather than alert() — more consistent UX"
metrics:
  duration: "~10m"
  completed: "2026-06-20T18:52:00Z"
  tasks_completed: 2
  files_modified: 2
---

# Phase 27 Plan 02: Brand Active Toggle + Inactive Distinction Summary

**One-liner:** Wire `PATCH /brands/{key}/active` endpoint to SettingsPage via new `ApiClient.setBrandActive`, adding per-row Power toggle and "Inativa" badge with opacity dimming, guarded off for virtual marketplaces.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Add ApiClient.setBrandActive PATCH method | 1addece | frontend/src/api/client.ts |
| 2 | Extend SettingsPage brand rows with toggle + inactive distinction | 2ac325d | frontend/src/App.tsx |

## What Was Built

### Task 1 — ApiClient.setBrandActive
Added `static setBrandActive(brandKey: string, isActive: boolean)` to `ApiClient` in `client.ts` after `deleteBrand`. Issues `PATCH /brands/{brandKey}/active` with `body: JSON.stringify({ is_active: isActive })` — mirrors the `deleteBrand` pattern, delegates error handling to the shared `request` wrapper (throws on non-OK including 404 for unknown keys).

### Task 2 — SettingsPage brand row extensions
Three additions to `SettingsPage` in `App.tsx`:

1. **`handleToggleActive(brand)`** — async handler calling `ApiClient.setBrandActive(brand.brand_key, !brand.is_active)` then `onRefresh()`. No `confirm()` — instant and reversible (D-10). Errors surface via `setStatus({ type: 'error', ... })` banner.

2. **Virtual-marketplace guard** — `const VIRTUAL = ['mercado_livre', 'netshoes', 'amazon']` with `const canToggle = !VIRTUAL.includes(b.brand_key)` per row. Toggle rendered only when `canToggle` (landmine A1: these brands have no backend record, PATCH would 404).

3. **Brand row extensions**:
   - **Active toggle**: `.btn-icon` with `Power` icon (imported from lucide-react). ON state colored `var(--primary)`, OFF state `var(--text-muted)`. `aria-label` per UI-SPEC copy contract ("Ativar marca {nome}" / "Desativar marca {nome}"). `aria-pressed` reflects `b.is_active`.
   - **Inactive distinction**: when `b.is_active === false`, `.brand-info` block gets `opacity: 0.55` via inline style; an "Inativa" `.monitor-badge` with `color: var(--warning)` renders next to `.brand-name-text`. `.brand-actions` remains fully opaque and interactive.
   - Existing delete button (confirm-gated `handleDeleteBrand`) is unchanged.

## Verification

- `cd frontend && npm run build` — exits 0 (tsc + vite build pass)
- `python -m pytest tests/test_brand_active.py -x` — 7/7 passed (backend endpoint regression-guarded)
- `npm run lint` — 6 pre-existing errors (lines 654, 977, 992, 1516, 1521 in App.tsx; line 15 in client.ts); ZERO new errors introduced by this plan

## Deviations from Plan

### Pre-existing lint failures

**[Out of Scope] Pre-existing ESLint errors not introduced by this plan**
- **Found during:** Task 2 verification
- **Issue:** `npm run lint` returns 6 errors — `react-hooks/set-state-in-effect` at lines 654, 977, 1516, 1521 (preloaded history useEffect + MonitoredCategoriesPage), `prefer-const` at line 992, `@typescript-eslint/no-unused-vars` for `_token` in client.ts line 15.
- **Status:** All confirmed pre-existing via `git show HEAD~1`. Not introduced by this plan. Logged to deferred-items.
- **Impact:** `npm run lint` does not exit 0 — but this was already the state before plan 27-02 started.

None — plan executed as written. Auto-fixes or architectural deviations: none.

## Known Stubs

None — all data flows from the live API (GET /brands/ returns is_active field; PATCH /brands/{key}/active persists state server-side).

## Threat Flags

No new security surface introduced. The plan consumes an existing endpoint (PATCH /brands/{key}/active) with an existing Pydantic validation gate (BrandActiveUpdate). Virtual-marketplace guard (T-27-02-03) implemented as specified.

## Manual UAT Notes (to be verified live)

- Deactivate a real brand → it dims (0.55 opacity on info block) + shows "Inativa" warning badge
- Refresh page → inactive state persists (server-side)
- Reactivate → opacity restored, badge removed
- Mercado Livre / Netshoes / Amazon rows → NO Power toggle button visible, only delete button

## Self-Check

- [x] `frontend/src/api/client.ts` contains `setBrandActive` — file modified
- [x] `frontend/src/App.tsx` contains `handleToggleActive`, `VIRTUAL`, `Power` icon — file modified
- [x] Commit 1addece exists — Task 1
- [x] Commit 2ac325d exists — Task 2
