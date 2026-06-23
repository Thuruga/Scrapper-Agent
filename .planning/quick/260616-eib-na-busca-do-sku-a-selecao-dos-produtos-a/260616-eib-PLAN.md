---
phase: quick-260616-eib
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: [frontend/src/App.tsx]
autonomous: true
requirements: [QUICK-260616-EIB]
must_haves:
  truths:
    - "On a fresh search or history load, no per-card selection checkboxes are visible and the toolbar shows only the 'Exportar Excel' button"
    - "Clicking 'Exportar Excel' enters selection mode (checkboxes + select-all + export actions appear) and does NOT open a modal"
    - "In selection mode the user can pick products and click 'Exportar selecionados (N)' or 'Exportar todos'"
    - "Clicking 'Cancelar' exits selection mode and clears the current selection"
    - "After an export finishes, selection mode is reset and selection is cleared"
    - "The old showExportDialog modal no longer exists"
  artifacts:
    - path: "frontend/src/App.tsx"
      provides: "CrossMarketplacePage with selectionMode-gated product selection UI"
      contains: "selectionMode"
  key_links:
    - from: "Exportar Excel button"
      to: "setSelectionMode(true)"
      via: "onClick"
      pattern: "setSelectionMode\\(true\\)"
    - from: "card-select-checkbox render"
      to: "selectionMode"
      via: "conditional render guard"
      pattern: "selectionMode &&"
---

<objective>
In the "Busca por SKU" (cross-marketplace) tab, hide product-selection UI until the user explicitly opts into it. Today the per-card checkboxes and "Selecionar todos" toolbar are always visible, confusing users about what the selection means.

Introduce a `selectionMode` boolean (default `false`). When off, only an "Exportar Excel" button shows and clicking it turns selection mode ON (no modal). When on, per-card checkboxes, "Selecionar todos", a counter, and inline "Exportar todos" / "Exportar selecionados (N)" / "Cancelar" actions appear. The redundant `showExportDialog` modal is removed entirely.

Purpose: Make the selection workflow discoverable and unambiguous — selection only matters after the user chooses to export.
Output: Modified `frontend/src/App.tsx` (CrossMarketplacePage component only).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

# The single file to modify. Focus on CrossMarketplacePage (starts line 885).
@frontend/src/App.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add selectionMode state and reset wiring</name>
  <files>frontend/src/App.tsx</files>
  <action>
In CrossMarketplacePage, replace the `showExportDialog` state (line ~892) with a new state `selectionMode` initialized to `false` (i.e. delete the `showExportDialog`/`setShowExportDialog` useState line and add `const [selectionMode, setSelectionMode] = useState(false);`). The `showExportDialog` state must no longer exist anywhere.

Update `handleExport` (lines ~929-946): remove the `setShowExportDialog(false)` line at the top (~line 930). In the `finally` block (lines ~943-945), alongside `setExporting(false)`, also call `setSelectionMode(false)` and `setSelectedItems(new Set())` so a completed export exits selection mode and clears the selection.

Update `handleSearch` (lines ~1014-1033): right after the existing `setSelectedItems(new Set());` at line ~1021, add `setSelectionMode(false);` so a new search resets selection mode.

Update the `preloadedJobId` useEffect (lines ~948-957): inside the `.then(...)` callback that loads history results, add `setSelectionMode(false);` and `setSelectedItems(new Set());` so loading a history job starts outside selection mode with no selection.

Do not touch toggleItem, isAllSelected, toggleSelectAll, the shipping logic, or any other state.
  </action>
  <verify>
    <automated>cd frontend && npm run build</automated>
  </verify>
  <done>`selectionMode` state exists (default false); `showExportDialog`/`setShowExportDialog` removed from state and handleExport; handleExport finally resets selectionMode + selectedItems; handleSearch and the preloadedJobId useEffect both reset selectionMode (and useEffect clears selection). `npm run build` (tsc -b + vite build) passes with no type errors.</done>
</task>

<task type="auto">
  <name>Task 2: Gate the toolbar and card selection UI on selectionMode, remove the modal</name>
  <files>frontend/src/App.tsx</files>
  <action>
