# Phase 24: Exportação Excel da Busca por SKU — Pattern Map

**Mapped:** 2026-06-15
**Files analyzed:** 5 (4 modified, 1 created)
**Analogs found:** 5 / 5

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `api/routes_search.py` | route + service | request-response (streaming) | `api/routes_search.py` lines 181–296 (`export_search_products`) | exact — same file, same xlsx-streaming tail |
| `frontend/src/api/client.ts` | service (HTTP client) | request-response | `frontend/src/api/client.ts` lines 105–140 (`exportSearch`) | exact — same file, same blob download pattern |
| `frontend/src/App.tsx` | component (page) | event-driven (user selection + async export) | `frontend/src/App.tsx` lines 634–646 (`toggleBrand`/`selectAllBrands`/`clearBrands`) + lines 911–913 (`handleCalculateShipping` stopPropagation) | role-match + data-flow-match |
| `frontend/src/App.css` | config (styles) | — | `frontend/src/App.css` lines 569–632 (`.stock-toggle`, `.btn-excel`) | role-match |
| `tests/test_export_cross_marketplace.py` | test | CRUD (endpoint unit tests) | `tests/test_relevance_gates.py` (class-based pytest, pure function import) + `tests/test_cross_marketplace_service.py` (TestClient import pattern) | role-match |

---

## Pattern Assignments

### `api/routes_search.py` — add `ExportItem`, `CrossMarketplaceExportRequest`, `POST /cross-marketplace/export`

**Analog:** `api/routes_search.py` lines 181–296 (`export_search_products`)

**Existing imports block** (lines 1–24) — all needed imports are already present:

```python
# lines 1-24 (verified in file read)
from typing import List, Optional
import io
import pandas as pd
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
```

**Existing Pydantic model pattern** (lines 75–81) — `CrossMarketplaceRequest` as the structural template:

```python
# lines 75-81 — use as structural template for CrossMarketplaceExportRequest
class CrossMarketplaceRequest(BaseModel):
    target_sku: str = Field(..., description="SKU base para referência.")
    search_query: Optional[str] = Field(None, description="Query estrita/específica.")
    broad_query: Optional[str] = Field(None, description="Query ampla para buscar volume.")
    min_score: float = Field(55.0, description="Match score mínimo.")
    zipcode: Optional[str] = Field(None, pattern=r"^\d{5}-?\d{3}$", description="CEP de destino")
```

**New models to add** (place after `CrossMarketplaceRequest`, before the first `@router.post`):

```python
# NEW — add after line 81
import re

FORMULA_CHARS_RE = re.compile(r'^[=+\-@]')

def _sanitize_cell(value: str) -> str:
    """Prepend single-quote to strings that start with a formula character."""
    if isinstance(value, str) and FORMULA_CHARS_RE.match(value):
        return "'" + value
    return value

class ExportItem(BaseModel):
    marketplace: str
    seller: str
    title: str
    price: float
    shipping_price: Optional[float] = None
    landed_price: float
    is_free_shipping: bool = False
    final_match_score: float = 0.0
    match_score: float = 0.0          # compat alias
    is_similar: bool = False
    url: str
    display_order: Optional[int] = Field(None, alias="_display_order")

    model_config = {"extra": "allow", "populate_by_name": True}

class CrossMarketplaceExportRequest(BaseModel):
    items: List[ExportItem] = Field(..., min_length=1, max_length=500)
    search_query: Optional[str] = None
    target_sku: str = Field(..., min_length=1)
```

**Xlsx-streaming pattern** (lines 274–296) — copy verbatim, omit the scraping steps (lines 186–272):

```python
# lines 274-296 — the ONLY part to copy; do NOT copy the engine_factory/gather calls above
output = io.BytesIO()
with pd.ExcelWriter(output, engine='openpyxl') as writer:
    df.to_excel(writer, index=False, sheet_name='Comparativo')
output.seek(0)

safe_query = "".join([c if c.isalnum() else "_" for c in request.query])
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
filename = f"busca_comparativa_{safe_query}_{timestamp}.xlsx"

headers = {
    'Content-Disposition': f'attachment; filename="{filename}"',
    'Access-Control-Expose-Headers': 'Content-Disposition'   # line 289 — REQUIRED for CORS
}

return StreamingResponse(
    output,
    headers=headers,
    media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
)
```

