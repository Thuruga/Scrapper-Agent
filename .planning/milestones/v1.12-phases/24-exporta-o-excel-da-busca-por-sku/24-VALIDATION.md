---
phase: 24
slug: exporta-o-excel-da-busca-por-sku
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-15
---

# Phase 24 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | none — default discovery (`tests/`, `test_*.py`) |
| **Quick run command** | `python -m pytest tests/test_export_cross_marketplace.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~2 seconds (baseline 130 tests in ~1.76s) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_export_cross_marketplace.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green (130 baseline + new tests)
- **Max feedback latency:** ~2 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| W0 | 00 | 0 | EXPORT-04/05/06 | — | N/A | unit scaffold | `python -m pytest tests/test_export_cross_marketplace.py -q` | ❌ W0 | ⬜ pending |
| backend | — | 1 | EXPORT-04 | — | xlsx has 10 PT columns + correct values | unit | `pytest tests/test_export_cross_marketplace.py::test_happy_path -x` | ❌ W0 | ⬜ pending |
| backend | — | 1 | EXPORT-04 | — | null shipping → "A calcular", total=price | unit | `pytest tests/test_export_cross_marketplace.py::test_null_shipping -x` | ❌ W0 | ⬜ pending |
| backend | — | 1 | EXPORT-04 | — | booleans → "Sim"/"Não" | unit | `pytest tests/test_export_cross_marketplace.py::test_boolean_mapping -x` | ❌ W0 | ⬜ pending |
| backend | — | 1 | EXPORT-04 | — | score is rounded integer | unit | `pytest tests/test_export_cross_marketplace.py::test_score_rounding -x` | ❌ W0 | ⬜ pending |
| backend | — | 1 | EXPORT-04 | T-formula-injection | cells starting `= + - @` prefixed with `'` | unit | `pytest tests/test_export_cross_marketplace.py::test_formula_injection -x` | ❌ W0 | ⬜ pending |
| backend | — | 1 | EXPORT-05 | — | row order follows `_display_order` | unit | `pytest tests/test_export_cross_marketplace.py::test_display_order -x` | ❌ W0 | ⬜ pending |
| backend | — | 1 | EXPORT-05 | — | output values equal input (fidelity) | unit | `pytest tests/test_export_cross_marketplace.py::test_fidelity -x` | ❌ W0 | ⬜ pending |
| backend | — | 1 | EXPORT-06 | — | filename `busca_sku_<q>_<ts>.xlsx` | unit | `pytest tests/test_export_cross_marketplace.py::test_filename -x` | ❌ W0 | ⬜ pending |
| backend | — | 1 | — | T-empty-payload | empty items → HTTP 400/422 | unit | `pytest tests/test_export_cross_marketplace.py::test_empty_items -x` | ❌ W0 | ⬜ pending |
| backend | — | 1 | — | T-oversized-payload | >500 items → HTTP 422 | unit | `pytest tests/test_export_cross_marketplace.py::test_oversized_payload -x` | ❌ W0 | ⬜ pending |
| frontend | — | 2 | EXPORT-01/02/03 | — | selection + dialog behavior | manual/UAT | — (see Manual-Only) | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_export_cross_marketplace.py` — stubs/tests for EXPORT-04, EXPORT-05, EXPORT-06 + edge cases (empty, oversized, formula injection). Mirror the existing `tests/test_relevance_gates.py` style. Prefer testing the pure helpers (`_build_row`, `_sanitize_cell`) + Pydantic model directly; use `fastapi.testclient.TestClient` only if the app imports cleanly (verify entry point first — see RESEARCH Open Question #2).
- [ ] No `conftest.py` gap — existing tests run without shared fixtures.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Checkbox per card; no tab opens on click; card visual + counter update | EXPORT-01 | DOM interaction in browser | Run a SKU search, click a card checkbox — verify no new tab, card highlights, "N selecionado(s)" increments |
| "Selecionar todos" toggles all on/off | EXPORT-02 | DOM interaction | Click select-all → all checked; click again → all unchecked |
| Dialog: "Apenas selecionados" disabled at 0 selected; overlay click closes, keeps selection | EXPORT-03 | DOM interaction | Open dialog with 0 selected — option greyed/unclickable; click overlay — closes; selection preserved |
| Downloaded filename matches `busca_sku_<query>_<timestamp>.xlsx`; file opens in Excel/LibreOffice; rows match screen | EXPORT-06 | Real download + spreadsheet open | Export "Todos" and "Apenas selecionados"; open both files; compare rows to on-screen results |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (`tests/test_export_cross_marketplace.py`)
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
