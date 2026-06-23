---
spike: 005
name: sfcc-public-parser-prototype
type: mvp-test
validates: "Given browser-rendered public SFCC observations, when parsing JSON-LD, OpenGraph metadata, and visible cards, then normalize products toward RawProductBronze without production integration"
verdict: VALIDATED_WITH_DETAIL_PAGE_ENRICHMENT
related: [004]
tags: [scraping, sfcc, parser, json-ld, opengraph]
isolation: "No production imports, no network calls, no EngineFactory registration, no brands.json changes, no main code edits"
---

# Spike 005: SFCC Public Parser Prototype

## User Story
**As a** competitive intelligence operator,
**I want to** normalize public SFCC storefront observations into our canonical product shape,
**so that** we can decide whether a future `sfcc_public` engine is worth planning.

## MVP Mode
**Mode:** mvp

**Goal:** Prove that public browser-rendered SFCC data from Hugo Boss and Lacoste can be converted into `RawProductBronze`-like dictionaries without using unauthorized APIs or touching the production scraper.

## Guardrails
- Offline fixtures only.
- No production imports.
- No network calls.
- No OCAPI/SCAPI.
- No checkout, account, cart, wishlist, ZIP/store availability, private endpoint, proxy, stealth, or CAPTCHA flow.
- No edits under `services/`, `api/`, `core/`, `frontend/`, or `data/brands.json`.

## How to Run
```bash
python .planning/spikes/005-sfcc-public-parser-prototype/experiment.py
```

Outputs:
- `RESULTS.json` - normalized product dictionaries and stats.
- `REPORT.md` - human-readable summary.

## What This Tests
- `Product` and `ProductGroup` JSON-LD.
- OpenGraph product metadata.
- Visible category card price/name/URL hints.
- Canonical field readiness:
  - `url`
  - `brand`
  - `raw_title`
  - `raw_description`
  - `price_full`
  - `price_discount`
  - `stock_availability`
  - `category`
  - `composition`
  - `available_colors`
  - `available_sizes`
  - `image_url`

## Verdict
Validated with product detail enrichment.

Hugo Boss can produce bronze-ready products from category/product JSON-LD plus visible price text.
Lacoste product pages produce bronze-ready products from JSON-LD plus OpenGraph metadata.
Lacoste category cards are useful for discovery but should trigger PDP enrichment because the captured category fixture lacks image and public stock metadata.
