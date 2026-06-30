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
    - "Identify-first monitor flow: paste product URL → identifyBrand → domain→registered-brand match → addToMonitor; manual-select fallback when no domain match"
    - "e.preventDefault()+e.stopPropagation() on buttons inside <a href> cards (Pattern 8)"
key_files:
  created: []
  modified:
    - frontend/src/api/client.ts
    - frontend/src/App.tsx
decisions:
  - "[40-05/handleAddToMonitor-per-page]: handleAddToMonitor defined in each of the 3 pages (SearchPage, CrossMarketplacePage, MonitoredCategoriesPage) rather than hoisted to App — keeps each page self-contained and avoids prop drilling into deeply-nested components"
  - "[40-05/VIRTUAL-removal]: const VIRTUAL array and canToggle guard fully removed from SettingsPage; marketplace brands (mercado_livre/netshoes/amazon) now have real brands.json entries (Plan 04) so PATCH /brands/{key}/active is valid — no 404 risk"
  - "[40-05/UX-03-rework]: UX-03 reworked per operator feedback — moved URL-identify INTO the MonitorPage 'Monitorar Novo Produto' form (paste product link → auto-identify brand by domain). The standalone brand-add-by-URL form in SettingsPage was REMOVED. SettingsPage returns to pure management (toggle/delete) + marketplace toggles."
  - "[40-05/domain-match]: Registered brand resolved by normalized-domain equality. normalizeDomain lowercases + strips a leading literal 'www.' via slice (NOT lstrip — lstrip strips the {w,.} char-set and would corrupt hosts); the same normalization is applied to the identified domain and each brands[].domain (mirrors 40-01/literal-www-strip)."
  - "[40-05/manual-fallback]: When no registered brand matches the identified domain, the monitor is NOT started; the previously-hidden 'Marca Concorrente' select is revealed so the operator can pick a brand manually and submit. The form is never a dead end."
metrics:
  duration: "~30m"
  completed_date: "2026-06-30"
  tasks_completed: 2
  tasks_total: 3
  files_modified: 2
---

# Phase 40 Plan 05: UI Identify-in-Monitor + Add-to-Monitor + Marketplace Toggles Summary

**One-liner:** Frontend wires UX-03/04/05 — UX-03 reworked to an identify-first monitor flow (paste product URL → auto-identify brand by domain → add to monitor, with manual-select fallback), add-to-monitor Plus button on 3 product surfaces with dedup toasts, and VIRTUAL guard removal for marketplace power toggles.

**Status: FLOWS 2 & 3 OPERATOR-APPROVED. FLOW 1 (UX-03) REWORKED — PENDING RE-VERIFICATION.**

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add identifyBrand + addToMonitor to client.ts | `8d28284` | `frontend/src/api/client.ts` |
| 2 | Add-to-monitor x3 + marketplace toggles + (original) onboarding form | `95629a9` | `frontend/src/App.tsx` |
| 2-rework | Move URL-identify into monitor flow; remove brand-add-by-URL form | _(this commit)_ | `frontend/src/App.tsx` |

**Operator verification status:**
- Flow 2 (add-to-monitor button x3) — **APPROVED** (unchanged, as committed in `95629a9`)
- Flow 3 (marketplace toggles) — **APPROVED** (unchanged, as committed in `95629a9`)
- Flow 1 (UX-03) — **REWORKED** per operator feedback; pending re-verification

## Task 3: PENDING HUMAN VERIFICATION

See checkpoint details below. Plan will be marked complete after operator approval.

---

## What Was Built

### Task 1 — client.ts (commit `8d28284`)

Two new static methods added to `ApiClient` in `frontend/src/api/client.ts`:

- `ApiClient.identifyBrand(url: string)` — POSTs to `/brands/identify`, returns `{ engine, inferred_name, domain, warning? }`. Placed in the Brands section after `setBrandActive`.
- `ApiClient.addToMonitor(url: string, brand: string)` — POSTs to `/monitor/start` with `{ url, brand, interval: 10, duration: 24 }` (D-05 defaults), returns `{ job_id, status, config }`. Placed in the Monitors section after `startMonitor`. Semantic helper over `/monitor/start`; reuses the existing `request<T>` generic, no second HTTP layer.

### Task 2 — App.tsx (commit `95629a9`, reworked in this commit)

**(a) UX-03 — Identify-first monitor flow (MonitorPage) — FINAL (reworked per operator feedback):**

