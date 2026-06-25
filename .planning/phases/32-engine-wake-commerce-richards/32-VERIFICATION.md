---
phase: 32-engine-wake-commerce-richards
verified: 2026-06-24T15:00:00Z
status: gaps_found
score: 3/4 must-haves verified
overrides_applied: 0
gaps:
  - truth: "WakeEngine.search returns a BrandSearchResult with >=1 real product (title+URL+price) via Wake GraphQL, never via the VTEX path (SC-2, D-10/D-11)"
    status: partial
    reason: >
      The happy-path search flow is correctly implemented and tested. However, the
      GraphQL error-response shape (HTTP 200 + { "errors": [...], "data": null })
      causes an uncaught AttributeError in the parse block (line 199):
      `data.get("data", {})` returns None (not {}) when the key is present with
      value null, and the chained `.get("search", {})` raises AttributeError. This
      block is outside the try/except that ends at line 195. The AttributeError is
      ultimately caught by factory._search_one as a generic Exception, but the
      structured D-07 error path (BrandSearchResult.error with the GraphQL message)
      is bypassed — the operator receives a cryptic "AttributeError" string instead
      of the actionable GraphQL error. Verified by running:
        python -c "d={'data':None}; d.get('data',{}).get('search',{})"
      which raises AttributeError. This means any malformed/throttled/expired-token
      response from the Wake GraphQL API will produce an opaque crash rather than a
      diagnosable error message, defeating the explicit D-07 design.
    artifacts:
      - path: "backend/services/engines/wake_engine.py"
        issue: "Lines 198-203: chained .get() on data.get('data',{}) raises AttributeError when data['data'] is null (GraphQL error shape). Block is outside the try/except. Fix: use `(data.get('data') or {})` OR check data.get('errors') before parsing."
    missing:
      - "Guard for GraphQL-level errors before the parse block: check data.get('errors') and/or use `(data.get('data') or {})` null-coalescing on line 199"
      - "Test case for the GraphQL errors-in-200 response shape (CR-01 from code review)"
human_verification: []
---

# Phase 32: Engine Wake Commerce — Richards Verification Report

**Phase Goal:** Confirmar empiricamente o fluxo GraphQL + `TCS-Access-Token` da Wake contra a Richards (spike gating) e, uma vez validado, entregar o `WakeEngine` plugado na `EngineFactory` para que o operador onboarde e busque produtos da Richards.
**Verified:** 2026-06-24T15:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Step 0: Previous Verification

No previous VERIFICATION.md found. Initial mode.

---

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC-1 | Spike demonstrates, against Richards (or Shop2gether), that the Wake GraphQL endpoint responds with products when sent TCS-Access-Token — producing a GO/NO-GO decision BEFORE any engine code | VERIFIED | `.planning/spikes/007-wake-graphql-token-confirmation/experiment.py` and `REPORT.md` exist. REPORT.md contains `## Veredito` with explicit `**GO**`, lists 5 products returned (Camisa Linho Hortencia etc.), A1-A6 all CONFIRMADO, token prefix `tcs_richa_35...` masked, all required sections present. |
| SC-2 | With Richards registered and token configured, a product search returns real items (title, URL, price) via the Wake GraphQL API — NOT via the VTEX path | PARTIAL | `WakeEngine.search()` correctly posts to `storefront-api.fbits.net/graphql` with variables, parses `search.products.edges[].node`, builds URLs using `https://{domain}/{alias}`, applies Quality Gates, and returns BrandSearchResult. Tests pass with mocked SessionManager. **BUT**: when Wake returns HTTP 200 with `{"errors":[...],"data":null}` (GraphQL app-level error), the parse block at L198-203 raises `AttributeError` because `data.get("data",{})` returns `None` (not `{}`) when the key is present with value `null`. This block is outside the try/except. The D-07 structured error path is bypassed — produces opaque AttributeError string rather than the actionable GraphQL error message. |
| SC-3 | WakeEngine is registered in EngineFactory and auto-selected for brands with engine="wake", sending TCS-Access-Token per store in each GraphQL request | VERIFIED | `factory.py` L55-57: `if engine_type == "wake": from services.engines.wake_engine import WakeEngine; return WakeEngine(brand_key)`. Lazy import mirrors SFCC pattern. No `NotImplementedError` remains in the wake branch. `TCS-Access-Token` header is sent in every POST. Test `TestWakeFactory::test_factory_returns_wake_engine` passes. |
| SC-4 | TCS-Access-Token is configured per store (not hardcoded global); absent/error token produces a clear diagnosable failure — not 0 silent products | VERIFIED | `_resolve_token` uses per-instance `self._token_cache`, checks `brand.wake_access_token` override first, then cache, then auto-extracts. Raises `ValueError` with explicit message when unresolved (`D-07`). `calculate_shipping` returns `None` (no false "Frete Gratis" badge). `TestWakeTokenFailure::test_missing_token_returns_error` verifies ValueError is captured as `BrandSearchResult.error` via `_search_one`. |

