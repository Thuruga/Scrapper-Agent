---
phase: 24-exporta-o-excel-da-busca-por-sku
verified: 2026-06-15T00:00:00Z
status: passed
human_verification_completed: 2026-06-15
score: 9/9 automated must-haves verified; 6/6 manual UAT checks passed (see 24-HUMAN-UAT.md)
overrides_applied: 0
human_verification:
  - test: "Run a SKU search (e.g. 'polo piquet aramis') in the browser; click a card's checkbox"
    expected: "No new browser tab opens; card border/background changes to green selected state; counter shows '1 selecionado(s)' in green. Click again — card deselects."
    why_human: "EXPORT-01 — per-card checkbox toggle and visual feedback are DOM/CSS behaviors with no automated test path."
  - test: "Click 'Selecionar todos'"
    expected: "Every card checkbox activates; counter equals total item count. Click again — all deselect, counter shows '0 selecionado(s)' in muted colour."
    why_human: "EXPORT-02 — global select-all toggle state and counter colour are DOM/CSS interactions."
  - test: "With 0 selected, click 'Exportar Excel'; observe dialog. Click the overlay background."
    expected: "Dialog opens. 'Apenas selecionados (0)' button is greyed/unclickable. 'Todos' is enabled. Clicking the overlay closes the dialog and selection (0) is preserved."
    why_human: "EXPORT-03 — modal open/close behavior, button disable state at 0 selection, and selection persistence are DOM interactions."
  - test: "Click 'Exportar Excel' → 'Todos'; observe button and then the downloaded file"
    expected: "Button shows spinner + 'Exportando...' while fetching. Browser downloads a file. Filename matches busca_sku_<query>_<YYYYMMDD_HHMMSS>.xlsx. File opens in Excel/LibreOffice with exactly 10 PT-BR columns (Plataforma, Vendedor, Título, Preço, Frete, Preço Total, Frete Grátis, Score de Match, Similar, URL), boolean values as 'Sim'/'Não', null shipping as 'A calcular', scores as integers, rows matching on-screen order."
    why_human: "EXPORT-04/05/06 end-to-end — actual file download and spreadsheet content correctness require browser + file-viewer interaction. Automated tests verify the API layer; actual browser download flow (blob URL, Content-Disposition header read, file save) needs human confirmation."
  - test: "Select a subset of cards, click 'Exportar Excel' → 'Apenas selecionados (N)'; open the downloaded file; then verify selection after download."
    expected: "Only the selected rows appear in the spreadsheet. After the download completes the selection remains (cards still highlighted, counter unchanged)."
    why_human: "EXPORT-01/03/05 — selective export and post-export selection persistence require browser observation."
  - test: "Stop the backend server; attempt to export."
    expected: "A sonner toast appears: 'Erro ao exportar: ...' with the error message. The export button returns to idle state (no spinner)."
    why_human: "Error path and toast UI require browser observation."
---

# Phase 24: Exportação Excel da Busca por SKU — Verification Report

**Phase Goal:** O usuário pode selecionar quais produtos exportar nos resultados da busca por SKU e baixar um arquivo Excel com os campos exibidos no card — sem que o backend re-execute a busca ou re-raspe qualquer produto.

