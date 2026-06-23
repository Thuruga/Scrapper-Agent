---
spike: 003
name: sfcc-inditex-storefront-mvp
type: mvp-test
validates: "Given public storefront pages only, when probing SFCC and Inditex targets without API credentials, then decide whether a safe isolated scraper path is viable before touching production code"
verdict: BLOCKED_BY_DIRECT_HTTP_403
related: []
tags: [scraping, sfcc, inditex, storefront, compliance]
isolation: "No production imports, no EngineFactory registration, no brands.json changes, no main code edits"
---

# Spike 003: SFCC / Inditex Storefront MVP Test

## User Story
**As a** competitive intelligence operator,
**I want to** validate whether public storefront pages from SFCC brands and Inditex/Zara can provide enough product/category data without authorized API access,
**so that** we can decide whether to invest in a production engine without risking main scraper stability or compliance.

## MVP Mode
**Mode:** mvp

**Goal:** Prove, in an isolated test bench, whether a public-page-only scraper can discover useful product data for Salesforce Commerce Cloud storefronts and Inditex/Zara, while explicitly avoiding internal APIs, checkout/account flows, anti-bot bypass, and production integration.

## SPIDR Split Check
This story is broad if implemented as a production feature. For a test MVP, it is acceptable only with hard scope limits:

- **Spike:** first validate access patterns, robots/sitemap signals, and HTML extractability.
- **Paths:** split SFCC and Inditex paths in the report because the risk profile differs.
- **Interfaces:** produce a markdown/JSON report only; no app endpoint, no UI, no engine factory.
- **Data:** collect only public metadata from robots/homepage and link hints, not cart, stock, checkout, account, or protected JSON.
- **Rules:** stop at 403/401/challenge responses; do not retry aggressively or add bypass logic.

If this spike validates SFCC but not Inditex, the next phase should be SFCC-only. Inditex should remain product-URL monitoring only unless explicit authorization or a clearly public, allowed feed exists.

## Non-Goals
- No OCAPI/SCAPI use without a valid authorized client id.
- No mobile/private Zara endpoint cloning.
- No Playwright stealth, CAPTCHA solving, proxy rotation, or WAF bypass.
- No edits under `services/`, `api/`, `core/`, `frontend/`, or `data/brands.json`.
- No automatic onboarding of Lacoste, Hugo Boss, Zara, or other non-VTEX brands.

## How to Run
```bash
python .planning/spikes/003-sfcc-inditex-storefront-mvp/experiment.py
```

Outputs:
- `REPORT.md` - human-readable feasibility report.
- `report.json` - raw probe data for later comparison.

## What to Expect
The experiment makes a small number of public GET requests per target:

- `robots.txt`
- the configured public homepage/locale URL

It then classifies each target as:

- `sfcc_public_storefront_candidate`
- `inditex_public_storefront_candidate`
- `blocked_from_local_runtime`
- `unknown_or_insufficient_signal`

## Decision Rule
Proceed to a production plan only if the spike shows:

1. enough public category/product links or sitemap signals;
2. product detail data extractable from public HTML/JSON-LD;
3. no need to call blocked/internal/credentialed endpoints;
4. a clear way to enforce crawl rate, robots review, and per-brand disablement.

If those are not true, keep the platform out of the main code and document it as unsupported or manual/product-URL-only.

## Initial Run
Executed on 2026-06-18 from the local project runtime.

Result:
- Hugo Boss US: `403` on robots and homepage.
- Lacoste US: `403` on robots and homepage.
- Zara BR: `403` on robots and homepage.

Current verdict: **BLOCKED_BY_DIRECT_HTTP_403**. The isolated direct-HTTP path is not viable from this runtime without adding bypass behavior, so it must not be promoted into the main code. A later test may evaluate a normal user-controlled browser/manual product URL workflow, but that should remain a separate explicit decision.
