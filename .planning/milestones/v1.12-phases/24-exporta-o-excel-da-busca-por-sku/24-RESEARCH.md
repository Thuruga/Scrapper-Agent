# Phase 24: Exportação Excel da Busca por SKU — Research

**Researched:** 2026-06-15
**Domain:** FastAPI endpoint (xlsx streaming) + React 19 selection UI + blob download
**Confidence:** HIGH — all findings verified directly against codebase files read in this session

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Checkbox posicionado como overlay no canto superior esquerdo do card; usar `stopPropagation`/`preventDefault` para que marcar/desmarcar NÃO dispare a navegação do link `<a>` do card.
- Estado inicial ao carregar resultados: nada selecionado (opt-in do usuário).
- "Selecionar todos": um único toggle global no header dos resultados (abrange todos os marketplaces).
- Exibir contador "N selecionado(s)" próximo ao botão de exportar.
- Botão de exportar no header dos resultados, reutilizando o estilo existente `.btn-excel` + ícone `FileSpreadsheet`.
- Diálogo com duas opções: "Todos" (sempre habilitado) e "Apenas selecionados" (desabilitado quando 0 selecionados).
- Após a exportação concluir: manter a seleção intacta (não limpar).
- Feedback durante a exportação: spinner no botão + toast de erro via `sonner`; sucesso = download do navegador.
- Cabeçalhos das colunas em Português: Plataforma, Vendedor, Título, Preço, Frete, Preço Total, Frete Grátis, Score de Match, Similar, URL.
- Booleanos renderizados como "Sim" / "Não" (Frete Grátis, Similar).
- Frete não calculado (`shipping_price === null`): Frete = "A calcular"; Preço Total = preço do produto (nunca um 0 enganoso).
- Score de match como inteiro arredondado (ex.: 87).
- Ordem das linhas: preservar a ordem exibida na tela (agrupada por marketplace, `_display_order`) — fidelidade exigida pelo EXPORT-05.
- Payload: frontend envia os objetos de item exibidos completos; o backend seleciona/mapeia as 10 colunas.
- Token do nome do arquivo: `search_query` com fallback para `target_sku`. Padrão: `busca_sku_<query>_<YYYYMMDD_HHMMSS>.xlsx`.
- Array de itens vazio: backend retorna HTTP 400.
- Nome da planilha (sheet): "Busca SKU".

### Claude's Discretion

- Estrutura exata do modelo Pydantic da requisição (nome dos campos do item), desde que cubra as 10 colunas.
- Detalhes de estilo do checkbox/diálogo dentro das convenções existentes (`.stock-toggle`, glass tokens) — definidos no UI-SPEC.

### Deferred Ideas (OUT OF SCOPE)

- Histórico de exportações (`EXPORT-HIST-01`) — Future Requirement, fora do v1.12.
- Unificação com o export por marca (`EXPORT-UNIFY-01`) — Future Requirement, fora do v1.12.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EXPORT-01 | Checkbox por card para selecionar/desselecionar individualmente | UI-SPEC markup + `stopPropagation` pattern verified in `handleCalculateShipping` |
| EXPORT-02 | Toggle global "selecionar todos" | `useState<Set<string>>` pattern; mirrors `toggleBrand`/`selectAllBrands` already in App.tsx |
| EXPORT-03 | Diálogo de exportação com "Todos" / "Apenas selecionados" | Modal CSS from UI-SPEC; not yet in App.css — must be added as Wave 0 gap |
| EXPORT-04 | Arquivo .xlsx com 10 colunas PT-BR corretas | `io.BytesIO` + `pd.ExcelWriter(engine='openpyxl')` pattern exists in `/search/export` |
| EXPORT-05 | Conteúdo reflete exatamente o que está na tela (sem re-busca) | Endpoint receives items in body; no search/scrape call path |
| EXPORT-06 | Download com nome significativo derivado do SKU/query + timestamp | `Content-Disposition` + blob pattern exists in `ApiClient.exportSearch` |
</phase_requirements>

---

## Summary

Phase 24 adds selection + export-to-xlsx to the existing `CrossMarketplacePage`. The scope is narrow and well-bounded: three additive concerns that do not touch existing search logic.

**Backend:** A new `POST /search/cross-marketplace/export` endpoint receives an already-computed items array in its request body, maps the 10 fields to Portuguese column headers, and streams back an `.xlsx` file. It never calls any search engine or scraper. The entire Excel-writing pattern is a direct copy of the existing `export_search_products` function in `api/routes_search.py` (lines 274–296), minus the scraping steps. The pandas + openpyxl stack is already installed and version-verified.