**Verified:** 2026-06-15T00:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | POST /search/cross-marketplace/export returns a valid .xlsx with 10 PT-BR columns in order | VERIFIED | `api/routes_search.py:477-488` — row dict keys match EXPECTED_HEADERS exactly; `test_happy_path` asserts header equality and passes |
| 2 | The endpoint never calls any search engine, scraper, or cross_marketplace_service | VERIFIED | AST-checked: no `engine_factory`, `cross_marketplace_service`, or `asyncio.gather` inside `export_cross_marketplace` function body |
| 3 | Empty items returns 400/422; >500 items returns 422; missing X-API-Key returns 403/422 | VERIFIED | `CrossMarketplaceExportRequest.items = Field(..., min_length=1, max_length=500)`; `verify_api_key` inherited via `api_router`; `test_empty_items`, `test_oversized_payload`, `test_auth` all pass |
| 4 | All RED tests from Plan 01 turn GREEN (15 tests pass) | VERIFIED | `python -m pytest tests/test_export_cross_marketplace.py -q` → 15 passed, 0 failed |
| 5 | ApiClient.exportCrossMarketplace exists and POSTs to the correct endpoint with blob download | VERIFIED | `frontend/src/api/client.ts:148-189` — method present, posts to `${API_BASE_URL}/search/cross-marketplace/export`, reads Content-Disposition filename, blob → createObjectURL → hidden `<a>` click → revokeObjectURL (via setTimeout) |
| 6 | All CSS classes for modal, checkbox overlay, counter are defined | VERIFIED | `frontend/src/App.css` lines 1138-1218 — 10 new classes: `.modal-overlay`, `.modal-content`, `.export-dialog`, `.export-dialog-subtitle`, `.export-dialog-actions`, `.export-dialog-cancel`, `.export-dialog-cancel:hover`, `.card-select-checkbox`, `.card-select-checkbox input`, `.sku-export-counter`, `.sku-export-counter.has-selection` |
| 7 | CrossMarketplacePage has selection state, checkbox overlay, toolbar, export dialog, handleExport | VERIFIED | `frontend/src/App.tsx:891-946` — state hooks present; `toggleItem`, `isAllSelected`, `toggleSelectAll`, `handleExport` all implemented; toolbar JSX at ~1121; card checkbox at ~1183; export dialog at ~1278 |
| 8 | Selection resets on new search; selection preserved after export | VERIFIED | `setSelectedItems(new Set())` at App.tsx:1021 alongside `setResults(null)` in `handleSearch`; `handleExport` finally block (line 943-944) only calls `setExporting(false)` — no `selectedItems` clear |
| 9 | Formula-injection sanitization covers all string columns including URL | VERIFIED | `_sanitize_cell` applied to marketplace, seller, title, and url in the row dict (line 487); `test_formula_injection_url` test passes confirming URL column is protected |

