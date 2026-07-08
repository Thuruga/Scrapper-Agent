---
phase: 38
slug: ux-de-busca-monitoramento-quick-wins
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-01
---

# Phase 38 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (backend) / no runner (frontend — `npm run build` type-check only) |
| **Config file** | none found — backend discovery relies on default pytest conventions (`test_*.py` in `backend/tests/`) |
| **Quick run command** | `cd backend && python -m pytest tests/test_price_monitor.py tests/test_brand_active.py tests/test_category_monitor.py -q` (backend tasks); `cd frontend && npm run build` (frontend tasks) |
| **Full suite command** | `cd backend && python -m pytest -q` + `cd frontend && npm run build` |
| **Estimated runtime** | ~5-15 seconds (backend suite is small; frontend build under a minute) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command matching the task's stack (backend pytest subset or frontend build)
- **After every plan wave:** Run the full suite command (full backend pytest + frontend build)
- **Before `/gsd-verify-work`:** Full suite must be green + manual UAT complete for UX-01/UX-06/UX-07/UX-08 (see 38-HUMAN-UAT.md)
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

Reconciled with the finalized PLAN.md files (38-01, 38-02, 38-03). Wave 0 (the three backend baseline tests) is folded into Plan 38-01 Task 1 — the failing UX-02 test (RED) is created before the model/service change (Task 2/3) in the same plan, satisfying Nyquist Dimension 8.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 38-01-T1 | 38-01 | 1 (W0) | COMP-08, UX-08, UX-02 | T-38-02 | Chokepoint regression + RED baseline | unit/integration | `pytest tests/test_brand_active.py::TestLacosteExcludedFromActiveOnly tests/test_category_monitor.py -x -q` (COMP-08+UX-08 green; UX-02 RED) | ❌→✅ (creates all 3) | ⬜ pending |
| 38-01-T2 | 38-01 | 1 | UX-02 | T-38-01 | Field default None (D-02 back-compat) | unit/contract | `python -c "from core.models import PriceMonitorConfig, PriceHistoryEntry ..."` | ✅ (after T1) | ⬜ pending |
| 38-01-T3 | 38-01 | 1 | UX-02 | T-38-01 | D-01/D-03 discount-aware detection | unit | `pytest tests/test_price_monitor.py -q` (Task-1 RED test now GREEN) | ✅ (after T2) | ⬜ pending |
| 38-02-T1 | 38-02 | 1 | UX-01 | T-38-SC | N/A (CSS) | manual + build | `cd frontend && npm run build` + 38-HUMAN-UAT §1 | N/A | ⬜ pending |
| 38-02-T2 | 38-02 | 1 | UX-06 | T-38-03 | Type-scoped badge (Pitfall 3) | manual + build | `cd frontend && npm run build` + 38-HUMAN-UAT §2 | N/A | ⬜ pending |
| 38-03-T1 | 38-03 | 2 | UX-07 | T-38-04 | Frontend regex is UX-only; backend SKU validation unaffected | manual + build | `cd frontend && npm run build` + 38-HUMAN-UAT §3 | N/A | ⬜ pending |
| 38-03-T2 | 38-03 | 2 | UX-08 | T-38-05 | Bounded poll (max-attempts, clear on unmount) | manual + build | `cd frontend && npm run build` + 38-HUMAN-UAT §4 | N/A | ⬜ pending |
| 38-03-T3 | 38-03 | 2 | UX-02 | — | Promo render from polled payload (no new call) | manual + build | `cd frontend && npm run build` + 38-HUMAN-UAT (render check under §4 setup) | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Dimension 8 (sampling continuity) check:** No run of 3 consecutive tasks lacks an automated verify or Wave-0 dependency. Plan 38-01's three tasks each have an automated pytest/python command. Plan 38-02 and 38-03's frontend tasks each carry `npm run build` (type-check) as their automated verify, backed by the Plan 38-01 Wave-0 backend tests for the data behaviors (UX-02, COMP-08, UX-08 trigger). Frontend interaction/visual behavior has no runner (RESEARCH.md) → covered by 38-HUMAN-UAT.md.

---

## Wave 0 Requirements

Wave 0 is folded into **Plan 38-01 Task 1** (all three backend tests created there; the UX-02 test is RED before Task 2/3 implement it):

- [ ] `backend/tests/test_price_monitor.py::test_price_monitor_promo_only_change_triggers_history` — RED baseline for D-01/D-03 (promo-only change triggers history + WS `price_update` with discount field). Goes GREEN in 38-01 Task 3.
- [ ] `backend/tests/test_brand_active.py::TestLacosteExcludedFromActiveOnly` — COMP-08 regression, following `TestMarketplacesInBrandsJson`. Green immediately (no prod code — chokepoint pre-exists).
- [ ] `backend/tests/test_category_monitor.py` — new file (confirmed absent via Glob). Asserts `run_category_scan` populates `last_scraped_at` (UX-08 backend contract for the Plan 38-03 poll). Green immediately (trigger pre-exists).

---

## Manual-Only Verifications

All four are in `38-HUMAN-UAT.md` (mirrors `44-HUMAN-UAT.md`):

| Behavior | Requirement | Plan/Task | Why Manual | UAT Ref |
|----------|-------------|-----------|------------|---------|
| `.grid-category` + category-scan layout collapse without overflow at ≤768px | UX-01 | 38-02 T1 | No automated DOM/viewport test infra (frontend has no test runner) | 38-HUMAN-UAT §1 |
| History icon toggles panel with correct type-scoped badge, top-right on both tabs | UX-06 | 38-02 T2 | No frontend test runner; visual/interaction check | 38-HUMAN-UAT §2 |
| SKU field rejects non-`ML.05.XXXXXXX` with inline error copy; CEP inline on same row; submit disabled | UX-07 | 38-03 T1 | No frontend test runner for interaction/copy (build only catches type errors) | 38-HUMAN-UAT §3 |
| Full UX-08 sequence: Salvar → modal closes → row spinner → scan completes → spinner clears → products modal auto-opens | UX-08 | 38-03 T2 | End-to-end UI sequence spanning frontend state + backend async completion; no frontend runner | 38-HUMAN-UAT §4 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (backend tasks: pytest/python; frontend tasks: `npm run build` + Wave-0 backend tests + human-check)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (Dimension 8)
- [x] Wave 0 covers all MISSING references (`test_price_monitor.py` new test, `test_brand_active.py` new class, `test_category_monitor.py` new file) — folded into 38-01 Task 1
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `38-HUMAN-UAT.md` created for UX-01/UX-06/UX-07/UX-08
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-07-01 (reconciled with 38-01/38-02/38-03 PLAN.md)
