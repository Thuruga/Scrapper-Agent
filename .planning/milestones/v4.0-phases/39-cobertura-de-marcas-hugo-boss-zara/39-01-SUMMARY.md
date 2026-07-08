---
phase: 39-cobertura-de-marcas-hugo-boss-zara
plan: 01
subsystem: api
tags: [vtex, vtex-io, intelligent-search, category-mapping, hugoboss, brands-json, playwright]

requires:
  - phase: prior VTEX onboarding (onboard_vtex_brands.py, category_mapping)
    provides: VTEXEngine.discover_categories, auto_match, persist_mappings, resolve_category_for_brands, get_canonical_categories
provides:
  - hugoboss.mappings populated in brands.json (7 canonical category mappings, all /-relative)
  - onboard_hugoboss_categories.py (one-shot VTEX discovery+persist for Hugo Boss)
  - hermetic tests for Hugo Boss category resolution + VTEX scan schema
  - evidence + follow-up todo that Hugo Boss category MONITORING needs a VTEX-IO/GraphQL scan strategy
affects: [category-monitor, vtex_api_scraper, future hugoboss-vtex-io-category-scan spike]

tech-stack:
  added: []
  patterns: ["VTEX-IO/Intelligent-Search detection: legacy catalog_system category APIs return 0/generic while full-text search works; category listings served by GraphQL persistedQuery"]

key-files:
  created:
    - backend/scripts/onboard_hugoboss_categories.py
    - backend/tests/test_hugoboss_category_mapping.py
    - backend/tests/test_hugoboss_vtex_scan.py
    - .planning/todos/pending/hugoboss-vtex-io-category-scan.md
  modified:
    - backend/data/brands.json

key-decisions:
  - "Hugo Boss category monitoring deferred (operator decision): live category scan needs a new VTEX-IO/GraphQL strategy, not the legacy catalog_system the engine drives"
  - "Disproved the map=c,c,c shortcut: returns generic (non-leaf-filtered) data identical across categories — would silently corrupt per-category comparison"
  - "calcas auto_match corrected from /masculino/calcados (footwear) to /masculino/roupas/calcas via the human-review gate"

patterns-established:
  - "Read-only live preview/probe before persisting a human-verify checkpoint (discovery + sample scan + ground-truth network capture)"

requirements-completed: [COMP-06]  # resolution (a/b/c) complete; COMP-06-d live monitoring DEFERRED — see Deviations

duration: ~35min
completed: 2026-06-29
---

# Phase 39 / Plan 01: Hugo Boss VTEX Onboarding Summary

**Hugo Boss category resolution shipped (7 canonical mappings persisted, resolve + get_canonical green, 318 tests pass); live category monitoring deferred after live probes proved Hugo Boss is a VTEX-IO/Intelligent-Search storefront the legacy scraper can't browse.**

## Performance

- **Tasks:** 2 autonomous (executor) + 1 human-verify checkpoint (orchestrator continuation)
- **Files created:** 4 (script, 2 tests, follow-up todo)
- **Files modified:** 1 (brands.json)
- **Tests:** 318 passed (full suite); 3 new hermetic tests green
- **Completed:** 2026-06-29

## Accomplishments
- `hugoboss.mappings` populated in `brands.json` with 7 operator-approved canonical mappings, every `vtex_fq_path` `/`-relative (COMP-06-a).
- `resolve_category_for_brands("camisas", ["hugoboss"])` → `https://www.hugoboss.com.br/masculino/roupas/camisas` (COMP-06-b, verified live).
- `get_canonical_categories()` lists `hugoboss` under all 7 categories (COMP-06-c, verified live).
- `onboard_hugoboss_categories.py` reuses the VTEX pipeline (`discover_categories` + `auto_match` + `print_and_confirm` + `persist_mappings`); respects D-01/D-03/D-04.
- 3 hermetic tests (mocked, no network) cover COMP-06-b/c/d.
- Characterized and documented (with a live probe matrix) why Hugo Boss category MONITORING is blocked, and opened a high-priority follow-up todo.

## Task Commits

1. **Task 1: hermetic tests for category mapping + VTEX scan** — `96a5a78` (test)
2. **Task 2: Hugo Boss discovery-and-persistence script** — `d50980e` (feat)
3. **Task 3 (human-verify checkpoint): persist corrected mappings** — `ecd30d2` (feat)

