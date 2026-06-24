---
phase: 31
slug: engine-sfcc-browser-p-blico-lacoste-hugoboss
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-24
---

# Phase 31 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `31-RESEARCH.md` § Validation Architecture. Task IDs are linked at plan time.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pytest.ini` (repo root) — `testpaths = backend/tests`, `pythonpath = backend` |
| **Quick run command** | `pytest backend/tests/test_sfcc_engine.py -x` |
| **Full suite command** | `pytest backend/tests/ -ra` |
| **Estimated runtime** | ~15 seconds (hermetic — `BrowserManager.fetch_html` mocked, no real browser launched) |

---

## Sampling Rate

- **After every task commit:** Run `pytest backend/tests/test_sfcc_engine.py -x`
- **After every plan wave:** Run `pytest backend/tests/ -ra`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

> Task IDs / Plan / Wave columns are filled by the planner (step 8) and the nyquist auditor. Rows below seed the contract from the research test map.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | COMP-03 / SC-2 | — | Factory returns real engine, not `NotImplementedError` | unit | `pytest backend/tests/test_sfcc_engine.py::test_factory_returns_sfcc_engine -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-04 / BaseEngine | — | All abstract methods implemented (no `TypeError` on instantiation) | unit | `pytest backend/tests/test_sfcc_engine.py::test_sfcc_engine_implements_base_engine -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | COMP-03 / SC-3 | T-31 price-tamper | `parse_price_br("R$ 1.234,56") == 1234.56`; `parse_price_br("R$ 119,00") == 119.0`; rejects bare integers / US format | unit | `pytest backend/tests/test_sfcc_engine.py::test_parse_price_br -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | COMP-03 / SC-1 | — | `search("polo", max_results=3)` returns `BrandSearchResult` with ≥1 product (title, URL, `price_full > 0`) | unit (browser mocked) | `pytest backend/tests/test_sfcc_engine.py::test_search_returns_products -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-07 / enrichment | — | Each product in search result has `image_url` (PDP enrichment ran) | unit (browser mocked) | `pytest backend/tests/test_sfcc_engine.py::test_search_results_have_image -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | COMP-03 / SC-4 | — | `calculate_shipping(product, "01310-100")` returns `None` (no false "Frete Grátis") | unit (no mock) | `pytest backend/tests/test_sfcc_engine.py::test_calculate_shipping_returns_none -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-06 / stub | DoS partial-HTML | `discover_categories()` returns `[]` without crash when nav empty/missing | unit (browser mocked, empty nav) | `pytest backend/tests/test_sfcc_engine.py::test_discover_categories_stub -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_sfcc_engine.py` — stubs for all rows above (COMP-03 SC-1..4, D-04, D-06, D-07)
- [ ] `backend/services/engines/sfcc_engine.py` — engine class under test
- [ ] `backend/services/engines/sfcc_parser.py` — parser helpers including `parse_price_br()`
- [ ] Mock pattern: `core.browser_manager.BrowserManager.fetch_html` as `AsyncMock` (per `test_engine_detection.py`)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live search returns real products from `lacoste.com.br` and `hugoboss.com.br` | COMP-03 / SC-1 | Requires network + live BR storefronts; CI mocks the browser | Onboard both brands; run a real search for a known term (e.g. "polo"); confirm ≥1 product per brand with title/URL/price in reais |
| Price rendered as `R$ X,XX` in the search UI with no "Frete Grátis" badge | COMP-03 / SC-3, SC-4 | Visual frontend rendering of `None` shipping | Inspect the comparative results view; confirm shipping block absent and price shown in reais |
| BR search URL pattern for each store | Open Question #1 | Storefront URL config not spike-validated; must be observed live | Wave 0 smoke: navigate native search box on each `.com.br` store; record final resolved URL pattern as a constant |
| Category-tree discovery feasibility on BR stores (D-06 confirm) | D-05 / D-06 | Not spike-validated; nav may need JS interaction | If `discover_categories()` returns items, spot-check they are valid category paths; if `[]`, confirm graceful stub (no crash) is acceptable per D-06 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
