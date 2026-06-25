---
phase: 32-engine-wake-commerce-richards
reviewed: 2026-06-24T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - backend/core/models.py
  - backend/services/engines/factory.py
  - backend/services/engines/wake_engine.py
  - backend/tests/test_sfcc_engine.py
  - backend/tests/test_wake_engine.py
findings:
  critical: 0
  warning: 5
  info: 4
  total: 9
status: issues_found
---

# Phase 32: Code Review Report (re-review)

**Reviewed:** 2026-06-24T00:00:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Re-review of the `WakeEngine` (Wake Commerce GraphQL storefront engine) after the
prior BLOCKER fix. The previously-reported CR-01 (GraphQL errors-in-HTTP-200
causing an uncaught `AttributeError`) is **genuinely resolved** and is NOT
re-reported — see verification below.

The security posture remains sound: GraphQL injection is avoided (`$q`/`$first`
variables, never f-string interpolation), `allow_redirects=False` guards the
open-redirect threat on the home GET, and the token is masked in logs.

Five WARNINGs and four INFO items remain. None is a blocker, but two WARNINGs
(WR-05 timeout, WR-01 apex-redirect) materially affect reliability in production:
a hung storefront stalls the entire multi-brand `asyncio.gather`, and a bare-apex
domain silently yields no token. The shipping/checkout/category stubs returning
`None`/`[]` are intentional per D-08 and are NOT flagged.

### CR-01 verification (FIXED — not re-reported)

`wake_engine.py:197-218` now guards the GraphQL error shape before parsing:
`gql_errors = data.get("errors")` / `payload_data = data.get("data")`, then
`if gql_errors or payload_data is None:` returns a structured
`BrandSearchResult(error=...)` joining all GraphQL `message` fields. The
subsequent parse is null-safe (`payload_data.get("search") or {}`,
`... or {}`, `... or []`). The regression test
`test_search_graphql_errors_in_200` (test_wake_engine.py:200-235) asserts no
`AttributeError`, empty `products`, and the surfaced message. Confirmed resolved.

## Warnings

### WR-01: `allow_redirects=False` + no status check silently breaks token auto-extraction on apex→www redirect

**File:** `backend/services/engines/wake_engine.py:310-336` (GET at 318), fallback domain at `159`
**Issue:** Token auto-extraction builds `store_url = f"https://{domain}"` and calls
`session.get(store_url, allow_redirects=False)` (line 318). `allow_redirects=False`
is correct for the open-redirect threat (T-32-01), but with no status check the
common case where `domain` is the bare apex (`richards.com.br`, which 301→
`www.richards.com.br`) fails silently: `resp.text()` returns the short redirect
body, `_TOKEN_RE` matches nothing, `_resolve_token` returns `None`, and `search()`
raises `ValueError` "Token Wake nao resolvido" — even though the storefront is
healthy. Worse, `search()`'s fallback domain (line 159) is
`f"{self.brand_key}.com.br"` — exactly the redirect-prone apex form with no
`www.`. The sibling SFCCEngine treats `www.` differently, so the two engines
disagree on whether `www.` is part of the domain; an operator onboarding a brand
with a bare apex domain gets a confusing token failure.
**Fix:** Detect a redirect status and either log it distinctly or follow it to a
same-registrable-domain target (preserving open-redirect protection):
```python
async with session.get(store_url, allow_redirects=False, timeout=aiohttp.ClientTimeout(total=5)) as resp:
    if resp.status in (301, 302, 303, 307, 308):
        logger.warning(
            "[Wake] %s redirected (%s) with redirects disabled; token HTML not read. "
            "Check domain form (www vs apex).", store_url, resp.status,
        )
        return None
    html = await resp.text()
```
Also normalize the domain story to match SFCC (decide whether stored `domain`
includes `www.` and apply it consistently in both the GET and the product-URL builder at line 226).

### WR-02: Unbounded `max_results` forwarded to GraphQL `$first` (no clamp / non-positive guard)

**File:** `backend/services/engines/wake_engine.py:176-182`
**Issue:** `max_results` flows straight into `variables.first` (line 180) with no
upper bound and no lower-bound validation. A caller passing a very large value
asks Wake for an unbounded page; a `0` or negative value (e.g. from a
misconfigured frontend) is sent verbatim and may produce a GraphQL validation
error response. Note that response is now handled gracefully by the CR-01 guard,
so this no longer crashes — but it still produces a needless failed round-trip
and an opaque "GraphQL error" rather than rejecting bad input at the boundary.
The `$first: Int!` schema also requires an integer; a non-int `max_results` would
be serialized as-is.
**Fix:** Clamp and coerce before building the payload:
```python
first = max(1, min(int(max_results), 50))  # sane floor/ceiling
payload = {"query": _WAKE_SEARCH_QUERY, "variables": {"q": query.strip(), "first": first}}
```

### WR-03: Manual-override token path is not cached; brand is re-resolved every search call

**File:** `backend/services/engines/wake_engine.py:144` (brand re-read), `296-302` (override returned before cache)
**Issue:** `_resolve_token` returns the manual override (step 1, lines 296-302)
*before* checking `self._token_cache` (step 2) and never seeds the cache from the
override. Meanwhile `search()` calls `brand_service.get_brand()` on every
invocation (line 144) and `_resolve_token` re-reads `wake_access_token` each time.
The docstring claims caching "avoids re-fetching home page on every search call",
but that short-circuit applies only to the auto-extracted path; the override path
has no equivalent, creating redundant work and an inconsistency with the stated
"override > cache > auto-extract" precedence.
**Fix:** Either document that override is intentionally not cached (cheap dict
read), or seed `self._token_cache = override` so the documented precedence holds
on subsequent calls. Prefer the explicit comment if override changes must take
effect live.

