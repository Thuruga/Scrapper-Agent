---
phase: 24-exporta-o-excel-da-busca-por-sku
plan: "03"
subsystem: frontend
tags: [export, excel, selection, modal, cross-marketplace, sku-search]
dependency_graph:
  requires: ["24-02"]
  provides: ["EXPORT-01", "EXPORT-02", "EXPORT-03", "EXPORT-04", "EXPORT-05", "EXPORT-06"]
  affects: [frontend/src/App.tsx, frontend/src/api/client.ts, frontend/src/App.css]
tech_stack:
  added: []
  patterns: [blob-download, Set-based-selection, modal-overlay, stopPropagation-checkbox]
key_files:
  created: []
  modified:
    - frontend/src/api/client.ts
    - frontend/src/App.css
    - frontend/src/App.tsx
decisions:
  - "Selection keyed on item.url (unique per result); Set<string> in component state"
  - "Card checkbox label calls both preventDefault+stopPropagation — no navigation on toggle"
  - "Selected-card colors (0.07/0.25 alpha) deliberately distinct from buybox-winner (0.1/0.3)"
  - "Selection preserved in handleExport finally block; reset only on new search (setResults(null) path)"
  - "Removed pre-existing unused Image import to unblock build (tsc -b noUnusedLocals)"
metrics:
  duration_minutes: 25
  completed_date: "2026-06-15"
  tasks_completed: 2
  tasks_total: 3
  files_modified: 3
---

# Phase 24 Plan 03: Frontend Export Wiring Summary

**One-liner:** Per-card selection checkboxes, global select-all toolbar, and Excel export dialog wired end-to-end to `POST /search/cross-marketplace/export` via blob download.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | ApiClient.exportCrossMarketplace + Phase 24 CSS | c1a4cb9 | frontend/src/api/client.ts, frontend/src/App.css |
| 2 | Wire CrossMarketplacePage — selection, toolbar, dialog, handler | ec58858 | frontend/src/App.tsx |
| 3 | Human-verify checkpoint | auto-approved | — |

---

## What Was Built

**EXPORT-01 — Per-card checkbox overlay**
- Each result card `<a>` gains `position: relative` and a `.card-select-checkbox` `<label>` as its first child
- The label `onClick` calls `e.preventDefault()` + `e.stopPropagation()` so toggling never navigates
- Selected card background/border changes to `rgba(16,185,129,0.07)` / `rgba(16,185,129,0.25)` — distinct from the buybox-winner highlight

**EXPORT-02 — Results-header toolbar**
- Rendered when `results` is non-null, immediately above the marketplace grid
- `.stock-toggle` "Selecionar todos" toggle (`.active` when all items selected)
- `.sku-export-counter` "N selecionado(s)" counter (green via `.has-selection` when N > 0)
- `.btn-excel` "Exportar Excel" button at the right; shows `<RefreshCw animate-spin>` + "Exportando..." while exporting

**EXPORT-03 — Export dialog**
- `.modal-overlay` closes on overlay click; `.modal-content.export-dialog` stops propagation
- "Todos" (`.btn-primary`, always enabled) and "Apenas selecionados (N)" (`.btn-excel`, disabled + opacity 0.4 at N=0)
- "Manter seleção" dismiss link (`.export-dialog-cancel`)

**EXPORT-04/05/06 — ApiClient.exportCrossMarketplace**
- `POST /search/cross-marketplace/export` with `X-API-Key`
- Sends `{ items, search_query?, target_sku }` as JSON
- Reads filename from `Content-Disposition` header (regex `/filename="([^"]+)"/`), fallback `busca_sku.xlsx`
- `blob()` → `window.URL.createObjectURL` → hidden `<a download=filename>` → `click()` → `revokeObjectURL` → `removeChild`
- On non-ok response: reads `data.detail` and throws; frontend catches with `toast.error`

**State management**
- `useState<Set<string>>(new Set())` keyed on `item.url`
- `toggleItem` (immutable Set add/delete via if/else)
- `isAllSelected` computed from `allItems.every(i => selectedItems.has(i.url))`
- `toggleSelectAll` (if isAllSelected → empty Set; else Set of all item.url)
- `setSelectedItems(new Set())` in `handleSearch` alongside `setResults(null)` — resets on new search
- `selectedItems` NOT cleared in `handleExport` finally — selection preserved after export

**CSS added to App.css**
- `.modal-overlay`, `.modal-content`, `.export-dialog`, `.export-dialog-subtitle`
- `.export-dialog-actions`, `.export-dialog-cancel`, `.export-dialog-cancel:hover`
- `.card-select-checkbox`, `.card-select-checkbox input`
- `.sku-export-counter`, `.sku-export-counter.has-selection`
- All using existing CSS variables (`--border`, `--text-muted`, `--text-main`, `--success`)

