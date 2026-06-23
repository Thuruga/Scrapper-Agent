# Phase 29: Diagnóstico de Categorias Vazias/Erro - Pattern Map

**Mapped:** 2026-06-22
**Files analyzed:** 6 new/modified files
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `services/category_diagnostic_service.py` | service | request-response (async probe) | `services/vtex_api_scraper.py` (`scrape_category_paged`, `fetch_categories`) | role-match (same aiohttp pattern, same resources-header logic) |
| `api/routes_diagnostic.py` | route | request-response | `api/routes_category.py` (thin-route, no BackgroundTasks, GET endpoints) | exact |
| `core/models.py` (extend) | model | — | `core/models.py` (`BrandSearchResult`, `DynamicBrand`, `CategoryMapping`) | exact |
| `frontend/src/pages/DiagnosticPage.tsx` | component | request-response | `App.tsx` `MonitoredCategoriesPage` (L1754) + `SettingsPage` brand list (L1699) | role-match |
| `frontend/src/api/client.ts` (extend) | utility | request-response | `client.ts` `getHistoryList()` (GET without body, static method) | exact |
| `tests/test_category_diagnostic.py` | test | — | `tests/test_vtex_api_client.py` (`_FakeResp`/`_FakeSession` pattern) | exact |

---

## Pattern Assignments

### `services/category_diagnostic_service.py` (service, request-response / async probe)

**Primary analog:** `services/vtex_api_scraper.py`

**Imports pattern** — follow the module-level imports from `vtex_api_scraper.py` lines 1-20:
```python
import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

import aiohttp
from curl_cffi.requests import AsyncSession   # for fetch_categories reuse (D-10)

from services.brand_service import brand_service
from services.category_mapping import _CATEGORY_INDEX, resolve_category_for_brands
from services.engines.factory import engine_factory
```

**Domain auto-discovery reuse pattern (D-10)** — `vtex_api_scraper.py` lines 46-130.
`VtexApiClient.fetch_categories(domain)` performs the public→stable domain auto-discovery using `curl_cffi.AsyncSession(impersonate="chrome")`. The diagnostic service calls this **once per brand** before launching probes:
```python
# vtex_api_scraper.py L46-130 (condensed — call this, do not re-implement)
from services.vtex_api_scraper import VtexApiClient

async def _resolve_base_url(domain: str) -> str:
    """
    Returns the correct base URL (public OR stable) for probing.
    Reuses fetch_categories() which already implements public→stable auto-discovery.
    Result is used for ALL category probes of this brand (D-10: once per brand, not per category).
    """
    domain_clean = domain.replace("https://", "").replace("http://", "").strip("/")
    # fetch_categories already returns [] on failure; we only need the stable domain as a side effect.
    # Alternative: call _discover_account_from_html directly if you want to avoid fetching the tree.
    # Safest: attempt the public JSON endpoint; if HTML, extract account_name via the same path
    # the scraper uses (L75-96).
    url_principal = f"https://{domain_clean}/api/catalog_system/pub/category/tree/1"
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    async with AsyncSession(impersonate="chrome", timeout=15) as session:
        response = await session.get(url_principal, headers=headers)
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    return f"https://{domain_clean}"   # public domain works
            except Exception:
                pass
        # HTML or failure → discover stable domain
        account_name = VtexApiClient._discover_account_from_html(domain_clean, response.text)
        return f"https://{account_name}.vtexcommercestable.com.br"
```

**Raw aiohttp probe pattern (D-08) — the intentional negation of `_request_json`.**
The scraper's `_request_json` (L228-294) has retry, stable-domain-fallback-per-call, and Playwright fallback on 403. The probe MUST NOT use any of that. Instead, use `aiohttp.ClientSession.get()` directly:

