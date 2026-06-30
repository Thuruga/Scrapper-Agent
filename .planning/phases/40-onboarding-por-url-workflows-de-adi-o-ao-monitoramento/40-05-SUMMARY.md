---
phase: 40-onboarding-por-url-workflows-de-adi-o-ao-monitoramento
plan: "05"
subsystem: frontend
status: pending-human-verify
tags: [frontend, onboarding, monitoring, ui, ux]
dependency_graph:
  requires: ["40-02", "40-03", "40-04"]
  provides: ["UX-03", "UX-04", "UX-05"]
  affects: ["frontend/src/api/client.ts", "frontend/src/App.tsx"]
tech_stack:
  added: []
  patterns:
    - "identifyBrand/addToMonitor client methods over existing request<T> generic"
    - "handleAddToMonitor handler with status-aware toasts (already_active/reactivated/created)"
    - "Onboarding form: identify dry-run → pre-fill → confirm with confirmed engine (never auto)"
    - "e.preventDefault()+e.stopPropagation() on buttons inside <a href> cards (Pattern 8)"
key_files:
  created: []
  modified:
    - frontend/src/api/client.ts
    - frontend/src/App.tsx
decisions:
  - "[40-05/handleAddToMonitor-per-page]: handleAddToMonitor defined in each of the 3 pages (SearchPage, CrossMarketplacePage, MonitoredCategoriesPage) rather than hoisted to App — keeps each page self-contained and avoids prop drilling into deeply-nested components"
  - "[40-05/VIRTUAL-removal]: const VIRTUAL array and canToggle guard fully removed from SettingsPage; marketplace brands (mercado_livre/netshoes/amazon) now have real brands.json entries (Plan 04) so PATCH /brands/{key}/active is valid — no 404 risk"
  - "[40-05/onboarding-placement]: Onboarding form placed as a top-level GlassCard in SettingsPage (Marcas tab), above the brand list — consistent with the existing brand-management area and operator workflow"
  - "[40-05/engine-options-hardcoded]: ENGINE_OPTIONS in onboarding form is a static list matching known engine values; no API endpoint needed since the engine select is an editable override for operator review, not a dynamic server list"
metrics:
  duration: "~20m"
  completed_date: "2026-06-30"
  tasks_completed: 2
  tasks_total: 3
  files_modified: 2
---

# Phase 40 Plan 05: UI Onboarding por URL + Add-to-Monitor + Marketplace Toggles Summary

**One-liner:** Frontend wires UX-03/04/05 — URL onboarding form (identify→pre-fill→confirm with engine override), add-to-monitor Plus button on 3 product surfaces with dedup toasts, and VIRTUAL guard removal for marketplace power toggles.

**Status: TASKS 1-2 COMPLETE — AWAITING HUMAN VERIFICATION (Task 3)**

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add identifyBrand + addToMonitor to client.ts | `8d28284` | `frontend/src/api/client.ts` |
| 2 | Onboarding form + add-to-monitor x3 + marketplace toggles | `95629a9` | `frontend/src/App.tsx` |

## Task 3: PENDING HUMAN VERIFICATION

See checkpoint details below. Plan will be marked complete after operator approval.

---

## What Was Built

### Task 1 — client.ts (commit `8d28284`)

Two new static methods added to `ApiClient` in `frontend/src/api/client.ts`:

- `ApiClient.identifyBrand(url: string)` — POSTs to `/brands/identify`, returns `{ engine, inferred_name, domain, warning? }`. Placed in the Brands section after `setBrandActive`.
- `ApiClient.addToMonitor(url: string, brand: string)` — POSTs to `/monitor/start` with `{ url, brand, interval: 10, duration: 24 }` (D-05 defaults), returns `{ job_id, status, config }`. Placed in the Monitors section after `startMonitor`. Semantic helper over `/monitor/start`; reuses the existing `request<T>` generic, no second HTTP layer.

### Task 2 — App.tsx (commit `95629a9`)