**Frontend:** `CrossMarketplacePage` gains three pieces of state: `selectedItems: Set<string>`, `showExportDialog: boolean`, and `exporting: boolean`. Selection is keyed on `item.url` (already used as the React `key` on each card). The checkbox, toolbar, dialog, and blob-download code follow patterns established in the codebase — nothing architecturally new. The only genuinely new CSS is the modal overlay/content block, which is fully specified in the UI-SPEC.

**Security:** The endpoint accepts a client-supplied items array but does not execute any of those values as code or re-fetch URLs. The primary risks are formula injection in Excel cells and oversized payloads. Both are mitigatable with cheap, targeted defenses.

**Primary recommendation:** Copy the xlsx-streaming tail of `export_search_products` verbatim; write a new Pydantic model `CrossMarketplaceExportRequest`; in the frontend, layer selection state and dialog into `CrossMarketplacePage` following the UI-SPEC exactly.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Selection state (which items are checked) | Frontend (client) | — | Ephemeral UI state; lives in React `useState`; no persistence needed |
| Select-all toggle logic | Frontend (client) | — | Pure derived computation over the items array already in React state |
| Export dialog (modal) | Frontend (client) | — | Pure UI interaction; no server round-trip until user confirms |
| Excel file generation | API / Backend | — | pandas + openpyxl already on server; no new frontend dependency needed (explicit Out of Scope) |
| Filename derivation | API / Backend | — | Backend owns the timestamp; Content-Disposition header carries filename to browser |
| Blob download triggering | Frontend (client) | — | Browser-level DOM trick; client.ts already has the pattern |
| Authentication | API / Backend | — | `Depends(verify_api_key)` inherited from `api_router` at module level |

---

## Standard Stack

### Core (already installed — no new installs required)

| Library | Version (verified) | Purpose | Provenance |
|---------|--------------------|---------|------------|
| pandas | 2.3.3 | DataFrame → xlsx serialization | [VERIFIED: runtime `import pandas`] |
| openpyxl | 3.1.5 | xlsx engine for `pd.ExcelWriter` | [VERIFIED: runtime `import openpyxl`] |
| FastAPI | 0.132.0 | HTTP framework + Pydantic integration | [VERIFIED: runtime `import fastapi`] |
| Pydantic v2 | (bundled w/ FastAPI) | Request model validation | [VERIFIED: requirements.txt `pydantic>=2.0`] |
| React 19 + TypeScript | — | Frontend framework | [VERIFIED: read frontend/src/App.tsx] |
| lucide-react | — | Icons (FileSpreadsheet, RefreshCw, Check) | [VERIFIED: read App.tsx imports] |
| sonner | — | Toast notifications | [VERIFIED: read App.tsx imports] |

**No new packages to install in this phase.** The Excel generation and download infrastructure is 100% reuse.

---

## Package Legitimacy Audit

**No new packages are introduced in this phase.** All libraries (pandas, openpyxl, FastAPI, Pydantic, React, lucide-react, sonner) were already present as project dependencies before this phase began. No audit action required.

---

## Architecture Patterns

### System Architecture Diagram

```
User clicks "Exportar Excel" in CrossMarketplacePage
  │
  ▼
Export Dialog opens (modal, client-side only)
  │
  ├─ "Todos" → itemsToExport = results.results (all)
  └─ "Apenas selecionados" → itemsToExport = results.results.filter(i => selectedItems.has(i.url))
  │
  ▼
ApiClient.exportCrossMarketplace({ items: itemsToExport, search_query, target_sku })
  │  POST /search/cross-marketplace/export
  │  X-API-Key header (inherited from existing ApiClient pattern)
  │
  ▼
FastAPI endpoint (api/routes_search.py)
  ├─ Pydantic validates request (min 1 item, else 400)
  ├─ Formula-injection sanitization on string fields
  ├─ Build DataFrame: sort by _display_order, map 10 fields → PT column names
  └─ pd.ExcelWriter (openpyxl) → io.BytesIO → StreamingResponse
       Content-Disposition: attachment; filename="busca_sku_<query>_<ts>.xlsx"
       Access-Control-Expose-Headers: Content-Disposition
  │
  ▼
Browser receives blob
  └─ client.ts reads Content-Disposition filename
  └─ Creates object URL → hidden <a> → click → revoke
  └─ File saved to user's Downloads folder
```

### Recommended Project Structure

No new files or folders needed. All changes are additive within:

```
api/
└── routes_search.py          # +1 Pydantic model, +1 endpoint function

frontend/src/
├── api/client.ts             # +1 method: exportCrossMarketplace
├── App.tsx                   # CrossMarketplacePage: +3 useState hooks, +toolbar, +dialog, +checkbox overlays
└── App.css                   # +modal-overlay, +modal-content, +export-dialog, +card-select-checkbox, +sku-export-counter
```

### Pattern 1: Pydantic Model for Client-Supplied Items

**What:** Accept an open-ish item shape without over-specifying. Use `Optional` for fields that may be null (shipping), and rely on Python `float`/`int`/`str` coercion from JSON.

**When to use:** When the frontend sends display-layer objects that include fields the backend doesn't need — simply ignore extras and only declare what the Excel mapping requires.

**Recommended model:**

```python
# Source: mirrors CrossMarketplaceRequest pattern in api/routes_search.py
from typing import List, Optional
from pydantic import BaseModel, Field

class ExportItem(BaseModel):
    marketplace: str
    seller: str
    title: str
    price: float
    shipping_price: Optional[float] = None   # None → "A calcular"
    landed_price: float
    is_free_shipping: bool = False
    final_match_score: float = 0.0           # preferred field
    match_score: float = 0.0                 # compat alias
    is_similar: bool = False
    url: str
    # Extra fields the frontend sends (image_url, _display_order, etc.)
    # are silently ignored by Pydantic v2 unless model_config forbids extras.
    _display_order: Optional[int] = None

    model_config = {"extra": "allow"}        # accept extra frontend fields without error

class CrossMarketplaceExportRequest(BaseModel):
    items: List[ExportItem] = Field(..., min_length=1)   # 400 if empty
    search_query: Optional[str] = None
    target_sku: str = Field(..., min_length=1)
```