```python
# Verified pattern: aiohttp direct use (contrasts with VtexApiClient._request_json L228-294)
# resources header: verified in scrape_category_paged L546-559
_PROBE_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; DiagnosticProbe/1.0)",
}

async def probe_category(
    session: aiohttp.ClientSession,
    base_url: str,
    path: str,
    semaphore: asyncio.Semaphore,
) -> dict:
    """
    Single raw GET. No retry. No stable-domain fallback per category. No Playwright.
    Reports the real http_status (D-08).
    """
    path_clean = path.lstrip("/") if path.startswith("/") else path
    # Use ?fq= variant for vtex_fq_path that starts with C:/ or B:
    if path_clean.startswith("C:/") or path_clean.startswith("B:"):
        url = f"{base_url}/api/catalog_system/pub/products/search?fq={path_clean}&_from=0&_to=9"
    else:
        url = f"{base_url}/api/catalog_system/pub/products/search/{path_clean}?_from=0&_to=9"

    async with semaphore:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                http_status = resp.status
                content_type = resp.headers.get("Content-Type", "")

                if http_status != 200:
                    return {"status": "error", "http_status": http_status,
                            "error_detail": f"HTTP {http_status}", "total_count": None, "probed_url": url}

                if "text/html" in content_type:
                    return {"status": "error", "http_status": http_status,
                            "error_detail": "HTML instead of JSON (possible headless/WAF block)",
                            "total_count": None, "probed_url": url}

                try:
                    body = await resp.json(content_type=None)
                except Exception as parse_err:
                    return {"status": "error", "http_status": http_status,
                            "error_detail": f"JSON parse error: {parse_err}",
                            "total_count": None, "probed_url": url}

                # resources header: format "x-y/total" (verified L546-559)
                total_count: Optional[int] = None
                res_header = resp.headers.get("resources", "")
                if "/" in res_header:
                    try:
                        total_count = int(res_header.split("/")[-1])
                    except ValueError:
                        pass

                if isinstance(body, list) and len(body) > 0:
                    return {"status": "ok", "http_status": 200, "error_detail": None,
                            "total_count": total_count, "probed_url": url}
                else:
                    return {"status": "empty", "http_status": 200, "error_detail": None,
                            "total_count": total_count or 0, "probed_url": url}

        except asyncio.TimeoutError:
            return {"status": "error", "http_status": None, "error_detail": "Timeout",
                    "total_count": None, "probed_url": url}
        except Exception as exc:
            return {"status": "error", "http_status": None, "error_detail": f"Network error: {exc}",
                    "total_count": None, "probed_url": url}
```

**Concurrency pattern (D-05)** — `asyncio.gather` is used in `orchestrator_multi.py` and referenced in `scrape_category_paged` L659:
```python
async def run_brand_probes(session, base_url, categories, semaphore):
    tasks = [probe_category(session, base_url, cat["path"], semaphore) for cat in categories]
    return await asyncio.gather(*tasks)
```

**Engine-type guard (D-02)** — verified in `services/engines/factory.py`: `engine_factory.get_engine()` returns `VTEXEngine` for `engine="unknown"` (no special case). The service must check `brand_data.engine` directly:
```python
# Do NOT rely on engine_factory for VTEX vs no-probe decision
engine_type = getattr(brand_data, "engine", "vtex")
is_vtex_probe_eligible = (engine_type == "vtex")
```

**`list_brands(active_only=False)` call (D-01)** — verified in `brand_service.py` L207:
```python
# Signature confirmed: active_only=False is the default → returns all brands including inactive
brands = brand_service.list_brands()  # or explicitly: active_only=False
```

---

### `api/routes_diagnostic.py` (route, request-response)

**Primary analog:** `api/routes_category.py`

**Imports pattern** (routes_category.py lines 1-32):
```python
from fastapi import APIRouter, HTTPException
from services.category_diagnostic_service import run_brand_diagnostic, run_all_brands_diagnostic
from services.brand_service import brand_service
```

**Router declaration** (routes_category.py line 32):
```python
router = APIRouter()
```

**Thin GET endpoint pattern** — mirror `get_categories` (routes_category.py L95-104):
```python
@router.get("/brands/{brand}/categories")
async def get_categories(brand: str):
    brand_key = brand.lower()
    if not brand_service.get_brand(brand_key):
        raise HTTPException(status_code=404, detail=f"Marca '{brand}' não suportada.")
    engine = engine_factory.get_engine(brand_key)
    categories = await engine.get_catalog()
    return {"brand": brand, "categories": categories}
```

For the diagnostic, the equivalent thin endpoints are:
```python
@router.get("/diagnostic/brands/{brand_key}")
async def diagnose_brand(brand_key: str):
    brand_key = brand_key.lower()
    if not brand_service.get_brand(brand_key):
        raise HTTPException(status_code=404, detail=f"Marca '{brand_key}' não encontrada.")
    result = await run_brand_diagnostic(brand_key)
    return result

@router.get("/diagnostic/all")
async def diagnose_all():
    return await run_all_brands_diagnostic()
```

Key difference from routes that use BackgroundTasks: diagnostic is **synchronous (async def, no `BackgroundTasks`)**, following D-05. No `background_tasks.add_task()`.

**Router registration** — `api/__init__.py` lines 12-31 (exact pattern to copy):
```python
# In api/__init__.py, add:
from api.routes_diagnostic import router as diagnostic_router
# ...
api_router.include_router(diagnostic_router)
```
The `api_router` already has `dependencies=[Depends(verify_api_key)]` (line 23) — the diagnostic router inherits auth automatically.

---