**(a) UX-03 — Onboarding by URL (SettingsPage):**
- New GlassCard "Adicionar Marca por URL" at top of SettingsPage (above brand list).
- URL input + "Identificar" button calls `ApiClient.identifyBrand(url)`.
- On success: pre-filled editable confirmation form with fields: `brand_name` (always editable, D-01), `domain`, `engine` (select with all known engine options for manual override).
- If `warning` present in response (engine=unknown), shows a non-blocking amber alert — operator can still save (D-03).
- On confirm: calls `ApiClient.saveBrand({ brand_name, domain, engine: confirmedEngine })` — `confirmedEngine` is always the value from the select, never `'auto'` (T-40-08 / Pitfall 7).
- Refreshes brand list on save; toasts success.

**(b) UX-04 — Add-to-Monitor button on 3 surfaces:**
- `handleAddToMonitor(url, brand)` handler defined in each page: `SearchPage`, `CrossMarketplacePage`, `MonitoredCategoriesPage`.
- Calls `ApiClient.addToMonitor(url, brand)` and toasts by `result.status`:
  - `already_active` → `toast.info('Produto já está em monitoramento')`
  - `reactivated` → `toast.success('Monitor reativado')`
  - else → `toast.success('Adicionado ao monitoramento')`
  - catch → `toast.error`
- Button: `<Plus size={14} />`, title "Adicionar ao monitoramento", rendered inside product cards.
- `onClick` always has `e.preventDefault() + e.stopPropagation()` (mandatory — cards are `<a href>` elements, Pattern 8).
- Surface 1: SearchPage comparative cards — `brand = brandKey` (in scope from outer map).
- Surface 2: CrossMarketplacePage SKU cards — `brand = MARKETPLACE_BRAND_KEY[marketplace]` (maps display names to brand_keys: "Mercado Livre"→`mercado_livre`, "Netshoes"→`netshoes`, "Amazon"→`amazon`).
- Surface 3: MonitoredCategoriesPage modal product cards — `brand = selectedMonitor.brand`; button only shown when `p.url` is present.
- All 3 buttons target `/monitor/start` only — never the category monitor endpoint (Pitfall 6).

**(c) UX-05 — Marketplace toggles (SettingsPage):**
- Removed `const VIRTUAL = ['mercado_livre', 'netshoes', 'amazon']` from `SettingsPage`.
- Removed `const canToggle = !VIRTUAL.includes(b.brand_key)` guard.
- Power toggle now renders for ALL brands including mercado_livre/netshoes/amazon (now real brands.json entries from Plan 04; PATCH /brands/{key}/active no longer returns 404).
- Inactive-row distinction (opacity 0.55 on `.brand-info` + "Inativa" badge) preserved for all brands including marketplaces.
- CategoryPage filter (`l.531`: `.filter(b => !['mercado_livre', 'netshoes', 'amazon'].includes(...))`) KEPT — intentional (Pitfall 3).
- BannersPage `virtualMarketplaces` Set (`l.886`) KEPT — intentional (Pitfall 4).

---

## Automated Verification Results

**Task 1:**
```
cd frontend && npx tsc --noEmit
# Output: (none — no errors)
```

**Task 2:**
```
cd frontend && npx tsc --noEmit && npm run build
# tsc: (none — no errors)
# vite build: ✓ built in 1.48s
# Chunk size warning is pre-existing, not from this plan
```

---

## Deviations from Plan

### Auto-applied adjustments

**1. [Rule 2 — Completeness] `handleAddToMonitor` defined per-page rather than as a single hoisted handler**
- **Found during:** Task 2 implementation
- **Issue:** The three target surfaces (SearchPage, CrossMarketplacePage, MonitoredCategoriesPage) are separate top-level components in App.tsx; there is no shared state context between them. Hoisting the handler to `App()` would require threading it down through multiple component props, adding coupling not present in the existing codebase pattern.
- **Fix:** Defined identical `handleAddToMonitor` in each of the 3 page components. The implementation is identical in all 3; the only difference is the `brand` argument passed from each context.
- **Files modified:** `frontend/src/App.tsx`

