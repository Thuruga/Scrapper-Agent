# Phase 44: Ruptura de Estoque & Avaliações Reforçadas - Pattern Map

**Mapped:** 2026-06-29  
**Files analyzed:** 14  
**Analogs found:** 14 / 14

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/core/models.py` | model | request-response | `backend/core/models.py` | exact |
| `backend/config.py` | config | request-response | `backend/config.py` | exact |
| `backend/services/stock_summary_service.py` | service | transform | `backend/services/shipping/base.py` | role-match |
| `backend/services/stock_depth_service.py` | service | request-response | `backend/services/shipping/base.py` | role-match |
| `backend/services/stock_depth/base.py` | service | request-response | `backend/services/shipping/base.py` | exact |
| `backend/services/stock_depth/vtex.py` | service | request-response | `backend/services/vtex_shipping.py` + `backend/core/browser_manager.py` | role-match |
| `backend/services/stock_depth/resolver.py` | service | request-response | `backend/services/shipping/resolver.py` | exact |
| `backend/services/review_service.py` | service | request-response | `backend/services/review_service.py` | exact |
| `backend/services/category_monitor_service.py` | service | file-I/O | `backend/services/category_monitor_service.py` | exact |
| `backend/api/routes_monitor.py` | route | request-response | `backend/api/routes_monitor.py` | exact |
| `backend/api/routes_category.py` | route | request-response | `backend/api/routes_category.py` | exact |
| `frontend/src/api/client.ts` | utility | request-response | `frontend/src/api/client.ts` | exact |
| `frontend/src/App.tsx` | component | event-driven | `frontend/src/App.tsx` | exact |
| `backend/tests/test_stock_summary_service.py`, `test_stock_depth_service.py`, `test_review_comments_service.py`, `test_phase44_routes.py` | test | transform/request-response | `backend/tests/test_vtex_shipping.py`, `backend/tests/test_shipping_resolver.py` | role-match |

## Pattern Assignments

### `backend/core/models.py` (model, request-response)

**Analog:** `backend/core/models.py`

**Imports pattern** (lines 8-10):
```python
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Dict, List, Any
```

**Additive optional fields pattern** (lines 59-69, 136-163):
```python
stock_availability: Optional[bool] = None
rating: Optional[float] = None
review_count: Optional[int] = None
shipping: ShippingInfo | None = None

sku_id: Optional[str] = Field(
    default=None,
    description="itemId do SKU selecionado ...",
)
shipping_options: List[ShippingInfo] = Field(default_factory=list)
```

**Validation/computed field pattern** (lines 75-88, 90-102):
```python
@model_validator(mode="after")
def calculate_landed_price(self):
    if self.landed_price is None:
        base_price = self.price_discount if self.price_discount is not None else self.price_full
        if base_price is not None:
            self.landed_price = base_price + self.shipping_price if self.shipping_price is not None else base_price
    return self

@field_validator("image_url")
@classmethod
def image_url_must_be_present(cls, v: Optional[str]) -> str:
    if not v or not v.strip() or v == "None":
        raise ValueError("URL da imagem ausente ou inválida")
    return v
```

**Apply to Phase 44:** add compact `ReviewComment` / stock-depth fields with safe defaults. Keep `None` meaningful for unknown stock and do not replace existing `rating` / `review_count`.

---

### `backend/config.py` (config, request-response)

**Analog:** `backend/config.py`

**Settings pattern** (lines 40-51, 53-61, 100-124):
```python
class Settings(BaseSettings):
    APP_HOST: Literal["127.0.0.1", "localhost", "::1"] = "127.0.0.1"
    APP_PORT: int = 8000

    VTEX_CACHE_TTL_SECONDS: int = Field(
        default=3600,
        description="Tempo de vida do cache de categorias em segundos (default: 1h).",
    )
    SCRAPER_DELAY_SECONDS: float = Field(default=2.0)
    REQUEST_TIMEOUT_SECONDS: int = Field(default=20)
```

**Singleton pattern** (lines 133-137, 352-354):
```python
model_config = {
    "env_file": BASE_DIR / ".env",
    "env_file_encoding": "utf-8",
    "extra": "ignore",
}

