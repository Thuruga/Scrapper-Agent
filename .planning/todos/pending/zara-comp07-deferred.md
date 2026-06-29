---
created: 2026-06-29
area: backend (engine) + research
source: 39-02 spike 010 (NO-GO verdict, operator-ratified)
priority: medium
resolves_phase:
---

# COMP-07 (Zara) deferred — public extraction blocked by anti-bot

Phase 39-02 spike 010 returned **NO-GO**: Zara BR's public storefront blocks
product+price extraction within the allowed envelope (browser + playwright-stealth,
no proxy/CAPTCHA/login).

## Evidence (2026-06-29, live)

- Spike 2 rounds (queries `camiseta`/`calça`, `section=MAN`): HTTP 200 + ~940KB
  challenge shells, **0 extractable products** (JSON-LD / network interception /
  HTML tiles all empty). See `.planning/spikes/010-zara-product-price/REPORT.md`.
- Independent adversarial reprobe: hard **403 Access Denied** (301 bytes, captcha/
  block signals, 0 product tiles, 0 product XHR).
- Conclusion: not an extraction gap — a genuine, variable anti-bot block.

## Re-evaluation conditions (future spike, separate phase)

Revisit COMP-07 only if pursuing an **out-of-envelope** approach (explicitly out of
scope for Phase 39 per D-06/T-39-ENV):

1. Official Inditex/Zara data feed or API access (if obtainable).
2. Authorized residential/anti-bot proxy or scraping gateway (cost + ToS review).
3. CAPTCHA/challenge handling (legal + ToS review).

Mirror the 39-02 gate: run a viability spike that proves ≥3 real products in 2
rounds BEFORE any `InditexEngine` code is written. Until then, no Zara engine,
no `zara` entry in `brands.json`.
