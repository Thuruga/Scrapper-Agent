# Spike 005 Report: SFCC Public Parser Prototype

## Summary
- Normalized products: `4`
- Bronze-ready products: `3`
- Needs product detail page: `1`
- Insufficient: `0`

## Product Output
| Source | Quality | Brand | Title | Full | Discount | Availability | Missing |
|---|---|---|---|---:|---:|---|---|
| hugoboss_category_productgroup | bronze_ready | BOSS | Slim-fit cotton polo shirt | 119.00 | - | - | - |
| hugoboss_product_productgroup | bronze_ready | BOSS | Slim-fit cotton polo shirt | 119.00 | - | - | - |
| lacoste_category_card | needs_detail_page | Lacoste | Men's Classic Fit Original L.12.12 Polo | 110.00 | 54.99 | - | image_url |
| lacoste_product_jsonld_meta | bronze_ready | Lacoste | Men's Classic Fit Original L.12.12 Polo | 110.00 | - | True | - |

## Verdict
The parser prototype is viable for a future isolated `sfcc_public` engine design.

Hugo Boss is strongest at category level because rendered category pages expose ProductGroup JSON-LD.
Lacoste is strongest at product page level because PDP pages expose Product JSON-LD and OpenGraph product metadata.
Lacoste category cards are useful for discovery but should be enriched by visiting the product detail page because image and stock are missing from the captured card fixture.

## Production Implications
- Use JSON-LD first.
- Use OpenGraph product metadata as a supplement, especially for Lacoste price/material/color/availability.
- Use visible card text for discovery and price hints, not as final product data when image or availability are missing.
- Keep checkout, account, cart, wishlist, ZIP availability, private APIs, and bypass behavior out of scope.
