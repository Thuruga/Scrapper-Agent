# MVP Test Plan: SFCC Browser Public Probe

## Scope
Use a normal browser-rendered page flow to inspect public SFCC candidate pages:

- Hugo Boss home, category, product.
- Lacoste home, category, product.

This is a feasibility probe only. It does not create an engine.

## Acceptance Criteria
1. At least one SFCC target loads homepage, category, and product pages in browser context.
2. Category pages expose product names and URLs through public rendered DOM, JSON-LD, or visible cards.
3. Product pages expose enough fields for a future normalized product record: title, URL, image, description, price or price text, and brand/category hints.
4. The probe does not call internal API endpoints or any checkout/account/cart/availability path.
5. The output is documented under `.planning/spikes/004-*` only.

## Observed Pages
| Brand | Page Type | URL |
|---|---|---|
| Hugo Boss | home | `https://www.hugoboss.com/us/` |
| Hugo Boss | category | `https://www.hugoboss.com/us/men-polo-shirts/` |
| Hugo Boss | product | `https://www.hugoboss.com/us/slim-fit-cotton-polo-shirt/hbna50564688_835.html` |
| Lacoste | home | `https://www.lacoste.com/us/` |
| Lacoste | category | `https://www.lacoste.com/us/lacoste/men/clothing/polos/` |
| Lacoste | product | `https://www.lacoste.com/us/lacoste/men/clothing/polos/L1212-51.html?color=001` |

## Pass/Fail
Pass: both brands expose usable public storefront data through browser rendering.

Fail: any future implementation requires direct API credentials, checkout, account, anti-bot bypass, or private mobile/internal endpoints.

## Follow-Up
Build one more isolated parser spike before touching app code. The parser should normalize observed fields and record missing-data behavior per brand.
