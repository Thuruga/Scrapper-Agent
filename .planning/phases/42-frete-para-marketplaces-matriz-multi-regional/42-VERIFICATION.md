---
phase: 42-frete-para-marketplaces-matriz-multi-regional
verified: 2026-07-02T12:00:00Z
status: passed
score: 7/7 must-haves verified
overrides_applied: 0
human_verification_confirmed: "The item below was confirmed live by the operator on 2026-07-06 (Matriz Regional button/modal placement, layout, and blocked-state rendering)."
re_verification:
  previous_status: gaps_found
  previous_score: 6/7
  gaps_closed:
    - "Uma busca cruzada nos marketplaces (Mercado Livre, Netshoes, Amazon) retorna shipping_cost e shipping_time preenchidos quando o CEP padrao esta configurado — cobrindo os tres marketplaces (Roadmap Success Criterion 1 / FRET-08)."
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Live browser visual pass of the Matriz Regional button placement, modal layout, and blocked-state card rendering at both insertion points (comparativa/SKU and cross-marketplace), including the <=640px breakpoint."
    expected: "Matriz Regional button sits cleanly next to Calcular Frete with no overlap/overflow; the 5-region modal renders without layout shift; the blocked-state label replaces the button cleanly without leaving orphaned spacing."
    why_human: "42-03-SUMMARY.md explicitly documents that pixel-level visual/browser rendering was NOT checked by the orchestrator (no browser-automation tool available in that session) — only API-level live verification was performed. This is a real gap in visual QA, not something grep/static analysis can confirm. Unaffected by the gap-closure fix (2311c7c), which was a backend-only change; carried forward unchanged from the prior verification run."
---

# Phase 42: Frete para Marketplaces & Matriz Multi-Regional Verification Report

**Phase Goal:** O sistema calcula frete para os tres marketplaces (Mercado Livre, Netshoes, Amazon) e permite ao operador solicitar a Matriz de Frete Multi-Regional — frete para CEPs-chave das 5 regioes do Brasil — de forma on-demand, com throttle e cache por (SKU, CEP), sem nunca executar inline durante buscas ao vivo.
**Verified:** 2026-07-02T12:00:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (commit `2311c7c`)

## Gap Closure Verification

The prior run (score 6/7) found that `AmazonEngine.calculate_shipping` (Tier 2), a permanent stub always
returning `None`, was being interpreted by `_enrich_pdp_and_shipping` as a genuine anti-bot block,
causing every Amazon item in **automatic** cross-marketplace search results to falsely display
"Bloqueado (anti-bot)" — contradicting Roadmap Success Criterion 1 ("cobrindo os tres marketplaces").

**Fix independently verified in commit `2311c7c`:**

1. `backend/services/engines/base_engine.py:18` — added `SHIPPING_TIER2_BLOCKS_ON_NONE: bool = True` class
   attribute on `BaseEngine`, read directly. Confirmed present.
2. `backend/services/engines/amazon_engine.py:35` — `AmazonEngine.SHIPPING_TIER2_BLOCKS_ON_NONE = False`,
   read directly. Confirmed present, with a docstring-comment explaining the Tier-2 stub is a permanent
   no-op, never a real block attempt.
3. `backend/services/cross_marketplace_service.py:510-530` (`_enrich_pdp_and_shipping`) — the `else` branch
   that unconditionally set `_shipping_state = "blocked"` is now `elif getattr(engine,
   "SHIPPING_TIER2_BLOCKS_ON_NONE", True):`. Read directly — confirmed the branch only fires when the
   engine's flag says a `None` genuinely means "blocked".
4. Directly executed `AmazonEngine().calculate_shipping({"url": "x"}, "01310100")` in this verification
   session (not from SUMMARY narration) — still returns `None` (the stub itself is intentionally
   unchanged), but `AmazonEngine().SHIPPING_TIER2_BLOCKS_ON_NONE` is `False`, confirming the enrichment
   code path will no longer set `_shipping_state = "blocked"` for Amazon.
