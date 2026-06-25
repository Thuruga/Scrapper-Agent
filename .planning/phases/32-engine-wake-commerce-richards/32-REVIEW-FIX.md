---
phase: 32-engine-wake-commerce-richards
fixed_at: 2026-06-24T00:00:00Z
review_path: .planning/phases/32-engine-wake-commerce-richards/32-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 32: Code Review Fix Report

**Fixed at:** 2026-06-24T00:00:00Z
**Source review:** .planning/phases/32-engine-wake-commerce-richards/32-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (0 Critical, 5 Warning — Info items IN-01..IN-04 out of scope)
- Fixed: 5
- Skipped: 0

All in-scope warnings were fixed without regressing the phase's security
posture: `allow_redirects=False` is preserved (T-32-01), GraphQL input still
flows only through `$q`/`$first` variables (T-32-02), the token stays masked in
logs, and the catalog+price-only scope (shipping/category stubs per D-08) is
untouched. Full backend suite: 236 -> 244 passing (8 net-new tests; none
removed). WR-01/WR-04 fixes did NOT enable redirect-following to arbitrary
hosts — a 3xx is detected and refused with a distinct warning.

## Fixed Issues

### WR-01: apex->www redirect silently breaks token auto-extraction

**Files modified:** `backend/services/engines/wake_engine.py`, `backend/tests/test_wake_engine.py`
**Commit:** 7de8f61
**Applied fix:** In `_resolve_token`, the home GET now inspects `resp.status`
and, on a redirect (301/302/303/307/308), logs a distinct warning ("Check the
registered domain form (www vs apex)") and returns `None` instead of feeding the
short redirect body to `_TOKEN_RE`. `allow_redirects=False` is kept (T-32-01) —
the redirect is NOT followed to an arbitrary host. Also normalized the
`search()` fallback domain from the redirect-prone bare apex
`f"{self.brand_key}.com.br"` to the `www.` form `f"www.{self.brand_key}.com.br"`,
keeping WakeEngine self-consistent (stored brand domains already include `www.`,
so the product-URL builder at the join site does not produce a double-`www.`).
The sibling SFCC `www.` double-prefix bug is left as-is (tracked in STATE.md).
Tested by `TestWakeTokenAutoExtract.test_redirect_status_yields_no_token` (a 301
with a token-looking body must NOT be parsed).

### WR-02: unbounded `max_results` forwarded to `$first`

**Files modified:** `backend/services/engines/wake_engine.py`, `backend/tests/test_wake_engine.py`
**Commit:** 7de8f61
**Applied fix:** Before building the GraphQL payload, `max_results` is coerced
and clamped: `first = max(1, min(int(max_results), 50))`, with a `TypeError`/
`ValueError` fallback to `DEFAULT_MAX_RESULTS` for non-int input. This rejects
`0`/negative/huge values at the boundary so `$first: Int!` always receives a
sane bounded positive integer. Tested by `TestWakeMaxResultsClamp` (0 -> 1,
-5 -> 1, 10000 -> 50, 7 -> 7) which inspects the captured POST payload.

### WR-03: manual-override token not cached

**Files modified:** `backend/services/engines/wake_engine.py`, `backend/tests/test_wake_engine.py`
**Commit:** 4b63df6
**Applied fix:** When `_resolve_token` returns the manual override, it now seeds
`self._token_cache = override` first, so the documented
"override > cache > auto-extract" precedence holds consistently on subsequent
calls (the override path no longer re-resolves every search). Chose the
cache-seeding option (not the documentation-only option) because there is no
requirement for live override changes within an engine instance lifetime.
Tested by `TestWakeOverrideCaching.test_override_seeds_cache`.

### WR-04: non-200 home GET bodies parsed as if valid

**Files modified:** `backend/services/engines/wake_engine.py`, `backend/tests/test_wake_engine.py`
**Commit:** 7de8f61
**Applied fix:** After the redirect check, the home GET returns `None` with a
warning when `resp.status != 200`, so 403 (anti-bot), 404, and 5xx bodies are
never fed to `_TOKEN_RE`. This closes the trust gap where a hostile/cached error
page containing a `storefrontAccessToken:'...'` string could be accepted. Tested
by `TestWakeTokenAutoExtract.test_non_200_status_yields_no_token` (a 403 body
with a token-looking string is ignored) and
`test_200_status_extracts_token` (the happy 200 path still extracts).

### WR-05: no request timeout on home GET or GraphQL POST

**Files modified:** `backend/services/engines/wake_engine.py`, `backend/tests/test_wake_engine.py`
**Commit:** 7de8f61
**Applied fix:** Added `import aiohttp` and an explicit `aiohttp.ClientTimeout`
to both storefront calls, mirroring `routes_brands.py`: `total=10` on the
GraphQL `session.post(...)` and `total=5` on the home-page `session.get(...)`.
This bounds a hung Wake endpoint so it can no longer stall the shared
`asyncio.gather` in `EngineFactory.search_all_brands` for aiohttp's 5-minute
default. The `SessionManager` default (no session-level timeout) was left
unchanged to avoid affecting other engines that share the session — the timeout
is applied per-request, matching the established sibling pattern.

## Out-of-Scope (not fixed — Info severity, fix_scope=critical_warning)

IN-01 (`_brand_field` helper extraction), IN-02 (`aliasComplete` scheme/host
validation), IN-03 (`available` default of `True`), and IN-04 (stale test
comment) are INFO-severity and excluded by `fix_scope: critical_warning`. They
were not modified.

---

_Fixed: 2026-06-24T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