## Files Created/Modified
- `backend/scripts/onboard_hugoboss_categories.py` - one-shot VTEX discovery + auto_match + human-review + persist for Hugo Boss.
- `backend/tests/test_hugoboss_category_mapping.py` - COMP-06-b/c hermetic tests (resolve URL + get_canonical includes hugoboss).
- `backend/tests/test_hugoboss_vtex_scan.py` - COMP-06-d hermetic test (VTEXEngine.search returns valid BrandSearchResult schema, mocked).
- `backend/data/brands.json` - `hugoboss.mappings`: 7 CategoryMapping entries (camisas, polos, camisetas, calcas, bermudas, jaquetas, infantil).
- `.planning/todos/pending/hugoboss-vtex-io-category-scan.md` - follow-up for the deferred VTEX-IO category-scan engine work.

## Decisions Made
- **Persist resolution, defer monitoring** (operator-chosen): ship COMP-06-a/b/c now; defer COMP-06-d (live per-category scan) to a dedicated VTEX-IO category-scan spike — mirrors how Zara (39-02) is gated by a spike rather than assumed.
- **calcas corrected** from `/masculino/calcados` (footwear) to `/masculino/roupas/calcas` (trousers) via the human-review gate.

## Deviations from Plan

The plan assumed reusing the existing VTEX pipeline would deliver live category monitoring. **Live investigation during the Task 3 human-verify checkpoint disproved that assumption** and changed the scope.

**1. [Plan assumption invalid] Hugo Boss category scanning is not supported by the existing engine**
- **Found during:** Task 3 (human-verify checkpoint) — read-only live discovery + sample scan + Playwright ground-truth capture.
- **Issue:** `run_bulk_scrape` / `scrape_category_paged` drive the legacy VTEX `catalog_system` category APIs, which return 0 (no map), 3 generic non-leaf-filtered products (with `map=c,c,c`), or 0 (`fq=C:/{id}/`). Intelligent Search `product_search/{path}` returns `records=0`; the browser fallback's `ROOT_QUERY` regex doesn't match Hugo Boss's render. Ground truth (Playwright network capture): the storefront serves category listings via **VTEX IO GraphQL persistedQuery** and renders 36 product tiles. Full-text `search()` works (real products), but per-category browsing does not.
- **Resolution:** Per operator decision, persisted the resolution mappings (the achievable part of COMP-06) and deferred live monitoring to `.planning/todos/pending/hugoboss-vtex-io-category-scan.md`. The proposed `map=c,c,c` fix was **rejected** because it returns generic data that would corrupt per-category comparison.
- **Impact:** COMP-06-d (live scheduler scan returning real per-category products) is NOT met this plan. `monitored_categories.json` was intentionally left unmodified (a monitor scanning 0 products would be misleading). COMP-06-a/b/c are met.

**2. [Data correction] calcas → footwear mismatch**
- **Found during:** Task 3 discovery preview.
- **Issue:** `auto_match` mapped canonical `calcas` to `/masculino/calcados` (Calçados / footwear) via "calça"≈"calçados" accent collision.
- **Fix:** Corrected to `/masculino/roupas/calcas` (Calças / trousers) before persisting. Logged the auto_match reproducibility gap in the follow-up todo.

---

**Total deviations:** 1 scope deviation (monitoring deferred) + 1 data correction.
**Impact on plan:** COMP-06 resolution shipped and verified; COMP-06 live monitoring honestly deferred with evidence rather than faked. No false "it works" claims.

## Issues Encountered
- Re-running `onboard_hugoboss_categories.py` would re-propose the wrong `calcas` path (auto_match accent collision) — fix folded into the follow-up todo.
- Benign `aiohttp` "Unclosed client session" warning in `test_hugoboss_vtex_scan.py` (mocked client session not closed); not a failure — worth tidying.

## User Setup Required
None - no external service configuration. NOTE: the Backstage coding-standards MCP (`backstage_get_coding_standards`) mandated by CLAUDE.md was unavailable in this session (`.mcp.json` not configured), so the standards consult was skipped — flagging for follow-up review.

## Next Phase Readiness
- Resolution layer ready: Hugo Boss appears in category selection and resolves to valid URLs.
- **Blocker for full COMP-06:** live category monitoring requires the deferred VTEX-IO category-scan strategy (high-priority follow-up todo). Phase verification will (correctly) flag this as a gap.

---
*Phase: 39-cobertura-de-marcas-hugo-boss-zara*
*Completed: 2026-06-29*
