---
phase: 24-exportacao-excel-da-busca-por-sku
reviewed: 2026-06-15T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - api/routes_search.py
  - tests/test_export_cross_marketplace.py
  - frontend/src/api/client.ts
  - frontend/src/App.tsx
  - frontend/src/App.css
findings:
  critical: 1
  warning: 4
  info: 2
  total: 7
status: issues_found
---

# Phase 24: Code Review Report

**Reviewed:** 2026-06-15T00:00:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

The phase-24 export feature (POST `/search/cross-marketplace/export`) is broadly correct in structure. The no-re-scrape guarantee (EXPORT-05), Pydantic payload limits, PT-BR column names, boolean/score mapping, and the `_display_order` alias handling all work as documented. The `_sanitize_cell` helper correctly guards formula injection for the string columns it is applied to. Auth is inherited through the `api_router` dependency chain and is not missing.

Two issues require attention before shipping: a formula-injection gap in the URL column (Critical) and a race-condition pattern in the blob-download helpers that will cause silent download failures on Firefox/Safari under load (Warning). Three additional warnings cover a fragile score-fallback operator, an unstable sort edge case, and an empty catch block that swallows error detail.

---

## Critical Issues

### CR-01: URL Column Bypasses Formula-Injection Sanitization

**File:** `api/routes_search.py:488`

**Issue:** Every string column written to Excel goes through `_sanitize_cell` — except `"URL"`. Since the URL value is client-supplied (received verbatim from the browser payload), a crafted request can submit a URL starting with `=`, `+`, `-`, or `@` (e.g., `=HYPERLINK("https://evil.com","Click")`). This value will be written as an Excel formula, not a text literal. All other injection guards in the file become irrelevant if the URL column is unguarded because spreadsheet users typically open URLs by clicking cells.

```python
# Current — line 488 (unguarded):
"URL": item.url,

# Fix — wrap with _sanitize_cell:
"URL": _sanitize_cell(item.url),
```

The corresponding test `test_formula_injection` (tests/test_export_cross_marketplace.py:208) only exercises column 2 ("Vendedor") and does not assert column 10 ("URL"), so this gap is not caught by the existing test suite. A companion test case should be added:

```python
item = {**ITEM_BASE, "url": "=HYPERLINK(\"https://evil.com\",\"Click\")"}
# assert ws.cell(2, 10).value.startswith("'")
```

---

## Warnings

### WR-01: `revokeObjectURL` Called Before Browser Download Completes (Firefox/Safari)

**File:** `frontend/src/api/client.ts:138` and `frontend/src/api/client.ts:175`

**Issue:** Both `exportSearch` and `exportCrossMarketplace` revoke the object URL synchronously immediately after `a.click()`:

```ts
a.click();
window.URL.revokeObjectURL(url);  // revoked before download dialog has opened
document.body.removeChild(a);
```

Chromium copies the blob reference before the URL is revoked and handles this safely. Firefox and Safari, however, may begin resolving the blob URL asynchronously after the click event returns, which causes a silent download failure (the download dialog appears briefly then shows "download failed" or silently produces a 0-byte file). This has been a long-standing cross-browser incompatibility with the immediate-revoke pattern.

**Fix:** Defer revocation by one event-loop tick using `setTimeout`:

```ts
a.click();
// Allow the browser to initiate the download before releasing the blob URL.
setTimeout(() => {
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}, 100);
```

This fix should be applied to both `exportSearch` (line 138) and `exportCrossMarketplace` (line 175).

---

### WR-02: `score` Fallback Uses Falsy `or` — Breaks on Negative `final_match_score`

**File:** `api/routes_search.py:465`

**Issue:**

```python
score = round(item.final_match_score or item.match_score)
```

The intent (per test at line 196) is: "if `final_match_score` is 0, fall back to `match_score`." The `or` operator short-circuits on any falsy value. For floats, `0.0` is falsy, so the fallback fires correctly for zero. However, if a future scoring engine returns a legitimately negative `final_match_score` (e.g., `-1.0` as a sentinel for "no match"), the value is truthy and will be used directly — this is correct behavior. Conversely, if someone passes `final_match_score=0.0` intending to express "explicitly scored zero", the fallback to `match_score` overrides that intent.

