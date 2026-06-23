# Spike 006 Report: SFCC Live Browser E2E Prototype

## Summary
- Verdict: `VALIDATED_LIVE_E2E_PUBLIC_BROWSER`
- Brands tested: `2`
- Normalized products: `6`
- Bronze-ready products: `6`
- Browser errors: `0`
- Validation passed: `True`

## Brand Results
| Brand | Category | Candidate Count | PDPs Visited | Bronze Ready | Notes |
|---|---|---:|---:|---:|---|
| Hugo Boss | https://www.hugoboss.com/us/men-polo-shirts/ | 20 | 3 | 3 | 5 category JSON-LD products, demandware=508 |
| Lacoste | https://www.lacoste.com/us/lacoste/men/clothing/polos/ | 20 | 3 | 3 | category discovery via rendered product links, demandware=1729 |

## Product Output
| Brand | Title | Price | Availability | Color | Quality |
|---|---|---:|---|---|---|
| BOSS | Slim-fit cotton polo shirt | 119 | None | Light Orange | bronze_ready |
| BOSS | Johnny-collar polo shirt in cotton and linen | 179 | None | Light Blue | bronze_ready |
| BOSS | Active Paddy regular-fit polo shirt in quick-dry stretch pique | 129 | None | Light Beige | bronze_ready |
| Lacoste | Men's Classic Fit Original L.12.12 Polo | 110 | True | White | bronze_ready |
| Lacoste | Men's Classic Fit Original L.12.12 Polo | 110 | True | Green | bronze_ready |
| Lacoste | Men's Classic Fit Original L.12.12 Polo | 110 | True | Purple | bronze_ready |

## Findings
- The live browser path met the success threshold: at least 2 bronze-ready products per brand.
- Hugo Boss category pages expose ProductGroup JSON-LD, but PDP visible text is still needed for price.
- Lacoste category pages require stricter PDP-link filtering, then PDP pages provide Product JSON-LD and stock metadata.
- Price parsing must prefer money patterns such as `$119.00`; generic numbers in accessibility text caused false positives in the first trial.
- This remains a browser-rendered public extraction path, not API scraping.

## Out of Scope Preserved
- No OCAPI/SCAPI.
- No checkout, account, cart, wishlist, ZIP/store availability, or shipping.
- No proxy, stealth, CAPTCHA solving, or WAF bypass.
- No production engine/factory/brand registry changes.