### WR-04: `_resolve_token` ignores HTTP status on the home GET; non-200 pages parsed as if valid

**File:** `backend/services/engines/wake_engine.py:318-324`
**Issue:** Unlike the GraphQL POST (which calls `raise_for_status()` at line 187),
the home-page GET never inspects `resp.status`. A 403 (anti-bot block), 404, or
5xx body is still fed to `_TOKEN_RE`. In the happy path the regex simply misses,
but a hostile or error page that happens to contain a
`storefrontAccessToken:'...'` string (e.g. a cached CDN error page or an
attacker-controlled mirror reached via the apex redirect in WR-01) would be
trusted. Combined with WR-01, auto-extraction failures are also hard to diagnose
because every non-200 collapses into the same generic "not found" branch.
**Fix:** Check status before parsing:
```python
async with session.get(store_url, allow_redirects=False, timeout=...) as resp:
    if resp.status != 200:
        logger.warning("[Wake] home GET %s returned %s; skipping token extraction", store_url, resp.status)
        return None
    html = await resp.text()
```

### WR-05: No request timeout on the home GET or the GraphQL POST; a hung storefront blocks the whole search

**File:** `backend/services/engines/wake_engine.py:186` (POST), `318` (GET); root cause `core/session_manager.py:22-23`
**Issue:** Neither `session.post(GRAPHQL_ENDPOINT, ...)` (line 186) nor
`session.get(store_url, ...)` (line 318) passes an `aiohttp.ClientTimeout`, and
`SessionManager.get_session()` (session_manager.py:22-23) creates the
`ClientSession` with only a `TCPConnector` and no default timeout. aiohttp's
default total timeout is 5 minutes, so a slow or hung Wake endpoint stalls the
coroutine for that long. Because `EngineFactory.search_all_brands` runs all
engines under one `asyncio.gather` (factory.py:104-105), a single hung Wake
storefront delays the entire multi-brand search result. The sibling pattern in
`routes_brands.py:24,34,44` explicitly sets `timeout=aiohttp.ClientTimeout(total=5)`
on every storefront call.
**Fix:** Add an explicit timeout to both calls, mirroring `routes_brands.py`:
```python
import aiohttp
...
async with session.post(GRAPHQL_ENDPOINT, json=payload, headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10)) as resp:
    ...
async with session.get(store_url, allow_redirects=False,
                       timeout=aiohttp.ClientTimeout(total=5)) as resp:
    ...
```

## Info

### IN-01: `getattr(brand, "domain", None)` on a dict relies on a non-obvious fallback

**File:** `backend/services/engines/wake_engine.py:150-155`, `296-299`
**Issue:** `getattr(brand, "domain", None) or (brand.get("domain", "") if isinstance(brand, dict) else "")`
works because `getattr(dict_instance, "domain", None)` returns `None` (dicts have
no `domain` attribute), letting the `or` fall through to `.get`. Correct but
fragile and non-obvious; a reader could reasonably think `getattr` on a dict
throws. The same pattern is duplicated for `brand_name` (153-155),
`wake_access_token` (297-299), and in SFCCEngine.
**Fix:** Extract a shared `_brand_field(brand, name, default)` helper that both
WakeEngine and SFCCEngine import, and document the `getattr`-returns-None behavior.

### IN-02: Product-URL construction does not validate `aliasComplete` scheme/host

**File:** `backend/services/engines/wake_engine.py:225-226`
**Issue:** `product_url = f"https://{domain}/{alias.lstrip('/')}"` assumes
`aliasComplete` is always a relative path (confirmed by spike 007). If a future
Wake response returns an absolute URL (`https://evil/...`) in `aliasComplete`, the
result is the harmless-but-broken `https://{domain}/https://evil/...`. No
assertion guards the spike's assumption. Low risk since it is server-supplied from
an authenticated GraphQL call.
**Fix:** Optionally skip nodes whose `aliasComplete` contains `://`, or strip a
leading scheme before joining.

### IN-03: `available` defaults to `True` for nodes missing the field

**File:** `backend/services/engines/wake_engine.py:234`
**Issue:** `available = node.get("available", True)` defaults missing availability
to in-stock. Spike 007 says the field is "present and correct", so this default
only triggers on schema drift — but defaulting *unknown* availability to "in
stock" is the optimistic direction and could surface out-of-stock items as
available if Wake ever omits the field. Downstream `SearchProductResult.available`
is `Optional[bool]`, so a `None` (unknown) is representable.
**Fix:** Default to `None` (unknown) rather than `True`, letting downstream
distinguish unknown from confirmed-available.

### IN-04: Stale comment reference to removed `test_factory_wake_still_raises`

**File:** `backend/tests/test_sfcc_engine.py:235-236`
**Issue:** Lines 235-236 are an explanatory comment about a removed test
(`test_factory_wake_still_raises`). Accurate but commented-out-code-adjacent
narration left in a test file — minor housekeeping that accumulates.
**Fix:** Remove the obsolete note now that the WakeEngine test in
`test_wake_engine.py` is the source of truth, or move it to the phase changelog.

---

_Reviewed: 2026-06-24T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