**Score: 3/4 truths verified** (SC-2 is PARTIAL due to the null-data AttributeError gap; SC-1, SC-3, SC-4 are VERIFIED)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.planning/spikes/007-wake-graphql-token-confirmation/experiment.py` | Isolated spike confirming GraphQL+TCS-Access-Token flow | VERIFIED | Exists, 542 lines. Contains `storefront-api.fbits.net/graphql`, `allow_redirects=False`, `variables` (not f-string), `SessionManager.get_session()`, token masking. Syntactically valid Python. |
| `.planning/spikes/007-wake-graphql-token-confirmation/REPORT.md` | GO/NO-GO verdict + evidence (product, masked token, endpoint, confirmed fields) | VERIFIED | Exists. Contains `## Veredito` with `**GO**`, `## Evidencia`, `## Campos confirmados`, `## Formato do preco`, `## Token auto-extraido`, `## Alvo testado`. Token shown as `tcs_richa_35...` (masked). 5 products listed. A1-A6 all confirmed. |
| `backend/core/models.py` | `wake_access_token: Optional[str] = None` in DynamicBrandCreate | VERIFIED | Line 226: `wake_access_token: Optional[str] = None`. After `logo_url`, inherits automatically to DynamicBrand. Does not break existing brands. |
| `backend/services/engines/wake_engine.py` | `class WakeEngine(BaseEngine)` — GraphQL search + per-store token + graceful stubs | PARTIAL | Exists, 354 lines (>120 min). Contains `class WakeEngine(BaseEngine)`, `storefront-api.fbits.net/graphql`, `variables`, `TCS-Access-Token`, `return None` in calculate_shipping, `return []` in discover_categories/get_catalog, `allow_redirects=False`. No BrowserManager import. **Gap: null-data response handling (CR-01).** |
| `backend/services/engines/factory.py` | `engine_type=='wake'` -> WakeEngine (lazy import, no NotImplementedError) | VERIFIED | L52-57 contain lazy import `from services.engines.wake_engine import WakeEngine` and `return WakeEngine(brand_key)`. No `NotImplementedError` in the wake branch. Pattern mirrors SFCC (L48-50). |
| `backend/tests/test_wake_engine.py` | Hermetic tests covering SC-2/SC-3/SC-4/D-06/D-08 with SessionManager mocked | VERIFIED | Exists, 334 lines (>80 min). Contains `TestWakeFactory`, `TestWakeEngineSearch`, `TestWakeTokenFailure`, `TestWakeModels`, `TestWakeStubs`. 11 test methods. Uses `core.session_manager.SessionManager.get_session` mock seam (not BrowserManager). Suite reported 235 passed. |
| `backend/tests/test_sfcc_engine.py` | Removal of `test_factory_wake_still_raises` method | VERIFIED | Line 235 is a comment-only reference (`# test_factory_wake_still_raises removed in Phase 32 plan 02 — WakeEngine is now live.`). No active `def test_factory_wake_still_raises` method exists. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `factory.py` | `wake_engine.py` | Lazy import `from services.engines.wake_engine import WakeEngine` inside `get_engine` for `engine_type=='wake'` | WIRED | L52-57 confirmed. Mirrors SFCC pattern exactly. |
| `wake_engine.py` | `storefront-api.fbits.net/graphql` | `SessionManager.get_session()` POST with header `TCS-Access-Token` and GraphQL variables | WIRED | L175-188. `TCS-Access-Token` set from resolved token, payload uses `variables={"q":..., "first":...}`. No f-string interpolation of query term. |
| `wake_engine.py` | `filter_mens_fashion` / `validate_single` | Quality Gates applied before BrandSearchResult construction | WIRED | L238-252: `self.filter_mens_fashion(parsed_dicts)` then `self.validate_single(p)` for each item. Correct CAT-01 order. |
| `test_wake_engine.py` | `SessionManager.get_session` | `patch(_SESSION_GET_TARGET)` where `_SESSION_GET_TARGET = "core.session_manager.SessionManager.get_session"` | WIRED | L31, L143, L171, L230. No live network in tests. |
| `test_wake_engine.py` | `WakeEngine` / `EngineFactory` | Import + `assertIsInstance` via `EngineFactory.get_engine` | WIRED | `TestWakeFactory::test_factory_returns_wake_engine` L98-113. |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `wake_engine.py` | `edges` (GraphQL response nodes) | POST to `storefront-api.fbits.net/graphql` with real TCS-Access-Token per store | Yes — confirmed by spike 007 (5 products returned against live Richards) | FLOWING (happy path) / HOLLOW on GraphQL error shape (CR-01 gap) |
| `test_wake_engine.py` | `_GRAPHQL_RESPONSE` fixture | Hardcoded mock dict, mirrors spike 007 confirmed shape | Intentional mock — no live data | STATIC (intentional — hermetic tests) |

