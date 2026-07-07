# Phase 45: Análise de Sortimento - Pattern Map

**Mapped:** 2026-07-05
**Files analyzed:** 9
**Analogs found:** 9 / 9

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/services/sortiment_snapshot_service.py` | service | batch | `backend/services/category_monitor_service.py` | exact |
| `backend/services/sortiment_artifact_service.py` | service | file-I/O | `backend/services/stock_summary_service.py` | exact |
| `backend/services/sortiment_registry_service.py` | service | CRUD | `backend/services/category_monitor_service.py` | role-match |
| `backend/api/routes_sortiment.py` | route | request-response | `backend/api/routes_monitor.py` | exact |
| `backend/app.py` | config | event-driven | `backend/app.py` | exact |
| `backend/api/__init__.py` | config | request-response | `backend/api/__init__.py` | exact |
| `backend/core/models.py` | model | transform | `backend/core/models.py` | exact |
| `frontend/src/api/client.ts` | utility | request-response | `frontend/src/api/client.ts` | exact |
| `frontend/src/App.tsx` | component | request-response | `frontend/src/App.tsx` | exact |

## Pattern Assignments

### `backend/services/sortiment_snapshot_service.py` (service, batch)

**Analog:** `backend/services/category_monitor_service.py`

**Imports + local JSON ownership** (`backend/services/category_monitor_service.py:3-23`):
```python
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from core.models import resolve_effective_price
from services.stock_summary_service import (
    compute_stock_summary,
    ensure_scan_product_ids,
    persist_monitor_stock_summary,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
MONITORS_FILE = DATA_DIR / "monitored_categories.json"
logger = logging.getLogger("CategoryMonitor")
```

**Core batch pattern** (`backend/services/category_monitor_service.py:121-161`):
```python
async def run_category_scan(monitor: dict, notify_completion: bool = False) -> None:
    from services.engines.factory import engine_factory

    url = monitor.get("url")
    brand = monitor.get("brand")
    monitor_id = monitor.get("id")
    if not url or not brand or not monitor_id:
        logger.warning("Categoria monitorada invalida: %s", monitor)
        return

    engine = engine_factory.get_engine(brand)
    scraped_products = []
    try:
        async for product in engine.run_bulk_scrape(category_url=url):
            scraped_products.append(product)
            if len(scraped_products) >= 1000:
                logger.warning("Limite de 1000 produtos atingido para %s.", brand)
                break
    except Exception as exc:
        logger.error("Erro ao extrair %s: %s", url, exc)

    scraped_products = ensure_scan_product_ids(scraped_products, brand, monitor_id)
    ...
    products_file.write_text(
        json.dumps(scraped_products, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
```

**Previous snapshot before overwrite** (`backend/services/category_monitor_service.py:152-166`):
```python
# Snapshot anterior precisa ser lido ANTES de sobrescrever o arquivo,
# senão o diff de preços compararia o novo scan com ele mesmo.
previous_products = _load_previous_snapshot(monitor_id)

...

if previous_products and scraped_products:
    changes = _detect_price_changes(previous_products, scraped_products)
```

**Batch job loop should stay isolated** (`backend/services/category_monitor_service.py:218-224`):
```python
async def category_monitor_job() -> None:
    categories = load_monitored_categories()
    for category in categories:
        try:
            await run_category_scan(category)
        except Exception as exc:
            logger.error("Falha no monitor %s: %s", category.get("id"), exc)
```

**Phase 45 guidance:** keep the sortimento cron separate from the category monitor job; persist one JSON snapshot per category run plus a lightweight index lookup; never store the full normalized catalog if aggregates and evidence are enough.

---

### `backend/services/sortiment_artifact_service.py` (service, file-I/O)

**Analog:** `backend/services/stock_summary_service.py`

**Safe JSON helpers** (`backend/services/stock_summary_service.py:102-117`):
```python
def _safe_artifact_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value))


def _write_json(path: Path, payload: Any) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
```

**Artifact persistence shape** (`backend/services/stock_summary_service.py:120-150`):
```python
def persist_monitor_stock_summary(
    monitor_id: str,
    summary: StockRuptureSummary,
) -> None:
    path = DATA_DIR / f"stock_summary_{_safe_artifact_id(monitor_id)}.json"
    _write_json(path, summary.model_dump(mode="json"))


def load_monitor_stock_summary(monitor_id: str) -> StockRuptureSummary | None:
    path = DATA_DIR / f"stock_summary_{_safe_artifact_id(monitor_id)}.json"
    data = _read_json(path)
    if data is None:
        return None
    return StockRuptureSummary.model_validate(data)
```

**Stable evidence ids** (`backend/services/stock_summary_service.py:76-99`):
```python
def ensure_scan_product_ids(
    products: Iterable[Any],
    brand: str,
    scan_id: str,
) -> list[dict[str, Any]]:
    ...
            digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]
            item["scan_product_id"] = f"{scan_id}:{digest}"
