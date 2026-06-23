---
spike: 006
name: sfcc-live-browser-e2e-prototype
type: mvp-test
validates: "Given public browser-rendered SFCC category pages, when discovering PDP links and extracting up to 3 products per brand, then produce bronze-ready normalized products without production integration"
verdict: VALIDATED_LIVE_E2E_PUBLIC_BROWSER
related: [004, 005]
tags: [scraping, sfcc, browser, e2e, parser]
isolation: "No production imports, no EngineFactory registration, no brands.json changes, no main code edits"
---

# Spike 006: SFCC Live Browser E2E Prototype

## User Story
**As a** competitive intelligence operator,
**I want to** prove the public SFCC browser path from category discovery to PDP extraction,
**so that** we can decide whether a real `sfcc_public` engine deserves a production phase.

## MVP Mode
**Mode:** mvp

**Goal:** Visit one public category per brand, discover up to 3 product detail pages, extract public data, and emit `RawProductBronze`-like product dictionaries.

## Guardrails
- Public browser-rendered pages only.
- Maximum 3 product pages per brand.
- No OCAPI/SCAPI.
- No checkout, account, cart, wishlist, ZIP/store availability, shipping, or private endpoint.
- No proxy, stealth, CAPTCHA solving, or WAF bypass.
- No production code integration.

## How to Verify
```bash
python .planning/spikes/006-sfcc-live-browser-e2e-prototype/experiment.py
```

Outputs:
- `raw_products.json` - live normalized products.
- `LIVE_RESULT.json` - live browser run summary.
- `REPORT.md` - regenerated validation report.

## Verdict
Validated.

The live browser E2E produced 6 normalized products:
- Hugo Boss: 3 bronze-ready products.
- Lacoste: 3 bronze-ready products.
- Errors: 0.

This is enough evidence to plan a real `sfcc_public` phase, provided it remains behind explicit configuration, conservative rate limits, and the same public-page-only scope.
