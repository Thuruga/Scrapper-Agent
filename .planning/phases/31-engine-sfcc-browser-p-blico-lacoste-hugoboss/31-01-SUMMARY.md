---
phase: 31-engine-sfcc-browser-p-blico-lacoste-hugoboss
plan: 01
subsystem: engines/sfcc
tags: [sfcc, parser, tdd, wave-0, br-price]
dependency_graph:
  requires: []
  provides:
    - parse_price_br
    - extract_jsonld_products
    - extract_og_meta
    - offer_from
    - extract_price
    - parse_availability
    - parse_pdp
    - parse_search_results
    - test_sfcc_engine.py scaffold (TestSFCCParser GREEN; TestSFCCFactory/TestSFCCEngineSearch/TestSFCCCategoryDiscovery RED pending Wave 1/2)
  affects:
    - backend/services/engines/sfcc_parser.py
    - backend/tests/test_sfcc_engine.py
tech_stack:
  added: []
  patterns:
    - JSON-LD Product/ProductGroup extraction (BeautifulSoup + json.loads)
    - OpenGraph meta extraction
    - BR money regex (R$-anchored, dot-thousands, comma-decimal)
    - 3-layer price extraction (JSON-LD → OG → text)
key_files:
  created:
    - backend/services/engines/sfcc_parser.py
    - backend/tests/test_sfcc_engine.py
  modified: []