```

**Phase 45 guidance:** use the same `_safe_artifact_id` and `_write_json` pattern for canonical category filenames and manifest entries. Prefer `model_dump(mode="json")` for manifest/snapshot records. Reuse `scan_product_id` as lightweight bucket evidence instead of persisting the whole catalog.

---

### `backend/services/sortiment_registry_service.py` (service, CRUD)

**Analog:** `backend/services/category_monitor_service.py`

**Load/save local registry** (`backend/services/category_monitor_service.py:26-45`):
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
    MONITORS_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
```

**Status-filtered read** (`backend/services/category_monitor_service.py:44-45`):
```python
def load_monitored_categories() -> List[Dict[str, Any]]:
    return [item for item in _load_local() if item.get("status") == "active"]
```

**Phase 45 guidance:** mirror this JSON-backed registry pattern for `sortiment_categories.json`, but seed it one-way from `backend/data/monitored_categories.json` with new rows defaulting to disabled/inactive. Keep sortimento registry ownership separate from monitor CRUD.

---

### `backend/api/routes_sortiment.py` (route, request-response)

**Analog:** `backend/api/routes_monitor.py`

**Router + request models** (`backend/api/routes_monitor.py:8-39`):
```python
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/monitor", tags=["Monitoramento de Categorias"])


class CategoryMonitorCreate(BaseModel):
    url: str
    brand: str


class ReviewCommentsRequest(BaseModel):
    max_pages: Optional[int] = None

    model_config = {"extra": "forbid"}
```

**Create endpoint with background task** (`backend/api/routes_monitor.py:60-77`):
```python
@router.post("/category", response_model=CategoryMonitorResponse)
async def create_category_monitor(
    data: CategoryMonitorCreate, background_tasks: BackgroundTasks
):
    row = {
        "id": str(uuid.uuid4()),
        "url": data.url,
        "brand": data.brand,
        "status": "active",
    }
    ...
    background_tasks.add_task(run_category_scan, row, notify_completion=True)
    return CategoryMonitorResponse(**row)
```

**Read endpoint with tolerant missing-artifact handling** (`backend/api/routes_monitor.py:93-146`):
```python
@router.get("/category/{monitor_id}/products")
async def get_monitored_products(monitor_id: str):
    products_file = DATA_DIR / f"monitored_products_{monitor_id}.json"
    if not products_file.exists():
        return []
    try:
        products = json.loads(products_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    ...

@router.get("/category/{monitor_id}/stock-summary")
async def get_monitor_stock_summary(monitor_id: str):
    summary = load_monitor_stock_summary(monitor_id)
    if summary is None:
        raise HTTPException(
            status_code=404,
            detail="Resumo de estoque nao encontrado.",
        )
    return summary.model_dump(mode="json")
```

**Phase 45 guidance:** create a dedicated `/sortiment` router instead of extending `/monitor`. Follow the same split between list/create/toggle endpoints and artifact-read endpoints. Use `BackgroundTasks` only for manual triggers; the scheduled cron should stay in `backend/app.py`.

---

### `backend/app.py` (config, event-driven)

**Analog:** `backend/app.py`

