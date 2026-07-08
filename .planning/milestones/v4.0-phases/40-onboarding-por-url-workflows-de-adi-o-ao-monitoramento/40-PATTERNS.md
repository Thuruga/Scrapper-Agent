# Phase 40: Onboarding por URL & Workflows de Adição ao Monitoramento - Pattern Map

**Mapped:** 2026-06-29
**Files analyzed:** 10 new/modified files
**Analogs found:** 10 / 10

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/api/routes_brands.py` (POST /brands/identify) | route handler | request-response | `routes_brands.py::create_brand` (l.103-125) | exact |
| `backend/services/url_utils.py` (NEW) | utility | transform | `zara_parser.py` (stdlib urllib.parse imports) | role-match |
| `backend/api/routes_brands.py` (detect_engine refactor) | utility function | request-response | `routes_brands.py::detect_engine` (l.14-100) | exact |
| `backend/api/routes_brands.py` (remove runtime injection l.133-160) | route handler | request-response | `routes_brands.py::list_brands` (l.128-162) | exact |
| `backend/services/price_monitor_service.py` (dedup in start_monitor) | service | CRUD | `price_monitor_service.py::start_monitor` (l.51-66) | exact |
| `backend/services/cross_marketplace_service.py` (_active_engines) | service | request-response | `cross_marketplace_service.py::__init__` (l.152-158) | exact |
| `backend/data/brands.json` (add marketplace entries) | config | — | existing brand entries (l.1-46) | exact |
| `frontend/src/api/client.ts` (identifyBrand, addToMonitor) | api client | request-response | `client.ts::setBrandActive`, `startMonitor` (l.59-64, l.261-265) | exact |
| `frontend/src/App.tsx` (onboarding form + "Adicionar" button) | component | event-driven | `App.tsx` shipping button pattern (l.1524-1531 per RESEARCH) | role-match |
| `backend/tests/test_brand_identify.py`, `test_url_utils.py`, extensions | test | — | `tests/test_price_monitor.py` (l.1-100) | exact |

---

## Pattern Assignments

### `backend/api/routes_brands.py` — NEW `POST /brands/identify`

**Analog:** `routes_brands.py::create_brand` (l.103-125) and `routes_brands.py::detect_engine` (l.14-100)

**Imports pattern** (l.1-9 of routes_brands.py):
```python
from fastapi import APIRouter, HTTPException
from typing import List
import logging
import aiohttp
from core.models import DynamicBrand, DynamicBrandCreate, CategoryMapping, BrandActiveUpdate
from services.brand_service import brand_service
from services.engines.factory import engine_factory
from core.session_manager import SessionManager
```
Add to imports: `from pydantic import BaseModel` and `from urllib.parse import urlparse`.
New Pydantic models go at module level, before the router handlers, following existing `DynamicBrandCreate` pattern.

**Endpoint structure pattern** (l.103-125):
```python
@router.post("/brands/", response_model=DynamicBrand)
async def create_brand(brand_data: DynamicBrandCreate):
    """Cadastra ou atualiza uma nova marca no sistema."""
    try:
        if brand_data.engine == "auto":
            brand_data.engine = await detect_engine(brand_data.domain)
        saved = brand_service.add_brand(brand_data)
        if saved.engine == "unknown":
            logger.info(...)
            saved = brand_service.set_active(saved.brand_key, False)
        return saved
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```
New `POST /brands/identify` follows the same try/except → HTTPException 400 shape, but calls `detect_engine` and `infer_brand_name` without calling `brand_service.add_brand`.

**detect_engine refactor — tuple return** (current l.14, 100):

Current signature: `async def detect_engine(domain: str) -> str:`
New signature: `async def detect_engine(domain: str) -> tuple[str, str | None]:`

Each early `return "shopify"` (l.28) becomes `return "shopify", None`.
Step 3 html fetch (l.44-72): capture `html = await resp.text()` (already done at l.45), change each `return "wake"` etc. to `return "wake", html`. At the final `return "unknown"` (l.100) change to `return "unknown", None`.
Existing caller `create_brand` at l.109: change `brand_data.engine = await detect_engine(...)` to `brand_data.engine, _ = await detect_engine(...)`.

**Error handling pattern** (l.103-125):
```python
try:
    ...
