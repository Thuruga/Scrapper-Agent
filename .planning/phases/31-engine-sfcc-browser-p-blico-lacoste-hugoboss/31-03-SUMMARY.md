---
phase: 31-engine-sfcc-browser-p-blico-lacoste-hugoboss
plan: 03
subsystem: engines/sfcc
tags: [sfcc, engine, category-discovery, nav-extraction, wave-2, tdd]
dependency_graph:
  requires:
    - 31-01 (sfcc_parser.py: parse_pdp, parse_search_results, parse_price_br)
    - 31-02 (sfcc_engine.py: SFCCEngine full BaseEngine contract + D-06 stubs)
  provides:
    - extract_nav_categories(html, base_domain) — pure BeautifulSoup nav parser
    - SFCCEngine.discover_categories() — real home/nav render with D-06 [] fallback
    - SFCCEngine.get_catalog() — group-shape [{group, items:[{label,path}]}] wrapper
    - CATALOG_GROUP_LABEL constant
  affects:
    - backend/services/engines/sfcc_parser.py (extended — extract_nav_categories added)
    - backend/services/engines/sfcc_engine.py (upgraded — stubs replaced with real impl)
    - backend/tests/test_sfcc_engine.py (extended — 11 new category tests)
tech_stack:
  added: []
  patterns:
    - TDD RED/GREEN: failing tests committed before implementation
    - Pure parser function (extract_nav_categories) — no browser, hermetically testable
    - BeautifulSoup nav.find("nav") or find(attrs={"role":"navigation"}) fallback
    - Same-domain relative-href filter (startswith("/")) — T-31-07
    - Noise-term set for label + path segment filtering (account/login/cart/politica etc.)
    - Path-based deduplication preserving first-seen order
    - D-06 graceful stub: try/except on BrowserManager.fetch_html returns [] on any exception
    - BR domain fallback {brand_key}.com.br mirrors search() — enables pre-onboarding smoke
    - CATALOG_GROUP_LABEL constant mirrors ShopifyEngine "Coleções / Categorias"
key_files:
  created: []
  modified:
    - backend/services/engines/sfcc_parser.py
    - backend/services/engines/sfcc_engine.py
    - backend/tests/test_sfcc_engine.py
decisions:
  - name: BR domain fallback in discover_categories
    outcome: "Applied the same {brand_key}.com.br fallback pattern as search() — discover_categories does not early-return [] when brand_service.get_brand() returns None. This preserves the test contract (no brand_service mock needed) and allows smoke-testing before formal brand onboarding."
  - name: extract_nav_categories base_domain parameter reserved
    outcome: "base_domain is kept in the function signature as part of the public API contract (for future absolute-URL resolution callers) but is not used internally since same-domain filtering is done via startswith('/') on the href. Documented with noqa comment."
  - name: get_catalog returns single group even when empty
    outcome: "get_catalog() always returns a list with exactly one group dict (items=[] when discover_categories returns []). This matches the ShopifyEngine.get_catalog pattern and allows the frontend to render an empty but structurally valid catalog tree."
  - name: D-06 discover_categories fallback path
    outcome: "On any BrowserManager exception (anti-bot block, timeout, JS menu not rendering, network error), discover_categories catches all exceptions, logs a warning, and returns []. This is the D-06 graceful stub — category failure never crashes the engine and never blocks search delivery from Plan 02."
metrics:
  duration: 420s
  completed: "2026-06-24T17:10:00Z"
  tasks_completed: 2
  files_created: 0
  files_modified: 3
  tests_added: 11
  tests_turned_green: 11
---

# Phase 31 Plan 03: Category Discovery Expansion (D-05/D-06) Summary

Wave 2 catalog expansion: `extract_nav_categories` pure parser added to `sfcc_parser.py`; `discover_categories` and `get_catalog` upgraded from D-06 `[]` stubs to real home/nav-render implementations in `sfcc_engine.py`. 11 new tests all GREEN; full suite 225/225 with no regressions.

## One-Liner

Real nav-link category extraction for SFCC storefronts with BeautifulSoup noise filtering and D-06 `[]` fallback on any browser exception.

## Tasks Completed

### Task 1 — Add extract_nav_categories helper to sfcc_parser.py (TDD GREEN)

- **Status:** COMPLETE
- **File:** `backend/services/engines/sfcc_parser.py`
- **TDD Gate:**
  - RED commit `3cc413c`: 7 failing tests for `extract_nav_categories` (ImportError — function not yet defined)
  - GREEN commit `94493eb`: implementation added, all 7 tests pass
- **Key behaviors:**
  - Locates `<nav>` or `role="navigation"` element; returns `[]` when absent
  - Keeps only same-domain relative hrefs (`startswith("/")`) — drops external and `javascript:` hrefs (T-31-07)
  - Label extracted via `.get_text(strip=True)` only — no markup execution (T-31-07)
  - Filters labels <= 2 characters and noise terms (account/login/cart/conta/politica etc.)
  - Deduplicates by path, preserving first-seen order
  - Pure function: no `BrowserManager` import, no network I/O
- **Commit:** `94493eb`

### Task 2 — Upgrade SFCCEngine.discover_categories + get_catalog (GREEN)

- **Status:** COMPLETE
- **Files:** `backend/services/engines/sfcc_engine.py`, `backend/tests/test_sfcc_engine.py`
- **Key behaviors:**
  - `CATALOG_GROUP_LABEL = "Coleções / Categorias"` module constant (mirrors ShopifyEngine)
  - `discover_categories()`: fetches `https://www.{domain}` via `BrowserManager.fetch_html(wait_selector="nav", extra_sleep=2.0)`, delegates parsing to `extract_nav_categories`
  - D-06 fallback: `try/except` on entire BrowserManager call — any exception → `logger.warning` + `return []`
  - BR domain fallback (`{brand_key}.com.br`) when brand not registered — mirrors `search()` pattern
  - `get_catalog()`: `[{"group": CATALOG_GROUP_LABEL, "items": [{"label": c["name"], "path": c["path"]} for c in flat]}]`; always one group, `items=[]` when nav absent
  - Plan 02 behavior preserved: search/shipping/factory all untouched
