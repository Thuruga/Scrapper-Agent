---
phase: 32-engine-wake-commerce-richards
reviewed: 2026-06-25T00:54:43Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - backend/core/models.py
  - backend/services/engines/factory.py
  - backend/services/engines/wake_engine.py
  - backend/tests/test_sfcc_engine.py
  - backend/tests/test_wake_engine.py
findings:
  critical: 1
  warning: 5
  info: 4
  total: 10
status: issues_found
---

# Phase 32: Code Review Report

**Reviewed:** 2026-06-25T00:54:43Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Reviewed the new `WakeEngine` (Wake Commerce GraphQL storefront engine), its
`EngineFactory` wiring, the `wake_access_token` model field, and the Wake/SFCC
test suites. The security posture the phase set out to enforce is mostly sound:
GraphQL injection is avoided (query uses `$q`/`$first` variables, never f-string
interpolation), `allow_redirects=False` is present on the home GET, and the
token is masked in logs (only "auto-extracted and cached" / "using cached token"
are logged, never the value). The factory lazy-import wiring mirrors the SFCC
pattern correctly.

However, there is one BLOCKER: the GraphQL **response** parsing does not handle
the standard GraphQL error shape (`{"errors": [...], "data": null}`). Because
`resp.raise_for_status()` only catches non-2xx HTTP, a 200 response with
`data: null` reaches the parser and raises an uncaught `AttributeError`, defeating
the structured `BrandSearchResult.error` path the phase explicitly designed
(D-07). Several WARNINGs concern the token auto-extraction robustness
(`allow_redirects=False` combined with no status check silently breaks token
extraction when the bare apex domain 301-redirects to `www.`) and unbounded
`max_results` flowing into the GraphQL `$first` argument.

Note: the shipping/checkout/category stubs returning `None`/`[]` are intentional
per D-08 and are NOT flagged.

## Critical Issues

### CR-01: GraphQL error response (`data: null`) raises uncaught AttributeError, bypasses D-07 error path

**File:** `backend/services/engines/wake_engine.py:185-203`
**Issue:** GraphQL APIs return application-level errors as **HTTP 200** with a body
of the shape `{"errors": [...], "data": null}`. `resp.raise_for_status()` only
raises on non-2xx status, so this body passes through the `try/except` (which ends
at line 195) untouched. The parsing block then runs:

```python
edges = (
    data.get("data", {})        # returns None, NOT {} — the key exists with value null
    .get("search", {})          # AttributeError: 'NoneType' object has no attribute 'get'
    ...
)
```

`dict.get("data", {})` returns the **default only when the key is absent**. When
the key is present with value `null`, it returns `None`, and the chained `.get()`
raises `AttributeError`. This block is *outside* the `try/except`, so the
exception propagates out of `search()`. It is ultimately swallowed by
`factory._search_one`'s broad `except Exception`, but that:
  - produces an opaque `AttributeError(...)` string instead of the GraphQL error,
  - defeats the deliberate D-07 design (clear diagnostic via `BrandSearchResult.error`),
  - means any malformed/error response from Wake (expired token, throttling,
    schema drift) surfaces as a cryptic crash rather than an actionable message.

**Fix:** Guard the parse against `None` data and surface GraphQL `errors`
explicitly, inside the error-handling path:
```python
async with session.post(GRAPHQL_ENDPOINT, json=payload, headers=headers) as resp:
    resp.raise_for_status()
    data = await resp.json()

# Handle GraphQL-level errors (HTTP 200 + errors[] + data: null)
if data.get("errors"):
    msg = data["errors"][0].get("message", "unknown GraphQL error")
    logger.warning("[Wake] GraphQL errors for brand=%s: %s", self.brand_key, data["errors"])
    return BrandSearchResult(
        brand_key=self.brand_key, brand_name=brand_name,
        error=f"GraphQL error: {msg}",
    )

edges = (
    (data.get("data") or {})        # coalesce null -> {}
    .get("search", {})
    ...
)
```
(Wrap the whole block in the existing `try/except`, or coalesce every level with
`or {}` to be null-safe.)

## Warnings

