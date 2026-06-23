---
status: passed
phase: 30-detec-o-de-engine-sfcc-wake
requirements: [COMP-05]
verified_by: orchestrator-inline
verified_date: "2026-06-23"
plans_verified: ["30-01", "30-02", "30-03"]
tests: "46 passed (9 engine-detection + 37 brand/engine/search regression)"
---

# Phase 30 Verification — Detecção de Engine SFCC & Wake

**Verdict: PASSED.** The phase goal is achieved: `detect_engine` now recognizes and labels `sfcc` and `wake` (instead of `unknown`), `EngineFactory.get_engine` guards those engines diagnosably until Phases 31/32 ship, and a GREEN test suite proves SC-1..SC-4. COMP-05 is satisfied.

> Verification was performed inline by the execute-phase orchestrator (not a separate gsd-verifier agent) because an active provider session limit was terminating spawned subagents. Evidence is direct: source inspection plus 46 passing tests.

## Phase Goal (from ROADMAP)

> `detect_engine` reconhece e rotula `sfcc` e `wake` (em vez de `unknown`), liberando o cadastro dessas marcas com o engine correto (COMP-05).

**Achieved** — see SC mapping below.

## Requirement Traceability

| Req | Description | Status | Evidence |
|-----|-------------|--------|----------|
| COMP-05 | Ao cadastrar uma marca SFCC/Wake, `detect_engine` retorna `sfcc`/`wake` (não `unknown`), permitindo cadastro com engine certo em vez de desativar | ✓ Satisfied | `backend/api/routes_brands.py` `detect_engine` (Wake L51-53, SFCC probe L75-85); SC-2/SC-1/SC-3 tests green |

## Success Criteria

| SC | Criterion | Test(s) | Code | Result |
|----|-----------|---------|------|--------|
| SC-1 | SFCC labeled via last-resort browser probe (exclusive demandware host) | `test_sfcc_detected_via_browser` | `routes_brands.py` L75-81 | ✓ PASS |
| SC-2 | Wake labeled `wake` (fbitsstatic.net), not `unknown` | `test_wake_commerce_detected_returns_wake` | `routes_brands.py` L51-53 | ✓ PASS |
| SC-3 | sfcc/wake brands persist ACTIVE (D-04 deactivates only `unknown`) | `test_sfcc_brand_stays_active`, `test_wake_brand_stays_active` | `routes_brands.py` `create_brand` L104-109 (unchanged) | ✓ PASS |
| SC-4 | Anti-false-positive: 403 / marker-free rendered HTML → `unknown` | `test_sfcc_anti_false_positive_403_no_demandware`, `test_all_probes_fail_returns_unknown` | `routes_brands.py` L79 (exclusive markers, not bare `demandware`) | ✓ PASS |

## must_haves Check (per plan)

### 30-01 — detect_engine Wake flip + SFCC probe
- [x] `fbitsstatic.net` branch returns `"wake"` (was `"unknown"`) — `routes_brands.py:51-53`
- [x] Last-resort SFCC browser probe added after HTML fallback, before final `return "unknown"` — `routes_brands.py:75-88`
- [x] SFCC verdict uses exclusive hosts `demandware.static` / `demandware.edgesuite.net`, not bare `demandware` — `routes_brands.py:79`
- [x] `BrowserManager` imported lazily inside try; probe degrades to `unknown` on any exception (no crash) — `routes_brands.py:75-85`

### 30-02 — EngineFactory guard
- [x] `get_engine` raises `NotImplementedError` for `engine_type` `"sfcc"` AND `"wake"` (single guard) — `factory.py:51-54`
- [x] Guard sits after the `shopify` branch and before `return VTEXEngine(brand_key)` — `factory.py:42-56`
- [x] `vtex`, unknown legacy strings → `VTEXEngine`; `shopify` → `ShopifyEngine`; virtual marketplaces unchanged — `factory.py:22-45` (diff: +12/-1, only the guard block)
- [x] `NotImplementedError` (Exception subclass) caught by `_search_one`'s `except Exception` → `BrandSearchResult.error`, gather not downed — `factory.py:75-91` (unchanged)

### 30-03 — GREEN detection suite
- [x] shopify + vtex regression scenarios present unchanged
- [x] Wake test asserts `"wake"`; SFCC test patches `BrowserManager.fetch_html` (AsyncMock, demandware HTML) → `"sfcc"`
- [x] 403 anti-false-positive → `"unknown"`; all-probes-fail extended to mock browser → `"unknown"`
- [x] SC-3 stays-active tests assert `is_active is True` and `set_active` not called — `create_brand` unmodified
- [x] `pytest backend/tests/test_engine_detection.py` exits 0 → **9 passed**

## Test Evidence

```
backend $ python -m pytest tests/test_engine_detection.py -q
......... 9 passed in 2.37s

backend $ python -m pytest tests/test_brand_active.py tests/test_brand_gate.py \
    tests/test_netshoes_engine.py tests/test_shipping_engines.py \
    tests/test_vtex_brand_onboarding_contract.py tests/test_search_history_comparative.py -q
..................................... 37 passed in 5.32s
```

No regressions in the brand/engine/search surface affected by the `detect_engine` and `EngineFactory.get_engine` changes.

## Deviations

- **30-03 mock seam target** changed from the plan's `api.routes_brands.BrowserManager.fetch_html` to `core.browser_manager.BrowserManager.fetch_html`. The former is invalid because 30-01 implemented the SFCC probe with a lazy local import, so `api.routes_brands` has no module-level `BrowserManager` attribute. Functional criteria are met; the `verify.key-links` regex for that exact dotted path will not match by design. Documented in `30-03-SUMMARY.md`.

## Outstanding (non-blocking, routed)

- **Security:** `workflow.security_enforcement=true` and no `30-SECURITY.md` exists. Plans carry STRIDE threat models (T-30-01..09); run `/gsd-secure-phase 30` to formally verify mitigations.
- **Code review:** formal `/gsd-code-review 30` (subagent-based) was deferred due to the active session limit. Inline review of the diff (12 production lines in `factory.py`; tests-only in 30-03) found no correctness, security, or style issues.
