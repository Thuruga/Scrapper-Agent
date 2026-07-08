---
phase: 42
slug: frete-para-marketplaces-matriz-multi-regional
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-01
---

# Phase 42 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `42-RESEARCH.md` and `42-CONTEXT.md`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Backend framework** | pytest 9.0.3 |
| **Frontend framework** | Vite/TypeScript |
| **Config file** | none detected at root — pytest auto-discovers `backend/tests/test_*.py` |
| **Backend quick run** | `cd backend && python -m pytest tests/test_shipping_resolver.py tests/test_shipping_engines.py tests/test_shipping_regional_matrix.py -x -q` |
| **Backend route run** | `cd backend && python -m pytest tests/test_non_vtex_shipping_route.py -x -q` |
| **Frontend run** | `cd frontend && npm run build` (no frontend test runner exists — `tsc --noEmit`/build is the established TDD substitute per `[44-05/typecheck-tdd]`) |
| **Full backend suite** | `cd backend && python -m pytest -q` |
| **Estimated runtime** | ~30-90 seconds for hermetic subset; live checks are manual-only |

---

## Sampling Rate

- **After every task:** Run the task-specific automated command.
- **After every wave:** Run backend quick run plus backend route run.
- **Before verify-work:** Run full backend suite and frontend build.
- **Live probes:** Run only in manual smoke checks, never as pytest defaults.

---

## Per-Task Verification Map

| Req ID | Behavior | Wave | Threat Ref | Test Type | Automated Command | File Exists | Status |
|--------|----------|------|------------|-----------|-------------------|-------------|--------|
| FRET-08 | `resolve_shipping_provider` returns the correct provider for engines `mercadolivre`/`amazon`/`netshoes` (match on `engine`, not `brand_key`) | TBD | T-vtex-regression | unit | `cd backend && python -m pytest tests/test_shipping_resolver.py -x -q` | exists (extend) | pending |
| FRET-08 | ML provider returns `AVAILABLE` with cost + delivery-time populated from a fake `shipping_options` fixture | TBD | T-ssrf | unit | `cd backend && python -m pytest tests/test_shipping_engines.py -k mercado_livre -x -q` | missing (Wave 0) | pending |
| FRET-08 | Amazon provider extracts delivery-time text alongside price from a fixture delivery-block HTML | TBD | T-ssrf | unit | `cd backend && python -m pytest tests/test_shipping_engines.py -k amazon -x -q` | missing (Wave 0) | pending |
| FRET-08 | Netshoes provider returns `BLOCKED` state (never fake `0.0`) when Playwright flow matches the documented Akamai signature | TBD | T-pii-log | unit | `cd backend && python -m pytest tests/test_shipping_engines.py -k netshoes_blocked -x -q` | missing (Wave 0) | pending |
| FRET-08 | `/search/calculate-shipping-brand` accepts `engine in {mercadolivre, amazon, netshoes}` without 400 | TBD | T-ssrf | integration | `cd backend && python -m pytest tests/test_non_vtex_shipping_route.py -x -q` | exists (extend) | pending |
| FRET-09 | Matrix service returns 5 region results for a product+brand, one per curated CEP | TBD | T-access-control | unit | `cd backend && python -m pytest tests/test_shipping_regional_matrix.py -x -q` | missing (Wave 0, new file) | pending |
| FRET-09 | Second matrix request for the same `(product, cep)` is served from cache — resolver/provider NOT called again | TBD | T-cache-poison | unit | `cd backend && python -m pytest tests/test_shipping_regional_matrix.py -k cache_hit -x -q` | missing (Wave 0) | pending |
| FRET-09 | Matrix throttles between CEP calls (asserts sleep/delay called between requests, not before the first) | TBD | T-pii-log | unit | `cd backend && python -m pytest tests/test_shipping_regional_matrix.py -k throttle -x -q` | missing (Wave 0) | pending |
| FRET-09 | `cross_marketplace_search` / `run_category_scan` never invoke the matrix module (guard) | TBD | T-dos-self | regression | `cd backend && python -m pytest tests/test_shipping_regional_matrix.py -k guard_no_inline -x -q` | missing (Wave 0) | pending |
| FRET-09 | Frontend "Matriz Regional" action + blocked-state rendering compile cleanly | TBD | — | build | `cd frontend && npm run build` | existing pattern | pending |

