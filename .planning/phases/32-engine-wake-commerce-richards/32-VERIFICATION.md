---
phase: 32-engine-wake-commerce-richards
verified: 2026-06-24T22:30:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 3/4
  gaps_closed:
    - "SC-2 PARTIAL — GraphQL null-data AttributeError (CR-01): guard added before parse block; null-safe chained .get() with `or {}` coalescing; test_search_graphql_errors_in_200 regression test added. Commit 2790734."
  gaps_remaining: []
  regressions: []
human_verification: []
---

# Phase 32: Engine Wake Commerce — Richards Verification Report

**Phase Goal:** Confirmar empiricamente o fluxo GraphQL + `TCS-Access-Token` da Wake contra a Richards (spike gating) e, uma vez validado, entregar o `WakeEngine` plugado na `EngineFactory` para que o operador onboarde e busque produtos da Richards.
**Verified:** 2026-06-24T22:30:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (commit 2790734)

---

## Step 0: Previous Verification

Previous VERIFICATION.md found. Re-verification mode.

- Previous status: `gaps_found`
- Previous score: 3/4
- Gap to re-check: SC-2 PARTIAL — GraphQL error-response shape (`{"errors":[...],"data":null}`) caused uncaught `AttributeError` in the parse block, bypassing the D-07 structured-error path.
- Items previously VERIFIED (regression check only): SC-1, SC-3, SC-4.

---

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC-1 | Spike demonstrates, against Richards (or Shop2gether), that the Wake GraphQL endpoint responds with products when sent TCS-Access-Token — producing a GO/NO-GO decision BEFORE any engine code | VERIFIED | `.planning/spikes/007-wake-graphql-token-confirmation/experiment.py` and `REPORT.md` exist. REPORT.md contains `## Veredito` with explicit `**GO**`, lists 5 products, A1-A6 all CONFIRMADO, token masked. No regression — files untouched by commit 2790734. |
| SC-2 | With Richards registered and token configured, a product search returns real items (title, URL, price) via the Wake GraphQL API — NOT via the VTEX path | VERIFIED | Happy path: confirmed in prior verification. Error path (CR-01 gap): `wake_engine.py` lines 197-213 now contain an explicit guard that checks `data.get("errors")` and `payload_data is None` BEFORE any chained `.get()` calls. The guard returns a `BrandSearchResult` with the actual GraphQL error message via `D-07` structured path. The parse path (L216-218) uses `or {}` / `or []` coalescing and can only be reached when `payload_data` is confirmed non-None. Regression test `test_search_graphql_errors_in_200` (L200-235 of test file) covers the exact `{"errors":[...],"data":null}` shape, asserts no exception raised, asserts `result.error` is set with the GraphQL message text. Test passes (12/12 in wake suite, 236/236 full suite). |
| SC-3 | WakeEngine is registered in EngineFactory and auto-selected for brands with engine="wake", sending TCS-Access-Token per store in each GraphQL request | VERIFIED | `factory.py` L55-57: `if engine_type == "wake": from services.engines.wake_engine import WakeEngine; return WakeEngine(brand_key)`. Lazy import pattern mirrors SFCC. No `NotImplementedError` in the wake branch. No regression — factory untouched by commit 2790734. |
| SC-4 | TCS-Access-Token is configured per store (not hardcoded global); absent/error token produces a clear diagnosable failure — not 0 silent products | VERIFIED | `_resolve_token` uses per-instance `self._token_cache`. Raises `ValueError` with explicit message when unresolved (D-07). `calculate_shipping` returns `None`. `TestWakeTokenFailure::test_missing_token_returns_error` verifies error propagation. No regression — token logic untouched by commit 2790734. |

**Score: 4/4 truths verified** (SC-2 gap closed by commit 2790734)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.planning/spikes/007-wake-graphql-token-confirmation/experiment.py` | Isolated spike confirming GraphQL+TCS-Access-Token flow | VERIFIED | Exists, 542 lines. Contains `storefront-api.fbits.net/graphql`, `allow_redirects=False`, `variables`, `SessionManager.get_session()`, token masking. |
| `.planning/spikes/007-wake-graphql-token-confirmation/REPORT.md` | GO/NO-GO verdict + evidence | VERIFIED | Contains `## Veredito` with `**GO**`, all required sections, token masked. |
| `backend/core/models.py` | `wake_access_token: Optional[str] = None` in DynamicBrandCreate | VERIFIED | Line 226: `wake_access_token: Optional[str] = None` with D-06 comment. |
| `backend/services/engines/wake_engine.py` | `class WakeEngine(BaseEngine)` — GraphQL search + per-store token + graceful stubs + D-07 error path for HTTP-200 GraphQL errors | VERIFIED | 370 lines. Guard at L197-213 handles `{"errors":[...],"data":null}` shape before parse block. Parse path (L216-218) uses `or {}` / `or []` coalescing. All BaseEngine stubs implemented. No BrowserManager import. |
| `backend/services/engines/factory.py` | `engine_type=='wake'` -> WakeEngine (lazy import, no NotImplementedError) | VERIFIED | L55-57 contain lazy import and `return WakeEngine(brand_key)`. No NotImplementedError in wake branch. |
| `backend/tests/test_wake_engine.py` | Hermetic tests covering SC-2/SC-3/SC-4/D-06/D-08 with SessionManager mocked, including CR-01 regression test | VERIFIED | 372 lines. 12 test methods across 5 test classes. Includes `test_search_graphql_errors_in_200` (new). All 12 pass. |
| `backend/tests/test_sfcc_engine.py` | Removal of `test_factory_wake_still_raises` | VERIFIED | Method removed; only a comment-line reference remains. No regression. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `factory.py` | `wake_engine.py` | Lazy import inside `get_engine` for `engine_type=='wake'` | WIRED | L55-57 confirmed. |
| `wake_engine.py` | `storefront-api.fbits.net/graphql` | `SessionManager.get_session()` POST with `TCS-Access-Token` header and GraphQL variables | WIRED | L175-183. Token header set; payload uses `variables`. |
| `wake_engine.py` | D-07 error path | Guard at L197-213 checks `data.get("errors")` and `payload_data is None` before parse | WIRED (new — gap closure) | Returns `BrandSearchResult.error` with actual GraphQL message text. Previously this link was missing — parse block was outside the try/except and null data triggered AttributeError. |
| `wake_engine.py` | `filter_mens_fashion` / `validate_single` | Quality Gates applied before BrandSearchResult construction | WIRED | L253-267. CAT-01 order maintained. |
| `test_wake_engine.py` | `SessionManager.get_session` | `patch(_SESSION_GET_TARGET)` | WIRED | Used across all test classes requiring network mocking. |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `wake_engine.py` | `edges` (GraphQL response nodes) | POST to `storefront-api.fbits.net/graphql` with real TCS-Access-Token | Yes — confirmed by spike 007 (5 products returned against live Richards) | FLOWING |
| `wake_engine.py` | `BrandSearchResult.error` (error path) | Guard on `data.get("errors")` / `payload_data is None` before parse | Yes — produces actual GraphQL error message text from API response | FLOWING (gap closed) |

