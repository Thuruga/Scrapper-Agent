---
phase: 26-onboarding-das-5-marcas-vtex
verified: 2026-06-19T00:00:00Z
status: passed
score: 6/6 must-haves verified
overrides_applied: 0
human_verification_completed: 2026-06-19T18:46:42Z
human_verification:
  - test: "Run `python scripts/onboard_vtex_brands.py` once with network access"
    expected: |
      Each of the 5 brands (levis, calvinklein, zapalla, austral, trackfield) prints
      engine=vtex after detect_engine reconfirmation. The de/para review prompt appears
      per brand. [SMOKE] {brand}: >=1 produtos for all 5. Re-run shows no duplication
      and the mappings-already-exist prompt (D-06 idempotency).
    why_human: "D-10 explicitly rejected automated per-brand live tests (WAF/geo/network
      fragility). This is ROADMAP success criterion 1 and D-10a — operator-run only."
---

# Phase 26: Onboarding das 5 Marcas VTEX — Verification Report

**Phase Goal:** As cinco marcas concorrentes em plataforma VTEX confirmada estao cadastradas no
sistema com engine verificada, categorias mapeadas e prontas para busca e monitoramento.
**Verified:** 2026-06-19
**Status:** passed (live human verification completed 2026-06-19 — see 26-UAT.md / 26-HUMAN-UAT.md)
**Re-verification:** Yes — human layer closed after live operator run

---

## Goal Achievement

### Observable Truths

Per the decision model in 26-CONTEXT.md (D-10), this phase defines two verification layers:
(a) AUTOMATED — offline contract test + script structure checks (machine-verifiable now);
(b) MANUAL/LIVE — running the script with network (operator-run, explicitly not automated).

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ROADMAP SC-1: A search per brand returns real products for all 5 brands | ✓ VERIFIED (live) | Operator ran `python scripts/onboard_vtex_brands.py` with network on 2026-06-19. Live smoke returned products for all 5: levis 3, calvinklein 2, zapalla 3, austral 3, trackfield 3 (all ≥1). Recorded in 26-UAT.md (test 2) and 26-HUMAN-UAT.md. |
| 2 | ROADMAP SC-2: engine of each registered brand is "vtex" reconfirmed by detect_engine, not assumed manually | ✓ VERIFIED | Script calls `detect_engine(brand.domain)` after every `add_brand` and force-corrects `brand.engine` + `svc._save(brand)` when stale (onboard_brand lines 140-147). The only `brand.engine = "vtex"` assignment (line 156) is inside the Austral branch guarded by `resolve_austral_domain` which itself returns only when `detect_engine(candidate) == "vtex"` (lines 102-103). No unconditional `engine="vtex"` assignment exists. |
| 3 | ROADMAP SC-3: Unsupported brands (Richards, Lacoste, Hugo Boss, Zara) are NOT onboarded; Phase 25 COMP-02 identifies them as "unknown" | ✓ VERIFIED | BRAND_TABLE contains exactly 5 entries (levis, calvinklein, zapalla, austral, trackfield). Script sets `set_active(brand_key, False)` and returns None for any brand where engine != "vtex" after all retries (lines 165-168). The unsupported brands are not in BRAND_TABLE and would fail detection if added — COMP-02 (Phase 25) handles that gate. |
| 4 | Contract test exists with 6 tests all passing offline (D-10b automated layer) | ✓ VERIFIED | `python -m pytest tests/test_vtex_brand_onboarding_contract.py -q` → **6 passed in 0.18s** (executed by verifier). All 6 methods present: test_engine_is_vtex, test_brand_is_active, test_mappings_persisted, test_brand_in_active_list, test_vtex_fq_path_is_relative, test_resolve_category_returns_valid_url. |
| 5 | Script structure is complete: all required functions exist, BRAND_TABLE has 5 correct entries, CANONICAL_KEYWORDS has exactly 7 _RAW_CATEGORIES slugs, urlparse path extraction present, D-09 human gate present, D-08 dual-persistence via update_mappings, no manual engine override | ✓ VERIFIED | See artifact detail below. All structural checks pass. |
| 6 | services/category_mapping.py is unmodified (D-07 invariant) | ✓ VERIFIED | `git diff -- services/category_mapping.py` produces no output. No changes to that file. |