**Scheduler wiring** (`backend/app.py:26-42`):
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    from services.category_monitor_service import category_monitor_job
    from services.price_monitor_service import monitor_service

    monitor_service.load_monitors()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(category_monitor_job, "interval", minutes=10)
    scheduler.start()
    logger.info("Monitor de categorias iniciado (intervalo de 10 minutos).")

    yield
    scheduler.shutdown()
```

**Phase 45 guidance:** add a second job import and `scheduler.add_job(...)` call here rather than piggybacking on the existing 10-minute category monitor. The sortimento job should have its own cadence, its own log line, and no dependency on the live-search path.

---

### `backend/api/__init__.py` (config, request-response)

**Analog:** `backend/api/__init__.py`

**Protected router registration** (`backend/api/__init__.py:12-36`):
```python
from api.routes_monitor import router as monitor_router

api_router = APIRouter(dependencies=[Depends(verify_api_key)])

api_router.include_router(product_router)
api_router.include_router(category_router)
...
api_router.include_router(monitor_router)
...
api_router.include_router(notifications_router)
```

**Phase 45 guidance:** register `sortiment_router` here so it inherits the global `X-API-Key` dependency. Do not create a separate public router for sortimento analytics.

---

### `backend/core/models.py` (model, transform)

**Analog:** `backend/core/models.py`

**Existing source fields for v1 dimensions** (`backend/core/models.py:168-209`):
```python
class RawProductBronze(BaseModel):
    url: str
    brand: str
    raw_title: str
    raw_description: str
    price_full: float
    ...
    category: Optional[str] = None
    sub_category: Optional[str] = None
    composition: Optional[str] = None
    ...
    available_colors: List[str] = Field(default_factory=list)
    available_sizes: List[str] = Field(default_factory=list)
    ...
    scan_product_id: Optional[str] = None
    ...
    specifications: Dict[str, str] = Field(default_factory=dict)
```

**Phase 45 guidance:** Phase 45 can compute color/size/composition buckets from existing fields without expanding the Bronze contract. If you add new Pydantic models, keep them additive and JSON-serializable like the existing summary models.

---

### `frontend/src/api/client.ts` (utility, request-response)

**Analog:** `frontend/src/api/client.ts`

**Shared request wrapper** (`frontend/src/api/client.ts:87-117`):
```typescript
export class ApiClient {
  public static async request<T>(endpoint: string, options: RequestInit = {}, signal?: AbortSignal): Promise<T> {
    const headers: any = {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
      ...options.headers,
    };

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
      ...(signal ? { signal } : {}),
    });

    let data: any;
    try {
      data = await response.json();
    } catch {
      // Ignored
    }

    if (!response.ok) {
      throw new Error(data?.detail || `API Error: ${response.status}`);
    }

    return data as T;
  }
```

**Feature-scoped methods pattern** (`frontend/src/api/client.ts:427-469`):
```typescript
static getMonitoredCategories() {
  return this.request<any[]>('/monitor/categories');
}