Rework the export toolbar (lines ~1121-1144) to branch on `selectionMode`:
- When `selectionMode` is FALSE: render ONLY the "Exportar Excel" button. Reuse the existing `btn btn-excel` button (same `disabled={exporting}` and the same Exportando.../FileSpreadsheet label content), but change its onClick to `() => setSelectionMode(true)` (NOT `setShowExportDialog`). Do NOT render the "Selecionar todos" label or the `sku-export-counter` span in this state.
- When `selectionMode` is TRUE: render the full selection toolbar — the existing "Selecionar todos" label (lines ~1123-1129, using `isAllSelected`/`toggleSelectAll`), the `sku-export-counter` span (lines ~1130-1132), the `flex:1` spacer, and THREE action buttons:
  1. "Exportar todos" → `onClick={() => handleExport('all')}`, `disabled={exporting}`. Reuse `btn btn-primary`.
  2. "Exportar selecionados ({selectedItems.size})" → `onClick={() => handleExport('selected')}`, `disabled={exporting || selectedItems.size === 0}`. Reuse `btn btn-excel` (carry over the `opacity:0.4/cursor:not-allowed` style when size===0, as the old modal did).
  3. "Cancelar" → `onClick={() => { setSelectionMode(false); setSelectedItems(new Set()); }}`, `disabled={exporting}`. Reuse `btn` (plain).
  Keep the existing Exportando.../FileSpreadsheet spinner pattern on the export buttons if convenient, but it is acceptable to use plain text labels for the three inline actions.

Gate the per-card selection UI on `selectionMode`:
- The card background/border "selected" highlight (lines ~1166-1182): only apply the green selected styling when `selectionMode` is true. When `selectionMode` is false, fall back to the existing buybox/default styling (i.e. ignore `selectedItems.has(item.url)` for both `background` and `border`). When true, keep the current behavior exactly.
- The per-card `<label className="card-select-checkbox">` block (lines ~1184-1197): wrap it so it only renders when `selectionMode` is true (e.g. `{selectionMode && (<label ...>...</label>)}`). Keep its existing onClick/toggleItem/checked logic unchanged.

Remove the `showExportDialog` modal entirely (lines ~1279-1300) — delete the whole `{showExportDialog && (...)}` block. Its "Todos"/"Apenas selecionados" choices are now the inline "Exportar todos"/"Exportar selecionados" buttons.

Do NOT modify the price display, "Calcular Frete" button, shipping UI (lines ~1217-1262), or the Mercado Livre/Netshoes/Amazon grouping/sort logic.
  </action>
  <verify>
    <automated>cd frontend && npm run build</automated>
  </verify>
  <done>Toolbar renders only "Exportar Excel" (which sets selectionMode=true, opens no modal) when selectionMode is false, and shows "Selecionar todos" + counter + "Exportar todos"/"Exportar selecionados (N)"/"Cancelar" when true. "Exportar selecionados" is disabled when nothing is selected; "Cancelar" exits selection mode and clears selection. Per-card checkboxes and the selected-highlight only appear in selection mode. The showExportDialog modal block is gone. `npm run build` passes.</done>
</task>

</tasks>

<verification>
- `cd frontend && npm run build` succeeds (runs `tsc -b && vite build` — full TypeScript typecheck + production build). No type errors, no references to `showExportDialog`/`setShowExportDialog` remain.
- Grep `frontend/src/App.tsx` for `showExportDialog` returns zero matches.
- Grep for `selectionMode` shows: the useState declaration, the toolbar conditional, the card-highlight guards, the card-checkbox render guard, and the resets in handleSearch, the preloadedJobId useEffect, and handleExport's finally.
</verification>

<success_criteria>
- Default state (fresh load, after a new search, after loading a history job): no per-card checkboxes, no selected-highlight, toolbar shows only "Exportar Excel".
- Clicking "Exportar Excel" enters selection mode (checkboxes + select-all + counter + three actions appear) WITHOUT opening any modal.
- "Exportar todos" exports all; "Exportar selecionados (N)" exports only selected and is disabled when N=0; "Cancelar" exits selection mode and clears the selection.
- After any export completes, selection mode and selection are reset.
- The `showExportDialog` modal and state are fully removed.
- Only `frontend/src/App.tsx` changed; no backend, no new deps, no changes to SearchPage/comparativa or shipping UI.
- `npm run build` passes.
</success_criteria>

<output>
Create `.planning/quick/260616-eib-na-busca-do-sku-a-selecao-dos-produtos-a/260616-eib-SUMMARY.md` when done
</output>