**2. [Correctness] MARKETPLACE_BRAND_KEY map in CrossMarketplacePage**
- **Found during:** Task 2 — wiring CrossMarketplacePage button
- **Issue:** The marketplace column render uses display names ("Mercado Livre", "Netshoes", "Amazon") but `addToMonitor` requires brand_keys (`mercado_livre`, `netshoes`, `amazon`).
- **Fix:** Added `const MARKETPLACE_BRAND_KEY` lookup map before `handleExport`; button onClick derives `brandKey = MARKETPLACE_BRAND_KEY[marketplace]` with a safe lowercase fallback.
- **Files modified:** `frontend/src/App.tsx`

---

## Known Stubs

None — all 3 flows wire to real backend endpoints from Plans 02-04.

---

## Threat Flags

None beyond the plan's threat model (T-40-08 / T-40-09 / T-40-SC). The confirm path never sends `engine: 'auto'` (T-40-08 mitigated). No new network endpoints or trust boundaries introduced in this frontend plan.

---

## Task 3: Checkpoint — Human Verification Required

**Type:** checkpoint:human-verify  
**Gate:** blocking

**What was built:**
- Onboarding-by-URL confirmation form (UX-03) in the Marcas / Gerenciar Marcas tab
- "Adicionar ao monitoramento" button on 3 surfaces: Comparativa search, SKU search, Monitor de Categorias products modal (UX-04)
- Marketplace activate/deactivate Power toggles now visible in Gerenciar Marcas (UX-05)

**How to verify (3 flows):**

1. **UX-03 — Onboarding form:** Open the app → go to "Marcas" tab → in "Adicionar Marca por URL", paste `https://www.hugoboss.com.br` → click Identificar → confirm a pre-filled form appears with inferred name + detected engine, the name field is editable, and an engine override dropdown is available. Paste an unrecognized URL → confirm a non-blocking amber warning appears but Save is still available. Confirm and save → brand appears in the brand list below. Verify only the explicit Save persisted anything (Identify is dry-run).

2. **UX-04 — Add-to-monitor dedup:** Run a comparative search → click the Plus ("+") button on a product card → confirm a green toast "Adicionado ao monitoramento" and the product appears in price monitors. Click Plus again on the same product → confirm an info toast "Produto já está em monitoramento" and no duplicate is created. Repeat the same Plus click test from the SKU search (Busca por SKU tab) and from the Monitor de Categorias products modal (click a category row → view products → click Plus on a product) — all three flows add to the SAME price-monitor list with dedup.

3. **UX-05 — Marketplace toggles:** Open Marcas tab → confirm Mercado Livre, Netshoes, Amazon now show Power toggle buttons (not just delete). Deactivate one marketplace → run a cross-marketplace search → confirm that marketplace is absent from the results on the very next run. Reactivate → confirm it returns.

**Resume signal:** Type "approved" or describe any issue (which flow, expected vs actual).

---

## Self-Check

- [x] `frontend/src/api/client.ts` contains `static identifyBrand(` — grep confirms 1 match
- [x] `frontend/src/api/client.ts` contains `static addToMonitor(` — grep confirms 1 match
- [x] `frontend/src/App.tsx` contains `handleAddToMonitor` — grep confirms 6 matches (3 definitions, 3 call sites)
- [x] `frontend/src/App.tsx` contains `ApiClient.addToMonitor` — grep confirms 3 matches
- [x] `frontend/src/App.tsx` contains `ApiClient.identifyBrand` — grep confirms 1 match
- [x] `engine: 'auto'` in confirm path — grep confirms 0 matches
- [x] `const VIRTUAL` in App.tsx — grep confirms 0 matches
- [x] CategoryPage filter (`l.531`) preserved — grep confirms match
- [x] BannersPage `virtualMarketplaces` preserved — grep confirms match
- [x] Commit `8d28284` exists — verified via git log
- [x] Commit `95629a9` exists — verified via git log
- [x] `npx tsc --noEmit` — passes (no output)
- [x] `npm run build` — passes (built in 1.48s)

## Self-Check: PASSED (Tasks 1-2)

Task 3 (human-verify) remains open — plan completion deferred to operator approval.