**Key choices:**
- `extra = "allow"` avoids validation errors if the frontend sends `image_url`, `text_match_score`, etc.
- `min_length=1` on `items` makes Pydantic itself return the 400 (no manual check needed).
- Both `final_match_score` and `match_score` are declared; the mapping logic uses `final_match_score` with `match_score` as fallback (matching `build_formatted_results`'s dual-field convention). [VERIFIED: read `services/relevance_gates.py` lines 267-270]

### Pattern 2: Excel Column Mapping with Null-Shipping and Boolean Translation

**What:** Build a list of dicts in the exact PT-BR column order, then pass to `pd.DataFrame`. Sort by `_display_order` first.

```python
# Source: mirrors export_search_products pattern (api/routes_search.py lines 274-296)
import io, re
from datetime import datetime
import pandas as pd
from fastapi.responses import StreamingResponse

FORMULA_PREFIX_RE = re.compile(r'^[=+\-@]')

def _sanitize_cell(value: str) -> str:
    """Prepend single-quote to strings that start with a formula character."""
    if isinstance(value, str) and FORMULA_PREFIX_RE.match(value):
        return "'" + value
    return value

def _build_row(item: ExportItem) -> dict:
    score = round(item.final_match_score or item.match_score)
    shipping_display = (
        "A calcular"
        if item.shipping_price is None and not item.is_free_shipping
        else (0.0 if item.is_free_shipping else item.shipping_price)
    )
    landed_display = (
        item.price
        if item.shipping_price is None and not item.is_free_shipping
        else item.landed_price
    )
    return {
        "Plataforma":      _sanitize_cell(item.marketplace),
        "Vendedor":        _sanitize_cell(item.seller),
        "Título":          _sanitize_cell(item.title),
        "Preço":           item.price,
        "Frete":           shipping_display,
        "Preço Total":     landed_display,
        "Frete Grátis":    "Sim" if item.is_free_shipping else "Não",
        "Score de Match":  score,
        "Similar":         "Sim" if item.is_similar else "Não",
        "URL":             item.url,   # URLs are safe (start with http)
    }
```

**Null-shipping rule verified against CONTEXT.md decisions:**
- `shipping_price is None` AND `is_free_shipping = False` → Frete = "A calcular", Preço Total = `price` only
- `is_free_shipping = True` → Frete = 0 (grátis), Preço Total = `landed_price`
- `shipping_price` is a number → Frete = that number, Preço Total = `landed_price`

### Pattern 3: StreamingResponse (exact reuse of existing pattern)

```python
# Source: api/routes_search.py lines 274-296 [VERIFIED: file read]
sorted_items = sorted(request.items, key=lambda i: getattr(i, '_display_order', 0) or 0)
rows = [_build_row(item) for item in sorted_items]
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

### Pattern 4: Frontend — `exportCrossMarketplace` in client.ts

**What:** Direct clone of `exportSearch` (lines 105–140 of client.ts) with the new endpoint and a different payload shape.

```typescript
// Source: mirrors ApiClient.exportSearch pattern (frontend/src/api/client.ts lines 105-140) [VERIFIED: file read]
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

### Pattern 5: Selection State in CrossMarketplacePage

**What:** Three new `useState` hooks added at the top of `CrossMarketplacePage`. Reset `selectedItems` when a new search clears results.

```typescript
// Source: mirrors toggleBrand/selectAllBrands/clearBrands pattern (App.tsx lines 634-646) [VERIFIED: file read]
const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
const [showExportDialog, setShowExportDialog] = useState(false);
const [exporting, setExporting] = useState(false);

// Derive allItems from results for convenience
const allItems: any[] = results?.results ?? [];

const toggleItem = (url: string) =>
  setSelectedItems(prev => {
    const next = new Set(prev);
    next.has(url) ? next.delete(url) : next.add(url);
    return next;
  });

const isAllSelected = allItems.length > 0 && allItems.every(i => selectedItems.has(i.url));

const toggleSelectAll = () =>
  isAllSelected
    ? setSelectedItems(new Set())
    : setSelectedItems(new Set(allItems.map((i: any) => i.url)));

// In handleSearch: setResults(null) clears the results and selectedItems resets in useEffect or via separate setSelectedItems(new Set()) call
```

**Reset on new search:** add `setSelectedItems(new Set())` alongside `setResults(null)` in `handleSearch`. [VERIFIED: App.tsx line 972: `setResults(null)` is already there]

### Pattern 6: Checkbox Overlay Inside `<a>` Card

**What:** The `<a>` card currently has no `position: relative`. This must be added inline or via class so the absolute-positioned checkbox overlay works.

```tsx
// Source: UI-SPEC Component Inventory §1 [VERIFIED: read 24-UI-SPEC.md]
// The <a> element at App.tsx ~line 1087 needs: style={{ ...existing, position: 'relative' }}
// The checkbox is added as the FIRST child:
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
```

**stopPropagation contract:** The `onClick` on the `<label>` calls both `preventDefault()` (stops `<a>` navigation) and `stopPropagation()` (prevents event from bubbling to the `<a>`). This exact pattern is already used by `handleCalculateShipping` on the "Calcular Frete" button inside the same card (App.tsx line 911). [VERIFIED: file read]

### Pattern 7: Selected Card Visual State

When `selectedItems.has(item.url)`, the card's inline `background` and `border` change:

```typescript
// From UI-SPEC Color §Card selected state
background: selectedItems.has(item.url)
  ? 'rgba(16,185,129,0.07)'
  : item.is_buybox_winner ? 'rgba(16, 185, 129, 0.1)' : 'rgba(255,255,255,0.02)',
border: `1px solid ${
  selectedItems.has(item.url)
    ? 'rgba(16,185,129,0.25)'
    : item.is_buybox_winner ? 'rgba(16, 185, 129, 0.3)' : 'rgba(255,255,255,0.1)'
}`,
```

Note: selected state uses `0.07`/`0.25` while buybox winner uses `0.1`/`0.3`, making them visually distinct. [VERIFIED: UI-SPEC Color table]

### Pattern 8: Export Handler in CrossMarketplacePage

```typescript
const handleExport = async (mode: 'all' | 'selected') => {
  setShowExportDialog(false);
  const itemsToExport = mode === 'all'
    ? allItems
    : allItems.filter((i: any) => selectedItems.has(i.url));

  setExporting(true);
  try {
    await ApiClient.exportCrossMarketplace({
      items: itemsToExport,
      search_query: results?.search_query,  // present if backend echoes it
      target_sku: targetSku,
    });
  } catch (err: any) {
    toast.error("Erro ao exportar: " + err.message);
  } finally {
    setExporting(false);
    // selectedItems is NOT cleared (per CONTEXT.md)
  }
};
```

### Anti-Patterns to Avoid

- **Re-fetching in the export endpoint:** `POST /search/cross-marketplace/export` MUST NOT call `cross_marketplace_service`, `engine_factory`, or any scraper. It only processes the items it receives. The existing `/search/export` endpoint does re-fetch — do not copy that flow. [VERIFIED: CONTEXT.md + routes_search.py read]
- **Clearing selection after export:** Selection must remain after export completes. Do NOT call `setSelectedItems(new Set())` in the export finally block.
- **Dispatching `onChange` on the hidden `<input>`:** The `<label onClick>` pattern already triggers the checkbox. Do not also attach an `onClick` to the `<input>` or you will fire `toggleItem` twice.
- **Hardcoding hex colors in TSX:** Use `var(--success)`, `var(--text-muted)` etc. Do not hardcode `#10b981`.
- **Forgetting `Access-Control-Expose-Headers`:** Without this header, the browser's CORS policy hides `Content-Disposition` from `response.headers.get(...)` in `client.ts`. The existing pattern includes it. [VERIFIED: routes_search.py line 289]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| xlsx file generation | Custom binary xlsx writer | `pd.DataFrame.to_excel(engine='openpyxl')` | Excel format is complex; openpyxl handles cell types, encoding, sheets |
| Filename sanitization | Custom regex stripping | `"".join(c if c.isalnum() else "_" for c in query)` | Exact pattern already in `export_search_products` (routes_search.py line 283); consistent |
| Blob download | `window.location.href = url` or `XMLHttpRequest` | `fetch → blob() → createObjectURL → <a>.click()` | Allows reading headers (filename), handles non-2xx properly, already proven in `exportSearch` |
| Modal/dialog | Browser `window.confirm` or `alert` | Inline React modal with `.modal-overlay` CSS | The UI-SPEC specifies exact markup/CSS; keep it consistent with the glass design system |
| Formula injection protection | Scanning all fields | Simple `_sanitize_cell` for string fields only (prefix `'`) | Numeric fields (price, score) are never strings; only `marketplace`, `seller`, `title`, `url` need sanitization |

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (inherited) | `Depends(verify_api_key)` via `api_router` — already enforced for all `/search/*` routes [VERIFIED: api/__init__.py line 23] |
| V3 Session Management | no | API key only; no session tokens |
| V4 Access Control | no | Internal tool; single-tenant; all authenticated users have the same access level |
| V5 Input Validation | yes | Pydantic `min_length=1` on `items` list; `Optional[float]` for shipping; string field length is implicitly bounded by Pydantic's max JSON parse |
| V6 Cryptography | no | No encryption/hashing in this feature |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation | Applied Here |
|---------|--------|---------------------|--------------|
| Formula injection (CSV/xlsx) | Tampering | Prepend `'` to cells starting with `= + - @` | `_sanitize_cell()` on `marketplace`, `seller`, `title` |
| SSRF via client-supplied URLs | Tampering | N/A — endpoint does NOT fetch any URL | Not applicable (by design: no re-scraping) |
| Oversized payload (DoS) | Denial of Service | Pydantic + FastAPI's max request body (default: unlimited) | Mitigate: add `max_length=500` to the `items` list field in `CrossMarketplaceExportRequest` — 500 items × ~500 bytes each ≈ 250 KB, well within memory tolerance |
| Unauthenticated access | Elevation of Privilege | `X-API-Key` header validation | Inherited from `api_router`; no additional work needed |
| Data exfiltration of other users' data | Information Disclosure | N/A — tool is single-tenant internal; no user isolation model | Not applicable for this project scope |

**Concrete mitigations the plan must include:**

1. `items: List[ExportItem] = Field(..., min_length=1, max_length=500)` — bounds the payload size at the Pydantic layer.
2. `_sanitize_cell(value: str) -> str` — prepend `'` to values starting with `=`, `+`, `-`, `@` before writing to DataFrame. Apply to `marketplace`, `seller`, `title` only (numeric fields and URL are safe by type or structure).
3. No additional CORS changes needed — endpoint shares the same FastAPI CORS config as all other `/search/*` routes.

---

## Common Pitfalls

### Pitfall 1: `_display_order` is Not Always Present on the Item Object

**What goes wrong:** The `_display_order` field is assigned in `withDisplayOrder()` (App.tsx lines 889–898), a function called after search returns. But if the item was loaded from history (`getHistoryDetail`), the field may already be present. Either way, sorting in the backend must treat `None` gracefully.

**Why it happens:** `build_formatted_results` does not set `_display_order` — the frontend adds it client-side.

**How to avoid:** In `ExportItem`, declare `_display_order: Optional[int] = None`. In the sort key: `key=lambda i: getattr(i, '_display_order', None) or 0`. Also set `model_config = {"extra": "allow"}` so the field is accepted even though it starts with `_` (Pydantic v2 treats `_` prefixed fields as private by default unless explicitly declared).

**Warning signs:** If `_display_order` is missing from the exported rows and the sort produces wrong order, check whether the field is being passed in the request body and whether Pydantic is stripping it.

**Workaround:** Alternatively, declare it explicitly as `display_order: Optional[int] = Field(None, alias="_display_order")` with `model_config = {"populate_by_name": True}`. This is cleaner and avoids the private-field ambiguity.

### Pitfall 2: `<a>` Card Anchor Navigation Fires on Checkbox Click

**What goes wrong:** Clicking the checkbox label triggers the `<a>` href, opening the product URL in a new tab AND toggling the checkbox. The user experience is broken.

**Why it happens:** The checkbox label is a child of the `<a>` tag. Any click event inside an `<a>` triggers navigation unless explicitly cancelled.

**How to avoid:** The `onClick` handler on the `<label>` must call both `e.preventDefault()` AND `e.stopPropagation()`. **Both are required.** `stopPropagation` alone does not prevent `<a>` navigation in all browsers when the click originates inside it; `preventDefault` is the reliable anchor-navigation canceller. The pattern is already proven in `handleCalculateShipping` (App.tsx line 911-913). [VERIFIED: file read]

**Warning signs:** During testing, if clicking a checkbox opens a browser tab, the `preventDefault` is missing or on the wrong element.

### Pitfall 3: `Content-Disposition` Header Hidden by CORS

**What goes wrong:** `response.headers.get('content-disposition')` returns `null` in the browser even though the server is sending the header. The fallback filename is used instead of the meaningful one.

**Why it happens:** CORS hides non-safelisted response headers by default. `Content-Disposition` is not a safelist header. Without `Access-Control-Expose-Headers: Content-Disposition`, the browser JavaScript cannot read it.

**How to avoid:** Include `'Access-Control-Expose-Headers': 'Content-Disposition'` in the StreamingResponse headers. This is already done in the existing `export_search_products` endpoint (routes_search.py line 289) — copy it exactly. [VERIFIED: file read]

**Warning signs:** File downloads as `busca_sku.xlsx` instead of `busca_sku_polo_piquet_aramis_20260615_143022.xlsx`.

### Pitfall 4: Pydantic v2 Private Field Stripping for `_display_order`

**What goes wrong:** Pydantic v2 treats attributes starting with `_` as private by default and does not include them in the model's field schema. Sending `_display_order` in the JSON body results in it being silently dropped rather than validated/used.

**Why it happens:** Pydantic v2 reserves `_` prefix for private attributes and model internals.

**How to avoid:** Use an explicit alias: `display_order: Optional[int] = Field(None, alias="_display_order")` with `model_config = {"populate_by_name": True, "extra": "allow"}`. This allows the frontend to continue sending `_display_order` without changes, while Pydantic correctly maps it.

**Warning signs:** Sorting is random/wrong in the output even though the frontend sends `_display_order`.

### Pitfall 5: `modal-overlay` click-through (modal closes when clicking content)

**What goes wrong:** Clicking inside the modal content area triggers the overlay's `onClick={closeDialog}`, immediately closing the modal.

**Why it happens:** Click events bubble from modal content → overlay.

**How to avoid:** The modal content `<div>` must call `e.stopPropagation()` on its `onClick`. The UI-SPEC already specifies this: `onClick={e => e.stopPropagation()}` on `.modal-content`. [VERIFIED: read 24-UI-SPEC.md lines 201-202]

---

## Code Examples

### Full Endpoint Skeleton

```python
# api/routes_search.py — new endpoint, placed after /cross-marketplace
import re
from typing import List, Optional
from pydantic import BaseModel, Field

FORMULA_CHARS_RE = re.compile(r'^[=+\-@]')

def _sanitize_cell(value: str) -> str:
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
    match_score: float = 0.0
    is_similar: bool = False
    url: str
    display_order: Optional[int] = Field(None, alias="_display_order")

    model_config = {"extra": "allow", "populate_by_name": True}

class CrossMarketplaceExportRequest(BaseModel):
    items: List[ExportItem] = Field(..., min_length=1, max_length=500)
    search_query: Optional[str] = None
    target_sku: str = Field(..., min_length=1)

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

### Modal CSS Block (Wave 0 — must be added to App.css)

```css
/* Source: 24-UI-SPEC.md Component Inventory §3 [VERIFIED: file read] */
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

.sku-export-counter {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text-muted);
  transition: color 0.2s;
}

