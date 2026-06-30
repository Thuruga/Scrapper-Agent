---
phase: 44-ruptura-de-estoque-avalia-es-refor-adas
plan: 04
subsystem: backend-reviews
tags: [python, fastapi, pytest, review-comments, trustvox, vtex, json-persistence]

requires:
  - phase: 44-ruptura-de-estoque-avalia-es-refor-adas
    provides: Plan 44-01/44-02 monitor scan product contracts and Plan 44-03 explicit monitor-product action pattern
provides:
  - Audited review provider coverage for every registered brand
  - On-demand compact review comment service with explicit provider states
  - Persisted monitor scan-product review comments
  - VTEX review_product_id propagation without fetching full comments inline
  - POST /monitor/category/{monitor_id}/products/{scan_product_id}/reviews
affects: [44-05, monitor-products, review-comments, category-monitor]

tech-stack:
  added: []
  patterns:
    - Provider coverage requires evidence for supported providers and rationale for unsupported providers
    - Full review comments are fetched only through explicit monitor-product action
    - External review payloads normalize to compact ReviewComment records before persistence

key-files:
  created:
    - backend/tests/test_review_comments_service.py
  modified:
    - backend/core/models.py
    - backend/data/brands.json
    - backend/services/review_service.py
    - backend/services/vtex_api_scraper.py
    - backend/api/routes_monitor.py
    - backend/tests/test_phase44_routes.py

key-decisions:
  - "44-04/provider-audit-explicit: Aramis remains the only Trustvox-supported brand with store_id 78800 and recorded evidence; every other registered brand is review_provider='none' with unsupported rationale unless future evidence proves support."
  - "44-04/comments-on-demand-boundary: normal search and VTEX search remain summary-only through get_bulk_reviews/get_single_review; full comments are reachable only through the monitor scan-product reviews action."
  - "44-04/scan-product-identity: review comments resolve brand/product identity from persisted monitor artifacts and review_product_id; the route accepts no provider, domain, URL, product_id override, or raw payload."
  - "44-04/compact-comments: provider responses are normalized to ReviewComment fields and deduped before persistence; no raw provider payload fields are introduced."

patterns-established:
  - "ReviewState has available, unsupported, and temporary_failure for comments."
  - "Review comment dedup uses provider review_id first and deterministic hash fallback over rating/title/text/author/created_at."
  - "ReviewCommentsRequest contains only optional max_pages and forbids extra fields."

requirements-completed: [REVW-01]

duration: 68 min
completed: 2026-06-30
---

# Phase 44 Plan 04: On-Demand Compact Review Comments Summary

**Provider-audited, page-limited review comments for persisted monitor scan products without making normal search heavy**

## Performance

- **Duration:** 68 min
- **Started:** 2026-06-30T22:11:00Z
- **Completed:** 2026-06-30T23:19:37Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- Audited `backend/data/brands.json` so each brand has supported provider evidence or an explicit unsupported rationale.
- Added `ReviewState`, `get_review_comments`, provider fetchers, dedup/hash helpers, and compact normalization in `review_service.py`.
- Added `fetch_scan_product_review_comments` to update only the matched persisted monitor scan product.
- Propagated VTEX `productId` as `review_product_id` in product parse/search paths while preserving `rating`/`review_count` summary behavior.
- Added `POST /monitor/category/{monitor_id}/products/{scan_product_id}/reviews` with a body restricted to optional `max_pages`.

## Task Commits

1. **Task 1: Audit and configure review provider coverage per D-13**
   - `a033838` test(44-04): add provider coverage audit tests
   - `ddc5747` feat(44-04): audit review provider coverage
2. **Task 2: Extend review_service with compact on-demand comments**
   - `63ec3e5` test(44-04): add failing tests for review comments service
   - `2c35b9b` feat(44-04): implement on-demand review comments
3. **Task 3: Persist on-demand review comments for monitor scan products**
   - `5e3ac2b` test(44-04): add failing tests for monitor review persistence
   - `e37265f` feat(44-04): persist monitor product review comments

