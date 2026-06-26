---
phase: 36
slug: onboarding-das-marcas-concorrentes-restantes-lacoste-anti-bo
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-25
---

# Phase 36 - Validation Strategy

> Contrato de validacao por phase para amostragem de feedback durante a execucao.
> Derivado de `36-RESEARCH.md` e `36-CONTEXT.md`.

## Test Infrastructure

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | `pytest.ini` |
| Quick run command | `python -m pytest backend/tests/test_sfcc_antibot_fetcher.py backend/tests/test_sfcc_engine.py -q --tb=short` |
| Full suite command | `python -m pytest backend/tests/ -q` |
| Estimated runtime | ~20-60s for full backend suite |

## Sampling Rate

- **After every task:** run the task-specific `<automated>` command.
- **After Wave 0:** validate `REPORT.md` sections and gate value.
- **After Wave 1:** `python -m pytest backend/tests/test_sfcc_antibot_fetcher.py backend/tests/test_sfcc_engine.py -q --tb=short`.
- **Before phase close:** `python -m pytest backend/tests/ -q`.

## Per-Task Verification Map

| Item | Wave | Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|------|------|-------------|-----------------|-----------|-------------------|-------------|--------|
| Lacoste/Zara spike report | 0 | COMP-03 gap / COMP-FUT-03 | GO/NO-GO documented before backend code | live spike | `python .planning/spikes/008-lacoste-antibot-zara-recheck/experiment.py` | missing W0 | pending |
| REPORT schema | 0 | COMP-03 gap / COMP-FUT-03 | Veredito + Lacoste evidence + Zara outcome present | doc check | `python -c "from pathlib import Path; t=Path('.planning/spikes/008-lacoste-antibot-zara-recheck/REPORT.md').read_text(encoding='utf-8'); assert '## Veredito' in t and '## Zara' in t"` | missing W0 | pending |
| Fetcher applies stealth | 1 | COMP-03 gap | Dedicated fetcher applies `Stealth`, not global BrowserManager | unit | `python -m pytest backend/tests/test_sfcc_antibot_fetcher.py -q` | missing W1 | pending |
| SFCCEngine routes Lacoste through fetcher | 1 | COMP-03 gap | Only Lacoste/flag path uses anti-bot fetcher | unit | `python -m pytest backend/tests/test_sfcc_engine.py::TestSFCCEngineSearch -q` | existing, extend W1 | pending |
| Anti-bot failure is diagnostic | 1 | COMP-03 gap | Block signature returns `BrandSearchResult.error`, not silent empty success | unit | `python -m pytest backend/tests/test_sfcc_engine.py -q` | existing, extend W1 | pending |
| Activation gate | 2 | COMP-03 gap | `is_active=true` only after >=3 repeatable products | live smoke + data check | `python .planning/spikes/008-lacoste-antibot-zara-recheck/activation_smoke.py` | missing W2 | pending |
| Regression suite | 2 | all | Existing engines/tests still green | regression | `python -m pytest backend/tests/ -q` | existing | pending |

## Wave 0 Requirements

- [ ] `.planning/spikes/008-lacoste-antibot-zara-recheck/experiment.py`
- [ ] `.planning/spikes/008-lacoste-antibot-zara-recheck/REPORT.md`
- [ ] REPORT has explicit GO/NO-GO.
- [ ] Zara recheck outcome is documented.

## Manual-Only Verifications

None required by default. Proxy/gateway/CAPTCHA escalation is intentionally not planned; if the user later approves it, that approval becomes a separate checkpoint or phase.

## Validation Sign-Off

- [x] Every planned task has an automated verification command.
- [x] No three implementation tasks are consecutive without automated verification.
- [x] Wave 0 covers live-network uncertainty before backend code.
- [x] No watch-mode flags.
- [x] Nyquist validation document exists before plan execution.