*Status: pending / green / red / flaky*

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-ssrf | SSRF/Tampering | Product URL passed to new marketplace providers and to the matrix's per-CEP calls | mitigate | Reuse `is_url_allowed_for_brand` (Phase 41, `services/shipping/base.py`) before any outbound call — validate host matches the persisted brand domain, exactly as `WakeShipping`/`ShopifyShipping` already do. |
| T-pii-log | Information disclosure | CEP in throttle/cache/provider logging | mitigate | Never log the raw CEP at `info`/`error` (Phase 41 D-21 precedent); log the region label (e.g. "Sudeste") instead where a human-readable log line is needed. |
| T-access-control | Access control | New matrix endpoint (e.g. `/search/calculate-shipping-matrix`) | mitigate | Cover the new route with the same `X-API-Key` (`INTERNAL_API_KEY`) middleware already applied to every other `/search/*` route — verify no new route bypasses it. |
| T-cache-poison | Tampering | `(sku, cep)` cache key derivation when no stable SKU exists (marketplace items) | mitigate | Normalize the product URL (reuse existing `normalize_url` discipline from `routes_brands.py`/monitor flows) before deriving the product-identity half of the cache key, so tracking-param variants of the same URL hit the same entry. |
| T-dos-self | Denial of Service (self-inflicted) | Matrix guard (D-10) bypassed and triggered inline during a large category scan | mitigate | D-10 guard is the primary mitigation: explicit check that raises/no-ops if called from `cross_marketplace_search`/`run_category_scan`, covered by a dedicated regression test (`guard_no_inline`). |
| T-vtex-regression | Regression | Existing marketplace shipping paths (`calculate_shipping`/`calculate_shipping_advanced`) and VTEX/Wake/Shopify providers from Phase 41 | mitigate | New providers wrap and adapt existing engine methods rather than rewriting them; run the full backend suite before the phase gate to confirm no regression. |

---

## Wave 0 Requirements

- [ ] `backend/tests/test_shipping_regional_matrix.py` — new file, covers FRET-09 (5-region result, cache hit, throttle, inline guard).
- [ ] New test cases in `backend/tests/test_shipping_engines.py` (or a new `test_marketplace_shipping.py`) — covers FRET-08 provider mapping for all 3 engines, including the `BLOCKED` state for Netshoes.
- [ ] Extend `backend/tests/test_shipping_resolver.py` — 3 new resolver branch assertions (`mercadolivre`/`amazon`/`netshoes`).
- [ ] Extend `backend/tests/test_non_vtex_shipping_route.py` — `/search/calculate-shipping-brand` accepting marketplace engines.
- [ ] Frontend: no test runner exists — verify new UI (button, blocked-state rendering) via `npm run build` / `tsc --noEmit`, matching the Phase 44 precedent.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Instructions |
|----------|-------------|------------|--------------|
| Mercado Livre live `/shipping_options` delivery-time field shape | FRET-08 | External API response shape could not be independently verified in research (official docs returned HTTP 403 to scraping) — flagged `[ASSUMED]` in RESEARCH.md | During implementation, log one real `/shipping_options` response for a live product and confirm the delivery-time field names before finalizing the parser. |
| Netshoes Akamai edge-block persists | FRET-08 | Live anti-bot behavior, not hermetically testable | Rely on the existing evidence in `.planning/debug/monitor-marketplace-pendente.md`; do not re-probe the live site as part of CI. |
| Matrix operator smoke (5-region table) | FRET-09 | End-to-end UI + up to 5 live CEP calls per engine | Start backend/frontend, trigger "Matriz Regional" for one product per engine family (VTEX, Wake/Shopify, ML/Amazon, Netshoes), confirm the 5-region table renders with real/blocked states and the second identical request comes from cache. |

---

## Validation Sign-Off

- [ ] All tasks have automated verification or an explicit manual gate.
- [ ] Live network calls are isolated to manual smoke checks, never pytest defaults.
- [ ] No 3 consecutive tasks without automated verify.
- [ ] Wave 0 covers all MISSING references above.
- [ ] Full backend suite green + frontend build green before `/gsd-verify-work`.
- [ ] `nyquist_compliant: true` set in frontmatter.

**Approval:** pending
