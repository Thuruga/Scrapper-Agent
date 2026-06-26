# Phase 36: Onboarding das Marcas Concorrentes Restantes - Lacoste (anti-bot) & Zara - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-06-25
**Phase:** 36-Onboarding das Marcas Concorrentes Restantes - Lacoste (anti-bot) & Zara
**Areas discussed:** Anti-bot envelope, Lacoste GO threshold, implementation isolation, Zara scope

---

## Anti-bot limit

| Option | Description | Selected |
|--------|-------------|----------|
| Public realistic browser only | Use `playwright-stealth`, realistic browser context, low frequency, evidence logging. No proxy/CAPTCHA escalation by default. | yes |
| Include residential proxy/gateway now | Allow BrightData/ScraperAPI/proxy rotation inside the phase from the start. Higher cost/risk. | |
| Stop at current BrowserManager | Retest only the existing headless browser path. Lowest risk, likely repeats current Access Denied. | |

**User's choice:** Public realistic browser only.
**Notes:** Proxy residencial, ScraperAPI/BrightData, CAPTCHA solving, headed/manual browser or persistent real profile require explicit later approval.

---

## Lacoste GO threshold

| Option | Description | Selected |
|--------|-------------|----------|
| Technical GO >=1, activation >=3 repeatable | Prove route with one product, but only activate Lacoste after a stronger repeated result set. | yes |
| GO >=1 and activate immediately | Fastest path, weaker operational confidence. | |
| GO >=5 products | Stronger proof, may reject a viable early path unnecessarily. | |

**User's choice:** Technical GO with >=1 product; activation only with >=3 products and repeatable flow.
**Notes:** Product must have title + Lacoste URL + price. Query: `polo`, fallback `camisa`.

---

## Implementation placement

| Option | Description | Selected |
|--------|-------------|----------|
| Lacoste/SFCC-specific flagged path | Add a dedicated wrapper/fetcher used only for Lacoste/SFCC anti-bot, preserving global BrowserManager behavior. | yes |
| Change BrowserManager globally | All Playwright consumers inherit stealth/browser changes. Simpler but regression-prone. | |
| Separate standalone script only | Never integrate into backend. Good for NO-GO, insufficient for GO activation. | |

**User's choice:** Lacoste/SFCC-specific flagged path.
**Notes:** Do not globally change banners, detection, Amazon, Mercado Livre or other Playwright paths as the first implementation.

---

## Zara scope

| Option | Description | Selected |
|--------|-------------|----------|
| Spike/reassessment only | Reevaluate public viability and document promote/defer. No engine in this phase. | yes |
| Build Zara if any signal appears | Larger scope; risks mixing discovery with implementation. | |
| Defer Zara without retest | Keeps phase Lacoste-only, but misses requested recheck. | |

**User's choice:** Spike/reassessment only.
**Notes:** If viable, promote to active requirement/future phase. If still blocked/proprietary, keep COMP-FUT-03 deferred with updated evidence.

---

## Deferred Ideas

- Proxy/gateway/CAPTCHA escalation for Lacoste without explicit user approval.
- Building Zara/Inditex engine inside Phase 36.
- Frete/checkout/estoque for SFCC/Lacoste.
- Global BrowserManager stealth rewrite.
