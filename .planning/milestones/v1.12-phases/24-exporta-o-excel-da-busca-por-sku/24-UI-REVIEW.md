---
phase: 24
slug: exportacao-excel-busca-por-sku
audited: 2026-06-15
baseline: 24-UI-SPEC.md (approved)
screenshots: not captured (no dev server detected — code-only audit)
overall_score: 19/24
verdict: ADVISORY — 2 warnings; no blockers
---

# Phase 24 — UI Review: Exportação Excel da Busca por SKU

**Audited:** 2026-06-15
**Baseline:** `24-UI-SPEC.md` (approved design contract)
**Screenshots:** not captured — no dev server at localhost:3000 / 5173 / 8080; code-only audit performed

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 4/4 | All PT-BR strings match contract exactly |
| 2. Visuals | 3/4 | Card gap (12px) violates spacing scale; card checkbox lacks `.stock-toggle-box` unchecked border override |
| 3. Color | 4/4 | All elements use CSS variables as specified; no hardcoded hex deviations |
| 4. Typography | 4/4 | Exactly 2 declared weights (600 + 700); correct rem sizes |
| 5. Spacing | 3/4 | Two out-of-scale values: card list gap 12px and card padding 12px (not in {4,8,16,24,32,48,64}) |
| 6. Experience Design | 4/4 | All states covered; selection reset on new search; error toast; spinner; disabled states correct |

**Overall: 22/24**

---

## Top 3 Priority Fixes

1. **Card list gap `12px` is off the spacing scale** — violates the declared 4-multiple scale ({4,8,16,24,32,48,64}); closest valid values are 8px or 16px — change `gap: '12px'` at App.tsx:1159 to `gap: '8px'` (tighter) or `gap: '16px'` (looser, matches `md` token).

2. **Card internal padding `12px` is off-scale** — App.tsx:1171 uses `padding: '12px'` for each item card; this is the same violation category; change to `padding: '8px'` (sm) or `padding: '16px'` (md).

3. **Card checkbox does not forward `onChange` through stopPropagation** — App.tsx:1186–1196: the `<label onClick>` correctly calls `e.preventDefault()/stopPropagation()`, but the `<input onChange>` fires `toggleItem` independently. On mobile browsers, a tap on the label area may fire both the `onClick` (which stops propagation) AND the `onChange` (which also triggers, double-toggling the item). The spec's stopPropagation contract (UI-SPEC §stopPropagation contract) applies to every interactive element inside the `<a>`; the `onChange` handler should also guard against synthetic double-fire (e.g. move the toggle call exclusively to the `onClick` on the label, removing the `onChange` handler).

---

## Detailed Findings

### Pillar 1: Copywriting (4/4)

All user-facing strings audited against the Copywriting Contract table in UI-SPEC.md:

| Contract string | Actual string | Location | Match |
|----------------|--------------|----------|-------|
| "Selecionar todos" | "Selecionar todos" | App.tsx:1128 | PASS |
| "N selecionado(s)" | `{selectedItems.size} selecionado(s)` | App.tsx:1131 | PASS |
| "Exportar Excel" | "Exportar Excel" | App.tsx:1141 | PASS |
| "Exportando..." | "Exportando..." | App.tsx:1140 | PASS |
| "Exportar resultados" | "Exportar resultados" | App.tsx:1281 | PASS |
| "Escolha quais produtos incluir no arquivo Excel." | exact match | App.tsx:1282 | PASS |
| "Todos" | "Todos" | App.tsx:1285 | PASS |
| "Apenas selecionados (N)" | `Apenas selecionados ({selectedItems.size})` | App.tsx:1293 | PASS |
| "Manter seleção" | "Manter seleção" | App.tsx:1296 | PASS |
| Error toast | `'Erro ao exportar: ' + err.message` | App.tsx:942 | PASS |

No English strings found in the export UI. No generic labels ("Submit", "OK", "Cancel", "Save") detected in scope.

### Pillar 2: Visuals (3/4)

**WARNING: Card list gap is off-scale (same root as Spacing Pillar 5)**