static createMonitoredCategory(data: { url: string; brand: string }) {
  return this.request('/monitor/category', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

static getMonitoredCategoryStockSummary(monitorId: string) {
  return this.request<StockRuptureSummary>(
    `/monitor/category/${encodeURIComponent(monitorId)}/stock-summary`
  );
}
```

**Type export pattern** (`frontend/src/api/client.ts:7-18`):
```typescript
export type StockRuptureSummary = {
  brand: string;
  total_products: number;
  in_stock_count: number;
  out_of_stock_count: number;
  unknown_stock_count: number;
  verified_stock_count: number;
  rupture_pct: number | null;
  scan_id?: string | null;
  monitor_id?: string | null;
  scanned_at: string;
};
```

**Phase 45 guidance:** add sortimento types and methods in the same file, grouped as a dedicated section. The dashboard payload should be typed, not left as `any`, because the UI depends on stable cards and per-dimension chart structures.

---

### `frontend/src/App.tsx` (component, request-response)

**Analog:** `frontend/src/App.tsx`

**Reusable shell pieces** (`frontend/src/App.tsx:172-197`):
```tsx
const SidebarItem = ({ icon: Icon, label, active, onClick }: any) => (
  <button
    type="button"
    onClick={onClick}
    className={`sidebar-item ${active ? 'active' : ''}`}
  >
    <Icon size={20} />
    <span>{label}</span>
  </button>
);

const GlassCard = ({ children, title, className = "", subtitle }: any) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    className={`glass-card ${className}`}
  >
```

**Dedicated page with list + modal + loading states** (`frontend/src/App.tsx:3739-3917`):
```tsx
const refreshCategoriesList = async () => {
  const data = await ApiClient.getMonitoredCategories();
  setCategories(data);
  return data;
};

useEffect(() => {
  let active = true;
  ApiClient.getMonitoredCategories()
    .then(data => {
      if (active) setCategories(data);
    })
    .catch((err: Error) => {
      if (active) toast.error('Erro ao buscar categorias monitoradas: ' + err.message);
    })
    .finally(() => {
      if (active) setLoading(false);
    });
  return () => {
    active = false;
  };
}, []);

const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  setSubmitting(true);
  try {
    const created = await ApiClient.createMonitoredCategory(newCategory) as any;
    ...
    startAutoSweepPoll(created.id);
  } catch (err: any) {
    toast.error("Erro ao adicionar: " + err.message);
  } finally {
    setSubmitting(false);
  }
};
```

**Dashboard cards and responsive data blocks** (`frontend/src/App.tsx:4181-4200`):
```tsx
{selectedMonitorStockSummary && (
  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '8px', marginBottom: '16px' }}>
    <div className="badge" style={{ ... }}>
      <span>Verificados:</span>
      <strong>{selectedMonitorStockSummary.verified_stock_count}</strong>
    </div>
    ...
    {selectedMonitorStockSummary.rupture_pct !== null && (
      <div className="badge" style={{ ... }}>
        <span>Ruptura:</span>
        <strong>{Math.round(selectedMonitorStockSummary.rupture_pct * 100)}%</strong>
      </div>
    )}
  </div>
)}
```

**Toggle/page pattern for adjacent subviews** (`frontend/src/App.tsx:4344-4379`):
```tsx
type MonitorView = 'product' | 'category';

