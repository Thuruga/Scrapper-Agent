---
spike: 004
name: sfcc-browser-public-probe
type: mvp-test
validates: "Given normal browser-rendered public storefront pages, when probing SFCC candidates without API credentials, then determine whether public HTML/JSON-LD extraction is viable"
verdict: VALIDATED_FOR_SFCC_PUBLIC_BROWSER
related: [003]
tags: [scraping, sfcc, browser, storefront, compliance]
isolation: "No production imports, no EngineFactory registration, no brands.json changes, no main code edits"
---

# Spike 004: SFCC Browser Public Probe

## User Story
**As a** competitive intelligence operator,
**I want to** validate SFCC storefront extraction through normal public browser rendering,
**so that** we can decide whether to build a future `sfcc_public` scraper without using unauthorized APIs or changing the main application yet.

## MVP Mode
**Mode:** mvp

**Goal:** Prove whether Hugo Boss and Lacoste expose enough product/category data through public browser-rendered pages to justify a later isolated parser prototype.

## Guardrails
- Browser-rendered public pages only.
- No direct OCAPI/SCAPI.
- No checkout, account, cart, wishlist, availability endpoint, or store inventory flow.
- No proxy rotation, stealth plugin, CAPTCHA solving, or WAF bypass.
- No integration with `services/engines/factory.py`, `data/brands.json`, or app routes.

## Result
**Validated for SFCC public browser path.**

Hugo Boss and Lacoste both loaded in the normal browser context even though Spike 003's direct HTTP requests returned `403`.

High-signal evidence:
- Hugo Boss homepage/category/product loaded.
- Hugo Boss category exposed `ProductGroup` JSON-LD for product cards.
- Hugo Boss product page exposed product JSON-LD and visible price/title/details text.
- Lacoste homepage/category/product loaded.
- Lacoste category exposed product card names, prices, discounts, and product URLs after normal scroll.
- Lacoste product page exposed `Product` JSON-LD plus OpenGraph product price, currency, material, color, availability, and image.

## Verdict
Proceed with a **separate parser prototype** for SFCC browser-rendered public pages.

Do not build a production engine yet. The next step should still be isolated and should prove extraction into our canonical product shape from saved/public page observations.

## Recommended Next Slice
Create `005-sfcc-public-parser-prototype`:

1. Input: a small set of public product/category URLs for Hugo Boss and Lacoste.
2. Output: normalized product dictionaries matching the fields used by `RawProductBronze`.
3. Sources: JSON-LD, OpenGraph product meta, visible card text, and visible product page text.
4. Exclusions: checkout, stock-by-zip, internal APIs, protected endpoints.
