# Phase 42: Frete para Marketplaces & Matriz Multi-Regional - Pattern Map

**Mapped:** 2026-07-01
**Files analyzed:** 11 (3 new providers, 1 new matrix service, 2 new data files, 1 config extension, 1 resolver extension, 1 base.py extension, 1 route extension, 1 frontend extension)
**Analogs found:** 9 / 11 (2 have no direct analog — matrix orchestration and CEP matrix JSON are new ground)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/services/shipping/mercado_livre.py` (NEW) | service (shipping provider) | request-response | `backend/services/shipping/wake.py` | exact (same `BaseShipping` contract) |
| `backend/services/shipping/amazon.py` (NEW) | service (shipping provider) | request-response | `backend/services/shipping/wake.py` | exact (same `BaseShipping` contract) |
| `backend/services/shipping/netshoes.py` (NEW) | service (shipping provider) | request-response | `backend/services/shipping/wake.py` + `backend/services/stock_depth/base.py` (`BLOCKED` state precedent) | exact + role-match for blocked state |
| `backend/services/shipping/base.py` (MODIFIED — add `ShippingState.BLOCKED`) | model/utility | transform | `backend/services/stock_depth/base.py` (`StockDepthState.BLOCKED`) | exact |
| `backend/services/shipping/resolver.py` (MODIFIED — add 3 branches) | service (dispatcher) | request-response | itself (extend existing pattern) | exact |
| `backend/services/shipping/regional_matrix.py` (NEW) | service (orchestrator) | batch | `backend/services/category_monitor_service.py` (JSON local persistence load/save pattern) + `config.py` throttle constants | role-match (no direct batched-multi-CEP analog exists) |
| `backend/data/cep_matrix.json` (NEW) | config (static data) | — | `backend/data/brands.json` (JSON config file pattern) | role-match |
| `backend/data/shipping_matrix_cache.json` (NEW) | model (cache store) | file-I/O | `backend/data/price_monitors.json` / `backend/data/monitored_categories.json` (JSON local-storage pattern) | role-match |
| `backend/config.py` (MODIFIED — add `SHIPPING_MATRIX_*` settings) | config | — | itself (`STOCK_PROBE_THROTTLE_SECONDS`, `MAX_REVIEW_PAGES`, `DEFAULT_CEP` block) | exact |
| `backend/api/routes_search.py` (MODIFIED — extend `/calculate-shipping-brand`, add `/calculate-shipping-matrix`) | route/controller | request-response | itself (`calculate_shipping_brand` handler, lines 684-720) | exact |
| `frontend/src/App.tsx` (MODIFIED — extend `isBrandShippingSupported`, add "Matriz Regional" button + blocked-state rendering) | component | request-response | itself (existing "Calcular Frete" button + shipping-state rendering block, ~L1708-1871, ~L2525) | exact |

## Pattern Assignments

### `backend/services/shipping/mercado_livre.py` / `amazon.py` / `netshoes.py` (service, request-response)

**Analog:** `backend/services/shipping/wake.py`

**Imports pattern** (wake.py lines 1-21):
```python
from __future__ import annotations

import logging
from typing import Any

from core.models import SearchProductResult, ShippingInfo
from services.shipping.base import (
    BaseShipping,
    ShippingCalculation,
    ShippingState,
    get_field,
    is_url_allowed_for_brand,
    normalize_zipcode,
    sorted_shipping_options,
)

logger = logging.getLogger(__name__)
```
For the marketplace providers, import the corresponding engine class **lazily inside `__init__` or `calculate`**, not at module top — mirrors `resolver.py`'s own lazy-import discipline (Pitfall 1 in RESEARCH.md, to avoid `factory.py`'s eager engine imports causing a cycle).

**Core CEP validation + URL guard pattern** (wake.py lines 66-85, identical shape reused verbatim across all 3 new providers):
```python
async def calculate(
    self,
    product: SearchProductResult | dict[str, Any],
    zipcode: str,
    brand: Any,
) -> ShippingCalculation:
    try:
        cep = normalize_zipcode(zipcode)
    except ValueError:
        return ShippingCalculation(
            state=ShippingState.UNAVAILABLE_FOR_CEP,
            message="CEP invalido",
        )

    product_url = str(get_field(product, "url", "") or "")
    if not is_url_allowed_for_brand(product_url, brand):
        return ShippingCalculation(
            state=ShippingState.UNSUPPORTED,
            message="URL do produto nao pertence ao dominio da marca",
        )