- **Tests added:** populated-nav returns dicts, exception → [], get_catalog group shape, get_catalog empty-nav single group
- **Commit:** `9406682`

## Category Discovery Status

`discover_categories` is wired and functional in the test environment (mocked BrowserManager). Live behavior against `lacoste.com.br` and `hugoboss.com.br` is pending a manual smoke test (per 31-VALIDATION § Manual-Only, D-06 confirm):

- **If live smoke returns items:** spot-check that paths are valid SFCC category paths in the monitoring UI.
- **If live smoke returns `[]`:** the D-06 graceful stub is acceptable — Phase 31 closes via search (Plan 02 untouched). Catalog monitoring for Lacoste/HugoBoss should move to a follow-up phase with a dedicated spike against the live BR nav HTML.

**Nav selector used:** `soup.find("nav") or soup.find(attrs={"role": "navigation"})` with `wait_selector="nav"` and `extra_sleep=2.0` on `BrowserManager.fetch_html`.

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED — `test(31-03)` commit with failing tests | `3cc413c` | PRESENT |
| GREEN — `feat(31-03)` commit with implementation | `94493eb` | PRESENT |
| GREEN — `feat(31-03)` engine upgrade commit | `9406682` | PRESENT |
| REFACTOR | not needed — implementation clean | SKIPPED (OK) |

## Test Results

| Suite | Wave 1 State | Wave 2 State |
|-------|-------------|-------------|
| TestSFCCParser | 17 GREEN | 17 GREEN (unchanged) |
| TestSFCCFactory | 2 GREEN | 2 GREEN (unchanged) |
| TestSFCCEngineSearch | 4 GREEN | 4 GREEN (unchanged) |
| TestSFCCCategoryDiscovery | 1 GREEN (stub only) | **12 GREEN** (+11 new) |
| **Total SFCC** | 24 GREEN | **35 GREEN** |
| **Full suite** | 214/214 GREEN | **225/225 GREEN** |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] discover_categories early-return when brand_service.get_brand() returns None**

- **Found during:** Task 2 GREEN step — `test_discover_categories_populated_nav_returns_dicts` failed with `assert 0 >= 1` because brand is not registered in the test environment
- **Issue:** Initial implementation returned `[]` early when `brand_service.get_brand(brand_key)` returned `None`. The test mocks only `BrowserManager.fetch_html`, not `brand_service`, so the early return was triggered before the mock was ever reached.
- **Fix:** Applied the same BR domain fallback pattern as `search()` — when brand returns `None` or has no domain, derive `{brand_key}.com.br` and continue to the BrowserManager call. This is the correct behavior: allow smoke-testing before formal brand onboarding, matching the Wave 1 decision record.
- **Files modified:** `backend/services/engines/sfcc_engine.py`
- **Commit:** `9406682`

## Known Stubs

| Stub | File | Line | Reason |
|------|------|------|--------|
| `SEARCH_URL_TEMPLATE` pattern unverified for BR stores | `sfcc_engine.py` | ~58 | Pitfall 5: carried from Plan 02; live smoke will confirm or correct |
| Live category extraction result (items vs. `[]`) | `sfcc_engine.py` | discover_categories | D-06: outcome depends on live BR nav rendering — not testable without real browser hit |

The `SEARCH_URL_TEMPLATE` stub does NOT prevent Plan 03's goal from being achieved. The plan's goal is `discover_categories`/`get_catalog` real implementation (D-05/D-06), which is fully delivered.

## Threat Flags

No new network endpoints, auth paths, or schema changes beyond the plan threat model. Both new threats addressed:

| Threat | Status |
|--------|--------|
| T-31-07 (nav markup → label text injection) | Mitigated: `.get_text(strip=True)` only; `startswith("/")` drops external hrefs |
| T-31-08 (DoS / anti-bot / partial HTML in nav render) | Mitigated: try/except on BrowserManager returns `[]` — never crashes or blocks search |

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| `backend/services/engines/sfcc_parser.py` has `extract_nav_categories` | FOUND |
| `backend/services/engines/sfcc_engine.py` has `CATALOG_GROUP_LABEL` | FOUND |
| `backend/services/engines/sfcc_engine.py` discover_categories is real (not stub) | FOUND |
| `backend/services/engines/sfcc_engine.py` get_catalog is real (not stub) | FOUND |
| Commit `3cc413c` (RED — failing tests) | FOUND |
| Commit `94493eb` (GREEN — extract_nav_categories) | FOUND |
| Commit `9406682` (GREEN — engine upgrade) | FOUND |
| `pytest tests/test_sfcc_engine.py::TestSFCCCategoryDiscovery -x` exits 0 | PASSED (12/12) |
| `pytest tests/test_sfcc_engine.py::TestSFCCEngineSearch -x` exits 0 | PASSED (4/4) |
| `pytest tests/test_sfcc_engine.py::TestSFCCFactory -x` exits 0 | PASSED (2/2) |
| `pytest tests/test_sfcc_engine.py -x` exits 0 | PASSED (35/35) |
| `pytest tests/ -ra` exits 0 | PASSED (225/225) |
| `python -c "from services.engines.sfcc_parser import extract_nav_categories"` exits 0 | PASSED |
| No modification to STATE.md or ROADMAP.md | CONFIRMED |
</content>
</invoke>