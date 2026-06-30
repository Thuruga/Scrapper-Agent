---
phase: 40-onboarding-por-url-workflows-de-adi-o-ao-monitoramento
plan: 01
subsystem: api
tags: [python, urllib, pytest, url-normalization, test-scaffold]

# Dependency graph
requires: []
provides:
  - "normalize_url() — conservative URL normalizer (D-08) in backend/services/url_utils.py"
  - "Wave-0 test scaffold test_url_utils.py — 11 unit tests for UX-04 (all green)"
  - "Wave-0 test scaffold test_brand_identify.py — 3 guarded RED tests for UX-03 (xfail until Plan 02)"
affects:
  - "40-02 (identify endpoint: test_brand_identify.py flips to real assertions)"
  - "40-03 (monitor dedup: normalize_url imported by start_monitor)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "stdlib-only utility module: from __future__ import annotations + urllib.parse"
    - "Wave-0 xfail scaffold: pytest.mark.xfail(strict=False) with importability guard"

key-files:
  created:
    - backend/services/url_utils.py
    - backend/tests/test_url_utils.py
    - backend/tests/test_brand_identify.py
  modified: []

key-decisions:
  - "40-01/literal-www-strip: strip 'www.' via host[len('www.'):] not str.lstrip('www.') to avoid char-set corruption of hosts like wwww.example.com"
  - "40-01/xfail-guard: test_brand_identify.py uses module-level importability guard + xfail(strict=False) so suite is always green before Plan 02 lands"
  - "40-01/composite-tracking-filter: normalize_url checks both explicit _TRACKING_PARAMS frozenset AND any key.startswith('utm_') — composite + prefix per Anti-Pattern note"

patterns-established:
  - "stdlib-only utility: url_utils.py uses only urllib.parse — no new packages"
  - "Wave-0 RED scaffold: tests reference future symbols, guarded by importability check + xfail"

requirements-completed: [UX-03, UX-04]

# Metrics
duration: 15min
completed: 2026-06-30
---

# Phase 40 Plan 01: URL Utilities and Wave-0 Test Scaffolds Summary

**Pure stdlib `normalize_url` (D-08) + Wave-0 xfail scaffolds for identify (UX-03) and dedup (UX-04) giving Plans 02-03 failing test targets**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-06-30T12:30:00Z
- **Completed:** 2026-06-30T12:45:00Z
- **Tasks:** 2
- **Files created:** 3

## Accomplishments

- Created `backend/services/url_utils.py` — pure stdlib URL normalizer (D-08): forces https, lowercases host, strips literal `www.` prefix (not char-set lstrip), drops tracking params (explicit frozenset + `utm_` prefix check), preserves SKU query params
- Created `backend/tests/test_url_utils.py` — 11 unit tests for `normalize_url`, all green immediately since the implementation was in Task 1
- Created `backend/tests/test_brand_identify.py` — 3 Wave-0 RED scaffolds (`test_identify_returns_engine_and_name`, `test_infer_brand_name`, `test_identify_rejects_ssrf`) guarded by importability check + `xfail(strict=False)` so the suite remains green now; flips to real assertions when Plan 02 lands
- Full suite: 366 passed, 3 xfailed — zero regressions

## Task Commits

1. **Task 1: Create backend/services/url_utils.py with normalize_url (D-08)** - `705dad2` (feat)
2. **Task 2: Create Wave-0 test scaffolds test_url_utils.py and test_brand_identify.py** - `ac987fc` (test)

## Files Created/Modified

- `backend/services/url_utils.py` — Conservative URL normalization: https enforcement, www. strip (literal, not char-set), tracking-param drop, SKU preservation
- `backend/tests/test_url_utils.py` — 11 unit tests covering all UX-04 normalization rules
- `backend/tests/test_brand_identify.py` — 3 guarded Wave-0 scaffolds for UX-03 identify tests

## Decisions Made

- **40-01/literal-www-strip:** Used `host[len("www."):]` instead of `str.lstrip("www.")`. The `lstrip` method strips any character in the set `{w, .}`, which would corrupt hosts like `wwww.example.com` or `we.example.com`. The literal slice is the only correct approach.
- **40-01/xfail-guard:** `test_brand_identify.py` uses a module-level `_has_identify_symbols()` guard that checks whether `api.routes_brands` exposes `identify_brand` and `infer_brand_name`. If absent, all 3 tests are decorated with `xfail(strict=False)`. This keeps Wave 1 fully green without needing a skip that would hide test intent.
- **40-01/composite-tracking-filter:** `normalize_url` applies both `k.lower() not in _TRACKING_PARAMS` AND `not k.lower().startswith("utm_")` — the composite + prefix check per the Anti-Pattern note in RESEARCH.md, so dynamic utm_ variants not in the hardcoded frozenset are also dropped.

## Deviations from Plan

None — plan executed exactly as written. The only clarification was removing the docstring mention of `lstrip("www.")` to satisfy the acceptance criterion grep check (it appeared in a "do NOT use" warning comment in the docstring).

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `normalize_url` is importable from `services.url_utils` and ready for Plan 03 (monitor dedup in `start_monitor`)
- `test_brand_identify.py` provides Plan 02's test targets — once `identify_brand` and `infer_brand_name` are added to `routes_brands.py`, the 3 xfailed tests flip to real assertions automatically
- Full suite green (366 passed, 3 xfailed) — safe to proceed to Plan 02

---
*Phase: 40-onboarding-por-url-workflows-de-adi-o-ao-monitoramento*
*Completed: 2026-06-30*