```

**Delegation-to-existing-engine pattern (the "thin adapter" — this is the actual new logic per provider):**
```python
# Mercado Livre — delegate to already-proven engine method
# Source: backend/services/engines/mercado_livre_engine.py lines 649-829
from services.engines.mercado_livre_engine import MercadoLivreEngine  # lazy import inside __init__

result = await self.engine.calculate_shipping_advanced(product_url, cep)
# result shape today: {"is_free_shipping": bool, "shipping_price": float|None}
# TODO (D-02): extend _fetch_shipping_options in the engine itself to also return
# estimated_delivery_time before mapping to ShippingInfo.estimated_delivery_days.

# Amazon — delegate similarly
# Source: backend/services/engines/amazon_engine.py lines 521-635 (calculate_shipping_advanced)
result = await self.engine.calculate_shipping_advanced(product_url, cep)
# result may be {"error": "..."} on CAPTCHA (line 553-557) — map that to TEMPORARY_FAILURE,
# NOT to BLOCKED (CAPTCHA is transient per-session, unlike Netshoes' permanent Akamai edge block).

# Netshoes — delegate to Playwright CEP-modal flow
# Source: backend/services/engines/netshoes_engine.py lines 553-635
result = await self.engine.calculate_shipping_advanced(product_url, cep)
# result is None both on Akamai block AND on "no shipping element found" today — the engine
# itself does not distinguish. The provider wrapper must inspect the failure signature
# (documented in .planning/debug/monitor-marketplace-pendente.md: ~343-byte "Access Denied"
# HTML, no __INITIAL_STATE__/JSON-LD) to decide BLOCKED vs TEMPORARY_FAILURE. If the engine
# is not changed to expose this signal, default conservatively to BLOCKED for Netshoes since
# D-01 says "documented, reproducible, infra-only limitation."
```

**Error handling pattern** (wake.py lines 112-122):
```python
except Exception as exc:
    logger.warning(
        "[WakeShipping] quote failed brand=%s status=%s",
        get_field(brand, "brand_key", "unknown"),
        type(exc).__name__,
    )
    return ShippingCalculation(
        state=ShippingState.TEMPORARY_FAILURE,
        message="Frete temporariamente indisponivel",
    )
```
Note: never interpolate CEP into the log message (Phase 41 D-21, reused for this phase per RESEARCH.md Security Domain).

**Success mapping pattern** (wake.py lines 124-133):
```python
if not options:
    return ShippingCalculation(
        state=ShippingState.UNAVAILABLE_FOR_CEP,
        message="Entrega indisponivel para este CEP",
    )

return ShippingCalculation(
    state=ShippingState.AVAILABLE,
    shipping_options=sorted_shipping_options(options),
)
```
Marketplace providers construct a single `ShippingInfo` per result (not multiple SLA options like Wake) — set `price`, `status`, `estimated_delivery_days`, `raw_text`, `is_free_shipping`, then wrap in a one-element list before calling `sorted_shipping_options`.

---

### `backend/services/shipping/base.py` (MODIFIED — add `BLOCKED` state)

**Analog:** `backend/services/stock_depth/base.py` lines 10-16

```python
class StockDepthState:
    ESTIMATED = "estimated"
    AVAILABILITY_ONLY = "availability_only"
    UNAVAILABLE = "unavailable"
    UNSUPPORTED = "unsupported"
    BLOCKED = "blocked"          # <-- exact pattern to replicate in ShippingState
    TEMPORARY_FAILURE = "temporary_failure"