**Score:** 6/6 truths verified (automated layer + live human layer; live run passed 2026-06-19)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_vtex_brand_onboarding_contract.py` | Offline deterministic contract test, min 60 lines, contains `class TestBrandContract` | ✓ VERIFIED | 161 lines. Contains `class TestBrandContract`. All 6 test methods present. Imports `_RAW_CATEGORIES` (not non-existent `CANONICAL_SLUGS`). `VALID_SLUGS` derived dynamically from `_RAW_CATEGORIES`. `_save` only referenced inside `patch.object(svc, "_save")` context (line 103). `_check_reload` is `MagicMock()` (line 50). No network, no real I/O. |
| `scripts/onboard_vtex_brands.py` | Idempotent seed orchestrator, min 90 lines, contains `def onboard_brand` | ✓ VERIFIED | 306 lines. `def onboard_brand` present (line 115). All required functions: `normalize`, `auto_match`, `resolve_austral_domain`, `onboard_brand`, `discover_and_match`, `print_and_confirm`, `persist_mappings`, `main`. Entry point `asyncio.run(main())` present (lines 305-306). Parses as valid Python. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `scripts/onboard_vtex_brands.py` | `api.routes_brands.detect_engine` | engine reconfirmation after add_brand | ✓ WIRED | `detect_engine` imported inside `onboard_brand` (line 126) and called at line 140; also inside `resolve_austral_domain` (line 96, 100). 9 occurrences of `detect_engine` in file. |
| `scripts/onboard_vtex_brands.py` | `services.engines.vtex_engine.VTEXEngine.discover_categories` | category tree discovery | ✓ WIRED | `VTEXEngine(brand_key)` instantiated in `discover_and_match` (line 199); `engine.discover_categories()` called line 200. |
| `scripts/onboard_vtex_brands.py` | `services.brand_service.brand_service.update_mappings` | dual-persistence of CategoryMapping list | ✓ WIRED | `svc.update_mappings(brand_key, mappings)` called in `persist_mappings` (line 250). `persist_mappings` is called in `main` only after `print_and_confirm` returns True (line 280). |
| `scripts/onboard_vtex_brands.py` | `urllib.parse.urlparse` | extract relative path from discovered full URL (Pitfall 3/5) | ✓ WIRED | `from urllib.parse import urlparse` at line 17. `urlparse(item["path"]).path` called in `discover_and_match` (line 202). `persist_mappings` additionally guards against non-relative paths (lines 237-240). |
| `tests/test_vtex_brand_onboarding_contract.py` | `services.brand_service.BrandManagerService` | in-memory `__new__` factory, `_check_reload` + `_save` mocked | ✓ WIRED | `BrandManagerService.__new__(BrandManagerService)` at line 45. `svc._check_reload = unittest.mock.MagicMock()` at line 50. `patch.object(svc, "_save")` at line 103. |
| `tests/test_vtex_brand_onboarding_contract.py` | `services.category_mapping.resolve_category_for_brands` | import + call against in-memory brand_service | ✓ WIRED | Imported at line 19. Called in `test_resolve_category_returns_valid_url` (line 152) with monkeypatched `brand_service` (line 151). Asserts returned URL equals `"https://www.levi.com.br/roupas/jeans"`. |

### Data-Flow Trace (Level 4)

The contract test uses entirely in-memory data — no data flow from external sources.
The script is a standalone CLI orchestrator, not a component that renders dynamic data.
Level 4 data-flow trace is not applicable for this phase's artifacts.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Contract test: 6 tests all pass offline | `python -m pytest tests/test_vtex_brand_onboarding_contract.py -q` | 6 passed in 0.18s | ✓ PASS |
| Script parses as valid Python | `python -c "import ast; ast.parse(...); print('parse-ok')"` | parse-ok | ✓ PASS |
| Full suite: no regression introduced | `python -m pytest tests/ -q` | 162 passed, 1 pre-existing failure (test_ocr_service.py::test_compare_image_texts — passes in isolation, state-pollution issue predating phase 26) | ✓ PASS |
| Pre-existing failure is unrelated | `python -m pytest tests/test_ocr_service.py::test_compare_image_texts -q` | 1 passed (in isolation) | ✓ PASS |

### Probe Execution

No `probe-*.sh` scripts declared or discovered for this phase. The equivalent verification is the contract test run (executed above as a behavioral spot-check).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| COMP-01 | 26-01-PLAN.md, 26-02-PLAN.md | Usuário pode adicionar e buscar/monitorar as 5 marcas concorrentes em VTEX com engine reconfirmada via `detect_engine` | ✓ SATISFIED | Automated: contract test 6/6. Live (2026-06-19): 5 marcas engine=vtex reconfirmada, smoke ≥1 cada, 32 mappings de categoria SOMENTE masculinos persistidos (regra do operador), idempotência confirmada. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| No TBD/FIXME/XXX debt markers found in either artifact. | — | — | — | — |

No stub patterns detected. No empty return values in rendering paths. The script's
`brand.engine = "vtex"` at line 156 is guarded by `resolve_austral_domain()` return value
(which itself only returns non-None when `detect_engine(candidate) == "vtex"`) — this is
NOT an unconditional manual override and does NOT qualify as a stub or anti-pattern.

---

## Key Structural Assertions (verified against codebase)

**BRAND_TABLE:** 5 entries confirmed — levis, calvinklein, zapalla, austral, trackfield (all D-01 verbatim domains).

**CANONICAL_KEYWORDS keys:** Exactly 7 — camisas, polos, camisetas, calcas, bermudas, jaquetas, infantil. These match exactly the 7 slugs from `_RAW_CATEGORIES` (confirmed by running `{c["slug"] for c in _RAW_CATEGORIES}`).

**VALID_SLUGS in contract test:** Derived from `_RAW_CATEGORIES` at test import time (line 25: `VALID_SLUGS = {c["slug"] for c in _RAW_CATEGORIES}`) — stays in sync with the canonical source (D-04 anchor).

**No unconditional `engine="vtex"` assignment:** The only assignment is at script line 156, inside the Austral retry block that is entered only when `resolve_austral_domain()` returned a non-None domain. `resolve_austral_domain` iterates candidates and returns only when `await detect_engine(candidate) == "vtex"` (lines 102-103). This satisfies the D-11 requirement that "unknown is not a final state; NO manual override to vtex."

**D-07 invariant:** `git diff -- services/category_mapping.py` is empty. File unmodified.

**Commits exist:**
- `0e86617` — plan 26-01 (contract test)
- `8166e66` — plan 26-02 (onboarding script)

---

## Human Verification Required

### 1. Live Onboarding Run (ROADMAP Success Criterion 1, D-10a)

**Test:** Run `python scripts/onboard_vtex_brands.py` with network access. For each brand,
confirm the printed `detect_engine` result is `"vtex"`. Confirm the de/para review prompt
appears per brand. After confirming, verify `[SMOKE] {brand}: >=1 produtos` for all 5 brands.

**Expected:**
- All 5 brands print `engine=vtex` from `detect_engine` reconfirmation (not from hardcoded value)
- Austral either resolves via `www.austral.com.br` or triggers the domain-variant retry loop
- De/para proposals are printed per brand; mappings persist only after operator confirms "s"
- `[SMOKE] levis: >=1 produtos`, `[SMOKE] calvinklein: >=1 produtos`, etc. for all 5
- Re-running the script triggers the "N mappings already exist. Sobrescrever? [s/N]" prompt
  instead of re-discovering and duplicating

**Why human:** D-10 (CONTEXT.md) explicitly rejected automated per-brand live tests as
fragile (WAF/geo/network). The phase design commits to a two-layer verification model where
this live run is the mandatory human layer. ROADMAP success criterion 1 ("busca retorna
produtos reais para cada uma das cinco marcas") cannot be verified programmatically without
real network access.

---

## Gaps Summary

No blocking gaps. RESOLVED 2026-06-19: the human layer (live operator run) was completed and
passed — all 5 brands reconfirmed engine=vtex, live search returned products for each (≥1),
32 masculine-only category mappings persisted (operator rule: no feminine; infantil = boys
line only), and idempotency confirmed (re-run did not duplicate). Post-run hardening:
`auto_match` made gender-aware + 'mini' substring bug fixed (commit 8780b1e) with regression
test. Status advanced human_needed → passed.

---

_Verified: 2026-06-19_
_Verifier: Claude (gsd-verifier)_
