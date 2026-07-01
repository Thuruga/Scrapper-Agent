---
phase: 38
slug: ux-de-busca-monitoramento-quick-wins
status: draft
nyquist_compliant: false
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
| **Quick run command** | `cd backend && python -m pytest tests/test_price_monitor.py tests/test_brand_active.py -q` (backend tasks); `cd frontend && npm run build` (frontend tasks) |
| **Full suite command** | `cd backend && python -m pytest -q` + `cd frontend && npm run build` |
| **Estimated runtime** | ~5-15 seconds (backend suite is small; frontend build under a minute) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command matching the task's stack (backend pytest subset or frontend build)
- **After every plan wave:** Run the full suite command (full backend pytest + frontend build)
- **Before `/gsd-verify-work`:** Full suite must be green + manual UAT complete for UX-01/UX-06/UX-07/UX-08
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD-01 | TBD | 0 | COMP-08 | — | N/A | unit | `pytest tests/test_brand_active.py::TestLacosteExcludedFromActiveOnly -x` | ❌ W0 | ⬜ pending |
| TBD-02 | TBD | 0 | UX-02 | — | N/A | unit | `pytest tests/test_price_monitor.py -k discount -x` | ❌ W0 | ⬜ pending |
| TBD-03 | TBD | 0 | UX-08 | — | N/A | integration | `pytest tests/test_category_monitor.py -k auto_scan -x` | ❌ W0 | ⬜ pending |
| TBD-04 | TBD | 1 | UX-01 | — | N/A | manual | N/A — CSS-only, no automated viewport test infra | N/A | ⬜ pending |
| TBD-05 | TBD | 1 | UX-06 | — | N/A | manual | N/A — no frontend test runner | N/A | ⬜ pending |
| TBD-06 | TBD | 1 | UX-07 | V5 Input Validation | Frontend regex is UX-only; backend SKU validation unaffected | manual + build | `cd frontend && npm run build` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Exact Task IDs / Plan IDs / Waves finalized once gsd-planner produces PLAN.md files — this map is seeded from RESEARCH.md's Phase Requirements → Test Map and will be reconciled during plan-checking.*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_price_monitor.py::test_price_monitor_promo_only_change_triggers_history` — new test for D-01/D-03 (promo-only change triggers history + WS `price_update` with discount field)
- [ ] `backend/tests/test_brand_active.py::TestLacosteExcludedFromActiveOnly` — new test class for COMP-08 regression, following `TestMarketplacesInBrandsJson`'s pattern
- [ ] `backend/tests/test_category_monitor.py` — confirm via fresh `Glob` whether this file exists before creating; if not, create with a test asserting `run_category_scan` populates `last_scraped_at` / that `background_tasks.add_task` is invoked on category creation (UX-08 backend coverage)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|--------------------|
| `.grid-category` and category-scan layout collapse without overflow at ≤768px | UX-01 | No automated DOM/viewport test infra in this repo (frontend has no test runner) | Resize browser (or devtools responsive mode) to 768px width on the category monitor and category-scan screens; confirm no horizontal scroll/overlap |
| History icon toggles panel with correct badge count, positioned top-right on both search tabs | UX-06 | No frontend test runner; visual/interaction check | Open comparativa and SKU search tabs; click history icon top-right; confirm panel opens and badge count matches history entries |
| SKU field rejects non-`ML.05.XXXXXXX` input with inline error copy; CEP inline on same row as SKU | UX-07 | No frontend test runner for interaction/copy assertions (build only catches type errors) | Type invalid SKU, confirm error text "Formato inválido. Use o padrão ML.05.XXXXXXX (ex: ML.05.0326046)."; confirm CEP field renders inline with SKU input |
| Full UX-08 sequence: Salvar closes modal immediately → row shows spinner → sweep completes in background → spinner clears → products modal auto-opens | UX-08 | End-to-end UI sequence spanning frontend state + backend async task completion; no frontend test runner | Create a new monitored category; confirm modal closes immediately, spinner shows on the row, and the products modal opens automatically once the scan finishes (within poll's max-attempts window) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (`test_price_monitor.py` new test, `test_brand_active.py` new class, `test_category_monitor.py` existence check)
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `38-HUMAN-UAT.md` created for UX-01/UX-06/UX-07/UX-08 (mirrors `44-HUMAN-UAT.md` precedent for phases with unavoidable manual verification steps)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