```

Apply to `backend/services/shipping/base.py` lines 11-22:
```python
class ShippingState:
    AVAILABLE = "available"
    UNAVAILABLE_FOR_CEP = "unavailable_for_cep"
    TEMPORARY_FAILURE = "temporary_failure"
    UNSUPPORTED = "unsupported"
    BLOCKED = "blocked"  # NEW

DEFAULT_MESSAGES = {
    ShippingState.UNAVAILABLE_FOR_CEP: "Entrega indisponivel para este CEP",
    ShippingState.TEMPORARY_FAILURE: "Frete temporariamente indisponivel",
    ShippingState.UNSUPPORTED: "Frete nao suportado para este engine",
    ShippingState.BLOCKED: "Bloqueado (anti-bot)",  # exact vocabulary — App.tsx:437
}
```
The `apply_shipping_calculation`/`status_shipping` helpers in `base.py` (lines 95-124) already fall through generically for any non-`AVAILABLE` state via `DEFAULT_MESSAGES.get(state)`, so no other change is needed in `base.py` besides the enum + message entry.

---

### `backend/services/shipping/resolver.py` (MODIFIED)

**Analog:** itself — extend existing `if engine == "..."` chain (lines 9-19)

```python
def resolve_shipping_provider(brand: Any):
    engine = str(get_field(brand, "engine", "") or "").lower()
    if engine == "shopify":
        from services.shipping.shopify import ShopifyShipping
        return ShopifyShipping()
    if engine == "wake":
        from services.shipping.wake import WakeShipping
        return WakeShipping()
    # NEW branches — exact engine strings confirmed in brands.json (no underscore!):
    if engine == "mercadolivre":
        from services.shipping.mercado_livre import MercadoLivreShipping
        return MercadoLivreShipping()
    if engine == "amazon":
        from services.shipping.amazon import AmazonShipping
        return AmazonShipping()
    if engine == "netshoes":
        from services.shipping.netshoes import NetshoesShipping
        return NetshoesShipping()
    return UnsupportedShipping(reason=f"Frete nao suportado para engine '{engine or 'unknown'}'")
