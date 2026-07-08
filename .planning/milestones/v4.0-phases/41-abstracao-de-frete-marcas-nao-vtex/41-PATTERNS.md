# Phase 41: Abstracao de Frete & Marcas Nao-VTEX - Pattern Map

**Mapeado:** 2026-06-29
**Arquivos analisados:** planos/fases 31-33, engines Wake/Shopify, API de busca, modelos e testes existentes
**Analogs encontrados:** 10 / 10

---

## File Classification

| Novo/Modificado | Role | Data Flow | Analog mais proximo | Qualidade |
|-----------------|------|-----------|----------------------|-----------|
| `.planning/spikes/011-non-vtex-shipping/experiment.py` | spike | live probe | `.planning/spikes/010-zara-product-price/experiment.py` | role-match |
| `.planning/spikes/011-non-vtex-shipping/REPORT.md` | evidence | manual | spikes anteriores `REPORT.md` | exact |
| `backend/services/shipping/base.py` | service contract | request-response | `backend/services/engines/base_engine.py` | role-match |
| `backend/services/shipping/resolver.py` | factory/resolver | lookup | `backend/services/engines/factory.py` | exact |
| `backend/services/shipping/unsupported.py` | service fallback | request-response | `SFCCEngine.calculate_shipping -> None` decision | role-match |
| `backend/services/shipping/shopify.py` | provider | request-response | `backend/services/shopify_api_client.py` + Shopify Ajax Cart docs | role-match |
| `backend/services/shipping/wake.py` | provider | request-response | `backend/services/engines/wake_engine.py` | role-match |
| `backend/services/engines/shopify_engine.py` | integration | batch search | current inline shipping args pattern | exact |
| `backend/services/engines/wake_engine.py` | integration | batch search | current token/session/query pattern | exact |
| `backend/api/routes_search.py` | API route | request-response | `/search/calculate-shipping-vtex` | exact |
| `frontend/src/App.tsx` / `client.ts` | UI/API client | user action | Phase 33 shipping modal/options | exact |

---

## Contract Pattern: Provider Result

Use a small internal result shape, but emit existing models to the rest of the app.

```python
class ShippingState:
    AVAILABLE = "available"
    UNAVAILABLE_FOR_CEP = "unavailable_for_cep"
    TEMPORARY_FAILURE = "temporary_failure"
    UNSUPPORTED = "unsupported"

@dataclass
class ShippingCalculation:
    state: str
    shipping_options: list[ShippingInfo]
    message: str | None = None
    raw: dict[str, Any] | None = None
```

**Invariant:** callers only populate `shipping_price` from `shipping_options[0].price` when `state == "available"` and the list is non-empty. `None` remains not calculated.

---

## `backend/services/shipping/base.py`

**Analog:** `backend/services/engines/base_engine.py`

Pattern:

- ABC or Protocol with `async calculate(product, zipcode, brand) -> ShippingCalculation`.
- Keep domain-specific state constants here.
- No HTTP implementation in base.
- No VTEX import.

Read first during execution:

- `backend/core/models.py` for `ShippingInfo` and `SearchProductResult`.
- `backend/services/engines/base_engine.py` for style and async contract.
- `41-CONTEXT.md` D-01 to D-04.

---

## `backend/services/shipping/resolver.py`

**Analog:** `backend/services/engines/factory.py`

Pattern:

```python
def resolve_shipping_provider(brand: DynamicBrand) -> BaseShipping:
    if brand.engine == "shopify":
        return ShopifyShipping()
    if brand.engine == "wake":
        return WakeShipping()
    return UnsupportedShipping(reason=f"engine {brand.engine} not supported")
```

Rules:

- Centralize all engine branching here.
- VTEX should return unsupported or never be sent here; do not return a VTEX provider.
- Tests must assert `engine="vtex"` does not map to Wake/Shopify.

---

## `backend/services/shipping/shopify.py`

**Analogs:**

- `backend/services/shopify_api_client.py` for product URL -> product JSON and variant extraction.
- Shopify Ajax Cart API docs for cart add + shipping rates.

Provider flow:

1. Validate product URL host against persisted Shopify domain.
2. Resolve product JSON from URL and choose first available variant, unless product metadata provides a better variant.
3. Create/use isolated session with storefront host.
4. `POST /cart/clear.js` best effort before/after.
5. `POST /cart/add.js` with `{"items": [{"id": variant_id, "quantity": 1}]}`.
6. `POST /cart/prepare_shipping_rates.json` with `shipping_address[zip]`, `shipping_address[country]=Brazil`.
7. Poll `GET /cart/async_shipping_rates.json` with same params, bounded attempts.
8. Normalize `shipping_rates[]` to `ShippingInfo`.