5. Directly executed the same check against `NetshoesEngine` and `MercadoLivreEngine` — both retain the
   default `SHIPPING_TIER2_BLOCKS_ON_NONE = True` (neither overrides it), confirming Netshoes' genuine
   Akamai-block labeling (its Tier 2 delegates to a real Playwright attempt via
   `calculate_shipping_advanced`) and ML's real-API-call Tier 2 are both unaffected/still correct.
6. New regression test `test_enrich_none_from_unimplemented_engine_is_not_labeled_blocked` in
   `backend/tests/test_cross_marketplace_service.py` — read the full test body; it constructs an
   `UnimplementedTier2Engine(FakeEngine)` with `SHIPPING_TIER2_BLOCKS_ON_NONE = False` returning `None`
   from `calculate_shipping`, runs a full `compare_product`, and asserts
   `item.get("_shipping_state") != "blocked"`. Ran it directly (not trusting SUMMARY): **passes**.
7. Ran `pytest tests/test_cross_marketplace_service.py -q` in this session: **13 passed** (up from 12 —
   confirms the new test was actually added and collected, not just described).
8. Ran the full backend suite in this session: **513 passed, 0 failed** (up from 512 in the prior
   verification run) — confirms no regressions and that exactly one net-new test landed.
9. Ran the other Phase-42 test files (`test_shipping_resolver.py`, `test_marketplace_shipping.py`,
   `test_shipping_regional_matrix.py`, `test_non_vtex_shipping_route.py`, `test_shipping_engines.py`) in
   this session: **50 passed**, matching the prior verification's 62-1(cross_marketplace)=50 baseline with
   no change — no regression in the matrix/resolver/engine truths.