except Exception as e:
    raise HTTPException(status_code=400, detail=str(e))
```
For `/brands/identify`, wrap the `detect_engine` call in this same structure; domain parse errors raise 400.

---

### `backend/services/url_utils.py` — NEW utility

**Analog:** `zara_parser.py` (stdlib urllib.parse import at l.17), `zara_parser.py::parse_products` dedup pattern (l.279-299)

**Imports pattern** (zara_parser.py l.11-18):
```python
from __future__ import annotations
import json
import re
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup
```
For url_utils.py, use only stdlib:
```python
from __future__ import annotations
from urllib.parse import urlparse, urlencode, parse_qsl, urlunparse
```

**Core pattern** — normalize_url (RESEARCH Pattern 3):
```python
_TRACKING_PARAMS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_id", "gclid", "fbclid", "msclkid", "dclid",
})

def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    scheme = "https"
    host = parsed.netloc.lower().lstrip("www.")
    if not host:
        return url
    path = parsed.path.rstrip("/") or "/"
    filtered_qs = [
        (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k.lower() not in _TRACKING_PARAMS
        and not k.lower().startswith("utm_")
    ]
    query = urlencode(filtered_qs)
    return urlunparse((scheme, host, path, "", query, ""))
```

No class needed — module-level function only, matching project pattern of small pure utilities.

---

### `backend/api/routes_brands.py` — `infer_brand_name` helper

**Analog:** `zara_parser.py::_jsonld_blocks` (l.102-107) and `zara_parser.py::parse_product_detail` OG fallback (l.267-270)

**JSON-LD iteration pattern** (zara_parser.py l.102-107):
```python
def _jsonld_blocks(soup: BeautifulSoup) -> Iterable[Any]:
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            yield json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
```

**OG meta pattern** (zara_parser.py l.267-270):
```python
og_title = soup.find("meta", property="og:title")
og_image = soup.find("meta", property="og:image")
```
For brand name: `soup.find("meta", property="og:site_name")`, then `.get("content", "").strip()`.

**Domain fallback pattern** — import `re` (already used in zara_parser.py l.5):
```python
import re
host = domain.lower().replace("www.", "").split(".")[0]
name = re.sub(r"([a-z])([A-Z])", r"\1 \2", host)
return " ".join(w.capitalize() for w in name.replace("-", " ").replace("_", " ").split())
```

Place `infer_brand_name` in `routes_brands.py` as a module-level function (next to `detect_engine`). Add imports `import json as _json`, `import re`, `from bs4 import BeautifulSoup` at the top of `routes_brands.py`.

---

### `backend/api/routes_brands.py` — MODIFY `list_brands` (remove runtime injection)

**Analog:** `routes_brands.py::list_brands` (l.128-162) — the block to remove is l.133-160.

**Pattern before** (l.128-162): function returns `brand_service.list_brands()` then appends 3 hardcoded `DynamicBrand(...)` objects.

**Pattern after**: remove the `brands.append(...)` block entirely. Function body becomes:
```python
@router.get("/brands/", response_model=List[DynamicBrand])
async def list_brands():
    """Lista todas as marcas cadastradas."""
    return brand_service.list_brands()
```
No other changes to `list_brands`. The marketplaces will appear via `brands.json` entries.

---

### `backend/services/price_monitor_service.py` — MODIFY `start_monitor` (dedup)

**Analog:** `price_monitor_service.py::start_monitor` (l.51-66), `delete_monitors_by_brand` (l.86-89) for iteration pattern

**Existing iteration pattern** (l.86-89):
```python
to_delete = [job_id for job_id, config in self.monitors.items() if config.brand.lower() == brand_key.lower()]
```

**Existing resume_monitor** (l.92-97):
```python
async def resume_monitor(self, job_id: str):
    if job_id in self.monitors:
        self.monitors[job_id].active = True
        if job_id not in self.tasks or self.tasks[job_id].done():
            self.tasks[job_id] = asyncio.create_task(self._monitor_loop(job_id))
        self._save_monitors()
```

**Dedup pattern to insert at top of `start_monitor`** (before config creation at l.52):
```python
async def start_monitor(self, job_id: str, url: str, brand: str, interval: int, duration: int):
    from services.url_utils import normalize_url
    norm_url = normalize_url(url)
    for existing_id, config in self.monitors.items():
        if normalize_url(config.url) == norm_url and config.brand.lower() == brand.lower():
            if config.active:
                return config, "already_active"
            else:
                await self.resume_monitor(existing_id)
                return self.monitors[existing_id], "reactivated"
    # ... existing code continues unchanged
    config = PriceMonitorConfig(...)
    ...
    return config  # change to: return config, "created"
```

The caller in `routes_product.py` (`POST /monitor/start`) must unpack the tuple and respond with `status` field. Pattern for HTTP 200 with status field follows `routes_brands.py::set_brand_active` response shape (l.207-213).

---

### `backend/services/cross_marketplace_service.py` — MODIFY (rebuild engines per request)

**Analog:** `cross_marketplace_service.py::__init__` (l.152-158), `_enrich_pdp_and_shipping` (l.445-469)

**Current `__init__` pattern** (l.152-158):
```python
class CrossMarketplaceService:
    def __init__(self):
        self.engines = {
            "Mercado Livre": MercadoLivreEngine(),
            "Netshoes": NetshoesEngine(),
            "Amazon": AmazonEngine(),
        }
```

**Refactored pattern** (RESEARCH Pattern 7):
```python
_ENGINE_MAP = {
    "mercadolivre": ("Mercado Livre", MercadoLivreEngine),
    "netshoes":     ("Netshoes",      NetshoesEngine),
    "amazon":       ("Amazon",        AmazonEngine),
}

class CrossMarketplaceService:
    def __init__(self):
        self._engine_instances = {
            key: cls() for key, (_, cls) in _ENGINE_MAP.items()
        }
        # self._by_display: for _enrich_pdp_and_shipping lookup by display name
        self._by_display = {
            display_name: self._engine_instances[key]
            for key, (display_name, _) in _ENGINE_MAP.items()
        }

    def _active_engines(self) -> dict:
        active_brands = brand_service.list_brands(active_only=True)
        active_keys = {b.brand_key for b in active_brands}
        return {
            display_name: self._engine_instances[engine_key]
            for engine_key, (display_name, _) in _ENGINE_MAP.items()
            if engine_key in active_keys
        }
```

**`_enrich_pdp_and_shipping` fix** (l.452-453) — replace `self.engines` lookup:
```python
# Before:
if plat in self.engines:
    engine = self.engines[plat]
# After:
if plat in self._by_display:
    engine = self._by_display[plat]
```

**`_fetch_all_engines` / `compare_product` fix** — wherever `self.engines.items()` is called, replace with `self._active_engines().items()`.

---

### `backend/data/brands.json` — ADD marketplace entries

**Analog:** existing brand entries in brands.json (l.1-46)

**Entry shape to copy** (l.1-16 for "aramis"):
```json
{
  "brand_key": "aramis",
  "brand_name": "Aramis",
  "domain": "www.aramis.com.br",
  "review_provider": "trustvox",
  "review_store_id": "78800",
  "vtex_account": null,
  "engine": "vtex",
  "logo_url": null,
  "wake_access_token": null,
  "search_url_template": null,
  "proxy_url": null,
  "mappings": [],
  "is_active": true
}
```

**Three entries to add** (keys preserved from current runtime injection in l.134-160 of routes_brands.py):
```json
"mercado_livre": {
  "brand_key": "mercado_livre",
  "brand_name": "Mercado Livre",
  "domain": "mercadolivre.com.br",
  "review_provider": "none",
  "review_store_id": null,
  "vtex_account": null,
  "engine": "mercadolivre",
  "logo_url": null,
  "wake_access_token": null,
  "search_url_template": null,
  "proxy_url": null,
  "mappings": [],
  "is_active": true
},
"netshoes": { ... "engine": "netshoes", "domain": "netshoes.com.br" ... },
"amazon":   { ... "engine": "amazon",   "domain": "amazon.com.br"   ... }
```

---

### `frontend/src/api/client.ts` — ADD `identifyBrand` and `addToMonitor`

**Analog:** `client.ts::setBrandActive` (l.59-64) and `client.ts::startMonitor` (l.261-265)

**setBrandActive pattern** (l.59-64):
```typescript
static setBrandActive(brandKey: string, isActive: boolean) {
  return this.request(`/brands/${encodeURIComponent(brandKey)}/active`, {
    method: 'PATCH',
    body: JSON.stringify({ is_active: isActive }),
  });
}
```

**startMonitor pattern** (l.261-265):
```typescript
static startMonitor(data: any) {
  return this.request('/monitor/start', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}
```

**New methods to add** in the Brands section (after `setBrandActive`) and Monitors section respectively:
```typescript
static identifyBrand(url: string) {
  return this.request<{
    engine: string;
    inferred_name: string;
    domain: string;
    warning?: string;
  }>('/brands/identify', {
    method: 'POST',
    body: JSON.stringify({ url }),
  });
}

// In Monitors section, after startMonitor:
static addToMonitor(url: string, brand: string) {
  return this.request<{ job_id: string; status: string; config: any }>(
    '/monitor/start',
    {
      method: 'POST',
      body: JSON.stringify({ url, brand, interval: 10, duration: 24 }),
    }
  );
}
```

---

### `frontend/src/App.tsx` — ADD onboarding form + "Adicionar" button; fix VIRTUAL guard

**Analog:** product card button pattern from shipping feature (l.1524-1531 per RESEARCH.md Pattern 8); `setBrandActive` toggle handler pattern in SettingsPage.

**Button inside `<a>` card pattern** (RESEARCH Pattern 8 — verified from App.tsx l.1524-1531):
```typescript
<button
  type="button"
  className="btn-icon btn-sm"
  title="Adicionar ao monitoramento"
  onClick={async (e) => {
    e.preventDefault();
    e.stopPropagation();
    await handleAddToMonitor(p.url, brandKey);
  }}
>
  <Plus size={14} />
</button>
```
`e.preventDefault()` + `e.stopPropagation()` are mandatory because cards are `<a href>` elements.

**handleAddToMonitor handler pattern** — follows async event handler pattern already in App.tsx for shipping:
```typescript
const handleAddToMonitor = async (url: string, brand: string) => {
  try {
    const result = await ApiClient.addToMonitor(url, brand);
    if (result.status === 'already_active') {
      toast.info('Produto já está em monitoramento');
    } else if (result.status === 'reactivated') {
      toast.success('Monitor reativado');
    } else {
      toast.success('Adicionado ao monitoramento');
    }
  } catch (err: any) {
    toast.error(err.message || 'Erro ao adicionar ao monitoramento');
  }
};
```

**VIRTUAL guard removal** — SettingsPage (l.2325 per RESEARCH):
```typescript
// REMOVE this block:
const VIRTUAL = ['mercado_livre', 'netshoes', 'amazon'];
// and: canToggle = !VIRTUAL.includes(b.brand_key)
// KEEP CategoryPage filter (l.531) and BannersPage filter (l.886) — intentional.
```

**Onboarding form pattern** — follows existing modal/form patterns in App.tsx. The form receives `{ engine, inferred_name, domain }` from `ApiClient.identifyBrand(url)` and pre-fills a `DynamicBrandCreate`-shaped form. On confirm, calls `ApiClient.saveBrand({ ...formValues, engine: confirmedEngine })` — never `engine: "auto"`.

---

### `backend/tests/` — NEW and EXTENDED test files

**Analog:** `tests/test_price_monitor.py` (l.1-100) — exact pattern for all new tests

**Test file structure pattern** (test_price_monitor.py l.1-7):
```python
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone
from services.price_monitor_service import PriceMonitorService
from core.models import PriceMonitorConfig, RawProductBronze
```

**Async test decorator pattern** (l.8):
```python
@pytest.mark.asyncio
async def test_...:
```

**Service instantiation without persistence** (l.10-23):
```python
service = PriceMonitorService()
job_id = "test-job"
config = PriceMonitorConfig(
    job_id=job_id,
    url="http://example.com",
    brand="test-brand",
    interval_minutes=1,
    duration_hours=1,
    active=True,
    last_price=100.0
)
service.monitors[job_id] = config
```
Inject directly into `service.monitors` dict — no disk I/O in tests.

**Mock pattern** (l.39-40):
```python
with patch("services.price_monitor_service.engine_factory.get_engine", return_value=mock_engine), \
     patch("services.price_monitor_service.manager.send_message", new_callable=AsyncMock):
```

**test_url_utils.py pattern** — pure unit, no async needed:
```python
from services.url_utils import normalize_url

def test_normalize_strips_utm():
    result = normalize_url("https://www.example.com/produto?utm_source=google&skuId=123")
    assert "utm_source" not in result
    assert "skuId=123" in result

def test_normalize_removes_www():
    result = normalize_url("https://www.example.com/path/")
    assert result == "https://example.com/path"
```

**test_brand_identify.py pattern** — async, patch `detect_engine`:
```python
@pytest.mark.asyncio
async def test_identify_returns_engine_and_name():
    from unittest.mock import patch, AsyncMock
    with patch("api.routes_brands.detect_engine", new_callable=AsyncMock, return_value=("vtex", None)):
        # call identify_brand directly or via httpx TestClient
        ...
```

---

## Shared Patterns

### Logging
**Source:** `routes_brands.py` (l.10-11), `price_monitor_service.py` (l.14)
**Apply to:** All new backend files
```python
import logging
logger = logging.getLogger(__name__)
# or named: logger = logging.getLogger("ModuleName")
```

### Exception → HTTPException 400
**Source:** `routes_brands.py::create_brand` (l.103-125)
**Apply to:** `POST /brands/identify`
```python
except Exception as e:
    raise HTTPException(status_code=400, detail=str(e))
```

### brand.lower() comparison
**Source:** `price_monitor_service.py::delete_monitors_by_brand` (l.88)
**Apply to:** dedup scan in `start_monitor`
```python
config.brand.lower() == brand_key.lower()
```

### `_save_monitors()` after state change
**Source:** `price_monitor_service.py::stop_monitor` (l.74-75), `resume_monitor` (l.97)
**Apply to:** dedup reactivation path in `start_monitor`
```python
self._save_monitors()  # always after mutating self.monitors
```

### ApiClient.request generic pattern
**Source:** `client.ts::request` (l.12-37) — all static methods call `this.request<T>(endpoint, options)`
**Apply to:** `identifyBrand`, `addToMonitor`
```typescript
return this.request<ReturnType>(endpoint, { method: 'POST', body: JSON.stringify(payload) });
```

---

## No Analog Found

None — all files have close analogs in the existing codebase.

---

## Metadata

**Analog search scope:** `backend/api/`, `backend/services/`, `backend/tests/`, `backend/data/`, `frontend/src/api/`, `frontend/src/`
**Files read:** routes_brands.py, zara_parser.py, price_monitor_service.py (l.1-100), cross_marketplace_service.py (l.140-220, l.440-470), brands.json (l.1-50), client.ts, test_price_monitor.py
**Pattern extraction date:** 2026-06-29