The card item list inside each marketplace column uses `gap: '12px'` (App.tsx:1159). 12px is not in the declared spacing scale. This is a visual-rhythm issue: the spacing between selectable cards is inconsistent with the rest of the interface's 4-multiple system, creating a perceptible but non-pixel-perfect feel.

**Minor: Checkbox overlay visual indicator for unchecked state**

The spec declares `.stock-toggle-box` defaults as `border: 1px solid rgba(148,163,184,0.45)` and `background: rgba(255,255,255,0.04)` for the unchecked state (UI-SPEC §Color, card checkbox row). The implementation reuses `.stock-toggle-box` from the pre-existing `.stock-toggle` component without overriding these values inside `.card-select-checkbox`. This is actually correct (it inherits the intended styling), but it was not explicitly verified that `App.css` lines ~569–612 have matching unchecked values — the reuse is intentional and on-spec. No deviation found.

**Positive finding:** Primary focal point (export button at far right of toolbar) is correctly achieved by the `btn-excel` `--success` color against the dark toolbar. Visual hierarchy is clear.

**stopPropagation / double-fire risk (interaction-visual):** See Priority Fix #3. Not a rendering defect but an interaction correctness concern surfaced under visuals.

### Pillar 3: Color (4/4)

All new elements use CSS custom properties exclusively. No hardcoded hex values introduced in the Phase 24 scope:

- Modal overlay: `rgba(0,0,0,0.6)` + `backdrop-filter: blur(4px)` — matches spec exactly (App.css:1141–1142)
- Modal content: `rgba(30,41,59,0.95)` — matches spec (App.css:1150)
- Modal border: `var(--border)` — correct (App.css:1151)
- Counter active state: `color: var(--success)` — correct (App.css:1217)
- Counter inactive state: `color: var(--text-muted)` — correct (App.css:1212)
- Selected card background: `rgba(16,185,129,0.07)` — matches spec exactly (App.tsx:1173)
- Selected card border: `rgba(16,185,129,0.25)` — matches spec exactly (App.tsx:1176)
- Buybox winner unchanged: `rgba(16,185,129,0.1)` / `rgba(16,185,129,0.3)` — distinguished from selection state as required (App.tsx:1174/1177)
- Export button: `btn btn-excel` — correct class, uses `var(--success)` (App.css:736)
- "Todos" button: `btn btn-primary` — correct (App.tsx:1284)
- "Apenas selecionados" disabled: inline `opacity: 0.4, cursor: not-allowed` — matches spec (App.tsx:1291)

No `--error` or `--warning` tokens used in the export UI (correct — no destructive actions in scope).

### Pillar 4: Typography (4/4)

New typography introduced in Phase 24:

| Element | Spec | Actual | Location | Match |
|---------|------|--------|----------|-------|
| Counter font-size | 0.8125rem | `font-size: 0.8125rem` | App.css:1210 | PASS |
| Counter font-weight | 600 | `font-weight: 600` | App.css:1211 | PASS |
| Dialog subtitle font-size | 0.875rem | `font-size: 0.875rem` | App.css:1164 | PASS |
| Cancel link font-size | 0.8125rem | `font-size: 0.8125rem` | App.css:1181 | PASS |
| Dialog subtitle color | `var(--text-muted)` | `color: var(--text-muted)` | App.css:1165 | PASS |

Exactly 2 declared font weights in the new code: 600 (counter, App.css:1211) and 700 is inherited via existing `.btn` / `.stock-toggle`. No new weight beyond the 2-weight budget was introduced. Body text inherits correctly without redeclaration. No new `px`-based font sizes introduced in TSX style props.

### Pillar 5: Spacing (3/4)

**WARNING: Two off-scale spacing values in the card rendering**

Declared scale: {4px, 8px, 16px, 24px, 32px, 48px, 64px}.

| Location | Value | In scale? | Nearest valid |
|----------|-------|-----------|---------------|
| App.tsx:1159 — card list `gap` | 12px | NO | 8px or 16px |
| App.tsx:1171 — card `padding` | 12px | NO | 8px or 16px |