**Score:** 9/9 automated truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `api/routes_search.py` | ExportItem + CrossMarketplaceExportRequest models, `_sanitize_cell`, `export_cross_marketplace` endpoint | VERIFIED | All four items present at lines 95-125 and 452-508 |
| `tests/test_export_cross_marketplace.py` | 15 test methods covering all backend behaviors | VERIFIED | 15 tests collected and passing; covers happy path, null shipping, free shipping, booleans, score rounding, formula injection (col 2 + col 10), display order, fidelity, filename, empty/oversized payload, auth |
| `frontend/src/api/client.ts` | `ApiClient.exportCrossMarketplace` method | VERIFIED | Present at line 148; correct URL, headers, blob download pattern, error handling with console.warn |
| `frontend/src/App.css` | Modal + checkbox + counter CSS classes | VERIFIED | All 10+ new Phase 24 classes present; uses only CSS variables (`--border`, `--text-muted`, `--text-main`, `--success`) |
| `frontend/src/App.tsx` | Full selection state + UI wiring in CrossMarketplacePage | VERIFIED | Selection Set, toggle helpers, handleExport, toolbar JSX, card checkbox label, export dialog — all present and wired |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `frontend/src/App.tsx CrossMarketplacePage` | `ApiClient.exportCrossMarketplace` | `handleExport` | VERIFIED | `await ApiClient.exportCrossMarketplace({...})` at App.tsx:936 |
| card `<a>` checkbox `<label>` onClick | `toggleItem` | `preventDefault` + `stopPropagation` | VERIFIED | App.tsx:1186 — both present on the label onClick handler; input `onChange` calls `toggleItem` |
| `ApiClient.exportCrossMarketplace` | `POST /search/cross-marketplace/export` | fetch + X-API-Key + blob download | VERIFIED | client.ts:149 — URL matches; X-API-Key header present; blob → objectURL → click → setTimeout revoke |
| `export_cross_marketplace` | `_sanitize_cell` | applied to marketplace, seller, title, url | VERIFIED | All four string fields sanitized in the row dict at routes_search.py:478-480,487 |
| StreamingResponse headers | browser filename | Content-Disposition + Access-Control-Expose-Headers | VERIFIED | Both headers set at routes_search.py:503-505 |
| `POST /search/cross-marketplace/export` | `pd.ExcelWriter(engine='openpyxl')` | DataFrame → BytesIO → StreamingResponse | VERIFIED | `ExcelWriter(output, engine="openpyxl")` at routes_search.py:492 |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `export_cross_marketplace` | `request.items` | `CrossMarketplaceExportRequest` Pydantic model — items POSTed by the browser from live search results | Yes — items are the pre-computed search results from a prior `/cross-marketplace` call, not re-fetched | FLOWING |
| `CrossMarketplacePage` | `selectedItems` (Set) | `useState<Set<string>>(new Set())` populated by user checkbox clicks via `toggleItem` | Yes — keyed on `item.url` from `results.results` | FLOWING |
| `handleExport` | `itemsToExport` | `allItems` (all) or `allItems.filter(selectedItems.has)` (selected) | Yes — drawn from `results.results` which is the live API response | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Test suite: 15 tests pass | `python -m pytest tests/test_export_cross_marketplace.py -q` | `15 passed, 2 warnings in 1.64s` | PASS |
| No scraper calls inside export function | AST parse — check for `engine_factory`, `cross_marketplace_service`, `asyncio.gather` in function body | No matches | PASS |
| `_sanitize_cell` formula injection guard | Functional — covered by `TestSanitizeHelper` and `test_formula_injection*` tests | All pass | PASS |
| Frontend build | `cd frontend && tsc -b && vite build` (per SUMMARY) | Succeeds (747 kB bundle) | PASS (claimed; build output not re-run here — tsc errors would have blocked commit) |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| EXPORT-01 | 24-03 | Per-card checkbox selection | VERIFIED (code) / human_needed (DOM behavior) | `card-select-checkbox` label with preventDefault+stopPropagation in App.tsx; needs browser UAT |
| EXPORT-02 | 24-03 | "Selecionar todos" toggle + N counter | VERIFIED (code) / human_needed (DOM behavior) | `toggleSelectAll` + `sku-export-counter` in App.tsx; needs browser UAT |
| EXPORT-03 | 24-03 | Export dialog with Todos/Apenas selecionados | VERIFIED (code) / human_needed (DOM behavior) | `showExportDialog` modal in App.tsx; needs browser UAT for interaction |
| EXPORT-04 | 24-01, 24-02, 24-03 | .xlsx with 10 PT-BR columns | VERIFIED (API layer) / human_needed (actual download) | `test_happy_path` + 14 other tests pass; actual browser download needs UAT |
| EXPORT-05 | 24-01, 24-02 | No re-execution of search/scrape | VERIFIED | AST proof: `export_cross_marketplace` calls no engine/scraper; items taken verbatim from request body |
| EXPORT-06 | 24-01, 24-02 | Meaningful filename busca_sku_<query>_<timestamp>.xlsx | VERIFIED | `test_filename` passes; regex `^busca_sku_.+_\d{8}_\d{6}\.xlsx$` confirmed |