---

### Behavioral Spot-Checks

Step 7b: SKIPPED for live network checks (no server running). The spike 007 serves as the single live-network verification gate. Tests are hermetic. Suite count (235 passed) was independently confirmed by the executor and the verification prompt.

---

### Probe Execution

Step 7c: No probe scripts declared or found in conventional locations for this phase.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| COMP-04 | 32-01, 32-02, 32-03 | Operador consegue onboardar e buscar produtos da Richards (Wake Commerce) via API GraphQL com header TCS-Access-Token por loja | PARTIALLY SATISFIED | SC-1 (spike gate), SC-3 (factory), SC-4 (token per store + error) verified. SC-2 (search returns products) PARTIAL — happy path works, GraphQL error shape (data:null) triggers uncaught AttributeError that bypasses D-07 structured error. |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `wake_engine.py` | 198-203 | `data.get("data", {})` chained `.get()` when `data["data"]` can be `null` (GraphQL error shape) | BLOCKER | Raises `AttributeError` on any GraphQL-level error (HTTP 200 + `errors:[]` + `data:null`). Bypasses D-07 structured error path. Verified: `python -c "{'data':None}.get('data',{}).get('search',{})"` raises `AttributeError`. |
| `wake_engine.py` | 303-309 | No HTTP status check on home GET before parsing HTML for token | WARNING | A 403/404/5xx response body is still fed to `_TOKEN_RE`. Combined with `allow_redirects=False`, redirect responses (301 bare apex → www) silently produce empty token extraction. |
| `wake_engine.py` | 178-182 | `max_results` forwarded to `$first` with no clamp or non-positive guard | WARNING | `max_results=0` or very large value sent verbatim to Wake's GraphQL `$first` argument. |
| `wake_engine.py` | 327 | `calculate_shipping` stub `return None` | INFO | Intentional per D-08. Not a defect. |
| `tests/test_wake_engine.py` | — | No test for GraphQL error shape (`data:null`) | WARNING | The CR-01 bug is not caught by any test in the suite. |

**Debt marker gate:** No `TBD`, `FIXME`, or `XXX` markers found in the phase files.

The BLOCKER anti-pattern (CR-01) is the same as the `gaps:` entry above — it is the root cause of SC-2 being PARTIAL.

---

### Human Verification Required

No items require human verification. All observable SC behaviors can be verified by code inspection and automated test evidence. The live-network confirmation (spike 007) was already executed and its GO verdict is recorded in REPORT.md.

---

## Gaps Summary

**1 gap blocking full goal achievement:**

**SC-2 PARTIAL — GraphQL null-data AttributeError (CR-01)**

The `WakeEngine.search()` happy path is correct and tested. However, when the Wake GraphQL API returns HTTP 200 with a body of shape `{"errors":[...],"data":null}` (which occurs for expired tokens, throttling, or schema errors), the parse block at `wake_engine.py:198-203` raises an uncaught `AttributeError`:

```python
# Line 199 — THE BUG:
edges = (
    data.get("data", {})   # returns None when key present with value null
    .get("search", {})     # AttributeError: 'NoneType'.get
    ...
)
```

`dict.get(key, default)` only uses the default when the key is **absent**. When the key is present with `null`, it returns `None`. The chained `.get()` then raises `AttributeError`. This block is outside the `try/except` that ends at line 195.

The `AttributeError` is ultimately caught by `factory._search_one`'s broad `except Exception`, so the search does not crash entirely. But the `BrandSearchResult.error` field receives the string `"AttributeError: 'NoneType' object has no attribute 'get'"` instead of the actual GraphQL error message — defeating the explicit D-07 design ("clear diagnostic message") and making the error non-actionable for the operator.

**Fix required (minimal):** Replace line 199 with `(data.get("data") or {})` to null-coalesce, AND add a guard before the parse block to check `data.get("errors")` and return a `BrandSearchResult` with the actual GraphQL error message.

This gap is flagged by the existing `32-REVIEW.md` as CR-01 (Blocker). The remaining 5 REVIEW findings (WR-01 through WR-05, IN-01 through IN-04) are warnings/info and do not block goal achievement — they concern robustness of the token auto-extraction and missing timeouts, not the core SC-1/SC-3/SC-4 behaviors.

**Root cause grouping:** The single root cause is the missing null-guard on `data["data"]` after a GraphQL POST. One targeted fix resolves SC-2 fully.

---

_Verified: 2026-06-24T15:00:00Z_
_Verifier: Claude (gsd-verifier)_
