---
phase: 36-onboarding-das-marcas-concorrentes-restantes-lacoste-anti-bo
plan: "01"
subsystem: spike
tags: [lacoste, sfcc, anti-bot, zara, gate]
dependency_graph:
  requires: []
  provides:
    - ".planning/spikes/008-lacoste-antibot-zara-recheck/experiment.py"
    - ".planning/spikes/008-lacoste-antibot-zara-recheck/REPORT.md"
  affects:
    - "36-02 skipped when Lacoste verdict is NO-GO"
    - "36-03 skipped when Lacoste verdict is NO-GO"
key_files:
  created:
    - ".planning/spikes/008-lacoste-antibot-zara-recheck/experiment.py"
    - ".planning/spikes/008-lacoste-antibot-zara-recheck/REPORT.md"
  modified: []
decisions:
  - "Lacoste verdict: NO-GO within the approved public stealth envelope."
  - "Do not implement SFCCAntiBotFetcher in this phase."
  - "Keep backend/data/brands.json unchanged with lacoste.is_active=false."
  - "Zara public pages loaded without block; promote to a dedicated future Zara/Inditex validation phase, no engine built here."
verification:
  - "python -c experiment.py AST/schema check: PASS"
  - "python .planning/spikes/008-lacoste-antibot-zara-recheck/experiment.py: PASS, wrote REPORT.md"
  - "REPORT.md schema check: PASS"
completed: "2026-06-25"
---

# Phase 36 Plan 01: Lacoste Anti-Bot + Zara Recheck - Summary

## Verdict

**Lacoste: `NO-GO`**

All Lacoste probes returned the same anti-bot block signature:

| Probe set | Result |
|---|---|
| Home baseline | HTTP 403, 296 bytes, `Access Denied` |
| Search `polo` baseline | HTTP 403, 296 bytes, `Access Denied` |
| Search `camisa` baseline | HTTP 403, 296 bytes, `Access Denied` |
| Home stealth | HTTP 403, 296 bytes, `Access Denied` |
| Search `polo` stealth | HTTP 403, 296 bytes, `Access Denied` |
| Search `camisa` stealth | HTTP 403, 296 bytes, `Access Denied` |

The approved envelope was exhausted: public headless Chromium, coherent locale/timezone/headers/viewport, `playwright-stealth`, sequential low-rate probing, no profile persistence and no paid proxy/gateway/CAPTCHA/browser-manual escalation.

## Gate Decision

Stop the Lacoste implementation path in Phase 36.

- Do not run 36-02 implementation.
- Do not run 36-03 activation.
- Keep `backend/data/brands.json` unchanged with `lacoste.is_active=false`.
- Do not create a degraded engine or represent this as an empty successful search.

## Zara Outcome

**Zara: `PROMOVER_REQUISITO_FUTURO`**

The recheck loaded public Zara pages with stealth:

| Probe | Status | Bytes | Final URL |
|---|---:|---:|---|
| Home | 200 | 1,734,637 | `https://www.zara.com/br/` |
| Search `polo` | 200 | 960,113 | `https://www.zara.com/br/pt/search?searchTerm=polo&section=WOMAN` |

This does not create a Zara engine in Phase 36. It is only enough to promote a future dedicated Zara/Inditex phase to validate product+price extraction and implementation scope.

## Files

- Created `.planning/spikes/008-lacoste-antibot-zara-recheck/experiment.py`
- Created `.planning/spikes/008-lacoste-antibot-zara-recheck/REPORT.md`

## Verification

```powershell
python -c "import ast,io; p='.planning/spikes/008-lacoste-antibot-zara-recheck/experiment.py'; src=io.open(p,encoding='utf-8').read(); ast.parse(src); assert 'playwright_stealth' in src; assert 'REPORT.md' in src; assert 'BrightData' not in src and 'SCRAPERAPI' not in src; print('OK')"
python .planning/spikes/008-lacoste-antibot-zara-recheck/experiment.py
python -c "from pathlib import Path; p=Path('.planning/spikes/008-lacoste-antibot-zara-recheck/REPORT.md'); t=p.read_text(encoding='utf-8'); assert '## Veredito' in t; assert '## Lacoste' in t; assert '## Zara' in t; assert any(x in t for x in ['GO_TECHNICAL','GO_ACTIVATION','NO-GO']); print('OK')"
```

All passed.