### `core/models.py` — New Pydantic response models (extend existing file)

**Primary analog:** `core/models.py` `BrandSearchResult` (L136-143) and `CategoryMapping` (L199-204)

**Pattern from BrandSearchResult** (lines 136-143) — per-brand result with optional error:
```python
class BrandSearchResult(BaseModel):
    brand_key: str
    brand_name: str
    products: List[SearchProductResult] = Field(default_factory=list)
    error: Optional[str] = None   # filled if brand search failed
    total_found: int = 0
```

**New models to add** — follow the exact same BaseModel style with `Optional` fields, `Literal` for enum strings (Pydantic v2 style already used in the file):
```python
from typing import Literal

class CategoryDiagnosticResult(BaseModel):
    slug: str
    label: str
    status: Literal["ok", "empty", "error", "no_probe"]
    http_status: Optional[int] = None
    error_detail: Optional[str] = None
    total_count: Optional[int] = None
    probed_url: Optional[str] = None

class BrandDiagnosticResult(BaseModel):
    brand_key: str
    brand_name: str
    domain: str
    is_active: bool
    engine: str
    categories: List[CategoryDiagnosticResult]

class DiagnosticReportResponse(BaseModel):
    brands: List[BrandDiagnosticResult]
```

Place these after the `DynamicBrand` section (around line 233) to keep the file organized by domain.

---

### `frontend/src/pages/DiagnosticPage.tsx` (component, request-response)

**Primary analog:** `App.tsx` `MonitoredCategoriesPage` (L1754) + `SettingsPage` brand list (L1699)

**useState + fetch pattern** — `MonitoredCategoriesPage` L1754-1778:
```typescript
const MonitoredCategoriesPage = ({ brands }: { brands: any[] }) => {
  const [categories, setCategories] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  // ...
  const fetchCategories = async () => {
    setLoading(true);
    try {
      const data = await ApiClient.getMonitoredCategories();
      setCategories(data);
    } catch (err: any) {
      // toast error
    } finally {
      setLoading(false);
    }
  };
```

For DiagnosticPage, use per-brand loading state (Record<string, boolean>) since D-16 requires individual brand loading indicators:
```typescript
const [loadingMap, setLoadingMap] = useState<Record<string, boolean>>({});
const [results, setResults] = useState<DiagnosticReportResponse | null>(null);
```

**Inactive brand visual treatment (D-03)** — `SettingsPage` L1705 (exact line verified):
```tsx
<div className="brand-info" style={b.is_active === false ? { opacity: 0.55 } : undefined}>
  {/* brand content */}
  {b.is_active === false && (
    <span className="monitor-badge" style={{ color: 'var(--warning)', fontSize: '0.7rem' }}>Inativa</span>
  )}
</div>
```
Replicate exactly this pattern in `DiagnosticPage` for brand cards where `brand.is_active === false`.

**Status chip pattern** — use Tailwind classes (project stack confirmed: React 19 + Tailwind):
```tsx
const STATUS_CHIP: Record<string, string> = {
  ok:       'bg-green-500 text-white',
  empty:    'bg-yellow-500 text-white',
  error:    'bg-red-500 text-white',
  no_probe: 'bg-gray-400 text-white',
};
const STATUS_LABEL: Record<string, string> = {
  ok: 'OK', empty: 'Vazia', error: 'Erro', no_probe: 'Sem probe',
};
// <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_CHIP[cat.status]}`}>
//   {STATUS_LABEL[cat.status]}
// </span>
```

---

### `frontend/src/api/client.ts` — Add `getDiagnostic` method (extend)

**Primary analog:** `client.ts` `getHistoryList()` and `getHistoryDetail()` (L90-95) — GET without body, static method, typed return:

```typescript
static getHistoryList() {
  return this.request<any[]>('/history');
}

static getHistoryDetail(jobId: string) {
  return this.request<any>(`/history/${jobId}`);
}
```

**New method to add** — follows same pattern:
```typescript
static getDiagnostic(brandKey?: string) {
  const endpoint = brandKey
    ? `/diagnostic/brands/${encodeURIComponent(brandKey)}`
    : '/diagnostic/all';
  return this.request<DiagnosticReportResponse>(endpoint);
}
```

The `request<T>()` core (L12-37) already handles X-API-Key header, error parsing, and type return — no changes needed there.

---

### `tests/test_category_diagnostic.py` (test, offline/deterministic)

**Primary analog:** `tests/test_vtex_api_client.py` — `_FakeResp` / `_FakeSession` pattern (L128-154)

**`_FakeResp` pattern** (L128-140) — verified, use with `headers` dict extended for `resources`:
```python
class _FakeResp:
    def __init__(self, status, json_data):
        self.status = status
        self._json = json_data

    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False
    async def json(self): return self._json
