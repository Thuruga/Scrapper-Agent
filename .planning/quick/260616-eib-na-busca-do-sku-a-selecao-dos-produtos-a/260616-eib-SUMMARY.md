---
status: complete
phase: quick-260616-eib
plan: "01"
subsystem: frontend
tags: [ux, selection-mode, export, cross-marketplace]
dependency_graph:
  requires: []
  provides: [selectionMode-gated-product-selection]
  affects: [frontend/src/App.tsx]
tech_stack:
  added: []
  patterns: [conditional-render-guard, progressive-disclosure]
key_files:
  created: []
  modified: [frontend/src/App.tsx]
decisions:
  - "selectionMode replaces showExportDialog as the sole export-entry-point state; the modal is removed in favor of inline toolbar actions"
  - "Export buttons (Exportar todos / Exportar selecionados) are inline in the toolbar when selectionMode=true, removing one interaction layer"
metrics:
  duration: 8m
  completed: "2026-06-16"
  tasks: 2
  files: 1
---

# Quick Task 260616-eib: selectionMode gate for product selection in Busca por SKU

**One-liner:** Progressive-disclosure export UX — per-card checkboxes and select-all toolbar hidden until user clicks "Exportar Excel", which enters inline selection mode without a modal.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Add selectionMode state and reset wiring | 945844a | frontend/src/App.tsx |
| 2 | Gate toolbar and card selection UI on selectionMode, remove modal | 945844a | frontend/src/App.tsx |

## What Was Built

Replaced the `showExportDialog` boolean (which triggered a modal) with a `selectionMode` boolean (default `false`) in `CrossMarketplacePage`:

**State changes:**
- `showExportDialog` / `setShowExportDialog` removed
- `const [selectionMode, setSelectionMode] = useState(false)` added

**Reset wiring:**
- `handleExport` finally block: resets `selectionMode(false)` + `setSelectedItems(new Set())`
- `handleSearch`: resets `selectionMode(false)` + `setSelectedItems(new Set())`
- `preloadedJobId` useEffect `.then()`: resets both on history load

**Toolbar behavior (`selectionMode=false`):** Renders only the "Exportar Excel" button; `onClick` calls `setSelectionMode(true)` — no modal.

**Toolbar behavior (`selectionMode=true`):** Renders "Selecionar todos" label, `sku-export-counter` span, spacer, then three inline action buttons:
1. "Exportar todos" → `handleExport('all')`, `btn btn-primary`
2. "Exportar selecionados (N)" → `handleExport('selected')`, `btn btn-excel`, disabled + opacity 0.4 when N=0
3. "Cancelar" → `setSelectionMode(false)` + `setSelectedItems(new Set())`, `btn`

**Card UI gating:**
- Background/border selected highlight only applied when `selectionMode && selectedItems.has(item.url)`
- `<label className="card-select-checkbox">` block wrapped in `{selectionMode && (...)}`

**Modal removed:** The entire `{showExportDialog && (...)}` block (previously lines ~1279-1300) deleted.

## Verification

- `npm run build` passes: tsc -b + vite build, 0 type errors
- `grep showExportDialog frontend/src/App.tsx` → 0 matches
- `selectionMode` present in: useState, toolbar conditional, card-highlight guards (x2), card-checkbox render guard, handleExport finally, handleSearch, preloadedJobId useEffect

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or trust-boundary changes.

## Self-Check: PASSED

- [x] `frontend/src/App.tsx` modified
- [x] Commit 945844a exists and contains the changes
- [x] `npm run build` passes
- [x] `showExportDialog` fully removed (0 grep matches)
- [x] All 5 `setSelectionMode` call sites present and correct