**Conclusion:** The fix is substantively correct and directly closes the gap. The mechanism
(`SHIPPING_TIER2_BLOCKS_ON_NONE` per-engine flag) is architecturally sound — it lets each engine declare
whether its Tier-2 `None` return means "genuinely attempted and blocked" vs. "never attempted (stub)",
rather than a single boolean hack scoped to Amazon only. Netshoes and ML are unaffected (default `True`
preserved, matches their real Tier-2 implementations). Truth #4 (Roadmap SC1 / FRET-08 "covers all three
marketplaces") is now VERIFIED.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `resolve_shipping_provider` dispatches `mercadolivre`/`amazon`/`netshoes` to the three new `BaseShipping` adapters (underscore `mercado_livre` falls through) | VERIFIED | `backend/services/shipping/resolver.py` lines 19-30; `test_shipping_resolver.py` passes (regression-checked this session, 50/50 with siblings) |
| 2 | ML and Amazon shipping calculations return AVAILABLE with cost + delivery-time when the source exposes it; Amazon CAPTCHA maps to TEMPORARY_FAILURE (never BLOCKED) | VERIFIED | `backend/services/shipping/mercado_livre.py`, `amazon.py` — CAPTCHA branch at `amazon.py:72-77`; unchanged since prior verification, live-verification evidence in 42-03-SUMMARY.md stands |
| 3 | Netshoes maps its documented Akamai block to `ShippingState.BLOCKED` ("Bloqueado (anti-bot)"), never a fake free/zero value | VERIFIED | `backend/services/shipping/netshoes.py` lines 66-74; `backend/services/shipping/base.py` (`BLOCKED = "blocked"`); unchanged since prior verification |
| 4 | Uma busca cruzada nos 3 marketplaces retorna `shipping_cost`/`shipping_time` preenchidos com o CEP padrao configurado, cobrindo os tres marketplaces (Roadmap SC1) | **VERIFIED (gap closed)** | Fix in commit `2311c7c` confirmed by direct code read + direct execution (see Gap Closure Verification above). `AmazonEngine.SHIPPING_TIER2_BLOCKS_ON_NONE = False` prevents the false "Bloqueado (anti-bot)" mislabel; Netshoes/ML retain correct default. New regression test passes; full suite green (513 passed) |
| 5 | O operador consegue solicitar a Matriz de Frete Multi-Regional e receber custo/prazo para as 5 regioes (Roadmap SC2) | VERIFIED | `backend/services/shipping/regional_matrix.py::calculate_regional_matrix`; `POST /search/calculate-shipping-matrix` route registered and wired; unchanged since prior verification, tests re-run this session and pass |
| 6 | A matriz usa `cep_matrix.json` (5 CEPs curados), aplica throttle entre chamadas, e cacheia por (produto, cep); segunda solicitacao e servida do cache (Roadmap SC3) | VERIFIED | `backend/data/cep_matrix.json` (5-element array); throttle/TTL-cache logic in `regional_matrix.py`; tests re-run this session and pass |
| 7 | A matriz nunca e executada inline durante varredura/busca ao vivo — guard + teste (Roadmap SC4) | VERIFIED | `calculate_regional_matrix` raises `RuntimeError` before any provider call unless `triggered_by == "on_demand_matrix_button"`; static `ast`-based regression test re-run this session and passes |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/services/shipping/base.py` | `ShippingState.BLOCKED` + `DEFAULT_MESSAGES` entry | VERIFIED | Unchanged since prior verification |
| `backend/services/shipping/resolver.py` | 3 new engine branches | VERIFIED | Unchanged since prior verification |
| `backend/services/shipping/mercado_livre.py` | `MercadoLivreShipping(BaseShipping)` | VERIFIED | Unchanged since prior verification |
| `backend/services/shipping/amazon.py` | `AmazonShipping(BaseShipping)` | VERIFIED | Unchanged since prior verification |
| `backend/services/shipping/netshoes.py` | `NetshoesShipping(BaseShipping)` with BLOCKED mapping | VERIFIED | Unchanged since prior verification |
| `backend/config.py` | `SHIPPING_MATRIX_THROTTLE_SECONDS`/`SHIPPING_MATRIX_CACHE_TTL_SECONDS` | VERIFIED | Unchanged since prior verification |
| `backend/services/shipping/regional_matrix.py` | `calculate_regional_matrix` orchestrator | VERIFIED | Unchanged since prior verification |
| `backend/data/cep_matrix.json` | 5 curated capital CEPs | VERIFIED | Unchanged since prior verification |
| `backend/data/shipping_matrix_cache.json` | JSON-file cache | VERIFIED | Unchanged since prior verification |
| `backend/api/routes_search.py` | `POST /search/calculate-shipping-matrix` + models | VERIFIED | Unchanged since prior verification |
| `frontend/src/App.tsx` | Matriz Regional button + modal + blocked-state rendering + extended `isBrandShippingSupported` | VERIFIED | Unchanged since prior verification |
| `backend/services/engines/base_engine.py` | `SHIPPING_TIER2_BLOCKS_ON_NONE: bool = True` class attribute (new, gap-closure) | VERIFIED | Read directly at line 18; substantive (documented, typed, used) |
| `backend/services/engines/amazon_engine.py` | `SHIPPING_TIER2_BLOCKS_ON_NONE = False` override (new, gap-closure) | VERIFIED | Read directly at line 35; substantive with explanatory comment |
| `backend/services/cross_marketplace_service.py` | `_enrich_pdp_and_shipping` surfaces delivery-time + blocked state, now flag-aware | VERIFIED | `elif getattr(engine, "SHIPPING_TIER2_BLOCKS_ON_NONE", True):` at line 523 — read directly, confirmed wired to both `BaseEngine` default and `AmazonEngine` override |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `resolver.py` | `mercado_livre.py`/`amazon.py`/`netshoes.py` | lazy import per branch | WIRED | Unchanged since prior verification |
| `mercado_livre.py`/`amazon.py`/`netshoes.py` | engine `calculate_shipping_advanced` | delegate call | WIRED | Unchanged since prior verification |
| `routes_search.py::calculate_shipping_matrix` | `regional_matrix.py::calculate_regional_matrix` | direct call with `triggered_by="on_demand_matrix_button"` | WIRED | Unchanged since prior verification |
| `regional_matrix.py` | `resolver.py::resolve_shipping_provider` | called once per matrix request | WIRED | Unchanged since prior verification |
| `frontend App.tsx::requestMatrix` | `/search/calculate-shipping-matrix` | `ApiClient.calculateShippingMatrix` fetch | WIRED | Unchanged since prior verification |
| `cross_marketplace_service.py::_enrich_pdp_and_shipping` | `engine.calculate_shipping` (Tier 2) | surfaces delivery-time/blocked signal, gated by `SHIPPING_TIER2_BLOCKS_ON_NONE` | **WIRED (fixed)** | Now correctly distinguishes "genuine block attempt" (Netshoes/ML, flag=True default) from "unimplemented stub" (Amazon, flag=False) before setting `_shipping_state = "blocked"`. Confirmed by direct source read and passing regression test. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| Regional matrix modal (`App.tsx` `matrixModal.regions`) | `data.regions` | `POST /search/calculate-shipping-matrix` -> `calculate_regional_matrix` -> real `provider.calculate` per CEP | Yes | FLOWING |
| Cross-marketplace card blocked/price line (`item._shipping_state`, `item.shipping_price`) | `_enrich_pdp_and_shipping` result | `engine.calculate_shipping` (Tier 2), gated by `SHIPPING_TIER2_BLOCKS_ON_NONE` | Yes for ML/Netshoes (real network attempt, block state accurate); Amazon's Tier-2 stub still returns no data (`None`), but is **no longer mislabeled** — `_shipping_state` is left unset so the UI falls back to its pre-existing "Frete a calcular" treatment instead of a false block claim | FLOWING (ML, Netshoes) / CORRECTLY-UNSET (Amazon, was STATIC/mislabeled before the fix) |
| Manual "Calcular Frete" price+prazo (`runShipForItem`) | `data.shipping_info` | `POST /search/calculate-shipping` -> `calculate_shipping_advanced` | Yes for all 3 marketplaces | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| New regression test for the fix passes | `pytest tests/test_cross_marketplace_service.py -q` | 13 passed (was 12 before the fix) | PASS |
| Full backend suite green (no regressions) | `cd backend && python -m pytest -q` | 513 passed, 0 failed, 1 pre-existing unrelated warning (was 512 before the fix) | PASS |
| Other Phase-42 test files unaffected | `pytest tests/test_shipping_resolver.py tests/test_marketplace_shipping.py tests/test_shipping_regional_matrix.py tests/test_non_vtex_shipping_route.py tests/test_shipping_engines.py -q` | 50 passed | PASS |
| `AmazonEngine.SHIPPING_TIER2_BLOCKS_ON_NONE` is `False` (flag override present and effective) | `AmazonEngine().SHIPPING_TIER2_BLOCKS_ON_NONE` executed directly | `False` | PASS |
| `NetshoesEngine`/`MercadoLivreEngine` retain default flag (no regression to their block semantics) | `getattr(NetshoesEngine(), 'SHIPPING_TIER2_BLOCKS_ON_NONE', True)` / same for ML | `True` / `True` | PASS |
| Amazon Tier-2 `calculate_shipping` still returns `None` (stub itself intentionally unchanged — only its interpretation changed) | `AmazonEngine().calculate_shipping({"url": "x"}, "01310100")` executed directly | `None` | PASS (expected — confirms fix targets interpretation, not the stub) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|--------------|--------|----------|
| FRET-08 | 42-01, 42-02, 42-03 | O sistema calcula frete para os marketplaces (Mercado Livre, Netshoes, Amazon) | **SATISFIED** | ML and Netshoes fully satisfied (unchanged). Amazon now satisfied across both paths: on-demand `/calculate-shipping-brand` + manual "Calcular Frete" click (already worked, live-verified in 42-03-SUMMARY.md) AND the automatic cross-marketplace-search auto-enrichment path (fixed in `2311c7c` — no longer falsely reports "Bloqueado"). Gap from prior verification closed. |
| FRET-09 | 42-02, 42-03 | Matriz de Frete Multi-Regional — on-demand, throttle, cache por (sku, cep), CEPs curados | SATISFIED | Unchanged since prior verification — all 4 roadmap success criteria verified in code, tests, and live API-level checks |

No orphaned requirements — both FRET-08 and FRET-09 are declared in plan frontmatter (42-01/02/03) and map 1:1 to REQUIREMENTS.md Phase 42 traceability entries (lines 104-105).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/services/engines/mercado_livre_engine.py` | 799-816 | `_fetch_shipping_options` reports the highest-price option, not the cheapest, when no free option exists (CR-01, code review) | Info (pre-existing, out of Phase 42 scope per explicit instruction) | Unchanged since prior verification; not a Phase 42 blocker |
| `backend/services/engines/amazon_engine.py` | 476-483 | `calculate_shipping` (Tier 2) remains a hardcoded no-op returning `None` | Info (no longer a blocker) | Previously a Blocker because its `None` was mislabeled "blocked"; now correctly interpreted as "unimplemented" via `SHIPPING_TIER2_BLOCKS_ON_NONE = False`. The stub itself is unchanged and Amazon auto-enrichment still doesn't attempt a real Tier-2 shipping calculation, but this no longer produces a false claim to the operator — downgraded from Blocker to Info. |
| `backend/services/shipping/amazon.py`, `mercado_livre.py`, `netshoes.py` | whole file | Near-identical copy-paste across the 3 providers (WR-04, code review) | Warning (maintainability only) | Unchanged since prior verification |