The original `95629a9` placed a standalone "Adicionar Marca por URL" form in SettingsPage. The operator rejected that placement. UX-03 was reworked into the existing "Monitorar Novo Produto" form on the MonitorPage:

- "URL do Produto" is now the primary, first input. The "Marca Concorrente" `<select>` is hidden by default (still present in the component, only shown in the manual fallback path).
- On submit (happy path): calls `ApiClient.identifyBrand(url)` → `{ engine, inferred_name, domain, warning }`.
- Resolves the registered brand by **domain match**: `normalizeDomain` (lowercase + strip a leading literal `www.` via slice — not `lstrip`) is applied to BOTH the identified `domain` and each `brands[].domain`; the brand whose normalized domain equals the identified one is matched, and its `brand_key` is used.
- If a registered brand matches → calls `ApiClient.addToMonitor(url, matchedBrandKey)` and toasts by `result.status` (`already_active` → info "Produto já está em monitoramento"; `reactivated` → success "Monitor reativado"; else → success "Adicionado ao monitoramento"). Shows "Marca identificada: <brand_name>". Clears the URL and calls `refreshMonitors()` on success.
- If NO registered brand matches the domain → the monitor is NOT started. A non-blocking info message is shown ("Não identificamos uma marca cadastrada para este domínio. Selecione a marca manualmente.") AND the previously-hidden "Marca Concorrente" `<select>` is revealed as a manual fallback. When the operator picks a brand and submits, the monitor starts via `ApiClient.addToMonitor(url, selectedBrand)` with the same status-aware toasts. The form is never a dead end.
- Uses `addToMonitor` (interval=10, duration=24) so dedup + status feedback stays consistent with the approved button flow. Errors → `toast.error`.
- The standalone brand-add-by-URL form (and its `handleIdentify`/`handleConfirmSave`/`saveBrand`-on-confirm path, identify-form state, engine-override select) was REMOVED from SettingsPage. SettingsPage returns to pure management (toggle active/inactive, delete) plus the marketplace toggles. `ApiClient.saveBrand` remains in client.ts but is no longer called from App.tsx.

**(b) UX-04 — Add-to-Monitor button on 3 surfaces (OPERATOR-APPROVED, unchanged):**
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

**(c) UX-05 — Marketplace toggles (SettingsPage) (OPERATOR-APPROVED, unchanged):**
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

**Task 2 (original `95629a9`):**
```
cd frontend && npx tsc --noEmit && npm run build
# tsc: (none — no errors)
# vite build: ✓ built in 1.48s
```

**Task 2 rework (this commit):**
```
cd frontend && npx tsc --noEmit && npm run build
# tsc: (none — no errors)
# vite build: ✓ built in 732ms
# Chunk size warning (787KB JS) is pre-existing, not from this plan
```

---

## Deviations from Plan

### Operator-directed rework (UX-03)

**0. [Operator feedback] UX-03 moved from a SettingsPage brand-add-by-URL form into an identify-first monitor flow**
- **Found during:** post-checkpoint operator review
- **Issue:** The operator approved flows 2 & 3 but rejected the UX-03 placement. The intended UX is: paste a product link in the monitor form and have the system identify the registered brand automatically (not register a new brand from a store URL).
- **Fix:** Removed the standalone "Adicionar Marca por URL" GlassCard (and its identify/confirm/save state and handlers) from SettingsPage. Reworked the MonitorPage "Monitorar Novo Produto" form: URL is the primary input; on submit, `identifyBrand(url)` resolves the registered brand by normalized-domain match and starts the monitor via `addToMonitor`; when no brand matches, the hidden brand `<select>` is revealed as a manual fallback.
- **Files modified:** `frontend/src/App.tsx` only

### Auto-applied adjustments (flows 2 & 3, approved)

**1. [Rule 2 — Completeness] `handleAddToMonitor` defined per-page rather than as a single hoisted handler**
- **Found during:** Task 2 implementation
- **Issue:** The three target surfaces (SearchPage, CrossMarketplacePage, MonitoredCategoriesPage) are separate top-level components in App.tsx; there is no shared state context between them. Hoisting the handler to `App()` would require threading it down through multiple component props, adding coupling not present in the existing codebase pattern.
- **Fix:** Defined identical `handleAddToMonitor` in each of the 3 page components. (The MonitorPage rework adds a 4th, self-contained `startMonitorForBrand` helper for the identify-first flow.)
- **Files modified:** `frontend/src/App.tsx`