**New endpoint skeleton** (place after the existing `/cross-marketplace` endpoint):

```python
# NEW — POST /cross-marketplace/export
@router.post("/cross-marketplace/export", summary="Exporta busca por SKU em Excel")
async def export_cross_marketplace(request: CrossMarketplaceExportRequest):
    sorted_items = sorted(
        request.items,
        key=lambda i: i.display_order if i.display_order is not None else 0
    )

    rows = []
    for item in sorted_items:
        score = round(item.final_match_score or item.match_score)
        if item.shipping_price is None and not item.is_free_shipping:
            frete_display = "A calcular"
            total_display = item.price
        else:
            frete_display = 0.0 if item.is_free_shipping else item.shipping_price
            total_display = item.landed_price
        rows.append({
            "Plataforma":     _sanitize_cell(item.marketplace),
            "Vendedor":       _sanitize_cell(item.seller),
            "Título":         _sanitize_cell(item.title),
            "Preço":          item.price,
            "Frete":          frete_display,
            "Preço Total":    total_display,
            "Frete Grátis":   "Sim" if item.is_free_shipping else "Não",
            "Score de Match": score,
            "Similar":        "Sim" if item.is_similar else "Não",
            "URL":            item.url,
        })

    df = pd.DataFrame(rows)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Busca SKU')
    output.seek(0)

    query_token = request.search_query or request.target_sku
    safe_query = "".join(c if c.isalnum() else "_" for c in query_token)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"busca_sku_{safe_query}_{timestamp}.xlsx"

    return StreamingResponse(
        output,
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Access-Control-Expose-Headers': 'Content-Disposition',
        },
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
```

**Auth pattern:** inherited — `api_router = APIRouter(dependencies=[Depends(verify_api_key)])` at `api/__init__.py` line 23 covers all `/search/*` routes automatically. No `Depends(verify_api_key)` needed in the new endpoint decorator.

**Anti-pattern to avoid:** Lines 186–272 of `export_search_products` call `engine_factory.search_all_brands` and `asyncio.gather` to re-fetch product details. These MUST NOT appear in the new endpoint.

---

### `frontend/src/api/client.ts` — add `ApiClient.exportCrossMarketplace`

**Analog:** `frontend/src/api/client.ts` lines 105–140 (`exportSearch`)

**Pattern to copy** (lines 105–140) — direct clone, change endpoint URL and payload shape:

```typescript
// lines 105-140 — existing exportSearch (analog)
static async exportSearch(payload: { query: string; brands?: string[]; ... }) {
  const response = await fetch(`${API_BASE_URL}/search/export`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let errorMsg = `Export failed: ${response.status}`;
    try {
      const data = await response.json();
      if (data.detail) errorMsg = data.detail;
    } catch (e) {}
    throw new Error(errorMsg);
  }

  let filename = 'busca_comparativa.xlsx';
  const disposition = response.headers.get('content-disposition');
  if (disposition && disposition.includes('filename=')) {
    const matches = disposition.match(/filename="([^"]+)"/);
    if (matches && matches[1]) filename = matches[1];
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}
```

**New method to add** (place after `exportSearch`, before the Monitors section at line 144):

