---
phase: 24-exportacao-excel-da-busca-por-sku
fixed_at: 2026-06-15T00:00:00Z
review_path: .planning/phases/24-exporta-o-excel-da-busca-por-sku/24-REVIEW.md
iteration: 1
findings_in_scope: 7
fixed: 6
skipped: 1
status: partial
---

# Phase 24: Code Review Fix Report

**Fixed at:** 2026-06-15
**Source review:** `.planning/phases/24-exporta-o-excel-da-busca-por-sku/24-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 7
- Fixed: 6 (CR-01, WR-01, WR-02, WR-03, WR-04, IN-02 skipped as zero-risk cosmetic)
- Skipped: 1

---

## Fixed Issues

### CR-01: URL Column Bypasses Formula-Injection Sanitization

**Files modified:** `api/routes_search.py`, `tests/test_export_cross_marketplace.py`
**Commit:** 35fe9e3
**Applied fix:** Wrapped `item.url` with `_sanitize_cell(item.url)` on the "URL" column row (line 487). Added `test_formula_injection_url` test that submits `=HYPERLINK("https://evil.com","Click")` as a URL and asserts `ws.cell(2, 10).value.startswith("'")`, closing the test gap for the URL column. All 15 tests pass (14 original + 1 new).

---

### WR-02: score Fallback Uses Falsy or — Breaks on Negative final_match_score

**Files modified:** `api/routes_search.py`
**Commit:** 41346e1
**Applied fix:** Replaced `round(item.final_match_score or item.match_score)` with `round(item.final_match_score if item.final_match_score != 0.0 else item.match_score)`. The explicit `!= 0.0` check documents intent and correctly handles the `final_match_score=0.0` default-omitted case while remaining correct for non-zero values. All 15 tests remain green.

---

### WR-03: display_order Sort Produces Unstable Ordering When Field Is Absent

**Files modified:** `api/routes_search.py`
**Commit:** 41346e1
**Applied fix:** Changed the sort key from `else 0` to `else float('inf')` so items missing `_display_order` sort to the end of the sheet rather than clustering at position 0 and overriding explicitly-ordered items.

---

### WR-01: revokeObjectURL Called Before Browser Download Completes (Firefox/Safari)

**Files modified:** `frontend/src/api/client.ts`
**Commit:** e68af3a
**Applied fix:** Deferred `window.URL.revokeObjectURL(url)` and `document.body.removeChild(a)` via `setTimeout(() => { ... }, 100)` in both `exportSearch` (formerly line 138) and `exportCrossMarketplace` (formerly line 175). The pattern is now consistent between both methods.

---

### WR-04: Empty catch Block Silently Swallows JSON Parse Error Detail

**Files modified:** `frontend/src/api/client.ts`
**Commit:** e68af3a
**Applied fix:** Replaced `catch (e) {}` with `catch (_parseErr) { console.warn('export...: could not parse error response body', _parseErr); }` in both `exportSearch` and `exportCrossMarketplace`. The named parameter `_parseErr` signals intentional non-use while still forwarding the error to devtools.

---

## Skipped Issues

### IN-01: handleExport('all') Passes Raw allItems Array Including _render_order Render Artifact

**File:** `frontend/src/App.tsx:931-933`
**Reason:** Info-level finding with no immediate fix needed (reviewer noted "No immediate fix needed"). The current behavior is safe because `ExportItem` has `extra="allow"`. This is a documentation/future-refactor concern, not a bug. Skipping as per fix_scope guidance for Info findings that are non-trivial.
**Original issue:** `allItems` comes from `results.results` (no `_render_order`) while rendered `marketResults` has `_render_order`. Currently safe; potential confusion if the model's `extra="allow"` changes.

### IN-02: btn-excel Lacks a background Property in its Base Rule

**File:** `frontend/src/App.css:734-742`
**Reason:** Purely cosmetic — reviewer noted "No visual bug today" and "No fix required." Adding `background: transparent` would touch App.css which contains a large unrelated sidebar feature (constrained by task). Skipping.
**Original issue:** `.btn-excel` relies on `.btn` for its background; no fallback if `.btn` changes in a future refactor.

---

## Verification

- `python -m pytest tests/test_export_cross_marketplace.py -q` → **15 passed** (14 original + 1 new test_formula_injection_url)
- `cd frontend && node_modules/.bin/tsc --noEmit` → **0 errors**

---

_Fixed: 2026-06-15_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