settings = Settings()
relevance_settings = RelevanceSettings()
```

**Apply to Phase 44:** add conservative defaults such as `MAX_REVIEW_PAGES`, `STOCK_PROBE_THROTTLE_SECONDS`, `STOCK_PROBE_TIMEOUT_SECONDS`, and per-brand/run caps on `Settings`.

---

### `backend/services/stock_summary_service.py` (service, transform)

**Analog:** `backend/services/shipping/base.py`

**State/value separation pattern** (lines 11-22, 25-39):
```python
class ShippingState:
    AVAILABLE = "available"
    UNAVAILABLE_FOR_CEP = "unavailable_for_cep"
    TEMPORARY_FAILURE = "temporary_failure"
    UNSUPPORTED = "unsupported"

@dataclass
class ShippingCalculation:
    state: str
    shipping_options: list[ShippingInfo] = field(default_factory=list)
    message: str | None = None
    raw: dict[str, Any] | None = None
```

**Pure transform pattern** (lines 81-124):
```python
def sorted_shipping_options(options: list[ShippingInfo]) -> list[ShippingInfo]:
    return sorted(options, key=_option_sort_key)

def apply_shipping_calculation(product: SearchProductResult, calculation: ShippingCalculation) -> SearchProductResult:
    options = sorted_shipping_options(calculation.shipping_options)
    product.shipping_options = options
    if calculation.state == ShippingState.AVAILABLE and options:
        product.shipping = options[0]
    else:
        product.shipping = status_shipping(calculation.state, calculation.message)
        product.shipping_price = None
    return product
```

**Apply to Phase 44:** implement pure rupture math over `stock_availability is True/False/None`; return a serializable summary object. `rupture_pct` must be `None` when `verified_stock_count == 0`.

---

### `backend/services/stock_depth/base.py` and `stock_depth_service.py` (service, request-response)

**Analog:** `backend/services/shipping/base.py`

**Provider interface pattern** (lines 42-50):
```python
class BaseShipping(ABC):
    @abstractmethod
    async def calculate(
        self,
        product: SearchProductResult | dict[str, Any],
        zipcode: str,
        brand: Any,
    ) -> ShippingCalculation:
        """Calculate shipping for a product and destination CEP."""
```

**Server-side domain validation pattern** (lines 66-78):
```python
def brand_domain(brand: Any) -> str:
    return str(get_field(brand, "domain", "") or "").replace("https://", "").replace("http://", "").strip("/")

def is_url_allowed_for_brand(url: str, brand: Any) -> bool:
    expected = brand_domain(brand).lower()
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    return host == expected or host.endswith("." + expected)
```

**Apply to Phase 44:** define `StockDepthState` values `estimated`, `unavailable`, `unsupported`, `blocked`, `temporary_failure`; never turn timeout/block/unsupported into estimate `0`.

---

### `backend/services/stock_depth/resolver.py` (service, request-response)

**Analog:** `backend/services/shipping/resolver.py`

**Resolver pattern** (lines 9-19):
```python
def resolve_shipping_provider(brand: Any):
    engine = str(get_field(brand, "engine", "") or "").lower()
    if engine == "shopify":
        from services.shipping.shopify import ShopifyShipping
        return ShopifyShipping()
    if engine == "wake":
        from services.shipping.wake import WakeShipping
        return WakeShipping()
    return UnsupportedShipping(reason=f"Frete nao suportado para engine '{engine or 'unknown'}'")
```

**Apply to Phase 44:** create a resolver that returns VTEX stock-depth first if scoped, and an explicit unsupported provider for all engines without proved cart-probe support.

---

### `backend/services/stock_depth/vtex.py` (service, request-response)

**Analog:** `backend/core/browser_manager.py`

**Ephemeral browser/context cleanup pattern** (lines 125-148, 157-185):
```python
with sync_playwright() as p:
    browser = p.chromium.launch(**launch_kwargs)
    context = browser.new_context(
        user_agent="Mozilla/5.0 ...",
        viewport={"width": 1366, "height": 768},
        locale="pt-BR",
        timezone_id="America/Sao_Paulo",
    )
    page = context.new_page()
    try:
        page.goto(url, wait_until=wait_until, timeout=timeout)
        return page.content()
    finally:
        page.close()
        context.close()
        browser.close()