```typescript
// NEW — add after line 140
static async exportCrossMarketplace(payload: {
  items: any[];
  search_query?: string;
  target_sku: string;
}): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/search/cross-marketplace/export`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let errorMsg = `Export failed: ${response.status}`;
    try {
      const data = await response.json();
      if (data.detail) errorMsg = data.detail;
    } catch (_) {}
    throw new Error(errorMsg);
  }

  let filename = 'busca_sku.xlsx';
  const disposition = response.headers.get('content-disposition');
  if (disposition && disposition.includes('filename=')) {
    const matches = disposition.match(/filename="([^"]+)"/);
    if (matches && matches[1]) filename = matches[1];
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}
```

---

### `frontend/src/App.tsx` — modify `CrossMarketplacePage` (lines 882–1186)

**Analog 1 — selection state:** `toggleBrand`/`selectAllBrands`/`clearBrands` (lines 634–646)

```typescript
// lines 634-646 — selection pattern using array; new code uses Set<string>
const toggleBrand = (key: string) => {
  setSelectedBrands(prev =>
    prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
  );
};
const selectAllBrands = () => {
  setSelectedBrands(brands.map(b => b.brand_key));
};
const clearBrands = () => {
  setSelectedBrands([]);
};
```

**New state + helpers to add** at the top of `CrossMarketplacePage` (after line 887, alongside existing `useState` hooks):

```typescript
// NEW — add after existing useState hooks at ~line 887
const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
const [showExportDialog, setShowExportDialog] = useState(false);
const [exporting, setExporting] = useState(false);

const allItems: any[] = results?.results ?? [];

const toggleItem = (url: string) =>
  setSelectedItems(prev => {
    const next = new Set(prev);
    next.has(url) ? next.delete(url) : next.add(url);
    return next;
  });

const isAllSelected = allItems.length > 0 && allItems.every((i: any) => selectedItems.has(i.url));

const toggleSelectAll = () =>
  isAllSelected
    ? setSelectedItems(new Set())
    : setSelectedItems(new Set(allItems.map((i: any) => i.url)));
```

**Analog 2 — stopPropagation inside `<a>`:** `handleCalculateShipping` (lines 911–913)

```typescript
// lines 911-913 — proven stopPropagation pattern for interactive elements inside <a>
const handleCalculateShipping = async (e: React.MouseEvent, item: any, marketplace: string) => {
  e.preventDefault();
  e.stopPropagation();
  // ...
};
```

**New export handler** (add after `handleSearch` block ~line 984):

```typescript
// NEW
const handleExport = async (mode: 'all' | 'selected') => {
  setShowExportDialog(false);
  const itemsToExport = mode === 'all'
    ? allItems
    : allItems.filter((i: any) => selectedItems.has(i.url));

  setExporting(true);
  try {
    await ApiClient.exportCrossMarketplace({
      items: itemsToExport,
      search_query: results?.search_query,
      target_sku: targetSku,
    });
  } catch (err: any) {
    toast.error("Erro ao exportar: " + err.message);
  } finally {
    setExporting(false);
    // Do NOT clear selectedItems — per CONTEXT.md decision
  }
};
```

**Reset on new search** — add `setSelectedItems(new Set())` inside `handleSearch` alongside the existing `setResults(null)` at line 972:

```typescript
// line 972 existing:
setResults(null);
// ADD immediately after:
setSelectedItems(new Set());
```

**Analog 3 — SearchPage export button:** existing `.btn-excel` + `FileSpreadsheet` usage (App.tsx ~line 673–691, SearchPage):

```typescript
// lines 673-691 — export button + loading state pattern (SearchPage)
const handleExport = async () => {
  if (!query) return;
  setExporting(true);
  try {
    await ApiClient.exportSearch({ ... });
  } catch (err: any) {
    alert("Erro ao exportar: " + err.message);  // NOTE: new code uses toast.error instead
  } finally {
    setExporting(false);
  }
};
// button usage: className="btn btn-excel", icon <FileSpreadsheet size={16} />, loading: <RefreshCw className="animate-spin" />
```

**Toolbar JSX** — insert immediately after `{results.errors && ...}` block (after line 1070, before the grid `<div>` at line 1072):

```tsx
{/* NEW — results toolbar */}
{results && (
  <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '16px' }}>
    <label className={`stock-toggle${isAllSelected ? ' active' : ''}`}>
      <input type="checkbox" checked={isAllSelected} onChange={toggleSelectAll} />
      <span className="stock-toggle-box">
        {isAllSelected && <Check size={12} />}
      </span>
      Selecionar todos
    </label>
    <span className={`sku-export-counter${selectedItems.size > 0 ? ' has-selection' : ''}`}>
      {selectedItems.size} selecionado(s)
    </span>
    <div style={{ flex: 1 }} />
    <button
      className="btn btn-excel"
      onClick={() => setShowExportDialog(true)}
      disabled={exporting}
    >
      {exporting
        ? <><RefreshCw size={16} className="animate-spin" /> Exportando...</>
        : <><FileSpreadsheet size={16} /> Exportar Excel</>
      }
    </button>
  </div>
)}
```

**Card `<a>` modification** (line 1087) — add `position: 'relative'` and checkbox overlay as first child:

```tsx
// EXISTING <a> at line 1087 — add position relative:
<a
  key={`${marketplace}-${item.url || i}`}
  href={item.url}
  target="_blank"
  rel="noopener noreferrer"
  style={{
    position: 'relative',           // ADD THIS
    display: 'flex',
    // ... rest of existing styles, with background/border updated:
    background: selectedItems.has(item.url)
      ? 'rgba(16,185,129,0.07)'
      : item.is_buybox_winner ? 'rgba(16, 185, 129, 0.1)' : 'rgba(255,255,255,0.02)',
    border: `1px solid ${
      selectedItems.has(item.url)
        ? 'rgba(16,185,129,0.25)'
        : item.is_buybox_winner ? 'rgba(16, 185, 129, 0.3)' : 'rgba(255,255,255,0.1)'
    }`,
    // ... rest unchanged
  }}