---

## Verification

- `npx tsc --noEmit` — no type errors
- `npm run build` — production build succeeds (747 kB bundle, chunk size warning is pre-existing)
- Grep checks all pass:
  - `card-select-checkbox` in App.tsx: 1
  - `ApiClient.exportCrossMarketplace` in App.tsx: 1
  - `setShowExportDialog` in App.tsx: 5 (open + 4 close paths)
  - `preventDefault` + `stopPropagation` both present near card checkbox
  - `setSelectedItems(new Set())` in handleSearch reset path: 2
  - All PT-BR strings present verbatim
  - `Check` imported from lucide-react

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ternary expression in toggleItem causing ESLint parse error**
- **Found during:** Task 2 — line 912
- **Issue:** `next.has(url) ? next.delete(url) : next.add(url)` triggered ESLint `no-expressions` rule (expression used as statement)
- **Fix:** Rewrote as explicit `if (next.has(url)) { next.delete(url); } else { next.add(url); }`
- **Files modified:** frontend/src/App.tsx
- **Commit:** ec58858

**2. [Rule 3 - Blocking] Removed pre-existing unused `Image` import blocking production build**
- **Found during:** Task 2 verification — `npm run build` (tsc -b) failed on `Image` declared but never used
- **Issue:** `Image` was imported from lucide-react in the previous commit (8e44386) but never referenced; `tsc -b` with `noUnusedLocals: true` treats it as a hard error
- **Fix:** Removed `Image,` from the lucide-react import block (line 26)
- **Files modified:** frontend/src/App.tsx
- **Commit:** ec58858

**3. [Rule 1 - Bug] Stray closing `}` in App.css after Phase 24 CSS block**
- **Found during:** Task 1 — IDE CSS diagnostic at line 1219
- **Issue:** Edit inadvertently included a second `}` that closed a phantom block after the Phase 24 CSS
- **Fix:** Removed the extra `}`
- **Files modified:** frontend/src/App.css
- **Commit:** c1a4cb9

---

## Manual Verification (Deferred to UAT)

Task 3 (checkpoint:human-verify) was auto-approved per executor directive. The following steps must be verified manually before the milestone is considered done:

1. Start backend and `cd frontend && npm run dev`; run a SKU search (e.g. "polo piquet aramis")
2. Click a card checkbox — confirm NO new tab opens, card border/background changes to green selected state, counter shows "1 selecionado(s)" in green. Click again to deselect.
3. Click "Selecionar todos" — all cards check, counter equals total. Click again — all uncheck, counter "0 selecionado(s)" muted.
4. With 0 selected, click "Exportar Excel" — dialog opens; "Apenas selecionados (0)" greyed/unclickable; "Todos" enabled. Click overlay — dialog closes, selection preserved.
5. Click "Exportar Excel" → "Todos" — button shows spinner + "Exportando...", browser downloads file. Verify filename matches `busca_sku_<query>_<YYYYMMDD_HHMMSS>.xlsx`.
6. Open downloaded file in Excel/LibreOffice — confirm 10 PT-BR columns (Plataforma, Vendedor, Título, Preço, Frete, Preço Total, Frete Grátis, Score de Match, Similar, URL), "Sim"/"Não" booleans, "A calcular" where shipping is null, integer scores, rows match on-screen order.
7. Select a subset, export "Apenas selecionados" — confirm only those rows appear and selection remains after download.
8. (Error path) Stop backend, try export — sonner toast "Erro ao exportar: ..." appears, button returns to idle.

---

## Known Stubs

None. All data flows from the live API response; no placeholder values were introduced.

---

## Threat Flags

No new security surface beyond what the 24-03-PLAN.md threat model already covers (T-24-F1 through T-24-SC). All mitigations implemented:
- T-24-F1: `preventDefault` + `stopPropagation` on checkbox label — present
- T-24-F2: `Content-Disposition` filename read via regex — present
- T-24-F3: `revokeObjectURL` + `removeChild` after click — present
- T-24-F4: `X-API-Key: API_KEY` header in exportCrossMarketplace — present

---

## Self-Check: PASSED

- [x] frontend/src/api/client.ts — exportCrossMarketplace present
- [x] frontend/src/App.css — all 10 new Phase 24 classes present
- [x] frontend/src/App.tsx — all wiring present, tsc clean, build passes
- [x] Commits c1a4cb9 and ec58858 exist in git log
