---
phase: 23
slug: discrimina-o-de-modelo
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-13
---

# Phase 23 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing — no install) |
| **Config file** | none — default discovery |
| **Quick run command** | `pytest tests/test_model_discrimination.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~1 second |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_model_discrimination.py tests/test_brand_gate.py tests/test_relevance_gates.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 2 seconds

---

## Per-Task Verification Map

> Task IDs are provisional (mirror RESEARCH.md's 2-plan grouping); reconcile against PLAN.md once planning completes.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 23-01-01 | 01 | 1 | MODEL-01 | — | N/A (typed pydantic fields) | unit | `pytest tests/test_model_discrimination.py::TestModelPenalty -q` | ❌ W0 | ⬜ pending |
| 23-02-01 | 02 | 2 | MODEL-02 | — | N/A | unit | `pytest tests/test_model_discrimination.py::TestVisualTiebreak::test_promotes_higher_image_within_window -q` | ❌ W0 | ⬜ pending |
| 23-02-02 | 02 | 2 | MODEL-01 (criterion 3) | — | N/A | unit | `pytest tests/test_model_discrimination.py::TestModelPenalty::test_model_ratio_zero_below_cutoff_with_high_image -q` | ❌ W0 | ⬜ pending |
| 23-02-03 | 02 | 2 | MODEL-02 (fallback) | — | N/A | unit | `pytest tests/test_model_discrimination.py::TestVisualTiebreak::test_fallback_when_disabled -q` | ❌ W0 | ⬜ pending |
| 23-02-04 | 02 | 2 | MODEL-01 (criterion 4 non-regression) | — | N/A | unit | `pytest tests/test_model_discrimination.py::TestModelPenalty::test_correct_model_unaffected_by_penalty -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_model_discrimination.py` — 5 anchor tests for MODEL-01 / MODEL-02 (does not exist yet)

*All other infrastructure is in place: pytest, `relevance_gates`, `nlp_service`, and the test style from `tests/test_brand_gate.py`.*

---

## 5 Mandatory Anchor Tests (from CONTEXT.md / RESEARCH.md)

1. **MODEL-01 anchor:** Two Aramis polo candidates (correct model vs adjacent model). After Phase 23 penalties, correct model ranks first in `apply_visual_tiebreak` output.
2. **MODEL-02 anchor:** Two Aramis candidates with `final_match_score` within the 10-point window (e.g. 86 vs 85). Candidate with higher `image_match_score` ranks first.
3. **Criterion 3 anchor:** Candidate with `model_ratio ≈ 0` (same brand, zero model-words) → `compute_final_match_score(88*0.40, 85) < 60` AND `compute_final_match_score(90*0.40, 90) < 60` (below cutoff, even with the Gate-1 image rescue). Planner chose `HEAVY_WITH_BRAND=0.40` (conservative bound: `90*0.40=36 < 40` MED_TEXT_FLOOR; 0.45 fails at raw=90).
4. **Non-regression anchor:** Correct model + correct brand (`model_ratio = 1.0`): text score unaffected by penalty, stays at top.
5. **Fallback anchor:** `VISUAL_TIEBREAK_ENABLED=False` OR all `image_score == 0` → output order equals `(-final_match_score, preco)` — identical to current behavior.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Window default (10.0) cobre a dispersão real entre variantes de modelo correto em categorias além de polo (tênis, camiseta) | MODEL-02 (calibração) | Depende de dados reais de busca por categoria; o valor é tunável via `.env` sem código | Após primeira busca real por categoria nova, conferir em `data/search_history.json` se o spread do modelo correto cabe na janela; ajustar `VISUAL_TIEBREAK_TEXT_WINDOW` se necessário |

*Note: the [ASSUMED] window=10.0 (RESEARCH A1) is calibrated against polo data only; other categories are a manual re-calibration item, not a code blocker.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (`tests/test_model_discrimination.py`)
- [ ] No watch-mode flags
- [ ] Feedback latency < 2s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