>
  {/* NEW — checkbox overlay as first child */}
  <label
    className="card-select-checkbox"
    onClick={e => { e.preventDefault(); e.stopPropagation(); }}
  >
    <input
      type="checkbox"
      checked={selectedItems.has(item.url)}
      onChange={() => toggleItem(item.url)}
    />
    <span className="stock-toggle-box">
      {selectedItems.has(item.url) && <Check size={12} />}
    </span>
  </label>
  {/* ... rest of existing card children unchanged */}
```

**Export dialog JSX** — add at the end of `CrossMarketplacePage` return, just before the closing `</div>`:

```tsx
{/* NEW — export dialog */}
{showExportDialog && (
  <div className="modal-overlay" onClick={() => setShowExportDialog(false)}>
    <div className="modal-content export-dialog" onClick={e => e.stopPropagation()}>
      <h3>Exportar resultados</h3>
      <p className="export-dialog-subtitle">Escolha quais produtos incluir no arquivo Excel.</p>
      <div className="export-dialog-actions">
        <button className="btn btn-primary" onClick={() => handleExport('all')}>
          Todos
        </button>
        <button
          className="btn btn-excel"
          onClick={() => handleExport('selected')}
          disabled={selectedItems.size === 0}
          style={selectedItems.size === 0 ? { opacity: 0.4, cursor: 'not-allowed' } : undefined}
        >
          Apenas selecionados ({selectedItems.size})
        </button>
      </div>
      <button className="export-dialog-cancel" onClick={() => setShowExportDialog(false)}>
        Manter seleção
      </button>
    </div>
  </div>
)}
```

**Import check for `Check` icon** — verify line 1 of App.tsx imports. If `Check` is not already imported from `lucide-react`, add it to the existing lucide import line.

---

### `frontend/src/App.css` — add modal + checkbox + counter CSS

**Analog:** `frontend/src/App.css` lines 569–632 (`.stock-toggle`/`.stock-toggle-box`, `.btn-excel`)

**Existing `.stock-toggle-box`** (lines 591–601) — `.card-select-checkbox` reuses this class for the visual checkbox, so NO new box styles are needed; only the overlay container wrapper is new:

```css
/* lines 591-601 — existing, no change needed */
.stock-toggle-box {
  width: 18px;
  height: 18px;
  border: 1px solid rgba(148, 163, 184, 0.45);
  border-radius: 5px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: white;
  background: rgba(255, 255, 255, 0.04);
}