---

### Behavioral Spot-Checks

Step 7b: Live network checks skipped (no server running). Spike 007 serves as the single live-network verification gate. The new regression test `test_search_graphql_errors_in_200` provides hermetic behavioral verification of the CR-01 fix without network access.

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All wake engine tests pass (12, including new CR-01 regression) | `python -m pytest backend/tests/test_wake_engine.py -q` | `12 passed in 0.61s` | PASS |
| Full backend suite green (no regressions, 236 total) | `python -m pytest backend/tests/ -q` | `236 passed in 12.48s` | PASS |
| Null-safe coalescing verified | `python -c "d={'data':None}; result = d.get('data') or {}; print(repr(result))"` | `{}` | PASS |

---

### Probe Execution

Step 7c: No probe scripts declared or found in conventional locations for this phase.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| COMP-04 | 32-01, 32-02, 32-03 | Operador consegue onboardar e buscar produtos da Richards (Wake Commerce) via API GraphQL com header TCS-Access-Token por loja | SATISFIED | SC-1 (spike gate GO), SC-2 (search returns products — happy path + error path both correct), SC-3 (factory wiring), SC-4 (token per store + error path) — all 4 SCs now VERIFIED. Commit 2790734 closes the SC-2 CR-01 gap. |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `wake_engine.py` | 303-309 | No HTTP status check on home GET before parsing HTML for token | WARNING | A 403/404/5xx response body is still fed to `_TOKEN_RE`. Combined with `allow_redirects=False`, redirect responses (301 bare apex → www) silently produce empty token extraction. Not a blocker — auto-extract failure is handled gracefully (returns None, then ValueError with clear message via D-07). |
| `wake_engine.py` | 178-182 | `max_results` forwarded to `$first` with no clamp or non-positive guard | WARNING | `max_results=0` or very large value sent verbatim to Wake's `$first`. Not a blocker. |
| `wake_engine.py` | 346 | `calculate_shipping` stub `return None` | INFO | Intentional per D-08. Not a defect. |

No TBD, FIXME, or XXX markers found in phase files. No blockers. The prior BLOCKER (CR-01 / L198-203 AttributeError) is resolved by commit 2790734.

---

### Human Verification Required

No items require human verification. All SC behaviors are verifiable by code inspection and automated test evidence. The live-network confirmation (spike 007) was already executed and its GO verdict is recorded in REPORT.md.

---

## Re-verification Summary

**Gap closed:** SC-2 PARTIAL (CR-01) is now FULLY VERIFIED.

Commit 2790734 introduced two targeted changes:

1. `backend/services/engines/wake_engine.py` — A guard block at lines 197-213 intercepts the `{"errors":[...],"data":null}` response shape before the parse block. It checks `data.get("errors")` and `data.get("data") is None`, extracts the error message from the GraphQL `errors` array, and returns a `BrandSearchResult` with `error` set to the actual GraphQL message. The parse path (lines 216-218) additionally uses `or {}` / `or []` coalescing throughout, so even if the guard were bypassed no `AttributeError` could arise. The `payload_data` variable is confirmed non-None before line 216 is reached.

2. `backend/tests/test_wake_engine.py` — `test_search_graphql_errors_in_200` (class `TestWakeEngineSearch`) covers the exact `{"errors": [{"message": "Invalid storefront access token"}], "data": null}` response shape. It asserts: (a) no exception is raised, (b) `result.products == []`, (c) `result.error` is set, (d) `"Invalid storefront access token"` appears in `result.error`. This is a direct regression guard for CR-01.

No regressions in SC-1, SC-3, or SC-4: those code paths were not modified by commit 2790734, and the full backend suite (236 tests) is green.

**Phase 32 goal is fully achieved.**

---

_Verified: 2026-06-24T22:30:00Z_
_Verifier: Claude (gsd-verifier) — re-verification after gap closure_