### WR-01: `allow_redirects=False` + no status check silently breaks token auto-extraction on apex→www redirect

**File:** `backend/services/engines/wake_engine.py:298-321`
**Issue:** Token auto-extraction builds `store_url = f"https://{domain}"` and does
`session.get(store_url, allow_redirects=False)`. The `allow_redirects=False` is
correct for the open-redirect threat (T-32-01). But combined with no status check,
it produces a silent failure for the common case where `domain` is the bare apex
(`richards.com.br`) which 301-redirects to `www.richards.com.br`. With redirects
disabled, `resp.text()` returns the empty/short redirect body, `_TOKEN_RE` finds
nothing, and `_resolve_token` returns `None` → `ValueError` "token nao resolvido"
— even though the storefront is perfectly healthy. Note `search()`'s fallback
domain is `f"{self.brand_key}.com.br"` (no `www.`), which is exactly the
redirect-prone form; the sibling SFCCEngine instead prefixes `https://www.{domain}`.
The two engines disagree on whether `www.` is part of the domain.

**Fix:** Detect a redirect and either (a) log it distinctly so the failure is
diagnosable, or (b) follow it to a same-host/same-registrable-domain target only
(keeping open-redirect protection). Minimal version:
```python
async with session.get(store_url, allow_redirects=False) as resp:
    if resp.status in (301, 302, 303, 307, 308):
        logger.warning(
            "[Wake] %s redirected (%s) with redirects disabled; "
            "token HTML not read. Check domain form (www vs apex).",
            store_url, resp.status,
        )
    html = await resp.text()
```
Also normalize the domain handling to match SFCC (decide whether stored `domain`
includes `www.` and apply consistently in both the GET and the product-URL builder).

### WR-02: Unbounded `max_results` forwarded to GraphQL `$first` (no clamp / non-positive guard)

**File:** `backend/services/engines/wake_engine.py:178-182`
**Issue:** `max_results` is passed straight into `variables.first` with no upper
bound and no lower-bound validation. A caller passing a very large value asks Wake
for an unbounded page; a `0` or negative value (e.g. from a misconfigured frontend)
is sent verbatim and may produce a GraphQL validation error that then trips CR-01.
There is no clamping like the rest of the engine suite implies (`DEFAULT_MAX_RESULTS`).

**Fix:** Clamp before building the payload:
```python
first = max(1, min(int(max_results), 50))  # sane floor/ceiling
payload = {"query": _WAKE_SEARCH_QUERY, "variables": {"q": query.strip(), "first": first}}
```

### WR-03: Token override path is not cached; brand is re-resolved and re-read every search call

**File:** `backend/services/engines/wake_engine.py:280-292`
**Issue:** `_resolve_token` returns the manual override (step 1) *before* checking
`self._token_cache` (step 2), and never populates the cache from the override.
That is functionally fine, but `search()` calls `brand_service.get_brand()` again
on every invocation (line 144) and `_resolve_token` re-reads `wake_access_token`
each time. For the auto-extracted path the cache prevents re-fetching the home
page, but there is no equivalent short-circuit for the override path — minor
redundant work and an inconsistency in the caching story documented in the
docstring ("avoids re-fetching home page on every search call" applies to only
one of the two token sources).

**Fix:** Either document that override is intentionally not cached (cheap dict
read), or seed `self._token_cache = override` so the precedence comment
("override > cache > auto-extract") holds on subsequent calls without re-reading
the brand object. Prefer the explicit comment if you want override changes to take
effect live.

### WR-04: `_resolve_token` ignores HTTP status on the home GET; non-200 pages parsed as if valid

**File:** `backend/services/engines/wake_engine.py:303-309`
**Issue:** Unlike the GraphQL POST (which calls `raise_for_status()`), the home-page
GET never inspects `resp.status`. A 403 (anti-bot block), 404, or 5xx still has its
body fed to `_TOKEN_RE`. In the happy path the regex simply misses and you fall to
the "not found" branch, but a hostile/error page that *happens* to contain a
`storefrontAccessToken:'...'` string (e.g. a cached CDN error page or an attacker-
controlled mirror) would be trusted. Combined with WR-01 this makes auto-extraction
failures hard to diagnose.