/* lines 609-611 — active state, no change needed */
.stock-toggle.active .stock-toggle-box {
  border-color: var(--success);
  background: var(--success);
}
```

**CSS block to append to App.css** (Wave 0 gap — `.modal-overlay` does not exist yet):

```css
/* -----------------------------------------------------------------------
   Phase 24 — Export Dialog + Card Selection
   ----------------------------------------------------------------------- */

/* Modal overlay */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: rgba(30, 41, 59, 0.95);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
  max-width: 520px;
  width: 90%;
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.4);
}

.export-dialog { max-width: 420px; }

.export-dialog-subtitle {
  font-size: 0.875rem;
  color: var(--text-muted);
  margin: 8px 0 16px 0;
}

.export-dialog-actions {
  display: flex;
  gap: 8px;
  flex-direction: column;
}

.export-dialog-cancel {
  display: block;
  margin: 16px auto 0;
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 0.8125rem;
  cursor: pointer;
  text-decoration: underline;
}

.export-dialog-cancel:hover { color: var(--text-main); }

/* Card checkbox overlay */
.card-select-checkbox {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 2;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.card-select-checkbox input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

/* Selection counter */
.sku-export-counter {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text-muted);
  transition: color 0.2s;
}

.sku-export-counter.has-selection { color: var(--success); }
```

---

### `tests/test_export_cross_marketplace.py` — CREATE

**Analog 1 — file structure:** `tests/test_relevance_gates.py` (class-based pytest, pure function import pattern, lines 1–16)

```python
# tests/test_relevance_gates.py lines 1-16 — structural template
"""
Testes da lógica pura do motor de relevância (services/relevance_gates.py).
"""
from types import SimpleNamespace
import pytest
from services import relevance_gates as rg

class TestFinalMatchScore:
    def test_strong_text_dominates(self):
        assert rg.compute_final_match_score(95.0, 30.0) == 95.0
```

**Analog 2 — FakeEngine/dependency-override pattern:** `tests/test_cross_marketplace_service.py` lines 1–60 (asyncio.run for async functions, monkeypatching)

```python
# tests/test_cross_marketplace_service.py lines 1-35 — dependency override template
import asyncio
from config import relevance_settings
from services.cross_marketplace_service import CrossMarketplaceService
```

**App entry point verified:** `app.py` line 68 — `app = FastAPI(...)`. TestClient import: `from app import app`.

**New test file skeleton:**

```python
# tests/test_export_cross_marketplace.py
"""
Testes unitários do endpoint POST /search/cross-marketplace/export.

Estratégia:
  - TestClient síncrono (fastapi.testclient.TestClient) importa a app de app.py.
  - verify_api_key sobrescrito via app.dependency_overrides para aceitar qualquer key.
  - Resposta .content lida como io.BytesIO e validada com openpyxl.load_workbook().
  - Alternativa (se app.py tiver side-effects que impeçam import): testar _sanitize_cell
    e _build_row como funções puras diretamente (sem TestClient).
"""
import io
import pytest
from fastapi.testclient import TestClient
from app import app
from api.auth import verify_api_key
import openpyxl

# Override auth dependency
app.dependency_overrides[verify_api_key] = lambda: "test-key"
client = TestClient(app)

ITEM_BASE = {
    "marketplace": "Mercado Livre",
    "seller": "Vendedor Teste",
    "title": "Polo Piquet Aramis",
    "price": 199.90,
    "shipping_price": 15.00,
    "landed_price": 214.90,
    "is_free_shipping": False,
    "final_match_score": 87.4,
    "match_score": 0.0,
    "is_similar": False,
    "url": "https://example.com/produto",
    "_display_order": 0,
}

