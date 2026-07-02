---
phase: 41
slug: abstracao-de-frete-marcas-nao-vtex
status: verified
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-29
verified: 2026-07-02
---

# Phase 41 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `41-RESEARCH.md` and `41-CONTEXT.md`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Backend framework** | pytest |
| **Frontend framework** | Vite/TypeScript |
| **Backend quick run** | `cd backend && python -m pytest tests/test_shipping_resolver.py tests/test_shopify_shipping.py tests/test_wake_shipping.py tests/test_non_vtex_shipping_integration.py -x -q` |
| **Backend route run** | `cd backend && python -m pytest tests/test_non_vtex_shipping_route.py tests/test_search_shipping_contract.py -x -q` |
| **VTEX regression run** | `cd backend && python -m pytest tests/test_vtex_api_client.py tests/test_vtex_shipping.py tests/test_search_shipping_contract.py -x -q` |
| **Frontend run** | `cd frontend && npm run build` |
| **Full backend suite** | `cd backend && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~30-90 seconds for hermetic subset; live checks are manual/spike only |

---

## Sampling Rate

- **After every task:** Run the task-specific automated command.
- **After every wave:** Run backend quick run plus VTEX regression run.
- **Before verify-work:** Run full backend suite and frontend build.
- **Live probes:** Run only in spike/manual steps, never as pytest defaults.

---

## Per-Task Verification Map

| Req ID | Behavior | Wave | Threat Ref | Test Type | Automated Command | File Exists | Status |
|--------|----------|------|------------|-----------|-------------------|-------------|--------|
| FRET-07-spike | Spike 011 records GO/NO-GO for Shopify/Buckman and Wake/Richards | 1 | T-live-impact | manual/spike | `python .planning/spikes/011-non-vtex-shipping/experiment.py --provider all --write-report` | exists | green |
| FRET-07-a | Resolver selects Shopify/Wake and unsupported for SFCC/unknown; VTEX not routed | 2 | T-vtex-regression | unit | `cd backend && python -m pytest tests/test_shipping_resolver.py -x -q` | exists | green |
| FRET-07-a | Common result contract applies primary shipping from sorted `shipping_options` | 2 | T-free-false-positive | unit | `cd backend && python -m pytest tests/test_non_vtex_shipping_integration.py -x -q` | exists | green |
| FRET-07-b | Wake provider parses GO response or returns unsupported/temporary failure from NO-GO evidence | 2 | T-provider-auth | unit | `cd backend && python -m pytest tests/test_wake_shipping.py -x -q` | exists | green |
| FRET-07-c | Shopify provider parses cart/rates response and handles async null polling | 2 | T-provider-throttle | unit | `cd backend && python -m pytest tests/test_shopify_shipping.py -x -q` | exists | green |
| FRET-07-inline | Wake/Shopify inline search fills shipping only with valid CEP and never on missing CEP | 2 | T-dos | integration/mock | `cd backend && python -m pytest tests/test_non_vtex_shipping_integration.py -x -q` | exists | green |
| FRET-07-d | VTEX path remains green and outside `BaseShipping` | 2/3 | T-vtex-regression | regression | `cd backend && python -m pytest tests/test_vtex_api_client.py tests/test_vtex_shipping.py tests/test_search_shipping_contract.py -x -q` | exists | green |
| FRET-07-api | `/search/calculate-shipping-brand` validates CEP, brand, product host and unsupported states | 3 | T-ssrf | route/unit | `cd backend && python -m pytest tests/test_non_vtex_shipping_route.py -x -q` | exists | green |
| FRET-07-ui | Frontend calls non-VTEX endpoint and reuses shipping options renderer | 3 | T-ui-regression | build | `cd frontend && npm run build` | exists | green |

*Status: pending / green / red / flaky*

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-live-impact | DoS / abuse | Spike/provider calls to live stores | mitigate | Low frequency, short timeout, one product at a time, no bypass, no private credentials, clear Shopify cart. |
| T-provider-throttle | DoS | Shopify rates endpoint | mitigate | Use recommended prepare/async flow, bounded polling, no inline fan-out without semaphore. |
| T-provider-auth | Auth boundary | Wake/Fbits quote endpoint | mitigate | Use only public/available token path proved by spike; if private auth required, return unsupported and record NO-GO. |
| T-ssrf | SSRF/open redirect | On-demand `product_url` | mitigate | Resolve brand by persisted key and require URL host to match brand domain/subdomain before provider request. |
| T-free-false-positive | Data integrity | Result normalization | mitigate | `0.0` only from explicit provider price; `None` remains not calculated; tests cover failure states. |
| T-vtex-regression | Regression | Existing VTEX shipping | mitigate | No VTEX provider; keep `/calculate-shipping-vtex`; run Phase 33 regression tests. |
| T-pii-log | Information disclosure | CEP/logging | mitigate | Do not log CEP or full shipping payload at info/error. |

---

## Wave 0 / Spike Requirements

- [ ] `.planning/spikes/011-non-vtex-shipping/experiment.py` exists and has two independent probes: Shopify/Buckman and Wake/Richards.
- [ ] `.planning/spikes/011-non-vtex-shipping/REPORT.md` records:
  - date/time
  - domains tested
  - product URL/title
  - CEP class used (do not need to print full CEP in logs)
  - endpoint/flow tested
  - GO/NO-GO per provider
  - response signature/status
  - implementation recommendation
- [ ] Provider GO means at least one real product returns price (`0.0` allowed only if explicit free) plus delivery deadline/text, and the same path succeeds twice.
- [ ] Provider NO-GO includes enough evidence to implement unsupported/temporary failure without guessing.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Instructions |
|----------|-------------|------------|--------------|
| Shopify/Buckman live quote | FRET-07-c | Storefront cart/rates depends on live session and store config | Run spike 011 twice for Buckman; confirm options in `REPORT.md`; if blocked, retry Ricardo Almeida only as secondary evidence. |
| Wake/Richards live quote | FRET-07-b | Wake quote endpoint/token/product id must be proven against real store | Run spike 011 for Richards; record if quote endpoint accepts public token/product identity. |
| Post-implementation smoke | FRET-07-b/c | Validates real integration after code | Start backend/frontend, search Buckman/Richards with default CEP and inspect shipping state/options. |
| VTEX smoke | FRET-07-d | Guards real-store behavior beyond unit tests | Run one known VTEX brand search with frete and compare Phase 33 behavior. |

---

## Final Verification Run

2026-07-02:

```powershell
cd backend
python -m pytest tests/test_shipping_resolver.py tests/test_shopify_shipping.py tests/test_wake_shipping.py tests/test_non_vtex_shipping_integration.py tests/test_non_vtex_shipping_route.py tests/test_vtex_api_client.py tests/test_vtex_shipping.py tests/test_search_shipping_contract.py -x -q
```

Result: 86 passed.

```powershell
cd frontend
npm run build
```

Result: passed.

Manual browser smoke remains listed above as follow-up UAT, but the Phase 41 automated and live-spike gates are green.

---

## Validation Sign-Off

- [x] All plans have automated verification or explicit manual gate.
- [x] Live network is isolated to spike/manual checks.
- [x] No three consecutive implementation tasks without automated feedback.
- [x] VTEX regression is sampled after backend provider work and before completion.
- [x] `nyquist_compliant: true` set in frontmatter.

