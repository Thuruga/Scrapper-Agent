---
phase: 25
slug: funda-o-de-motores
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-18
---

# Phase 25 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (no `pytest.ini`/`pyproject` config detected — inferred from `tests/`) |
| **Config file** | none — run from project root |
| **Quick run command** | `pytest tests/test_engine_detection.py tests/test_brand_active.py -x -q` |
| **Full suite command** | `pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds (unit-heavy, mocked aiohttp; no network) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_engine_detection.py tests/test_brand_active.py -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 25-W0 | 00 | 0 | COMP-02 | — | N/A | unit (RED) | `pytest tests/test_engine_detection.py -q` | ❌ W0 | ⬜ pending |
| 25-W0 | 00 | 0 | MGMT-01 | — | N/A | unit (RED) | `pytest tests/test_brand_active.py -q` | ❌ W0 | ⬜ pending |
| detect-shopify | — | 1 | COMP-02 | — | N/A | unit | `pytest tests/test_engine_detection.py -k shopify -x` | ❌ W0 | ⬜ pending |
| detect-vtex | — | 1 | COMP-02 | — | N/A | unit | `pytest tests/test_engine_detection.py -k vtex -x` | ❌ W0 | ⬜ pending |
| detect-wake-unknown | — | 1 | COMP-02 | — | unsupported platform not silently VTEX | unit | `pytest tests/test_engine_detection.py -k wake -x` | ❌ W0 | ⬜ pending |
| detect-allfail-unknown | — | 1 | COMP-02 | T-spoofing-redirect | transient failure → unknown | unit | `pytest tests/test_engine_detection.py -k all_probes_fail -x` | ❌ W0 | ⬜ pending |
| create-unknown-inactive | — | 1 | COMP-02 | — | unknown engine saved inactive | integration | `pytest tests/test_engine_detection.py -k CreateBrandUnknown -x` | ❌ W0 | ⬜ pending |
| list-default-all | — | 2 | MGMT-01 (SC-4) | — | inactive still listed for management | unit | `pytest tests/test_brand_active.py -k default_returns_all -x` | ❌ W0 | ⬜ pending |
| list-activeonly | — | 2 | MGMT-01 | — | inactive excluded from search/scheduler | unit | `pytest tests/test_brand_active.py -k active_only_excludes -x` | ❌ W0 | ⬜ pending |
| set-active-deactivate | — | 2 | MGMT-01 | T-tampering-key | 404 on unknown key, no corruption | unit | `pytest tests/test_brand_active.py -k deactivate -x` | ❌ W0 | ⬜ pending |
| set-active-reactivate | — | 2 | MGMT-01 | — | reactivation visible next call | unit | `pytest tests/test_brand_active.py -k reactivate -x` | ❌ W0 | ⬜ pending |
| route-returns-inactive | — | 2 | MGMT-01 (SC-4) | — | `GET /brands/` opt-in, not global default | integration | `pytest tests/test_brand_active.py -k RouteReturnsInactive -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_engine_detection.py` — RED stubs for COMP-02 (Shopify/VTEX/Wake/all-fail detection + create_brand→unknown→inactive). Uses `unittest.mock` with `__aenter__`/`__aexit__` on mocked aiohttp responses; patches `api.routes_brands.SessionManager.get_session`.
- [ ] `tests/test_brand_active.py` — RED stubs for MGMT-01 (`list_brands(active_only)` + `set_active` + `GET /brands/` returns inactive). Builds `BrandManagerService` in-memory (no file I/O); patches `_save`.

*Existing infrastructure (pytest + unittest.mock) covers tooling — only the two new test files are missing.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Supabase `brands` table has `is_active` column in production | MGMT-01 (persistence) | Production schema not inspectable from code/tests | Run `ALTER TABLE brands ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;` before release; confirm PATCH persists after restart |
| Live Wake site (shop2gether.com.br) returns `"unknown"` from `detect_engine` | COMP-02 (SC-1) | Requires live network to a Wake storefront (anti-bot/WAF risk) | With network, call `detect_engine("www.shop2gether.com.br")` → expect `"unknown"`, log shows `fbitsstatic.net` marker |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (both new test files)
- [ ] No watch-mode flags
- [ ] Feedback latency < ~15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