decisions:
  - name: Backstage standards path
    outcome: In-repo exception approved (MCP unavailable)
  - name: parse_price_br numeric passthrough
    outcome: int/float input passes through as float; avoids float() ValueError on JSON-LD plain values
  - name: _looks_like_pdp_url heuristic
    outcome: Permissive in Wave 0; false positives filtered by Quality Gate at PDP enrichment stage
  - name: test_factory_wake_still_raises
    outcome: Tests via brand mock (engine="wake") rather than engine_type kwarg (factory doesn't expose that)
metrics:
  duration: 283s
  completed: "2026-06-24T14:23:52Z"
  tasks_completed: 3
  files_created: 2
  files_modified: 0
  tests_added: 24
  tests_green: 18
  tests_red: 6
---

# Phase 31 Plan 01: SFCC Parser + Test Scaffold Summary

Wave 0 foundation: BR-price-aware SFCC parser module (`sfcc_parser.py`) and hermetic test scaffold (`test_sfcc_engine.py`). Pure-Python JSON-LD/OG extraction with R$-anchored price regex. All TestSFCCParser tests green (17/17); engine/factory/category tests locked RED pending Wave 1.

## One-Liner

Pure-Python SFCC parser (JSON-LD first → OG → BR-regex fallback) with R$-anchored price parsing and hermetic test scaffold seeding the Wave 1/2 RED contract.

## Backstage Coding-Standards Path (Task 1)

**Path taken: In-repo conventions exception approved.**

- The Backstage MCP (`backstage_get_coding_standards`, server `backstage`) is NOT configured in this session — no `.mcp.json` in the repository.
- The orchestrator pre-approved the documented exception: **proceed under in-repo conventions** established by `shopify_engine.py` / `base_engine.py`.
- Conventions applied:
  - snake_case module names (`sfcc_parser.py`, `sfcc_engine.py`)
  - Thin engine + separate parser (Clean Code / refactoring.guru)
  - Conventional Commits with scope `31-01`
  - Branch off `develop`, PRs required for `main`, no secrets
  - BeautifulSoup + json.loads only (no eval/exec on scraped content)

## Tasks Completed

### Task 1 — Backstage prerequisite checkpoint (resolved)
- **Status:** RESOLVED (pre-approved by orchestrator)
- **Decision recorded:** In-repo conventions exception. MCP unavailable; no code blocked.
- **Commit:** `823dfa7` (docs — empty commit recording resolution)

### Task 2 — sfcc_parser.py (GREEN)
- **Status:** COMPLETE
- **Functions delivered:**
  - `_BR_MONEY_RE` — compiled regex: `R\$\s*([\d]{1,3}(?:\.[\d]{3})*,[\d]{2}|[\d]+,[\d]{2})`
  - `parse_price_br(text)` — BR format + numeric passthrough; rejects USD and accessibility text
  - `extract_jsonld_products(html)` — filters `@type` in Product/ProductGroup; swallows JSONDecodeError
  - `extract_og_meta(html)` — collects all `og:*` properties
  - `offer_from(product)` — first offer from list-or-dict
  - `extract_price(offer, og_meta, visible_text)` — 3-layer: JSON-LD → OG amount → BR text
  - `parse_availability(value)` — InStock/OutOfStock/SoldOut → bool
  - `parse_pdp(html, source_url)` — full PDP → RawProductBronze-compatible dict (or None)
  - `parse_search_results(html, base_domain)` — deduped absolute PDP URLs
  - `_looks_like_pdp_url(href, base_domain)` — same-domain, non-nav heuristic
  - `_extract_brand(product_ld, og_meta)` — brand from JSON-LD brand object or OG
- **Security mitigations (T-31-01, T-31-02):**
  - T-31-01: HTML via BeautifulSoup `.get_text()` only; JSON-LD via `json.loads` as data, never eval
  - T-31-02: `_BR_MONEY_RE` requires `R$` prefix — bare integers, star ratings, review counts never match
- **Commit:** `a509516`

### Task 3 — test_sfcc_engine.py scaffold
- **Status:** COMPLETE
- **Four test classes:**
  - `TestSFCCParser` — 17 tests, NO mocking, **GREEN** (Wave 0 complete)
  - `TestSFCCFactory` — 2 tests: `test_factory_wake_still_raises` GREEN (wake guard present), `test_factory_returns_sfcc_engine` RED (pending sfcc_engine.py Wave 1)
  - `TestSFCCEngineSearch` — 4 tests: `test_search_returns_products`, `test_search_results_have_image`, `test_calculate_shipping_returns_none`, `test_sfcc_engine_implements_base_engine` — all **RED** (pending Wave 1)
  - `TestSFCCCategoryDiscovery` — 1 test: `test_discover_categories_stub` — **RED** (pending Wave 2)
- `_BROWSER_FETCH_TARGET = "core.browser_manager.BrowserManager.fetch_html"` — matches `test_engine_detection.py` seam
- **Commit:** `6e1d2bf`

## Test Results

| Suite | Green | Red | Reason |
|-------|-------|-----|--------|
| TestSFCCParser | 17 | 0 | Pure parser, no external deps |
| TestSFCCFactory | 1 | 1 | wake guard green; sfcc_engine missing (Wave 1) |
| TestSFCCEngineSearch | 0 | 4 | sfcc_engine.py missing (Wave 1) |
| TestSFCCCategoryDiscovery | 0 | 1 | sfcc_engine.py missing (Wave 2) |
| **Total** | **18** | **6** | 6 RED = intentional Nyquist contract |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_factory_wake_still_raises to use brand mock**
- **Found during:** Task 3 initial test run
- **Issue:** Test used `EngineFactory.get_engine("...", engine_type="wake")` but `get_engine` only accepts `brand_key` — the `engine_type` kwarg doesn't exist. Test failed with `TypeError` rather than `NotImplementedError`.
- **Fix:** Updated the test to mock `brand_service.get_brand` returning a mock with `engine="wake"`, then call `EngineFactory.get_engine("richards")`. This correctly exercises the actual code path (brand lookup → engine type resolution → wake guard).
- **Files modified:** `backend/tests/test_sfcc_engine.py`
- **Result:** `test_factory_wake_still_raises` is now GREEN (the wake guard is verified to work correctly).

## RED Tests Pending Wave 1/2 (intentional)

The following tests are locked RED until `sfcc_engine.py` is implemented in Wave 1 (Plan 31-02):

| Test | Requirement | Wave |
|------|-------------|------|
| `test_factory_returns_sfcc_engine` | SC-2 | 1 |
| `test_search_returns_products` | SC-1 | 1 |
| `test_search_results_have_image` | D-07 | 1 |
| `test_calculate_shipping_returns_none` | SC-4 | 1 |
| `test_sfcc_engine_implements_base_engine` | D-04 | 1 |
| `test_discover_categories_stub` | D-06 | 2 |

## Known Stubs

None in this plan. `sfcc_parser.py` contains real implementation; no hardcoded empty values flow to UI rendering. The `_looks_like_pdp_url` heuristic is deliberately permissive (Wave 0 design decision — Wave 1 smoke will refine if needed).

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes introduced in this plan. Threat mitigations T-31-01 and T-31-02 implemented as designed.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| `backend/services/engines/sfcc_parser.py` exists | FOUND |
| `backend/tests/test_sfcc_engine.py` exists | FOUND |
| `31-01-SUMMARY.md` exists | FOUND |
| Commit `823dfa7` (Task 1) | FOUND |
| Commit `a509516` (Task 2) | FOUND |
| Commit `6e1d2bf` (Task 3) | FOUND |
| All 8 public functions + `_BR_MONEY_RE` in sfcc_parser.py | FOUND (9/9) |
| No USD `parse_price` reference (only `parse_price_br`) | OK |
| `_BROWSER_FETCH_TARGET` seam in test file | FOUND |
| TestSFCCParser 17/17 green | PASSED |