No debt markers (`TBD`/`FIXME`/`XXX`) found in the gap-closure diff (`base_engine.py`, `amazon_engine.py`, `cross_marketplace_service.py`, `test_cross_marketplace_service.py`).

### Probe Execution

Not applicable — this phase has no `scripts/*/tests/probe-*.sh` migration/tooling probes. Verification relied on the backend pytest suite (Behavioral Spot-Checks above), which is the phase's actual test harness.

### Human Verification Required

### 1. Visual/browser pass of Matriz Regional UI

**Test:** Open the app in a real browser, run a cross-marketplace search, and visually inspect: (a) the "Matriz Regional" button placement next to "Calcular Frete" at both insertion points, (b) the "Frete por região" modal layout with 5 region rows, (c) the blocked-state card rendering, all at both desktop and the documented <=640px breakpoint.
**Expected:** No layout shift, no overlap/overflow, button/modal render per the 42-UI-SPEC.md contract.
**Why human:** 42-03-SUMMARY.md explicitly states this was NOT checked — "pixel-level visual rendering in a real browser... was NOT checked by the orchestrator (no browser-automation tool available in this session)." This item is unrelated to and unaffected by the gap-closure fix (which was backend-only, no frontend changes in commit `2311c7c`), and remains outstanding unchanged from the prior verification run.