```

For the diagnostic probe, `_FakeResp` needs `headers` and `content_type` support (the probe reads `resp.headers.get("Content-Type")` and `resp.headers.get("resources")`). Extend accordingly:
```python
class _FakeResp:
    def __init__(self, status, json_data=None, content_type="application/json", headers=None):
        self.status = status
        self._json = json_data
        self.headers = {"Content-Type": content_type, **(headers or {})}

    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False
    async def json(self, content_type=None): return self._json

class _FakeSession:
    def __init__(self, resp): self._resp = resp
    def get(self, url, timeout=None): return self._resp
```

**asyncio.run() pattern** (L84) — project does NOT configure pytest-asyncio; run coroutines with:
```python
result = asyncio.run(probe_category(session, base_url, path, asyncio.Semaphore(5)))
```

**Test structure** — follow `TestParseProductDictCharacterization` class grouping (L69):
```python
class TestClassifier:
    def test_ok(self): ...
    def test_empty(self): ...
    def test_404(self): ...
    def test_html_body(self): ...
    def test_timeout(self, monkeypatch): ...

class TestBrandFilter:
    def test_non_vtex_no_probe(self): ...

class TestEndpoint:
    def test_get_brand_diagnostic_returns_200(self): ...
```

---

## Shared Patterns

### Authentication (apply to `api/routes_diagnostic.py`)
**Source:** `api/__init__.py` lines 23-31
The `api_router` is declared with `dependencies=[Depends(verify_api_key)]`. Any router included via `api_router.include_router(...)` inherits this dependency automatically. No per-endpoint auth decorator needed.
```python
api_router = APIRouter(dependencies=[Depends(verify_api_key)])
api_router.include_router(diagnostic_router)  # inherits auth
```

### Error Handling (apply to `api/routes_diagnostic.py`)
**Source:** `api/routes_category.py` lines 95-104
Pattern: validate input against `brand_service.get_brand()` → raise `HTTPException(404)` if not found → then call service:
```python
brand_key = brand.lower()
if not brand_service.get_brand(brand_key):
    raise HTTPException(status_code=404, detail=f"Marca '{brand}' não suportada.")
```

### Toast error in frontend (apply to `DiagnosticPage.tsx`)
**Source:** `App.tsx` `CrossMarketplacePage` — uses `sonner` toast for API errors:
```typescript
import { toast } from 'sonner';
// in catch block:
toast.error(err?.message || 'Erro ao executar diagnóstico');
```

### Pydantic BaseModel declaration style (apply to new models in `core/models.py`)
**Source:** `core/models.py` lines 95-153 (`SearchProductResult`, `BrandSearchResult`)
```python
class SearchProductResult(BaseModel):
    brand: str
    url: str
    price_full: Optional[float] = None
    error: Optional[str] = None
```
All optional fields default to `None`. Use `Literal["a", "b"]` for enum strings (Pydantic v2, no separate `Enum` class needed).

---

## No Analog Found

All files have close analogs. No files in this phase lack a codebase match.

---

## Key Anti-Patterns (from RESEARCH.md — planner must enforce)

| Anti-Pattern | Why | What to Do Instead |
|---|---|---|
| `VtexApiClient._request_json()` in probe | Has retry + stable-domain-fallback + Playwright (D-08) | `aiohttp.ClientSession.get()` directly |
| `VTEXEngine.search()` in probe | Has full-text fallback (L833) that masks empty categories (D-07) | Raw aiohttp probe to `/api/catalog_system/pub/products/search/{path}` |
| `BackgroundTasks.add_task()` in route | D-05 is synchronous; probe returns in the same response | `async def` handler that `await`s the service call |
| `engine_factory.get_engine()` for VTEX guard | Returns `VTEXEngine` even for `engine="unknown"` (verified in factory.py) | Check `brand_data.engine == "vtex"` directly |
| Portuguese enum values in Pydantic | API contract should be language-neutral | `Literal["ok", "empty", "error", "no_probe"]`; PT-BR only in frontend labels |
| `_to=0` in probe URL | VTEX returns 0-1 items, may not populate `resources` header | Use `_to=9` (10 items, same as scraper chunk) |

---

## Metadata

**Analog search scope:** `services/`, `api/`, `core/`, `frontend/src/`, `tests/`
**Files read:** `api/routes_category.py`, `api/__init__.py`, `core/models.py`, `frontend/src/App.tsx` (L1695-1773, L2100-2197), `frontend/src/api/client.ts`, `services/vtex_api_scraper.py` (L46-130, L540-565), `tests/test_vtex_api_client.py`
**Pattern extraction date:** 2026-06-22
