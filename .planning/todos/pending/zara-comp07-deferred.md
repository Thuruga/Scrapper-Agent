---
created: 2026-06-29
updated: 2026-07-01
area: backend (engine) + research
source: 39-02 spike 010 (NO-GO verdict, operator-ratified); REVISADO 2026-07-01 (operator live retest, GO)
priority: medium
resolves_phase: 39
status: resolved
---

# COMP-07 (Zara) — REVISADO 2026-07-01: GO, engine built and active

**Update (2026-07-01):** Operator re-tested Zara BR extraction live and confirmed
product + price are extractable (mirrors the Lacoste spike-009 pattern — the
original NO-GO was environment-dependent, not a structural block). `ZaraEngine`
+ `zara_parser.py` were built and `brands.json`'s `zara` entry (`engine: "zara"`,
`is_active: true`) is now backed by a real implementation — closing a latent gap
where `factory.py` (commit `d05b6eb`) referenced `services.engines.zara_engine`
before that module existed in git history. No fresh automated spike report was
generated for this reversal; evidence is the operator's live retest plus a
category scan export (`dados_zara_categoria.xlsx`) and the full backend suite
(473 tests) passing with the new engine wired in. `proxy_url` is still unset for
Zara — if the anti-bot block reappears from a datacenter/corporate IP (as with
Lacoste), the same clean-egress remediation applies.

Original NO-GO record preserved below for context.

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
