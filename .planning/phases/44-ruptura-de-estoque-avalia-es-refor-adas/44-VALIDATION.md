---
phase: 44
slug: ruptura-de-estoque-avalia-es-refor-adas
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-29
---

# Phase 44 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | `pytest.ini` with `testpaths = backend/tests` and `pythonpath = backend` |
| **Quick run command** | `python -m pytest backend/tests/test_stock_summary_service.py backend/tests/test_review_comments_service.py backend/tests/test_stock_depth_service.py -q` |
| **Full suite command** | `python -m pytest` |
| **Estimated runtime** | Quick: under 15s after Wave 0; full suite: project dependent |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest backend/tests/test_stock_summary_service.py backend/tests/test_review_comments_service.py backend/tests/test_stock_depth_service.py -q`
- **After every plan wave:** Run `python -m pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds for the Phase 44 quick suite after Wave 0

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 44-W0-01 | TBD | 0 | STOCK-01 | N/A | `stock_availability=None` never changes `rupture_pct`; all-unknown returns `rupture_pct=None` | unit | `python -m pytest backend/tests/test_stock_summary_service.py -q` | missing - Wave 0 | pending |
| 44-W0-02 | TBD | 0 | STOCK-02 | T-44-probe-flood / T-44-false-zero | Probe is explicit, throttled, cleans up browser context/page, and maps blocked/unsupported/failure to states rather than fake quantities | unit | `python -m pytest backend/tests/test_stock_depth_service.py -q` | missing - Wave 0 | pending |
| 44-W0-03 | TBD | 0 | STOCK-02 | T-44-search-probe | Normal search routes do not invoke stock-depth/cart-probe paths | regression | `python -m pytest backend/tests/test_stock_depth_service.py::test_search_path_does_not_call_probe -q` | missing - Wave 0 | pending |
| 44-W0-04 | TBD | 0 | REVW-01 | T-44-review-payload | Review comments are compact, page-limited, deduped, and `unsupported` for unknown providers | unit | `python -m pytest backend/tests/test_review_comments_service.py -q` | missing - Wave 0 | pending |
| 44-W0-05 | TBD | 0 | STOCK-01 / STOCK-02 / REVW-01 | T-44-route-inputs | API request models validate scan/product identity, brand/provider state, and max page/probe limits | integration | `python -m pytest backend/tests/test_phase44_routes.py -q` | missing - Wave 0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_stock_summary_service.py` — stubs and red tests for STOCK-01 formula, unknown counts, and all-unknown null percentage.
- [ ] `backend/tests/test_stock_depth_service.py` — stubs and red tests for STOCK-02 explicit action, throttle/cap behavior, cleanup, and state mapping.
- [ ] `backend/tests/test_review_comments_service.py` — stubs and red tests for REVW-01 provider routing, page cap, dedup, compact schema, and unsupported state.
- [ ] `backend/tests/test_phase44_routes.py` — stubs and red tests for API validation/wiring if endpoints are planned.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Controlled cart-probe returns a real stock-depth estimate for at least one supported product | STOCK-02 | Requires a live competitor storefront/cart behavior and must be low-frequency | Use a controlled scan product, trigger the explicit stock-depth action once, confirm result label includes "máximo observado/estimativa via cart-probe", and confirm no search endpoint initiated the probe. |
| Hugo Boss rupture UAT, if used | STOCK-01 | Hugo Boss category scan has a known Phase 39 dependency documented in `.planning/todos/pending/hugoboss-vtex-io-category-scan.md` | Only use Hugo Boss after the VTEX-IO category-scan todo is resolved; otherwise use another working brand and record HB as dependency risk. |
| Provider comment endpoint mapping for Trustvox/VTEX native | REVW-01 | Exact live provider comment fields may differ from summary endpoints | Run one low-frequency provider check per supported provider and verify normalized `review_id`, `rating`, `title`, `text`, `author`, `created_at`, and `source_provider`. |

---

## Validation Sign-Off

- [x] All phase requirements have automated test targets or manual-only justifications
- [x] Sampling continuity: no 3 consecutive implementation tasks should run without the Phase 44 quick suite after Wave 0
- [x] Wave 0 covers all missing Phase 44 test files
- [x] No watch-mode flags
- [x] Feedback latency target under 15s for quick suite after Wave 0
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** ready for planning