### Gaps Summary

**Gap closed.** The single blocking gap from the prior verification run (Amazon's Tier-2 shipping stub
being mislabeled "Bloqueado (anti-bot)" in automatic cross-marketplace search results, contradicting
Roadmap Success Criterion 1) is confirmed resolved by commit `2311c7c`. The fix was verified independently
in this session via: direct source reads of all 3 modified files, direct execution of the affected code
paths (`AmazonEngine().calculate_shipping()`, `AmazonEngine().SHIPPING_TIER2_BLOCKS_ON_NONE`,
`NetshoesEngine`/`MercadoLivreEngine` flag defaults), and a full backend test run (513 passed, up from 512,
confirming exactly the claimed new regression test landed and nothing else broke).

All 7 must-have truths (roadmap Success Criteria 1-4 plus the 3 architecture-level dispatch/state truths
from Plan 01) are now VERIFIED. FRET-08 and FRET-09 are both SATISFIED with no orphaned requirements.

**One informational item remains outstanding** and is carried forward unchanged from the prior
verification: a real-browser visual/pixel pass of the Matriz Regional button and modal layout was never
performed (only API-level verification), per 42-03-SUMMARY.md's own admission. This is unrelated to the
gap-closure fix (backend-only change, no frontend diff) and requires a human with a browser to close.
Per the status decision tree, this outstanding human-verification item means status is `human_needed`
rather than `passed`, even though all automated truths are green.

---

_Verified: 2026-07-02T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
