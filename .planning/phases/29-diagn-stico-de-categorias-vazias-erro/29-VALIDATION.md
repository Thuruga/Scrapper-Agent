---
phase: 29
slug: diagn-stico-de-categorias-vazias-erro
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-22
---

# Phase 29 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 (backend) · tsc/vite (frontend) |
| **Config file** | none — project convention (pytest defaults; `.pytest_cache` present; no pytest-asyncio fixtures, drive coroutines with `asyncio.run`) |
| **Quick run command** | `python -m pytest tests/test_category_diagnostic.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Frontend gate** | `cd frontend && npx tsc --noEmit && npm run build` |
| **Estimated runtime** | backend ~5s · frontend build ~30s |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_category_diagnostic.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -q` (and the frontend gate after Wave 4)
- **Before `/gsd-verify-work`:** Full suite green + frontend builds clean
- **Max feedback latency:** ~5 seconds (backend unit) / ~30s (frontend build)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 29-01-01 | 01 | 1 | DIAG-01 | T-29-01 | Offline mock; no live VTEX | unit (RED) | `python -m pytest tests/test_category_diagnostic.py -q` (expects RED) | ❌ W0 (creates it) | ⬜ pending |
| 29-02-01 | 02 | 2 | DIAG-01 | — | English Literal enum rejects PT-BR status | unit | `python -c "from core.models import CategoryDiagnosticResult"` | ❌ → ✅ | ⬜ pending |
| 29-02-02 | 02 | 2 | DIAG-01 | T-29-02 / T-29-03 / T-29-04 | Raw probe, no _request_json/search fallback; bounded concurrency+timeout | unit | `python -m pytest tests/test_category_diagnostic.py::TestClassifier tests/test_category_diagnostic.py::TestBrandFilter -q` | ✅ (29-01) | ⬜ pending |
| 29-03-01 | 03 | 3 | DIAG-01 | T-29-05 | brand_key validated; synchronous (no BackgroundTasks) | unit | `python -c "import api.routes_diagnostic as r; print(sorted({x.path for x in r.router.routes}))"` | ✅ (29-01) | ⬜ pending |
| 29-03-02 | 03 | 3 | DIAG-01 | T-29-06 / T-29-07 | Auth inherited (not public); offline endpoint test | unit/integration | `python -m pytest tests/test_category_diagnostic.py -q` (zero skips) | ✅ (29-01 TestEndpoint) | ⬜ pending |
| 29-04-01 | 04 | 4 | DIAG-02 | T-29-09 / T-29-10 | React auto-escape; X-API-Key attached | typecheck | `cd frontend && npx tsc --noEmit` | n/a (build gate) | ⬜ pending |
| 29-04-02 | 04 | 4 | DIAG-02 | — | Tab wired; build clean | build | `cd frontend && npm run build` | n/a (build gate) | ⬜ pending |
| 29-04-03 | 04 | 4 | DIAG-02 | T-29-08 | Three states distinguishable; probed URL exposed for operator | human-verify | manual (checkpoint) | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_category_diagnostic.py` — stubs for DIAG-01 (classifier matrix + probe + no_probe brand filter + endpoint placeholder) — created by 29-01 (Wave 1 here acts as the RED Wave 0 since no prior infra exists).
- [ ] No new `conftest.py` needed — project convention uses `asyncio.run()` without async fixtures.
- [ ] No framework install needed — pytest 9.0.3 already present.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Panel renders three distinct states (OK/Vazia/Erro), expandable detail, no_probe + inactive distinction against live backend | DIAG-02 | Visual/functional rendering against live VTEX brands cannot be asserted offline; the three-state visual distinction and operator workflow are inherently UI | See 29-04 Task 3 checkpoint steps 1-7 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (29-04 Task 3 is the single legitimate human-verify checkpoint for DIAG-02 visual confirmation)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (backend tasks all hit pytest; frontend tasks hit tsc/build)
- [x] Wave 0 covers all MISSING references (`probe_category`, `run_brand_diagnostic`, endpoint)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-22