const MonitoringPage = ({ brands, view, onViewChange }: { ... }) => {
  return (
    <>
      <div className="view-toggle-row">
        <div className="view-toggle" role="tablist" aria-label="Tipo de monitoramento">
          <button ... className={`view-toggle-btn ${view === 'product' ? 'active' : ''}`}>
            <Package size={16} /> Produto Único
          </button>
          <button ... className={`view-toggle-btn ${view === 'category' ? 'active' : ''}`}>
            <Layers size={16} /> Categorias
          </button>
        </div>
      </div>

      {view === 'product' ? <MonitorPage brands={brands} /> : <MonitoredCategoriesPage brands={brands} />}
    </>
  );
};
```

**Main tab registration** (`frontend/src/App.tsx:4502-4651`):
```tsx
function App() {
  const [activeTab, setActiveTab] = useState('monitor');
  ...
  const renderTab = () => {
    switch (activeTab) {
      case 'monitor': return <MonitoringPage brands={brands} view={monitorView} onViewChange={setMonitorView} />;
      case 'search': return <SearchPage ... />;
      case 'cross': return <CrossMarketplacePage ... />;
      case 'category': return <CategoryPage brands={brands} />;
      case 'banners': return <BannersPage brands={brands} />;
      case 'settings': return <SettingsPage brands={brands} onRefresh={refreshBrands} />;
      default: return <div className="p-8">Selecione uma aba...</div>;
    }
  };

  ...
  <SidebarItem
    icon={Layers}
    label="Categorias"
    active={activeTab === 'category'}
    onClick={() => navigateTab('category')}
  />
```

**Phase 45 guidance:** implement sortimento as another first-class page/tab in `App.tsx`, not as a nested modal under monitoring. Reuse `GlassCard`, responsive stat grids, loading/empty-state blocks, and the existing sidebar/page-switch pattern. The dashboard should place delta cards first and the current per-dimension distributions below.

---

### `backend/tests/test_phase45_sortiment_routes.py` (test, request-response)

**Analog:** `backend/tests/test_phase44_routes.py`

**Service monkeypatch + JSON artifact assertions** (`backend/tests/test_phase44_routes.py:41-105`):
```python
def test_run_category_scan_persists_products_with_scan_ids_and_stock_summary(
    tmp_path, monkeypatch
):
    import services.category_monitor_service as category_monitor_service
    import services.stock_summary_service as stock_summary_service
    from services.engines import factory

    ...
    monkeypatch.setattr(category_monitor_service, "DATA_DIR", tmp_path)
    ...
    asyncio.run(category_monitor_service.run_category_scan(monitor))

    persisted_products = json.loads(
        (tmp_path / "monitored_products_monitor-1.json").read_text(encoding="utf-8")
    )
    ...
    summary = json.loads(
        (tmp_path / "stock_summary_monitor-1.json").read_text(encoding="utf-8")
    )
```

**Route tests with `FastAPI()` + included router** (`backend/tests/test_phase44_routes.py:151-191`):
```python
app = FastAPI()
app.include_router(routes_monitor.router)

response = TestClient(app).get("/monitor/category/monitor-1/stock-summary")

assert response.status_code == 200
assert response.json() == summary.model_dump(mode="json")
```

**Phase 45 guidance:** test JSON snapshot naming, manifest lookup of the previous snapshot, baseline-without-delta responses, and protected route payloads using this same monkeypatch/TestClient structure.

## Shared Patterns

### JSON Artifact Persistence
**Sources:** `backend/services/stock_summary_service.py:102-150`, `backend/services/category_monitor_service.py:156-161`

Apply to all sortimento persistence services:
```python
def _safe_artifact_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value))

def _write_json(path: Path, payload: Any) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
```

Use one file per category per execution. Add a manifest/index file for fast previous-snapshot lookup, but keep the snapshot itself immutable and audit-friendly.

### Background Scheduler Wiring
**Source:** `backend/app.py:26-42`

Apply to the new sortimento cron:
```python
scheduler = AsyncIOScheduler()
scheduler.add_job(category_monitor_job, "interval", minutes=10)
scheduler.start()
```

Copy the shape, not the coupling. Phase 45 needs a second independent `add_job(...)`, with its own service import and cadence.

### Protected Route Registration
**Source:** `backend/api/__init__.py:24-36`

Apply to all sortimento routes:
```python
api_router = APIRouter(dependencies=[Depends(verify_api_key)])
...
api_router.include_router(monitor_router)
```

Mount the new router through `api_router` so it inherits the existing `X-API-Key` protection automatically.

### Route Error Handling
**Source:** `backend/api/routes_monitor.py:138-146`

Apply to snapshot/detail reads:
```python
summary = load_monitor_stock_summary(monitor_id)
if summary is None:
    raise HTTPException(
        status_code=404,
        detail="Resumo de estoque nao encontrado.",
    )
return summary.model_dump(mode="json")
```

Return `404` for a missing dashboard snapshot and a successful payload for baseline snapshots with no previous comparison.

### Frontend Dashboard Shell
**Sources:** `frontend/src/App.tsx:183-197`, `frontend/src/App.tsx:4181-4200`, `frontend/src/App.tsx:4502-4651`

Apply to the new sortimento page:
```tsx
<GlassCard title="...">
  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '8px' }}>
    ...
  </div>
</GlassCard>
```

Stay inside the current single-file page shell. Add a sidebar tab/page and use cards + responsive grids + charts rather than inventing a separate UI framework.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| None | - | - | Phase 45 fits existing JSON-service, APScheduler, protected-route, and dashboard-tab patterns closely. |

## Metadata

**Analog search scope:** `backend/app.py`, `backend/api`, `backend/services`, `backend/core`, `backend/tests`, `frontend/src`
**Files scanned:** 11
**Pattern extraction date:** 2026-07-05