```

**Async wrapper pattern** (lines 187-189):
```python
return await asyncio.to_thread(_sync_fetch)
```

**Apply to Phase 44:** use isolated context/page per probe with `finally` cleanup, fixed timeout, throttle, and no automatic loop over products.

---

### `backend/services/review_service.py` (service, request-response)

**Analog:** `backend/services/review_service.py`

**Async provider fetch pattern** (lines 34-70):
```python
async def _fetch_trustvox_single(session: aiohttp.ClientSession, store_id: str, product_id: str):
    url = "https://trustvox.com.br/widget/root"
    params = {"store_id": store_id, "code": product_id}
    headers = {"Accept": "application/vnd.trustvox-v2+json", "User-Agent": _USER_AGENT}
    try:
        async with session.get(url, params=params, headers=headers) as resp:
            if resp.status != 200:
                logger.debug(f"[Trustvox] HTTP {resp.status} para product {product_id}")
                return product_id, (None, None)
            data = await resp.json(content_type=None)
            rate_info = data.get("rate", {})
            return product_id, (round(float(rate_info.get("average")), 1), int(rate_info.get("count", 0)))
    except Exception as e:
        logger.debug(f"[Trustvox] Erro para product {product_id}: {e}")
    return product_id, (None, None)
```

**Bulk gather pattern** (lines 73-94, 135-156):
```python
async with aiohttp.ClientSession(timeout=_REVIEW_TIMEOUT) as session:
    tasks = [_fetch_trustvox_single(session, store_id, pid) for pid in product_ids]
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    for res in responses:
        if isinstance(res, tuple) and len(res) == 2:
            pid, rating_data = res
            results[pid] = rating_data
```

**Provider router pattern** (lines 182-200):
```python
brand_config = brand_service.get_brand(brand_key)
if not brand_config:
    return {}

provider = brand_config.review_provider
if provider == "trustvox":
    ...
elif provider == "vtex_native":
    ...