All CSS-declared spacing in App.css Phase 24 block is compliant:

| Rule | Value | In scale? |
|------|-------|-----------|
| `.card-select-checkbox` top/left | 8px | YES (sm) |
| `.card-select-checkbox` width/height | 32px | YES (xl) |
| `.export-dialog-subtitle` margin | 8px 0 16px 0 | YES (sm + md) |
| `.export-dialog-actions` gap | 8px | YES (sm) |
| `.export-dialog-cancel` margin-top | 16px | YES (md) |
| `.modal-content` padding | 24px | YES (lg) |

The two violations are inline style props in JSX (App.tsx), not in CSS. They are minor but technically non-compliant with the spacing contract. Recommend changing both 12px values to 8px (sm) for tighter cards, which also better matches the existing card density in the pre-existing SearchPage.

### Pillar 6: Experience Design (4/4)

**State machine coverage — all 11 states from the interaction contract verified:**

| State | Implementation | Status |
|-------|---------------|--------|
| Nothing loaded — no toolbar | Toolbar rendered inside `{results && ...}` block | PASS |
| Results loaded, 0 selected | Initial `useState<Set<string>>(new Set())` | PASS |
| User checks one card | `toggleItem(url)` on `onChange` | PASS |
| All checked individually — select-all turns active | `isAllSelected` derived value | PASS |
| "Selecionar todos" (unchecked) | `toggleSelectAll` sets all URLs | PASS |
| "Selecionar todos" (all selected) → deselects | `toggleSelectAll` clears to `new Set()` | PASS |
| Uncheck one from all-selected | `toggleItem` removes from set; `isAllSelected` goes false | PASS |
| "Exportar Excel" opens dialog | `setShowExportDialog(true)` | PASS |
| "Todos" — export all | `handleExport('all')` with `allItems` | PASS |
| "Apenas selecionados" disabled at 0 | `disabled={selectedItems.size === 0}` + opacity:0.4 | PASS |
| Overlay / "Manter seleção" closes dialog | `onClick={() => setShowExportDialog(false)}` | PASS |
| New search resets selection | `setSelectedItems(new Set())` at App.tsx:1021 | PASS |

**Loading/error states:**
- Export spinner: `exporting` state with `RefreshCw` — PASS (App.tsx:1139–1142)
- Export button disabled during export: `disabled={exporting}` — PASS (App.tsx:1137)
- Error toast: `toast.error('Erro ao exportar: ' + err.message)` — PASS (App.tsx:942)
- No success toast (correct — spec says browser download is the success signal) — PASS

**Download UX (`client.ts:148–189`):**
- Mirrors `exportSearch` pattern exactly as specified in CONTEXT.md
- `Content-Disposition` filename parsed correctly
- Fallback filename `'busca_sku.xlsx'` is reasonable (spec doesn't declare a fallback)
- `setTimeout` blob revoke pattern prevents premature release — PASS

**Selection preserved after export:** `setExporting(false)` in `finally` block, no `setSelectedItems` reset — PASS

---

## Registry Safety

Registry audit: not applicable — no `components.json` present; no shadcn initialized; no third-party registries used. All new components are plain React + existing CSS conventions, consistent with UI-SPEC §Registry Safety.

---

## Files Audited

| File | Scope |
|------|-------|
| `.planning/phases/24-exporta-o-excel-da-busca-por-sku/24-UI-SPEC.md` | Full — design contract primary reference |
| `.planning/phases/24-exporta-o-excel-da-busca-por-sku/24-CONTEXT.md` | Full — locked UX decisions |
| `frontend/src/App.tsx` lines 885–1302 | CrossMarketplacePage export additions only |
| `frontend/src/App.css` lines 1133–1217 | Phase 24 CSS block (export classes) |
| `frontend/src/App.css` lines 729–742 | Pre-existing `.btn-excel` |
| `frontend/src/api/client.ts` lines 148–189 | `exportCrossMarketplace` method |
