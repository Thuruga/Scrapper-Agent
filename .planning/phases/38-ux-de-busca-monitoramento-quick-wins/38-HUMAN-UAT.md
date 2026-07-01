---
status: pending
phase: 38-ux-de-busca-monitoramento-quick-wins
source: [38-VALIDATION.md, 38-UI-SPEC.md]
created: 2026-07-01
updated: 2026-07-01
---

## Current Test

[run after Wave 2 (Plan 03) is executed — frontend build green first]

> Manual UAT artifact for Phase 38, mirroring the `44-HUMAN-UAT.md` precedent.
> The frontend has NO test runner (confirmed in RESEARCH.md) — these four requirements
> (UX-01, UX-06, UX-07, UX-08) have no automated DOM/viewport/interaction test surface.
> Backend behaviors (UX-02, UX-08 backend trigger, COMP-08) are covered by pytest in Plan 01
> and are NOT retested here. Setup: `cd backend && python main.py` (or the project's run command)
> and `cd frontend && npm run dev`, then open the app in a browser.

## Tests

### 1. UX-01 — Responsive .grid-category at 768px (both screens)

requirement: UX-01
plan: 38-02 Task 1
expected: At exactly 768px viewport width (devtools responsive mode), BOTH the category-monitor screen (`MonitoredCategoriesPage`) and the category-sweep screen (`CategoryPage`) show the sidebar/category-tree column stacked ABOVE the content column, with no horizontal scrollbar on `.grid-category` and no element overlap. If the products modal is opened at 768px, its product grid does not overflow horizontally.
steps:
  1. Set the browser/devtools viewport to 768px width.
  2. Open the category monitor screen — confirm single-column stack, no horizontal scroll.
  3. Open the category-sweep screen — confirm the same.
  4. Open a category's products modal at 768px — confirm no horizontal overflow inside the modal.
result: pending

### 2. UX-06 — Search-history top-right icon + type-scoped badge (both tabs)

requirement: UX-06
plan: 38-02 Task 2
expected: A History icon button is visible top-right (opposite the page title) WITHOUT scrolling on page load, on BOTH the comparativa and SKU search tabs. Clicking it opens/closes the existing history panel. The icon's corner badge shows the count of history entries FOR THAT TAB's type — the comparativa tab and the SKU tab may show DIFFERENT counts (badge must be type-filtered, not the raw total). Tooltip reads "Ver histórico de buscas".
steps:
  1. Open the comparativa search tab — confirm the top-right History icon is visible without scrolling; hover shows tooltip "Ver histórico de buscas".
  2. Click it — the history panel opens; click again — it closes.
  3. Note the badge count on the comparativa icon.
  4. Switch to the SKU search tab — confirm the same icon/behavior; note its badge count.
  5. Confirm the two badge counts reflect each tab's own type-filtered history (they should differ if the underlying history differs by type).
result: pending

### 3. UX-07 — SKU pattern validation + CEP inline on same row

requirement: UX-07
plan: 38-03 Task 1
expected: On the SKU search tab, typing an invalid SKU (wrong prefix or wrong digit count) and blurring the field shows a red inline error with the copy "Formato inválido. Use o padrão ML.05.XXXXXXX (ex: ML.05.0326046)." and the "Buscar em Marketplaces" submit button is disabled. Typing a valid SKU like `ML.05.0326046` clears the error and enables submit. The CEP field renders on the SAME row as the SKU input (matching the comparative search layout) at viewport widths above the 980px collapse breakpoint.
steps:
  1. On the SKU search tab, type `ML.99.123` (invalid) and click elsewhere to blur.
  2. Confirm the red inline error with the exact copy above appears and submit is disabled.
  3. Replace with `ML.05.0326046` (valid) — confirm error clears and submit enables.
  4. Confirm the CEP field is inline (same row) with the SKU input at desktop width.
  5. Confirm submitting with an invalid SKU is blocked (button disabled / no search fires).
result: pending

### 4. UX-08 — Auto-start first sweep sequence (D-05/D-06)

requirement: UX-08
plan: 38-03 Task 2
expected: After clicking "Salvar" in the add-category modal: (1) the modal closes IMMEDIATELY (operator not blocked); (2) the new category row shows a spinner; (3) a success toast "Categoria adicionada. Iniciando primeira varredura…" appears; (4) NO manual "Iniciar" click is needed anywhere; (5) when the background scan finishes, the spinner clears and the products modal opens AUTOMATICALLY within the poll window; (6) on scan failure, the failure toast "Categoria salva, mas a primeira varredura falhou. Tente novamente na lista." appears.
steps:
  1. Open the add-category modal, fill a valid category/brand, click "Salvar".
  2. Confirm the modal closes immediately and the success toast appears.
  3. Confirm the new row shows the spinner and no "Iniciar" button click is required.
  4. Wait for the background scan — confirm the spinner clears and the products modal auto-opens with results.
  5. (Optional negative) Trigger a failing scan (e.g. a brand/URL that yields no products or blocks) — confirm the failure toast copy.
result: pending

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps

_(none yet — populate during UAT execution, mirroring 44-HUMAN-UAT.md's Gaps format)_