More concretely: `ExportItem` declares `final_match_score: float = 0.0` as a default, so a client that omits the field entirely (or passes `0.0`) will silently get `match_score` used instead. This may produce unexpected values in the exported sheet when both scores are populated.

**Fix:** Use an explicit zero-check to document intent:

```python
score = round(item.final_match_score if item.final_match_score != 0.0 else item.match_score)
```

---

### WR-03: `display_order` Sort Produces Unstable Ordering When Field Is Absent

**File:** `api/routes_search.py:458-461`

**Issue:**

```python
sorted_items = sorted(
    request.items,
    key=lambda i: i.display_order if i.display_order is not None else 0,
)
```

Items missing `_display_order` (which Pydantic deserializes to `None`) all receive sort key `0`. Python's `sorted()` is stable, so their relative order is preserved from `request.items`, which is the JSON array order. This is acceptable in the common case where the frontend always populates `_display_order` via `withDisplayOrder`. However, if any client omits the field for only some items (partial population), those items all cluster at the front of the sheet (key=0), overriding items with explicit `_display_order=1`, `2`, etc. that should precede them.

A more defensive key would be:

```python
key=lambda i: i.display_order if i.display_order is not None else float('inf'),
```

This pushes unordered items to the end rather than competing with position 0.

---

### WR-04: Empty `catch` Block Silently Swallows JSON Parse Error Detail

**File:** `frontend/src/api/client.ts:157` (and symmetrically at line 120 in `exportSearch`)

**Issue:**

```ts
try {
  const data = await response.json();
  if (data.detail) errorMsg = data.detail;
} catch (e) {}   // completely silent
```

When the error response body cannot be parsed as JSON (e.g., the backend returns a plain-text 500 or a proxy returns an HTML error page), the catch block suppresses the parse error with no logging. The thrown `Error` will carry only `"Export failed: 500"` instead of the actual error detail. This makes production debugging significantly harder — operators will only see the HTTP status code.

**Fix:**

```ts
} catch (_parseErr) {
  // Non-JSON error body; fall through with the status-based message.
  console.warn('exportCrossMarketplace: could not parse error response body', _parseErr);
}
```

---

## Info

### IN-01: `handleExport('all')` Passes Raw `allItems` Array Including `_render_order` Render Artifact

**File:** `frontend/src/App.tsx:931-933`

**Issue:** When `mode === 'all'`, `itemsToExport` is `allItems` — the same array that was previously augmented with `_render_order` at render time (line 1149: `{ ...r, _render_order: r._display_order ?? index }`). However, `allItems` is drawn directly from `results.results`, not from the rendered `marketResults` arrays. The `_render_order` property is only added inside the render closure. So `allItems` does not carry `_render_order` — it carries only `_display_order` (set by `withDisplayOrder` on search results). This is currently safe because the backend's `ExportItem` model has `extra="allow"`, so extra fields are accepted and ignored. But if someone adds a property to `allItems` in the future and expects it to be excluded, the `extra="allow"` on the Pydantic model will silently accept and drop it.

No immediate fix needed; noting as a potential confusion point between `allItems` (raw) and `marketResults` (render-decorated).

---

### IN-02: `btn-excel` Lacks a `background` Property in its Base Rule

**File:** `frontend/src/App.css:734-742`

**Issue:**

```css
.btn-excel {
  border-color: rgba(16, 185, 129, 0.55);
  color: var(--success);
}
```

The class is applied as `className="btn btn-excel"` — it piggybacks on `.btn`'s background. This is intentional and functional, but if the `.btn` base style changes in a future refactor, `.btn-excel` will have no fallback `background`. There is no visual bug today.

No fix required, but adding `background: transparent;` explicitly would make the component self-documenting.

---

_Reviewed: 2026-06-15T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
