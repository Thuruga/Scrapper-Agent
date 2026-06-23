---
phase: 26
slug: onboarding-das-5-marcas-vtex
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-19
---

# Phase 26 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (sem config especial — coleta `tests/` por default) |
| **Config file** | none |
| **Quick run command** | `python -m pytest tests/test_vtex_brand_onboarding_contract.py -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~{N} seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_vtex_brand_onboarding_contract.py -q`
- **After every plan wave:** Run `python -m pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** {N} seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| {N}-01-01 | 01 | 1 | COMP-01 | T-26-01 / — | {expected secure behavior or "N/A"} | unit | `{command}` | ✅ / ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_vtex_brand_onboarding_contract.py` — contract stubs for COMP-01 (engine=vtex, is_active, mappings persisted, in active list)
- [ ] shared fixtures — reuse existing `tests/test_engine_detection.py` / `test_brand_active.py` patterns

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Busca por marca retorna produtos reais (critério 1) | COMP-01 | WAF/geo/rede ao vivo — frágil para automação (D-10) | Rodar 1 query por marca via `search_all_brands`, confirmar ≥1 produto real |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < {N}s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** {pending / approved YYYY-MM-DD}