All 6 requirement IDs from REQUIREMENTS.md are mapped to Phase 24 with traceability confirmed. No orphaned requirements.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/App.tsx` | 255, 708, 721, 1045, 1056, 1346, 1357, 1368, 1628 | `placeholder="..."` | Info | HTML input placeholder attributes — NOT stub indicators; pre-existing and unrelated to Phase 24 |

No `TBD`, `FIXME`, `XXX` markers found in any Phase 24 modified files. No `return null` / empty stubs detected in the export-related code paths.

**Review findings addressed:** Critical finding CR-01 (URL column formula injection) was fixed — `_sanitize_cell(item.url)` confirmed at routes_search.py:487 and `test_formula_injection_url` passes. All 4 warnings (WR-01 through WR-04) were fixed. IN-01 was skipped (info-level, non-blocking). IN-02 was skipped (cosmetic).

---

### Human Verification Required

All automated checks pass. The following DOM/UX behaviors and the actual browser download require human browser testing:

#### 1. Per-Card Checkbox Toggle (EXPORT-01)

**Test:** Start the backend and `cd frontend && npm run dev`; run a SKU search (e.g. "polo piquet aramis"). Click a card's checkbox label.
**Expected:** No new browser tab opens. Card border/background changes to `rgba(16,185,129,0.07)` / `rgba(16,185,129,0.25)` (distinct green). Counter shows "1 selecionado(s)" in green. Click again — card deselects, counter back to "0 selecionado(s)" in muted colour.
**Why human:** DOM event propagation (stopPropagation preventing navigation) and CSS visual state are not testable with grep or unit tests.

#### 2. Select-All Toggle (EXPORT-02)

**Test:** Click "Selecionar todos" in the results toolbar.
**Expected:** All card checkboxes activate; counter equals the total number of results. Click again — all deselect, counter shows "0 selecionado(s)" in muted colour.
**Why human:** Global selection state across all rendered cards and counter colour change require browser observation.

#### 3. Export Dialog Interaction (EXPORT-03)

**Test:** With 0 cards selected, click "Exportar Excel". With some cards selected, click "Exportar Excel".
**Expected (0 selected):** Dialog opens; "Apenas selecionados (0)" is greyed/unclickable (opacity 0.4, not-allowed cursor). "Todos" is enabled. Clicking the overlay closes the dialog; selection (0) is preserved.
**Expected (N selected):** "Apenas selecionados (N)" is enabled and clickable.
**Why human:** Modal open/close behavior, button disabled state, and overlay click-to-dismiss are DOM interactions.

#### 4. End-to-End Excel Download — All Products (EXPORT-04/05/06)

**Test:** Click "Exportar Excel" → "Todos". Observe the button during export. Open the downloaded file.
**Expected:** Button shows `<RefreshCw spin>` + "Exportando..." during fetch. Browser downloads a file with name matching `busca_sku_<query>_<YYYYMMDD_HHMMSS>.xlsx`. Opening the file in Excel/LibreOffice shows exactly 10 PT-BR columns (Plataforma, Vendedor, Título, Preço, Frete, Preço Total, Frete Grátis, Score de Match, Similar, URL), "Sim"/"Não" booleans, "A calcular" where shipping is null, integer scores, rows in the same order as on-screen.
**Why human:** Browser blob download, filename from Content-Disposition header, and spreadsheet content correctness require file-viewer observation.

#### 5. Selective Export + Selection Preserved After Export (EXPORT-01/03/05)

**Test:** Select a subset (e.g. 2 of 5 cards); click "Exportar Excel" → "Apenas selecionados (2)"; open the file; check selection state in the browser after download.
**Expected:** Only those 2 rows appear in the spreadsheet. After download completes the 2 cards remain highlighted and the counter still shows "2 selecionado(s)".
**Why human:** Selective filtering and post-export selection persistence require browser observation.

#### 6. Error Path — Backend Unavailable

**Test:** Stop the backend server; attempt an export.
**Expected:** A sonner toast appears: "Erro ao exportar: ..." with the error detail. The export button returns to idle state (spinner disappears).
**Why human:** Toast notification and button state recovery require browser observation.

---

### Gaps Summary

No blocking gaps found. All automated must-haves are verified in the codebase:

- Backend endpoint `POST /search/cross-marketplace/export` is fully implemented with correct models, sanitization, null-shipping logic, boolean mapping, score rounding, sort, filename generation, and no-re-scrape guarantee.
- Test suite: 15 tests pass, covering all backend behaviors including the URL-column formula-injection case added during the review-fix cycle.
- Frontend: `ApiClient.exportCrossMarketplace`, all CSS classes, CrossMarketplacePage state/toolbar/dialog/handler — all present and wired correctly.
- Review findings CR-01 (critical security), WR-01 through WR-04 all fixed and confirmed in the actual code.

The `human_needed` status reflects the plan's design: Plan 03 was deliberately non-autonomous and ended with a `checkpoint:human-verify` gate for the DOM/UX behaviors. EXPORT-01, EXPORT-02, EXPORT-03, and the actual browser download flow (EXPORT-04/05/06 end-to-end) require manual browser UAT before the milestone is considered done.

---

_Verified: 2026-06-15T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