**Fix:** Check status before parsing:
```python
async with session.get(store_url, allow_redirects=False) as resp:
    if resp.status != 200:
        logger.warning("[Wake] home GET %s returned %s; skipping token extraction",
                        store_url, resp.status)
        return None
    html = await resp.text()
```

### WR-05: No request timeout on the home GET or GraphQL POST; a hung storefront blocks the search

**File:** `backend/services/engines/wake_engine.py:186, 303`
**Issue:** Neither `session.post(GRAPHQL_ENDPOINT, ...)` nor `session.get(store_url, ...)`
passes an `aiohttp.ClientTimeout`, and `SessionManager.get_session()`
(`core/session_manager.py:23`) creates the `ClientSession` without a default
timeout. A slow or hung Wake endpoint will stall the coroutine indefinitely; inside
`search_all_brands`'s `asyncio.gather` this stalls the entire multi-brand search.
The sibling pattern in `routes_brands.py:44` explicitly sets
`timeout=aiohttp.ClientTimeout(total=5)`.

**Fix:** Add an explicit timeout to both calls, mirroring `routes_brands.py`:
```python
timeout = aiohttp.ClientTimeout(total=10)
async with session.post(GRAPHQL_ENDPOINT, json=payload, headers=headers, timeout=timeout) as resp:
    ...
async with session.get(store_url, allow_redirects=False, timeout=aiohttp.ClientTimeout(total=5)) as resp:
    ...
```

## Info

### IN-01: `getattr(brand, "domain", None)` on a dict relies on a non-obvious fallback

**File:** `backend/services/engines/wake_engine.py:150-155`, `272-284`
**Issue:** `getattr(brand, "domain", None) or (brand.get("domain", "") if isinstance(brand, dict) else "")`
works because `getattr(dict_instance, "domain", None)` returns `None` (dicts have no
`domain` attribute), letting the `or` fall through to `.get`. This is correct but
fragile and non-obvious; a reader could reasonably think `getattr` on a dict throws.
The same pattern is duplicated in SFCC. Consider a small shared helper
(`_resolve_field(brand, "domain", default)`) to centralize the dict/Pydantic compat
and document the `getattr`-returns-None behavior.
**Fix:** Extract a `_brand_field(brand, name, default)` helper in a shared module;
both WakeEngine and SFCCEngine import it.

### IN-02: Product-URL construction does not validate `aliasComplete` scheme/host

**File:** `backend/services/engines/wake_engine.py:209-211`
**Issue:** `product_url = f"https://{domain}/{alias.lstrip('/')}"` assumes
`aliasComplete` is always a relative path (confirmed by spike 007). If a future
Wake response returns an absolute URL (`https://evil/...`) in `aliasComplete`, the
result is `https://{domain}/https://evil/...` — harmless today, but no assertion
guards the spike's assumption. Low risk since it is server-supplied from an
authenticated GraphQL call.
**Fix:** Optionally assert/strip a leading scheme, or skip nodes whose
`aliasComplete` contains `://`.

### IN-03: `available` defaults to `True` for nodes missing the field

**File:** `backend/services/engines/wake_engine.py:219`
**Issue:** `available = node.get("available", True)` defaults missing availability
to in-stock. Spike 007 says the field is "present and correct", so this default
only triggers on schema drift — but defaulting an *unknown* availability to
"available" is the optimistic direction and could show out-of-stock items as in
stock if Wake ever omits the field.
**Fix:** Default to `None` (unknown) rather than `True`, letting downstream treat
unknown distinctly from confirmed-available.

### IN-04: Stale comment reference and dead `test_factory_wake_still_raises` note

**File:** `backend/tests/test_sfcc_engine.py:235-236`
**Issue:** Lines 235-236 are an explanatory comment about a removed test
(`test_factory_wake_still_raises`). It is accurate but is commented-out-code-adjacent
narration left in a test file. Minor housekeeping — harmless but accumulates.
**Fix:** Remove the obsolete note now that the WakeEngine test in
`test_wake_engine.py` is the source of truth, or move it to the phase changelog.

---

_Reviewed: 2026-06-25T00:54:43Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