class TestExportEndpoint:
    def test_happy_path(self):
        response = client.post(
            "/search/cross-marketplace/export",
            json={"items": [ITEM_BASE], "target_sku": "ML.05.0326046"},
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 200
        wb = openpyxl.load_workbook(io.BytesIO(response.content))
        ws = wb["Busca SKU"]
        headers = [ws.cell(1, c).value for c in range(1, 11)]
        assert headers == [
            "Plataforma", "Vendedor", "Título", "Preço", "Frete",
            "Preço Total", "Frete Grátis", "Score de Match", "Similar", "URL"
        ]

    def test_null_shipping(self):
        item = {**ITEM_BASE, "shipping_price": None, "is_free_shipping": False, "_display_order": 0}
        response = client.post(
            "/search/cross-marketplace/export",
            json={"items": [item], "target_sku": "TEST"},
            headers={"X-API-Key": "test-key"},
        )
        wb = openpyxl.load_workbook(io.BytesIO(response.content))
        ws = wb["Busca SKU"]
        assert ws.cell(2, 5).value == "A calcular"   # Frete col
        assert ws.cell(2, 6).value == item["price"]  # Preço Total == price

    def test_empty_items_400(self):
        response = client.post(
            "/search/cross-marketplace/export",
            json={"items": [], "target_sku": "TEST"},
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 422  # Pydantic min_length=1 returns 422

    def test_auth(self):
        # Temporarily remove override to test real auth
        app.dependency_overrides.pop(verify_api_key, None)
        response = client.post(
            "/search/cross-marketplace/export",
            json={"items": [ITEM_BASE], "target_sku": "TEST"},
        )
        assert response.status_code == 403
        app.dependency_overrides[verify_api_key] = lambda: "test-key"  # restore
```

---

## Shared Patterns

### Authentication
**Source:** `api/__init__.py` line 23
**Apply to:** all `/search/*` routes automatically — no action needed per endpoint
```python
api_router = APIRouter(dependencies=[Depends(verify_api_key)])
```

### Blob Download (frontend)
**Source:** `frontend/src/api/client.ts` lines 131–139
**Apply to:** `ApiClient.exportCrossMarketplace`
```typescript
const blob = await response.blob();
const url = window.URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = filename;
document.body.appendChild(a);
a.click();
window.URL.revokeObjectURL(url);
document.body.removeChild(a);
```

### CORS Header for Content-Disposition
**Source:** `api/routes_search.py` line 289
**Apply to:** `export_cross_marketplace` StreamingResponse headers — without this, the browser cannot read the filename
```python
'Access-Control-Expose-Headers': 'Content-Disposition'
```

### stopPropagation inside `<a>` card
**Source:** `frontend/src/App.tsx` lines 911–913
**Apply to:** every interactive element added inside the card `<a>` tag (checkbox label)
```typescript
e.preventDefault();
e.stopPropagation();
// Both are required — preventDefault cancels <a> navigation; stopPropagation stops bubbling
```

### Toast error (not `alert`)
**Source:** `frontend/src/App.tsx` lines 629, 664 (SearchPage uses `toast.error`)
**Apply to:** `handleExport` in CrossMarketplacePage — use `toast.error(...)` NOT `alert(...)`
```typescript
toast.error("Erro ao exportar: " + err.message);
```

---

## No Analog Found

All files have analogs. No entries.

---

## Critical Constraints Summary (for planner)

1. `export_search_products` re-scrapes products (lines 186–272) — copy ONLY the xlsx tail (lines 274–296), not the engine calls.
2. `_display_order` starts with `_` — Pydantic v2 treats it as private; use `Field(None, alias="_display_order")` with `model_config = {"populate_by_name": True}`.
3. Modal `.modal-overlay` / `.modal-content` CSS does not exist in App.css today — must be Wave 0.
4. `Check` icon from lucide-react may not be imported in App.tsx — verify before using.
5. App entry point: `from app import app` (file is `app.py` line 68, not `main.py`).
6. Selection must NOT be cleared after export completes (per CONTEXT.md decision).
7. `selectedItems.size === 0` disables "Apenas selecionados" — use `.size` (Set), not `.length` (Array).

---

## Metadata

**Analog search scope:** `api/`, `frontend/src/`, `tests/`
**Files scanned:** 8 source files read directly
**Pattern extraction date:** 2026-06-15