Pitfalls:

- Price may be string decimal (`"12.46"`) rather than cents.
- Rate may have no delivery date/days; preserve raw text/name and leave parsed days `None`.
- A cart may be polluted by previous items if cleanup fails; use fresh session and cleanup.
- Locale-aware paths may be needed (`/pt-br/cart/...` or root). Spike decides exact path; provider should fallback root first then documented locale path if needed.

---

## `backend/services/shipping/wake.py`

**Analogs:**

- `backend/services/engines/wake_engine.py` for token resolution, domain, GraphQL session and product URL construction.
- Wake/Fbits official endpoint `POST https://api.fbits.net/fretes/cotacoes`.

Provider flow:

1. Validate product URL host against persisted Wake domain.
2. Resolve product identity from Wake product data: prefer `ProdutoVarianteId` if exposed; fallback `Sku` only if verified by spike.
3. Build quote request with CEP query param, `tipoIdentificador`, optional `retiradaLoja=false`, body `valorTotal` and `produtos`.
4. Add only headers proven by spike. Do not invent private credentials.
5. Normalize response options to `ShippingInfo`.

Pitfalls:

- The public storefront token used for GraphQL may not authorize `api.fbits.net/fretes/cotacoes`.
- Richards product search currently may not keep SKU/variant id in `SearchProductResult`; additive metadata may be needed only after spike evidence.
- If the endpoint returns 422 for unavailable CEP, classify as `unavailable_for_cep` only when response indicates valid processed absence; transport/auth failures are `temporary_failure` or `unsupported`.

---

## Engine Integration Pattern

### Shopify/Wake inline

```python
if include_shipping and zipcode:
    result = await self.calculate_shipping(product, zipcode)
    apply_shipping_result(product, result)
```

Rules:

- Do not attempt shipping when CEP is missing.
- Absorb provider failure per product.
- Preserve product result even when shipping fails.
- Do not run shipping for SFCC.

### Shared helper suggested

Create helper in `shipping/base.py` or `shipping/utils.py`:

```python
def apply_shipping_result(product: SearchProductResult, calc: ShippingCalculation) -> None:
    ...
```

This avoids duplicate logic in Wake and Shopify.

---

## API Pattern: `/search/calculate-shipping-brand`

**Analog:** existing `/search/calculate-shipping-vtex`.

Request model suggested:

```python
class CalculateBrandShippingRequest(BaseModel):
    brand_key: str
    product_url: str
    zipcode: str = Field(pattern=r"^\d{5}-?\d{3}$")
```

Implementation rules:

- Resolve `DynamicBrand` by `brand_key`.
- Validate URL host is brand domain or subdomain allowed by persisted domain.
- If brand engine is `vtex`, return an explicit error directing callers to existing VTEX endpoint or call existing endpoint only through the existing path. Do not silently route VTEX through `BaseShipping`.
- Return `state`, `shipping_options`, primary fields, and message.

---

## Frontend Pattern

**Analogs:** Phase 33 additions in `frontend/src/App.tsx`, `frontend/src/api/client.ts`, `frontend/src/stores/searchStore.ts`.

Rules:

- Keep renderer for `shipping_options` as source of truth.
- Same copy:
  - `Frete Gratis`
  - `Entrega indisponivel para este CEP`
  - `Frete temporariamente indisponivel`
- For non-VTEX supported brands, call the new endpoint.
- Do not show a working freight action for `sfcc`/unsupported; show state text if backend returns unsupported.
- Preserve old history entries with no `shipping_options`.

---

## Test Patterns

| Test File | Analog | Behavior |
|-----------|--------|----------|
| `backend/tests/test_shipping_resolver.py` | `test_engine_detection.py` / factory tests | engine -> provider, VTEX not mapped |
| `backend/tests/test_shopify_shipping.py` | `test_shopify.py` fake response style | product JSON, cart add, rates parse, throttled/null polling |
| `backend/tests/test_wake_shipping.py` | `test_wake_engine.py` fake session/token | quote request shape, parse, 422/unavailable |
| `backend/tests/test_non_vtex_shipping_integration.py` | `test_search_shipping_contract.py` | inline product mutation and no false free shipping |
| `backend/tests/test_non_vtex_shipping_route.py` | route tests | CEP validation, host anchoring, unsupported states |

No live network in pytest. Live network belongs only to `.planning/spikes/011-non-vtex-shipping/`.

