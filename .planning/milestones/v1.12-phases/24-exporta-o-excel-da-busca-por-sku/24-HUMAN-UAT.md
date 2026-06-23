---
status: complete
phase: 24-exporta-o-excel-da-busca-por-sku
source: [24-VERIFICATION.md]
started: 2026-06-15
updated: 2026-06-15
---

## Current Test

[all complete — user confirmed all actions manually on 2026-06-15]

## Tests

### 1. Per-card checkbox toggle (EXPORT-01)
expected: Run a SKU search (e.g. "polo piquet aramis"); click a card's checkbox. No new browser tab opens; card border/background changes to green selected state; counter shows "1 selecionado(s)" in green. Click again — card deselects.
result: pass

### 2. Select-all toggle (EXPORT-02)
expected: Click "Selecionar todos". Every card checkbox activates; counter equals total item count. Click again — all deselect, counter shows "0 selecionado(s)" in muted colour.
result: pass

### 3. Export dialog disable + overlay dismiss (EXPORT-03)
expected: With 0 selected, click "Exportar Excel". Dialog opens; "Apenas selecionados (0)" is greyed/unclickable; "Todos" is enabled. Click the overlay background — dialog closes and selection (0) is preserved.
result: pass

### 4. End-to-end download "Todos" (EXPORT-04/05/06)
expected: Click "Exportar Excel" → "Todos". Button shows spinner + "Exportando..." while fetching. Browser downloads a file named busca_sku_<query>_<YYYYMMDD_HHMMSS>.xlsx. File opens in Excel/LibreOffice with exactly 10 PT-BR columns (Plataforma, Vendedor, Título, Preço, Frete, Preço Total, Frete Grátis, Score de Match, Similar, URL), booleans as "Sim"/"Não", null shipping as "A calcular", scores as integers, rows matching on-screen order.
result: pass

### 5. Selective export + selection persistence (EXPORT-01/03/05)
expected: Select a subset of cards, click "Exportar Excel" → "Apenas selecionados (N)"; open the downloaded file. Only the selected rows appear. After download completes the selection remains (cards still highlighted, counter unchanged).
result: pass

### 6. Export error path (UI feedback)
expected: Stop the backend server; attempt to export. A sonner toast appears: "Erro ao exportar: ..." with the error message. The export button returns to idle state (no spinner).
result: pass

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

None — all 6 manual UAT checks passed (user confirmed manual testing of all actions on 2026-06-15).