```
**Critical pitfall (from RESEARCH.md Pitfall 2):** the `engine` field values are `"mercadolivre"`/`"amazon"`/`"netshoes"` (no underscores), NOT `brand_key` values like `mercado_livre` (underscore). Using the wrong string silently falls through to `UnsupportedShipping`. Verify against `backend/data/brands.json` lines ~567-617 before writing the test.

---

### `backend/services/shipping/regional_matrix.py` (NEW — orchestrator, batch)

**Analog:** No direct analog exists for the batched-multi-CEP-with-cache pattern; compose from:
1. `resolve_shipping_provider` as the single per-call chokepoint (resolver.py, above)
2. JSON local persistence pattern from `backend/services/category_monitor_service.py` / `backend/data/*.json` files (load/save helpers)
3. Throttle constant pattern from `config.py`

**Throttle config pattern** (`backend/config.py` lines 142-145, Phase 44 precedent):
```python
STOCK_PROBE_THROTTLE_SECONDS: float = Field(
    default=2.0,
    description="Throttle fixo entre probes de profundidade de estoque.",
)
```
Add to `config.py` following the exact same block style (near `DEFAULT_CEP`, lines 127-131):
```python
SHIPPING_MATRIX_THROTTLE_SECONDS: float = Field(
    default=2.0,
    description="Throttle fixo entre chamadas de frete da matriz regional (uma por CEP).",
)
SHIPPING_MATRIX_CACHE_TTL_SECONDS: int = Field(
    default=21600,
    description="TTL do cache (produto, CEP) da matriz regional — 6h default, curto por D-09.",
)
```

**TTL cache pattern (new ground — use epoch float, not datetime, per RESEARCH.md Pitfall 5):**
```python
import time

def _read_cache(cache: dict, key: str, ttl_seconds: float) -> dict | None:
    entry = cache.get(key)
    if not entry:
        return None
    if time.time() - entry.get("checked_at", 0) >= ttl_seconds:
        return None
    return entry.get("result")

def _write_cache(cache: dict, key: str, result: dict) -> None:
    cache[key] = {"checked_at": time.time(), "result": result}
```

**Product identity key (per RESEARCH.md Pitfall 6 — do NOT rely on `sku_id`):**
```python
# Use normalized product URL as primary key half; sku_id is VTEX-only and often None
# for marketplace engines. Follow the same URL-as-identity convention already used
# for dedup elsewhere in the app (normalize_url pattern in routes_brands.py/monitor flows).
def _stable_identity(product) -> str:
    return normalize_url(get_field(product, "url", "") or "")
```

**Guard against inline execution (D-10) — architectural, not just a flag:**
```python
# NEVER import this module from cross_marketplace_service.py's _enrich_pdp_and_shipping
# or from category_monitor_service.py's run_category_scan. This must be enforced by a
# regression test (ast-based or import-graph based) per RESEARCH.md Pitfall 4 — mirrors
# the Phase 44 STOCK_PROBE guard-rail precedent (controlled-scan-only invocation).
async def calculate_regional_matrix(product, brand, cep_list, *, triggered_by: str) -> list[dict]:
    if triggered_by != "on_demand_matrix_button":
        raise RuntimeError("Regional matrix guard: only reachable from the on-demand route.")
    provider = resolve_shipping_provider(brand)
    ...
    for i, region_cep in enumerate(cep_list):
        if i > 0:
            await asyncio.sleep(settings.SHIPPING_MATRIX_THROTTLE_SECONDS)
        calculation = await provider.calculate(product, region_cep["cep"], brand)
        ...
```

**Batch error isolation pattern (established, Phase 41/44 convention — one failure must not derail the batch):**
```python
# Mirrors asyncio.gather(*(...)) usage in cross_marketplace_service.py line 522 —
# for the matrix, use sequential loop (throttle requires ordering) but wrap each
# provider.calculate() call in try/except so one region's exception doesn't abort
# the other 4 regions.
```

---

### `backend/data/cep_matrix.json` (NEW — config data)

**Analog:** `backend/data/brands.json` (JSON config file convention — flat list of dicts, editable by operator)

```json
[
  {"region": "Sudeste", "capital": "São Paulo-SP", "cep": "01310100"},
  {"region": "Sul", "capital": "Porto Alegre-RS", "cep": "90010150"},
  {"region": "Centro-Oeste", "capital": "Brasília-DF", "cep": "70040010"},
  {"region": "Nordeste", "capital": "Salvador-BA", "cep": "40020000"},
  {"region": "Norte", "capital": "Manaus-AM", "cep": "69010001"}
]
```
(Exact CEP digits per RESEARCH.md Assumptions Log A2 — MEDIUM confidence, operator-editable per D-08.)

---

### `backend/data/shipping_matrix_cache.json` (NEW — cache store)

**Analog:** `backend/data/price_monitors.json` / `backend/data/monitored_categories.json` — flat JSON dict keyed by a stable identity string, loaded/saved via simple helper functions (not a DB). Follow whatever `_load_local`/`_save_local`-style helper already exists in `category_monitor_service.py` for shape consistency (read-modify-write full file, no partial writes).

---

### `backend/api/routes_search.py` (MODIFIED)

**Analog:** itself — `calculate_shipping_brand` handler, lines 684-720

**Extend existing handler (D-04 — no new logic needed, `engine == "vtex"` check already gates VTEX out, and the resolver dispatch already handles the 3 new engines once resolver.py is extended):**
```python
@router.post(
    "/calculate-shipping-brand",
    response_model=CalculateBrandShippingResponse,
    summary="Calculo de frete nao-VTEX sob demanda",
    description=(
        "Calcula frete para marcas Wake/Shopify/Mercado Livre/Amazon/Netshoes "
        "usando o resolver nao-VTEX. VTEX permanece no endpoint /calculate-shipping-vtex."
    ),
)
async def calculate_shipping_brand(request: CalculateBrandShippingRequest):
    # ... unchanged body — resolver.py extension is the only change needed here ...
```

**New endpoint — request/response model pattern to copy** (from `CalculateBrandShippingRequest`/`CalculateBrandShippingResponse`, lines 113-127):
```python
class CalculateShippingMatrixRequest(BaseModel):
    """Matriz de frete multi-regional sob demanda para um produto (FRET-09)."""

    brand_key: str = Field(..., min_length=1, description="Chave da marca.")
    product_url: str = Field(..., min_length=1, description="URL do produto na marca.")


class ShippingMatrixRegionResult(BaseModel):
    region: str
    capital: str
    cep: str
    state: str
    shipping: Optional[ShippingInfo] = None
    message: Optional[str] = None
    cached: bool = False


class CalculateShippingMatrixResponse(BaseModel):
    regions: List[ShippingMatrixRegionResult] = Field(default_factory=list)


@router.post(
    "/calculate-shipping-matrix",
    response_model=CalculateShippingMatrixResponse,
    summary="Matriz de frete multi-regional sob demanda (FRET-09)",
    description=(
        "Calcula frete/prazo para um produto nos 5 CEPs curados (uma capital por regiao). "
        "On-demand/batched apenas — nunca chamado durante varredura/busca ao vivo (D-10)."
    ),
)
async def calculate_shipping_matrix(request: CalculateShippingMatrixRequest):
    brand_key = request.brand_key.lower()
    brand = brand_service.get_brand(brand_key)
    if not brand:
        raise HTTPException(status_code=404, detail=f"Marca '{brand_key}' nao encontrada.")
    if not is_url_allowed_for_brand(request.product_url, brand):
        raise HTTPException(status_code=400, detail="URL do produto nao pertence ao dominio da marca.")

    product = SearchProductResult(brand=brand_key, product_name="Produto", url=request.product_url, price_full=None)
    results = await calculate_regional_matrix(product, brand, cep_matrix, triggered_by="on_demand_matrix_button")
    return CalculateShippingMatrixResponse(regions=results)
```
Same `X-API-Key`/`INTERNAL_API_KEY` middleware coverage applies automatically since it's under `/search/*` (per RESEARCH.md Security Domain V4 — no new bypass to introduce).

---

### `frontend/src/App.tsx` (MODIFIED)

**Analog:** itself — `isBrandShippingSupported` gate (line 1708) + shipping-state rendering block (~L1800-1871) + existing "Calcular Frete" button (~L1777, ~L2525)

**Extend the engine-support gate** (line 1708):
```typescript
const isBrandShippingSupported = ['shopify', 'wake', 'mercadolivre', 'amazon', 'netshoes'].includes(brand?.engine);
```

**Add explicit `blocked` branch to shipping-state rendering** (insert alongside the existing `isFailure`/`isUnavailable` branch at lines 1842-1871), reusing the exact vocabulary from the monitor panel (line 437):
```typescript
const isBlocked = p._shipping_state === 'blocked';
if (isBlocked) {
  return (
    <div className="shipping-section">
      <div className="shipping-state-row shipping-state-blocked">
        <AlertTriangle size={13} aria-hidden="true" />
        <span>Bloqueado (anti-bot)</span>
      </div>
    </div>
  );
}
```
Per D-07, this branch must NOT hide the "Calcular Frete"/"Matriz Regional" action — only render the state text; the button stays visible per the `isBrandShippingSupported` check already guarding button visibility (lines 1765, 1855).

**"Matriz Regional" button placement** — add next to the existing "Calcular Frete" button at both insertion points (D-06):
```typescript
// Mirrors the existing "Calcular Frete" button shape at ~L1777:
<button
  type="button"
  className="shipping-matrix-trigger"
  onClick={(e) => {
    e.preventDefault();
    e.stopPropagation();
    requestMatrix({ brandKey, product: p });  // new handler, sibling to requestCalc
  }}
>
  <Truck size={14} aria-hidden="true" /> Matriz Regional
</button>
```
Per D-07, this button renders unconditionally for any `isBrandShippingSupported` engine (including Netshoes) — never hidden to avoid an expected `blocked` result in all 5 regions.

## Shared Patterns

### `BaseShipping` contract (single source of truth for all providers)
**Source:** `backend/services/shipping/base.py`
**Apply to:** All 3 new marketplace shipping provider files
```python
class BaseShipping(ABC):
    @abstractmethod
    async def calculate(self, product, zipcode, brand) -> ShippingCalculation:
        """Calculate shipping for a product and destination CEP."""
```

### CEP validation + brand-domain SSRF guard
**Source:** `backend/services/shipping/base.py` lines 53-78 (`normalize_zipcode`, `is_url_allowed_for_brand`)
**Apply to:** All 3 new providers and the matrix service (reuse verbatim, never reimplement — RESEARCH.md Security Domain flags this as the SSRF mitigation)
```python
def normalize_zipcode(zipcode: str) -> str:
    digits = "".join(ch for ch in str(zipcode or "") if ch.isdigit())
    if len(digits) != 8:
        raise ValueError("CEP must contain 8 digits")
    return digits

def is_url_allowed_for_brand(url: str, brand: Any) -> bool:
    expected = brand_domain(brand).lower()
    ...
    return host == expected or host.endswith("." + expected)
```

### Explicit state enum, never a false zero/free result
**Source:** `backend/services/shipping/base.py` (`ShippingState`), `backend/services/stock_depth/base.py` (`StockDepthState.BLOCKED` precedent)
**Apply to:** All 3 new providers — `0.0` = confirmed free; `None`/dedicated state (`temporary_failure`/`unsupported`/`blocked`) = not calculated. Never conflate.

### Config throttle/limit constant naming
**Source:** `backend/config.py` lines 133-149 (Phase 44 `STOCK_PROBE_*` block)
**Apply to:** New `SHIPPING_MATRIX_THROTTLE_SECONDS`/`SHIPPING_MATRIX_CACHE_TTL_SECONDS` settings — same `Field(default=..., description="...")` style, grouped under a `# Phase 42 - ...` comment header matching the `# Phase 44 - ...` precedent.

### JSON local persistence (load full file / mutate / save full file)
**Source:** `backend/data/*.json` pattern used by `price_monitors.json`, `monitored_categories.json`, `search_history.json`
**Apply to:** `cep_matrix.json` (static, operator-editable) and `shipping_matrix_cache.json` (mutable cache with TTL) — no SQLite (Phase 37 not delivered, confirmed in RESEARCH.md).

### No CEP/PII in info/error logs
**Source:** Phase 41 D-21 precedent, reused by `wake.py`'s logging style (line 114-118 — logs `brand_key`/`type(exc).__name__`, never the CEP or payload)
**Apply to:** All 3 new providers and `regional_matrix.py` — log region label (e.g. "Sudeste") instead of raw CEP where possible.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `backend/services/shipping/regional_matrix.py` | service (orchestrator) | batch | No existing multi-call-with-throttle-and-cache batching service exists for shipping; composed from 3 separate precedents (resolver chokepoint, JSON persistence, throttle config) rather than one direct analog — see Pattern Assignments above |
| `backend/data/shipping_matrix_cache.json` (TTL semantics specifically) | model (cache) | file-I/O | No existing JSON-file-backed cache with TTL comparison exists in this codebase (VTEX's `VTEX_CACHE_TTL_SECONDS` is in-memory only, not file-backed) — genuinely new ground per RESEARCH.md Pitfall 5; use `time.time()` epoch floats to avoid timezone bugs |

## Metadata

**Analog search scope:** `backend/services/shipping/`, `backend/services/engines/`, `backend/services/stock_depth/`, `backend/services/cross_marketplace_service.py`, `backend/api/routes_search.py`, `backend/config.py`, `backend/data/*.json`, `frontend/src/App.tsx`
**Files scanned:** 12 (base.py, resolver.py, wake.py, unsupported.py, stock_depth/base.py, mercado_livre_engine.py, amazon_engine.py, netshoes_engine.py, cross_marketplace_service.py, routes_search.py, config.py, App.tsx)
**Pattern extraction date:** 2026-07-01
