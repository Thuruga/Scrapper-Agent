---
phase: 33
slug: frete-via-checkout-nos-sites-vtex
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-24
---

# Phase 33 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x; TypeScript compiler + Vite build; ESLint |
| **Config file** | `pytest.ini`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `frontend/eslint.config.js` |
| **Quick run command** | `python -m pytest backend/tests/test_vtex_shipping.py backend/tests/test_vtex_api_client.py backend/tests/test_search_shipping_contract.py -q` |
| **Full suite command** | `python -m pytest backend/tests -q && npm run lint --prefix frontend && npm run build --prefix frontend` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run the narrowest test file named in the task's `<verify>` block.
- **After every plan wave:** Run `python -m pytest backend/tests -q` plus frontend lint/build when frontend files have changed.
- **Before `/gsd-verify-work`:** Full suite must be green.
- **Max feedback latency:** 120 seconds.

---

## Threat References

| Ref | Threat | Required mitigation |
|-----|--------|---------------------|
| T-33-01 | SSRF through a caller-controlled checkout host | Build simulation URL only from the persisted VTEX brand domain; request payload never accepts a host. |
| T-33-02 | CEP/payload leakage in logs | Log brand/status/attempt only; no full payload or CEP at info/error level. |
| T-33-03 | A failing store stalls/cancels the whole search | Bound timeout and concurrency, retry once, absorb per-product failures. |
| T-33-04 | Untrusted SLA payload corrupts prices/states | Validate delivery channel, non-negative integer cents, estimate format, and Pydantic output. |

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 33-01-01 | 01 | 1 | FRET-05 | T-33-04 | Pickup filtered; cents and estimate units parsed deterministically | unit | `python -m pytest backend/tests/test_vtex_shipping.py -q` | ❌ task creates | ⬜ pending |
| 33-01-02 | 01 | 1 | FRET-05 | — | Additive model preserves zero-vs-null and legacy fields | unit | `python -m pytest backend/tests/test_vtex_shipping.py backend/tests/test_vtex_api_client.py -q` | partial | ⬜ pending |
| 33-02-01 | 02 | 2 | FRET-05 | Persisted domain only; SKU and seller paired; one bounded retry | integration | `python -m pytest backend/tests/test_vtex_api_client.py -q` | ✅ | ⬜ pending |
| 33-02-02 | 02 | 2 | FRET-05 | Default CEP endpoint exposes no secret and search serializes options | API contract | `python -m pytest backend/tests/test_search_shipping_contract.py -q` | ❌ task creates | ⬜ pending |
| 33-03-01 | 03 | 3 | FRET-05 | Default config never overwrites edited CEP; invalid CEP blocks request | static/behavior | `npm run lint --prefix frontend && npm run build --prefix frontend` | ✅ infrastructure | ⬜ pending |
| 33-03-02 | 03 | 3 | FRET-05 | Delivery list excludes pickup and keeps price/freight separate | static/behavior | `npm run lint --prefix frontend && npm run build --prefix frontend` | ✅ infrastructure | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing pytest, TypeScript, Vite, and ESLint infrastructure covers the phase. New phase-specific test files are created test-first inside their owning implementation tasks; no framework installation or shared fixture bootstrap is required.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live VTEX checkout smoke | FRET-05 | Shipping options depend on live store inventory, SLA configuration, and CEP | Search one onboarded VTEX brand with a non-sensitive test CEP; confirm at least one home-delivery option, pickup absent, reais displayed, and one failed brand does not cancel others. |
| Visible session CEP behavior | FRET-05 | Repository has no frontend component-test runner | Open brand search; confirm default CEP is visible, edit it, switch tabs and return (edited value remains), then reload (default returns). |

---

## Validation Sign-Off

- [x] All anticipated tasks have automated verification or existing infrastructure.
- [x] Sampling continuity: no three consecutive tasks without automated verify.
- [x] Wave 0 covers all missing infrastructure references.
- [x] No watch-mode flags.
- [x] Feedback latency target is below 120 seconds.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** pending plan checker
