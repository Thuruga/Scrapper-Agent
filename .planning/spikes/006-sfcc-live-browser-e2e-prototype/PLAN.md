# MVP Test Plan: SFCC Live Browser E2E Prototype

## Scope
Use a normal browser-rendered flow to test:

1. Open category page.
2. Discover PDP links.
3. Visit up to 3 PDPs.
4. Normalize products to `RawProductBronze`-like dictionaries.
5. Save results under this spike only.

## Targets
| Brand | Category URL | Limit |
|---|---|---:|
| Hugo Boss | `https://www.hugoboss.com/us/men-polo-shirts/` | 3 PDPs |
| Lacoste | `https://www.lacoste.com/us/lacoste/men/clothing/polos/` | 3 PDPs |

## Acceptance Criteria
1. At least 2 bronze-ready products per brand.
2. No browser errors or blocked pages.
3. Category discovery works without private APIs.
4. PDP extraction fills `url`, `brand`, `raw_title`, `price_full`, and `image_url`.
5. Any gaps are explicitly reported.
6. No production code files are touched.

## Result
Passed.

- Hugo Boss: 3/3 bronze-ready.
- Lacoste: 3/3 bronze-ready.
- Browser errors: 0.
- Production integration: none.

## Next Step
Plan a real implementation phase for a guarded `sfcc_public` engine.
