# Spike 004 Report: SFCC Browser Public Probe

## Summary
The SFCC browser-rendered public path is viable enough for one more isolated parser prototype.

Direct HTTP failed in Spike 003, but normal browser rendering loaded the storefront pages for both Hugo Boss and Lacoste. This matters: the viable path is not a simple `requests/aiohttp` scraper; it is a browser-rendered public storefront extractor with strict guardrails.

## Results
| Brand | Home | Category | Product | Evidence | Verdict |
|---|---|---|---|---|---|
| Hugo Boss | loaded | loaded | loaded | Demandware/SFCC signals, category `ProductGroup` JSON-LD, product JSON-LD, visible price/details | viable |
| Lacoste | loaded | loaded after normal scroll | loaded | Demandware/SFCC signals, rendered product cards, product JSON-LD, OpenGraph product price/material/color/availability | viable |

## Hugo Boss Evidence
- Home resolved to `https://www.hugoboss.com/us/home`.
- Home exposed Demandware signals and public product/category links.
- Category `https://www.hugoboss.com/us/men-polo-shirts/` exposed 5 product `ProductGroup` JSON-LD objects in the rendered page.
- Product card sample: `Slim-fit cotton polo shirt`, brand `BOSS`, color `Light Orange`, visible price `$119.00`.
- Product page exposed a matching `ProductGroup` JSON-LD object and visible PDP details.

## Lacoste Evidence
- Home loaded in browser context and exposed SFCC/Demandware signals.
- Category `https://www.lacoste.com/us/lacoste/men/clothing/polos/` exposed rendered product cards after normal scroll.
- Category visible text included `508 results`, product names, prices, discounts, and product URLs.
- Product page exposed `Product` JSON-LD and OpenGraph product metadata:
  - price `110.0`
  - currency `USD`
  - material `Cotton (100%)`
  - color `White`
  - availability `INSTOCK`

## Important Constraint
This validates **browser-rendered public extraction**, not API scraping.

Do not implement:
- OCAPI/SCAPI without authorized credentials.
- checkout simulation for these brands.
- availability by ZIP/store.
- cart/account/wishlist flows.
- anti-bot bypass or proxy rotation.

## Recommendation
Proceed to a new isolated spike: `005-sfcc-public-parser-prototype`.

That parser should consume only browser-rendered public HTML/DOM observations and normalize:
- `url`
- `brand`
- `raw_title`
- `raw_description`
- `price_full`
- `price_discount` when visible
- `stock_availability` when public meta exposes it
- `category`
- `composition`
- `available_colors`
- `available_sizes`
- `image_url`

Only after that parser proves stable should we consider a production phase for a guarded `sfcc_public` engine.
