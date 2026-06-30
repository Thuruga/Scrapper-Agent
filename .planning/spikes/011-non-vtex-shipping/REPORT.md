# Spike 011: Non-VTEX Shipping

Generated: 2026-06-29T21:43:08.605290+00:00
CEP used: 01415***

## Verdict

| Provider | Brand | Verdict | State | Options | Status |
|----------|-------|---------|-------|---------|--------|
| Shopify/Buckman | bck | GO | available | 2 | 200,200 |
| Wake/Richards | richards | GO | available | 2 | 200,200 |

## Evidence

### Shopify/Buckman

- Brand key: `bck`
- Domain: `buckmanbck.com.br`
- Product URL: `https://buckmanbck.com.br/products/blazer-de-veludo-chevron-marron-602-700`
- Response signature: `shipping_rates[] returned`
- Options count: 2
- Sample options:
  - `{"name": "PAC", "price": 0.0, "delivery_date": "2026-07-08", "delivery_days": [7, 7], "source": "Frenet"}`
  - `{"name": "Sedex", "price": 28.85, "delivery_date": "2026-07-02", "delivery_days": [3, 3], "source": "Frenet"}`
- Notes:
  - Primary Shopify target is Buckman/BCK; roadmap VTEX mention is ignored.
  - Product: BLAZER DE VELUDO CHEVRON MARROM / variant_id=52196300816673

### Wake/Richards

- Brand key: `richards`
- Domain: `www.richards.com.br`
- Product URL: `https://www.richards.com.br/produto/camisa-linho-hortencia-196863`
- Response signature: `shippingQuotes[] returned`
- Options count: 2
- Sample options:
  - `{"name": "PAC", "price": 24.32, "deadline": 8, "deadlineInHours": null, "type": "Tabela"}`
  - `{"name": "SEDEX", "price": 32.95, "deadline": 4, "deadlineInHours": null, "type": "Tabela"}`
- Notes:
  - Uses public Storefront GraphQL token already stored for Richards.
  - Product: Camisa Linho Hortencia / productVariantId=548230 / sku=61RB50499_112IS_2

## Implementation Decisions

- Shopify/Buckman: implement real provider using Shopify Ajax Cart (`cart/add.js`, `prepare_shipping_rates.json`, `async_shipping_rates.json`) when verdict is GO.
- Wake/Richards: implement real provider using Storefront GraphQL `shippingQuotes(cep, productVariantId, quantity)` when verdict is GO.
- VTEX remains unchanged in `VtexApiClient`; do not route VTEX through `BaseShipping`.
- SFCC remains unsupported in Phase 41.