## Files Created/Modified

- `backend/tests/test_review_comments_service.py` - Provider audit tests plus service, persistence, and VTEX review identity coverage.
- `backend/core/models.py` - Additive brand audit metadata plus `ReviewCommentsResult.source_provider` and `max_pages`.
- `backend/data/brands.json` - Explicit supported/unsupported review provider coverage for all 20 registered brands.
- `backend/services/review_service.py` - On-demand comments router, provider fetchers, compact normalization, dedup, and monitor product persistence.
- `backend/services/vtex_api_scraper.py` - Adds `review_product_id` from VTEX `productId` without importing full-comment functions.
- `backend/api/routes_monitor.py` - Adds the capped monitor scan-product reviews action.
- `backend/tests/test_phase44_routes.py` - Route request/response coverage for monitor review comments.

## Decisions Made

- Aramis remains the only supported Trustvox provider in the current registry because it already had `review_store_id="78800"`; no brand was marked `vtex_native` from VTEX engine alone.
- Unsupported providers are explicit configuration, not runtime failures; `get_review_comments` returns `reviews_state="unsupported"` for unknown brands, provider `none`, or missing audit evidence.
- Full comments are persisted only from monitor scan-product action and only onto the matched product record.
- VTEX search/scan paths propagate `review_product_id` but continue to call only summary functions (`get_bulk_reviews` / `get_single_review`).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Backstage coding standards MCP was unavailable in this Codex session; only Node REPL tooling was exposed after tool discovery. Implementation followed `CLAUDE.md`, the Phase 44 pattern map, and established local service/route conventions.
- The final working tree contains unrelated dirty files outside this plan (`__pycache__`, data artifacts, frontend dist, Zara/cross-marketplace files). They were not reverted or staged.
- One PowerShell verification command initially had nested `$` quoting expanded incorrectly; the same guard was rerun directly in PowerShell and passed.

## Known Stubs

None in production code. Empty lists/dicts in tests are intentional fixtures or expected unsupported results.

## Threat Flags

None. The new API surface is the planned REVW-01 monitor-product action and mitigates T-44-14 through compact normalization, T-44-15 through max page caps, T-44-16 through persisted product identity, T-44-17 through the existing authenticated monitor router, and T-44-18 through provider audit metadata.

## Verification

- `python -c "import json; json.load(open('backend/data/brands.json', encoding='utf-8'))"` -> passed.
- `python -m pytest backend/tests/test_review_comments_service.py -q` -> 10 passed.
- `python -m pytest backend/tests/test_review_comments_service.py backend/tests/test_phase44_routes.py -q` -> 28 passed.
- `rg -n 'get_review_comments|fetch_scan_product_review_comments|review_comments' backend/api/routes_search.py backend/services/vtex_api_scraper.py` guarded by PowerShell exit check -> no matches.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for Plan 44-05. The frontend/monitor modal can call the new review action against persisted scan products and render `reviews_state`, `rating`, `review_count`, and compact `review_comments`.

## Self-Check: PASSED

- Found created/modified files: `backend/tests/test_review_comments_service.py`, `backend/core/models.py`, `backend/data/brands.json`, `backend/services/review_service.py`, `backend/services/vtex_api_scraper.py`, `backend/api/routes_monitor.py`, `backend/tests/test_phase44_routes.py`, and this SUMMARY.
- Found commits: `a033838`, `ddc5747`, `63ec3e5`, `2c35b9b`, `5e3ac2b`, `e37265f`.
- Re-ran plan verification: `python -m pytest backend/tests/test_review_comments_service.py backend/tests/test_phase44_routes.py -q` -> 28 passed.
- Re-ran search-path guard: full-comment grep in `routes_search.py` and `vtex_api_scraper.py` -> no matches.

---
*Phase: 44-ruptura-de-estoque-avalia-es-refor-adas*
*Completed: 2026-06-30*