**2. [Correctness] MARKETPLACE_BRAND_KEY map in CrossMarketplacePage**
- **Found during:** Task 2 — wiring CrossMarketplacePage button
- **Issue:** The marketplace column render uses display names ("Mercado Livre", "Netshoes", "Amazon") but `addToMonitor` requires brand_keys (`mercado_livre`, `netshoes`, `amazon`).
- **Fix:** Added `const MARKETPLACE_BRAND_KEY` lookup map before `handleExport`; button onClick derives `brandKey = MARKETPLACE_BRAND_KEY[marketplace]` with a safe lowercase fallback.
- **Files modified:** `frontend/src/App.tsx`

---

## Known Stubs

None — all flows wire to real backend endpoints from Plans 02-04.

---

## Threat Flags

None beyond the plan's threat model (T-40-08 / T-40-09 / T-40-SC). The identify-first monitor flow forwards the URL to `/brands/identify` (dry-run; SSRF mitigated server-side per T-40-09) and only ever calls `addToMonitor` with a `brand_key` from the registered brand list (or operator-selected) — no new network endpoints or trust boundaries introduced. The brand-add-by-URL confirm path (which carried T-40-08) was removed; no client engine value is sent for brand creation anymore.

---

## Task 3: Checkpoint — Flow 1 Re-Verification Required

**Type:** checkpoint:human-verify  
**Gate:** blocking

**Operator status:** Flows 2 (add-to-monitor x3) and 3 (marketplace toggles) are APPROVED and unchanged. Flow 1 (UX-03) was reworked per operator feedback and needs re-verification.

**How to re-verify Flow 1 (UX-03 — identify-first monitor):**

Open the app → "Monitores" tab → "Monitorar Novo Produto":

1. Paste a product URL whose domain matches a registered brand (e.g. a product link from `https://www.hugoboss.com.br`) → submit ("Identificar e Monitorar"). Confirm: a green toast "Adicionado ao monitoramento", a line "Marca identificada: <brand_name>", the product appears in the monitor list, and the URL field clears. Submit the SAME URL again → confirm an info toast "Produto já está em monitoramento" and no duplicate.
2. Paste a product URL whose domain is NOT a registered brand → submit. Confirm: NO monitor is started, a non-blocking message "Não identificamos uma marca cadastrada para este domínio. Selecione a marca manualmente." appears, AND the "Marca Concorrente" select is revealed. Pick a brand → submit → confirm the monitor starts (success/info/reactivated toast as appropriate). The form must not be a dead end.
3. Confirm the "Adicionar Marca por URL" card is GONE from the Marcas tab — that tab now only shows brand management (toggle active/inactive + delete) and the marketplace toggles (flow 3, already approved).

**Resume signal:** Type "approved" or describe any issue (which flow, expected vs actual).

---

## Self-Check

- [x] `frontend/src/api/client.ts` contains `static identifyBrand(` and `static addToMonitor(` (unchanged — client.ts not touched in rework)
- [x] `frontend/src/App.tsx` contains `handleAddToMonitor` — grep confirms 6 matches (3 approved-surface call sites + definitions)
- [x] `frontend/src/App.tsx` contains `ApiClient.addToMonitor` — grep confirms 4 matches (3 approved surfaces + monitor-flow `startMonitorForBrand`)
- [x] `frontend/src/App.tsx` contains `ApiClient.identifyBrand` — grep confirms 1 match (now in MonitorPage)
- [x] `frontend/src/App.tsx` contains `normalizeDomain` — grep confirms 3 matches (1 def + 2 call sites)
- [x] Brand-add-by-URL form removed — `ApiClient.saveBrand` grep confirms 0 matches in App.tsx
- [x] `const VIRTUAL` in App.tsx — grep confirms 0 matches (flow 3 unchanged)
- [x] CategoryPage filter (`l.531`) preserved — grep confirms match
- [x] BannersPage `virtualMarketplaces` preserved — grep confirms match
- [x] Commit `8d28284` exists — verified via git log
- [x] Commit `95629a9` exists — verified via git log
- [x] `npx tsc --noEmit` — passes (no output)
- [x] `npm run build` — passes (built in 732ms)

## Self-Check: PASSED (Tasks 1-2 + UX-03 rework)

Task 3 (human-verify) remains open for Flow 1 re-verification — plan completion and STATE/ROADMAP advance deferred to the orchestrator after operator approval.