.sku-export-counter.has-selection { color: var(--success); }
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Re-executing search in `/search/export` | Receive pre-computed items in body (this phase) | Eliminates scraping latency; export is instant |
| Browser `alert()` for export errors | `sonner` `toast.error()` | Non-blocking, matches rest of codebase |

**Deprecated/outdated:**
- Using `window.alert()` for export errors: `SearchPage.handleExport` (App.tsx ~line 687) still uses `alert()` — this phase uses `toast.error()` instead (per CONTEXT.md). The old SearchPage pattern is not a template here.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | none (default discovery) — `tests/` directory, `test_*.py` files |
| Quick run command | `python -m pytest tests/test_export_cross_marketplace.py -x -q` |
| Full suite command | `python -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXPORT-01 | Checkbox per card renders; stopPropagation works | manual (UI) | — (DOM interaction, no backend) | N/A |
| EXPORT-02 | Select-all toggles all items | manual (UI) | — | N/A |
| EXPORT-03 | Dialog shows; "Apenas selecionados" disabled at 0 | manual (UI) | — | N/A |
| EXPORT-04 | POST /cross-marketplace/export returns valid .xlsx with 10 PT columns and correct values | unit (pytest) | `python -m pytest tests/test_export_cross_marketplace.py::TestExportEndpoint::test_happy_path -x` | ❌ Wave 0 |
| EXPORT-04 | null shipping_price → Frete="A calcular", Preço Total=price | unit (pytest) | `python -m pytest tests/test_export_cross_marketplace.py::TestExportEndpoint::test_null_shipping -x` | ❌ Wave 0 |
| EXPORT-04 | Boolean fields render as "Sim"/"Não" | unit (pytest) | `python -m pytest tests/test_export_cross_marketplace.py::TestExportEndpoint::test_boolean_mapping -x` | ❌ Wave 0 |
| EXPORT-04 | Score de Match is integer (round) | unit (pytest) | `python -m pytest tests/test_export_cross_marketplace.py::TestExportEndpoint::test_score_rounding -x` | ❌ Wave 0 |
| EXPORT-04 | Formula injection: cells starting with `=` are sanitized | unit (pytest) | `python -m pytest tests/test_export_cross_marketplace.py::TestExportEndpoint::test_formula_injection -x` | ❌ Wave 0 |
| EXPORT-05 | Row order follows `_display_order` ascending | unit (pytest) | `python -m pytest tests/test_export_cross_marketplace.py::TestExportEndpoint::test_display_order -x` | ❌ Wave 0 |
| EXPORT-05 | Fidelity: item fields in xlsx match exactly what was sent | unit (pytest) | `python -m pytest tests/test_export_cross_marketplace.py::TestExportEndpoint::test_fidelity -x` | ❌ Wave 0 |
| EXPORT-06 | Filename matches `busca_sku_<query>_<YYYYMMDD_HHMMSS>.xlsx` pattern | unit (pytest) | `python -m pytest tests/test_export_cross_marketplace.py::TestExportEndpoint::test_filename -x` | ❌ Wave 0 |
| — | Empty items array returns HTTP 400 | unit (pytest) | `python -m pytest tests/test_export_cross_marketplace.py::TestExportEndpoint::test_empty_items_400 -x` | ❌ Wave 0 |
| — | items array > 500 returns HTTP 422 (Pydantic max_length) | unit (pytest) | `python -m pytest tests/test_export_cross_marketplace.py::TestExportEndpoint::test_oversized_payload -x` | ❌ Wave 0 |
| — | Missing X-API-Key returns HTTP 403 | unit (pytest) | `python -m pytest tests/test_export_cross_marketplace.py::TestExportEndpoint::test_auth -x` | ❌ Wave 0 |

**Manual / UAT tests (no automation possible):**
- EXPORT-01: Click a card checkbox — verify no tab opens, card visual state changes, counter increments
- EXPORT-02: Click "Selecionar todos" — verify all checkboxes checked; click again → all unchecked
- EXPORT-03: Open dialog with 0 selected — "Apenas selecionados" button is visually greyed and unclickable
- EXPORT-03: Click modal overlay — dialog closes, selection preserved
- EXPORT-06: Verify filename in Downloads folder matches expected pattern with correct query string

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_export_cross_marketplace.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -q` (currently: 130 passed baseline)
- **Phase gate:** Full suite green (`130 + new tests` passing) before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_export_cross_marketplace.py` — covers EXPORT-04, EXPORT-05, EXPORT-06 and all backend test cases above using `fastapi.testclient.TestClient` (already available via FastAPI)
- [ ] No conftest.py gap — existing tests work without shared fixtures; new test file follows same pattern as `test_relevance_gates.py`

**Test strategy for the backend tests:** Use `from fastapi.testclient import TestClient` (bundled with FastAPI; no new install). Import the FastAPI `app` instance, override `verify_api_key` dependency to return a fixed key, call the endpoint with a crafted JSON body, read the response `.content` as `io.BytesIO`, and verify the xlsx via `openpyxl.load_workbook()` — checking sheet name, column headers, and cell values. This approach is sync-safe and does not require `pytest-asyncio`.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pandas | xlsx generation | ✓ | 2.3.3 | — |
| openpyxl | pd.ExcelWriter engine | ✓ | 3.1.5 | — |
| FastAPI TestClient | backend tests | ✓ | bundled w/ FastAPI 0.132.0 | — |
| pytest | test runner | ✓ | 9.0.3 | — |
| lucide-react `Check` icon | checkbox checkmark | ✓ (lib present) | — | Use text "✓" |
| sonner toast | error feedback | ✓ (lib present) | — | — |

**Missing dependencies with no fallback:** none
**Missing dependencies with fallback:** none

All external dependencies for this phase are already installed and version-verified.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The FastAPI app instance is importable as `from main import app` (or similar) for TestClient | Validation Architecture | Tests can't run; need to check actual app entry point |
| A2 | `results.search_query` is echoed in the frontend results object from the backend response | Pattern 8 (handleExport) | `search_query` in payload would be `undefined`; `target_sku` fallback still works for filename |
| A3 | The `Check` icon from `lucide-react` is already imported in App.tsx | Pattern 6 | Would need to add the import — low risk, trivial fix |

**Notes on A1:** The test file should verify the correct import path before writing tests. Looking at existing tests (`test_cross_marketplace_service.py`, `test_relevance_gates.py`), they import services directly rather than the FastAPI app — the TestClient approach may require discovering the app entrypoint. Alternative: test `_sanitize_cell`, `_build_row`, and the core DataFrame logic as pure functions (extracted to a helper), sidestepping TestClient entirely.

---

## Open Questions

1. **`results.search_query` in the frontend results object**
   - What we know: The `cross_marketplace_search` endpoint returns `result` from `cross_marketplace_service.compare_product`, plus `reference_product` and `job_id`. The shape of `result` is not fully verified.
   - What's unclear: Whether the search_query/strict_q is included in the response dict so the frontend can pass it back.
   - Recommendation: Pass `targetSku` as `target_sku` (always available) and also pass `results?.search_query` if present. The filename will always be meaningful via the `target_sku` fallback.

2. **FastAPI app import path for TestClient**
   - What we know: `test_cross_marketplace_service.py` imports `cross_marketplace_service` directly. No existing test imports the FastAPI app.
   - What's unclear: Entry point filename (`main.py`? `app.py`?).
   - Recommendation: The plan's Wave 0 task should check for the main app file and set up TestClient. If the app is hard to import (startup side effects), test the pure `_build_row`/`_sanitize_cell` functions directly and test the Pydantic model separately.

---

## Sources

### Primary (HIGH confidence)
- `api/routes_search.py` — read in full; Excel pattern verified at lines 274–296; existing endpoints verified
- `frontend/src/api/client.ts` — read in full; blob download pattern verified at lines 105–140
- `frontend/src/App.tsx` — read lines 882–1187 (`CrossMarketplacePage`) and 634–646 (selection pattern)
- `frontend/src/App.css` — verified `.stock-toggle` (lines 569–612), `.btn-excel` (lines 624–632), `.animate-spin` (line 784)
- `services/relevance_gates.py` — read lines 248–282; field names in `build_formatted_results` verified
- `api/auth.py` — `verify_api_key` dependency verified
- `api/__init__.py` — `api_router` auth dependency verified at line 23
- `.planning/phases/24-exporta-o-excel-da-busca-por-sku/24-CONTEXT.md` — all decisions read
- `.planning/phases/24-exporta-o-excel-da-busca-por-sku/24-UI-SPEC.md` — all component specs, CSS, interaction contract read
- `.planning/REQUIREMENTS.md` — EXPORT-01..06 verified
- Runtime: `python -m pytest tests/ -q` → 130 passed (baseline green)
- Runtime: `python -c "import pandas, openpyxl, fastapi; ..."` → versions confirmed

### Secondary (MEDIUM confidence)
- Pydantic v2 private-field behavior (`_` prefix stripping) — from training knowledge; mitigated with explicit `Field(alias=...)` recommendation [ASSUMED]

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified at runtime
- Architecture: HIGH — all patterns traced to specific verified lines in the codebase
- Pitfalls: HIGH (pitfalls 1–3 verified in source) / MEDIUM (pitfall 4 Pydantic v2 private field — training knowledge)
- Security: HIGH — threats are standard and mitigations are concrete + already tested via existing pattern

**Research date:** 2026-06-15
**Valid until:** 2026-07-15 (stable stack; pandas/openpyxl APIs are very stable)