return {}
```

**Apply to Phase 44:** extend with on-demand comments, page cap, compact normalized schema, dedup by provider id or stable hash, and `reviews_state="unsupported"` for `none`/unknown.

---

### `backend/services/category_monitor_service.py` (service, file-I/O)

**Analog:** `backend/services/category_monitor_service.py`

**Local JSON persistence pattern** (lines 15-30):
```python
def _load_local() -> list[dict]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not MONITORS_FILE.exists():
        return []
    try:
        return json.loads(MONITORS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

def _save_local(data: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MONITORS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
```

**Scan and persist pattern** (lines 37-70):
```python
async def run_category_scan(monitor: dict) -> None:
    engine = engine_factory.get_engine(brand)
    scraped_products = []
    try:
        async for product in engine.run_bulk_scrape(category_url=url):
            scraped_products.append(product)
            if len(scraped_products) >= 1000:
                break
    except Exception as exc:
        logger.error("Erro ao extrair %s: %s", url, exc)

    products_file = DATA_DIR / f"monitored_products_{monitor_id}.json"
    products_file.write_text(json.dumps(scraped_products, indent=2, ensure_ascii=False), encoding="utf-8")
```

**Apply to Phase 44:** compute and persist stock summary after scan, preferably beside or inside the monitor artifact until Phase 37 SQLite state is verified.

---

### `backend/api/routes_monitor.py` (route, request-response)

**Analog:** `backend/api/routes_monitor.py`

**Route model and background task pattern** (lines 17-28, 48-65):
```python
class CategoryMonitorCreate(BaseModel):
    url: str
    brand: str

class CategoryMonitorResponse(BaseModel):
    id: str
    url: str
    brand: str
    status: str
    last_scraped_at: Optional[str] = None

@router.post("/category", response_model=CategoryMonitorResponse)
async def create_category_monitor(data: CategoryMonitorCreate, background_tasks: BackgroundTasks):
    row = {"id": str(uuid.uuid4()), "url": data.url, "brand": data.brand, "status": "active"}
    _save_local(_load_local() + [row])
    background_tasks.add_task(run_category_scan, row)
    return CategoryMonitorResponse(**row)
```

**Existing product artifact read pattern** (lines 81-89):
```python
@router.get("/category/{monitor_id}/products")
async def get_monitored_products(monitor_id: str):
    products_file = DATA_DIR / f"monitored_products_{monitor_id}.json"
    if not products_file.exists():
        return []
    try:
        return json.loads(products_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
```

**Apply to Phase 44:** add explicit stock-depth and review-comments endpoints here if they mutate/read a persisted monitored scan product.

---

### `backend/api/routes_category.py` (route, request-response)

**Analog:** `backend/api/routes_category.py`

**Pydantic request and URL resolution pattern** (lines 50-68):
```python
class ScrapeCategoryRequest(BaseModel):
    brand: str
    category_path: Optional[str] = None
    custom_url: Optional[str] = None

    def resolved_url(self) -> str:
        if self.custom_url:
            return clean_url(self.custom_url)
        mapping = resolve_category_for_brands(self.category_path, [self.brand])
        return mapping[self.brand.lower()]["url"]
```

**Manual scan background job pattern** (lines 111-135):
```python
@router.post("/scrape-category")
async def scrape_category(request: ScrapeCategoryRequest, background_tasks: BackgroundTasks):
    url = request.resolved_url()
    if not url:
        raise HTTPException(status_code=400, detail="Forneça category_path ou custom_url.")
    job_id = str(uuid.uuid4())
    cancel_event = asyncio.Event()
    JOB_CANCEL_FLAGS[job_id] = cancel_event
    background_tasks.add_task(task_wrapper)
```

**Multi-brand validation pattern** (lines 175-182, 214-235):
```python
all_brands = {b.brand_key: b for b in brand_service.list_brands(active_only=True)}
invalid_brands = [b for b in request.brands if b.lower() not in all_brands]
if invalid_brands:
    raise HTTPException(status_code=400, detail=f"Marcas não suportadas: {invalid_brands}")

return {"job_id": job_id, "message": "...", "brands": list(url_map.keys()), "urls": url_map}
```

**Apply to Phase 44:** surface rupture summaries in manual scan responses/job artifacts without running cart-probe or full comments inline.

---

### `frontend/src/api/client.ts` (utility, request-response)

**Analog:** `frontend/src/api/client.ts`

**Authenticated request pattern** (lines 12-37):
```typescript
public static async request<T>(endpoint: string, options: RequestInit = {}, signal?: AbortSignal): Promise<T> {
  const headers: any = {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
    ...options.headers,
  };
  const response = await fetch(`${API_BASE_URL}${endpoint}`, { ...options, headers, ...(signal ? { signal } : {}) });
  const data = await response.json();
  if (!response.ok) throw new Error(data?.detail || `API Error: ${response.status}`);
  return data as T;
}
```

**On-demand action method pattern** (lines 83-97):
```typescript
static calculateVtexShipping(payload: { brand_key: string; sku_id: string; seller_id?: string; zipcode: string }) {
  return this.request<{ state: string; shipping_options: any[] }>('/search/calculate-shipping-vtex', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
```

**Apply to Phase 44:** add typed methods for explicit stock-depth probe and review-comments fetch; do not add calls to normal `search()`.

---

### `frontend/src/App.tsx` (component, event-driven)

**Analog:** `frontend/src/App.tsx`

**Async action state pattern** (lines 2484-2495):
```tsx
const handleViewProducts = async (monitor: any) => {
  setSelectedMonitor(monitor);
  setLoadingProducts(true);
  try {
    const prods = await ApiClient.getMonitoredCategoryProducts(monitor.id);
    setMonitorProducts(prods);
  } catch (err: any) {
    alert("Erro ao buscar produtos: " + err.message);
    setMonitorProducts([]);
  } finally {
    setLoadingProducts(false);
  }
};
```

**Icon button action pattern** (lines 2557-2565):
```tsx
<div style={{ display: 'flex', gap: '8px' }}>
  <button className="btn btn-icon btn-outline" onClick={() => handleViewProducts(c)} title="Ver Produtos">
    <Eye size={16} />
  </button>
  <button className="btn btn-icon btn-outline text-error" onClick={() => handleDelete(c.id)} title="Excluir Monitor">
    <Trash2 size={16} />
  </button>
</div>
```

**Product modal pattern** (lines 2647-2705):
```tsx
{selectedMonitor && (
  <div className="modal-overlay" onClick={() => setSelectedMonitor(null)}>
    <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '1200px', width: '95%' }}>
      {monitorProducts.map((p, i) => (
        <a key={i} href={p.url} className="product-card">
          <div className="product-details">
            <p className="product-name" title={p.raw_title}>{p.raw_title || 'Produto sem título'}</p>
          </div>
        </a>
      ))}
    </div>
  </div>
)}
```

**Apply to Phase 44:** only add minimal controls/status if planned: stock-depth button per persisted product and review comments button; keep UI secondary to backend source of truth.

---

### Phase 44 tests (test, transform/request-response)

**Analogs:** `backend/tests/test_vtex_shipping.py`, `backend/tests/test_shipping_resolver.py`

**Pure unit test style** (`backend/tests/test_vtex_shipping.py` lines 1-20):
```python
"""
Testes unitarios puros para o modulo vtex_shipping.
"""
import pytest

from services.vtex_shipping import (
    classify_result,
    filter_and_sort_slas,
    parse_estimate,
    select_candidate,
)
```

**State distinction assertions** (`backend/tests/test_vtex_shipping.py` lines 223-230):
```python
def test_price_zero_is_free_not_none(self):
    slas = [self._sla("Gratis", 0, "3bd")]
    result = filter_and_sort_slas(slas)
    assert result[0]["price_reais"] == 0.0
    assert result[0]["price_reais"] is not None
```

**Resolver test pattern** (`backend/tests/test_shipping_resolver.py` lines 4-31):
```python
def _brand(engine: str) -> DynamicBrand:
    return DynamicBrand(brand_key=f"{engine}_brand", brand_name=f"{engine} Brand", domain=f"{engine}.example.com", engine=engine)

def test_resolver_returns_unsupported_for_sfcc_unknown_and_vtex():
    from services.shipping.resolver import resolve_shipping_provider
    from services.shipping.unsupported import UnsupportedShipping
    for engine in ("sfcc", "unknown", "vtex"):
        assert isinstance(resolve_shipping_provider(_brand(engine)), UnsupportedShipping)
```

**Apply to Phase 44:** add hermetic tests for `True`/`False`/`None` rupture math, explicit unsupported provider states, dedup, page caps, throttling, and cleanup with fakes.

## Shared Patterns

### API Authentication

**Source:** `backend/api/__init__.py`  
**Apply to:** all new backend routes

```python
from api.auth import verify_api_key, verify_ws_api_key

# Todos os endpoints da API exigem X-API-Key
api_router = APIRouter(dependencies=[Depends(verify_api_key)])

api_router.include_router(product_router)
api_router.include_router(category_router)
api_router.include_router(search_router)
api_router.include_router(monitor_router)
```

### Error Handling

**Source:** `backend/api/routes_search.py` and `backend/services/review_service.py`  
**Apply to:** routes and provider calls

```python
try:
    result = await VtexApiClient.calculate_for_brand(...)
except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
```

```python
try:
    async with session.get(url, params=params, headers=headers) as resp:
        if resp.status != 200:
            logger.debug(f"[Trustvox] HTTP {resp.status} para product {product_id}")
            return product_id, (None, None)
except Exception as e:
    logger.debug(f"[Trustvox] Erro para product {product_id}: {e}")
return product_id, (None, None)
```

### Explicit Non-False States

**Source:** `backend/services/shipping/base.py`  
**Apply to:** stock depth, reviews, rupture summaries

```python
class ShippingState:
    AVAILABLE = "available"
    UNAVAILABLE_FOR_CEP = "unavailable_for_cep"
    TEMPORARY_FAILURE = "temporary_failure"
    UNSUPPORTED = "unsupported"
```

Use the same shape for `StockDepthState` and `reviews_state`; failure, blocked, timeout, unsupported, and unknown must not be represented as numeric zero or empty success.

### Brand/Domain Guard

**Source:** `backend/services/shipping/base.py`, `backend/api/routes_search.py`  
**Apply to:** stock-depth endpoints

```python
if not is_url_allowed_for_brand(request.product_url, brand):
    raise HTTPException(status_code=400, detail="URL do produto nao pertence ao dominio da marca.")
```

### Local Persistence

**Source:** `backend/services/category_monitor_service.py`, `backend/api/routes_monitor.py`  
**Apply to:** scan summaries and product-level stock-depth/review state until SQLite is verified

```python
products_file = DATA_DIR / f"monitored_products_{monitor_id}.json"
products_file.write_text(json.dumps(scraped_products, indent=2, ensure_ascii=False), encoding="utf-8")
```

### Browser Cleanup

**Source:** `backend/core/browser_manager.py`  
**Apply to:** Playwright cart-probe

```python
try:
    page.goto(url, wait_until=wait_until, timeout=timeout)
    return page.content()
finally:
    page.close()
    context.close()
    browser.close()
```

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| None | - | - | Every expected file has at least a role-match analog. The stock-depth provider is new domain logic, but should copy shipping provider/resolver and BrowserManager lifecycle patterns. |

## Metadata

**Analog search scope:** `backend/core`, `backend/services`, `backend/services/shipping`, `backend/api`, `backend/tests`, `frontend/src`  
**Files scanned:** 80+ via `rg --files` and targeted `rg`  
**Pattern extraction date:** 2026-06-29
