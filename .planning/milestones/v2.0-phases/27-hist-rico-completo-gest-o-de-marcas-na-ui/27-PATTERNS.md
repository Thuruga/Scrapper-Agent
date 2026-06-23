# Phase 27: Histórico Completo + Gestão de Marcas na UI - Pattern Map

**Mapped:** 2026-06-20
**Files analyzed:** 4 (3 modified, 1 created)
**Analogs found:** 4 / 4 (all exact or strong role-matches, all in-repo)

> This phase is ~90% reuse. Every analog below was verified by direct code read this session; line numbers are current. No new packages, no new endpoints, no new CSS classes — extend existing surfaces.

## File Classification

| File | New/Mod | Role | Data Flow | Closest Analog | Match Quality |
|------|---------|------|-----------|----------------|---------------|
| `api/routes_search.py` (`POST /search`, ~140-179) | MODIFY | route (sync endpoint) | request-response + persistence | `POST /search/cross-marketplace` same file (413-450) | exact (same file, same pattern) |
| `tests/test_search_history_comparative.py` | CREATE | test (backend integration/unit) | request-response / CRUD | `tests/test_brand_active.py` | exact (same test idiom) |
| `frontend/src/api/client.ts` (`setBrandActive`) | MODIFY | client (API wrapper method) | request-response (PATCH) | `deleteBrand` / `saveBrand` (54-65) + `request` wrapper (21-45) | exact |
| `frontend/src/App.tsx` (3 edits: App state+renderTab, `HistoryList`, SettingsPage rows) | MODIFY | component (React container + presentational) | event-driven UI / CRUD list | `SettingsPage` brand rows (1421-1450), `SearchPage` reopen useEffect (651-660), `renderTab` (1795-1805) | exact / role-match |

---

## Pattern Assignments

### `api/routes_search.py` — HIST-01 persistence in `POST /search` (route, request-response + persistence)

**Analog:** `POST /search/cross-marketplace` in the SAME file (lines 413-450). Mirror it, but apply the **shape-contract fix** (store the inner list, not the wrapper object).

**Current `POST /search` (lines 140-179)** has NO persistence and NO try/except — both are added by HIST-01. Imports `uuid` and `search_history_service` are done lazily inside the cross block (413,415) — mirror that or hoist to module top (planner discretion; lazy import matches the analog).

**Analog persistence block to mirror (lines 413-450):**
```python
import uuid
job_id = str(uuid.uuid4())
from services.search_history_service import search_history_service

display_query = strict_q or broad_q or request.target_sku
search_history_service.create_job(
    job_id=job_id,
    query=f"SKU: {display_query}",        # cross composes a label here...
    brands=["mercadolivre", "netshoes", "amazon"],
    type="cross"
)
try:
    result = await cross_marketplace_service.compare_product(...)
    result["reference_product"] = ref_product_data
    result["job_id"] = job_id
    search_history_service.update_job(
        job_id=job_id, status="COMPLETED", results=result   # ...stores the WHOLE dict
    )
    return result
except Exception as e:
    search_history_service.update_job(job_id=job_id, status="FAILED", error=str(e))
    raise
```

**Adapted block for the comparative endpoint (LANDMINE-aware — two deviations from the analog):**
```python
# Insert around routes_search.py:163 (after target_brands at :157-161 is computed)
import uuid
job_id = str(uuid.uuid4())
from services.search_history_service import search_history_service

search_history_service.create_job(
    job_id=job_id,
    query=request.query,        # DEVIATION 1: raw term, NOT a composed label (Pitfall 2;
                                #   SearchPage:656 dumps res.query back into the search box)
    brands=target_brands,       # already computed at routes_search.py:157-161
    type="search",
)
try:
    brand_results = await engine_factory.search_all_brands(...)  # existing call, :165-173
    result = ComparisonResult(query=request.query, brands_searched=target_brands, results=brand_results)
    search_history_service.update_job(
        job_id=job_id,
        status="COMPLETED",
        results=result.model_dump(mode="json")["results"],  # DEVIATION 2: INNER LIST only
                                                             #   (Pitfall 1 / Resolution A)
    )
    return result
except Exception as e:
    search_history_service.update_job(job_id=job_id, status="FAILED", error=str(e))
    raise
```

**Why the two deviations (do NOT copy the analog verbatim):**
1. **Store the inner list** `model_dump(mode="json")["results"]`, NOT the whole `ComparisonResult`. `SearchPage`'s reopen handler (App.tsx:655) does `setResults({ results: res.results, ... })` and expects `res.results` to BE the `List[BrandSearchResult]`. Storing the wrapper → silent empty render (Pitfall 1).
2. **Store `query=request.query` raw**, not a composed "Reserva, Aramis · 3 marcas" string. The reopen handler repopulates the search box from `res.query` (App.tsx:656). Label is composed in the frontend.

**Note on `job_id` return:** `response_model=ComparisonResult` (line 133) strips extra fields, so do NOT try to echo `job_id` in the response — the frontend refetches `getHistoryList()` instead (Pitfall 6).

---

### `tests/test_search_history_comparative.py` — HIST-01 tests (test, integration/unit)

**Analog:** `tests/test_brand_active.py` (full file). It establishes the exact project test idiom.

**Idiom to copy:**
- **In-memory service, no I/O:** build the service via `__new__` + manually set attrs, and mock `_save`/`_check_reload` (see `_make_service_with_brands`, lines 30-57). For history use `SearchHistoryService.__new__(...)` with an in-memory store and patched persistence (`_save_history`).
- **Monkeypatch the module singleton + call the async route fn directly via `asyncio.run`** (lines 184-203):
```python
import api.routes_search as routes_search_module
original = routes_search_module.search_history_service
routes_search_module.search_history_service = fake_svc
try:
    result = asyncio.run(routes_search_module.search_products(fake_request))
finally:
    routes_search_module.search_history_service = original
```
- For HIST-01 also patch `routes_search.engine_factory` so `search_all_brands` returns canned `BrandSearchResult`s (and a raising mock for the FAILED-path test).
- **Plain `assert` + class grouping** (`class TestX:`), pytest discovery by convention `tests/test_*.py` (no config file).

**Tests to write (per RESEARCH Validation map, Wave 0):**
- `test_post_search_persists_history` — a `type="search"` record is created.
- `test_persisted_results_shape_is_inner_list` — stored `results` is the inner `List[BrandSearchResult]` (guards Pitfall 1).
- `test_search_failure_marks_failed` — exception path → status FAILED + `error` set.
- `test_history_service_search_type` — service `create_job(type="search")` + `update_job` round-trip.

---

### `frontend/src/api/client.ts` — `setBrandActive` PATCH (client method)

**Analog:** `deleteBrand` (61-65) / `saveBrand` (54-65) using the `request` wrapper (21-45). The wrapper already injects `X-API-Key` + `Content-Type` and throws on `!response.ok` — no extra error handling needed.

**Method to add (place next to the other Brands methods, ~line 65):**
```ts
static setBrandActive(brandKey: string, isActive: boolean) {
  return this.request(`/brands/${brandKey}/active`, {
    method: 'PATCH',
    body: JSON.stringify({ is_active: isActive }),
  });
}
```
Endpoint `PATCH /brands/{brand_key}/active` exists (Phase 25, `routes_brands.py:176-182`); body `{ is_active: boolean }` (`BrandActiveUpdate`); 404 on unknown key (already handled by `request` throwing). Note: history methods `getHistoryList/getHistoryDetail/deleteHistory` (91-103) already exist — do NOT recreate.

---

### `frontend/src/App.tsx` — three edits

#### Edit 1: App-level reopen wiring (HIST-02, SC#2 — MANDATORY)

**Analog:** existing `App()` state + `renderTab` (1779-1805). `SearchPage`/`CrossMarketplacePage` already declare `preloadedJobId` + `onClearPreloadedJob` (SearchPage signature at 641) and already have the loading `useEffect` (651-660) — the props are dead-wired today. Only the App must feed them.

**Current `renderTab` (1797-1799) passes neither prop:**
```tsx
case 'search': return <SearchPage brands={brands} />;
case 'cross': return <CrossMarketplacePage />;
```

**Add to `App()` (near 1780-1789) + fix `renderTab`:**
```tsx
const [preloadedJobId, setPreloadedJobId] = useState<string | null>(null);

const handleReopen = (jobId: string, type: 'search' | 'cross') => {
  setActiveTab(type === 'cross' ? 'cross' : 'search'); // tab inherent (D-01)
  setPreloadedJobId(jobId);
};

// renderTab:
case 'search':
  return <SearchPage brands={brands}
                     preloadedJobId={preloadedJobId}
                     onClearPreloadedJob={() => setPreloadedJobId(null)} />;
case 'cross':
  return <CrossMarketplacePage preloadedJobId={preloadedJobId}
                               onClearPreloadedJob={() => setPreloadedJobId(null)} />;
```
The child clears the prop on a fresh search (`onClearPreloadedJob()` at App.tsx:678 / :1045). Optionally clear `preloadedJobId` on manual tab switch to avoid a stale reopen (low risk).

#### Edit 2: `HistoryList` reusable per-tab panel (HIST-02, D-01/D-02/D-03/D-06)

Built from scratch — no history-list UI exists today. Build ONE shared presentational component `<HistoryList type onReopen />`; mount per-tab (`type="search"` in SearchPage, `type="cross"` in CrossMarketplacePage). The `onReopen={(jobId) => handleReopen(jobId, type)}` bubbles to Edit 1.

**Row analog — reuse `SettingsPage` `.brand-item` geometry (1423-1447):**
```tsx
<div key={...} className="brand-item">
  <div className="brand-info"> ... <p className="brand-name-text">{label}</p>
    <p className="brand-domain-text"><Globe size={12} /> {meta}</p> </div>
  <div className="brand-actions">
    <button type="button" className="btn-icon text-error" onClick={...}>
      <Trash2 size={18} />
    </button>
  </div>
</div>
```
Reuse classes (per UI-SPEC): `.brand-item`/`.brand-info`/`.brand-name-text`/`.brand-domain-text`/`.brand-actions`, `.btn-icon .text-error`, `.monitor-badge` (type+status badges), `.empty-state`, `RefreshCw .animate-spin` (loading), `GlassCard` wrapper. Icons from lucide-react already imported (`Trash2`, `RefreshCw`, `Globe`, `ChevronDown`/`ChevronRight`, `History`).

**Data + interaction (from `SearchPage` reopen useEffect 651-660 + UI-SPEC §A):**
- Fetch `ApiClient.getHistoryList()` on mount, after a successful `handleSearch` (Pitfall 4 — refetch so the new entry shows), and after delete. Filter client-side by `type`.
- Label: `cross` keeps stored `query` (`"SKU: …"`); `search` composes in FE from `brands` + `query` (e.g. `Reserva, Aramis · 3 marcas — "polo piquet"`).
- Click only on `status === 'COMPLETED'` → `onReopen(job_id)` (D-06). FAILED dimmed + error badge, PENDING spinner badge — non-clickable. Delete button must `stopPropagation`. Delete via `ApiClient.deleteHistory(job_id)` → refetch (analog: `handleDeleteBrand`, 1349-1357, with `confirm()`).

#### Edit 3: SettingsPage brand-row extension (MGMT-02, D-08/D-09/D-10)

**Analog:** the brand row itself (1423-1447) + `handleDeleteBrand` (1349-1357). Extend in place; do NOT redesign. Keep the add-brand form (1378-1419) and delete button untouched.

**Add inside `.brand-actions` (before/after the existing delete button at 1439-1445):**
- **Active toggle** — `.btn-icon` with lucide `Power`, ON state `--primary`, OFF muted; calls `ApiClient.setBrandActive(b.brand_key, !b.is_active)` then `onRefresh()`. Instant/reversible, NO confirm (D-10). Mirror the `handleDeleteBrand` async+`onRefresh()` structure but without `confirm()`.
- Keep the existing `Trash2` delete (confirm-gated) as the permanent action.

**Inactive distinction (D-09):** when `b.is_active === false`, dim the `.brand-info` block (opacity ~0.55) + add an "Inativa" `.monitor-badge` (warning tint) next to `.brand-name-text`. Actions stay fully interactive so the brand can be reactivated.

**Virtual-marketplace guard (LANDMINE A1):** the three injected virtual marketplaces have no backend record → PATCH would 404. Hide the toggle for them:
```tsx
const VIRTUAL = ['mercado_livre', 'netshoes', 'amazon'];
const canToggle = !VIRTUAL.includes(b.brand_key);
// render the toggle only when canToggle
```

---

## Shared Patterns

### Backend job persistence
**Source:** `services/search_history_service.py` (`create_job`/`update_job`) + the cross block `routes_search.py:413-450`.
**Apply to:** `POST /search` (HIST-01). Sequence: `create_job(type=...)` → work → `update_job("COMPLETED", results=...)` / on except `update_job("FAILED", error=str(e))` + re-raise. **Apply the inner-list + raw-query deviations** for the comparative endpoint.

### Pydantic → JSON for storage
**Source:** `result.model_dump(mode="json")` (handles datetime/nested models). `_save_history` already uses it.
**Apply to:** HIST-01 stored `results` — use `model_dump(mode="json")["results"]`.

### Frontend API call
**Source:** `ApiClient.request` wrapper (`client.ts:21-45`) — injects `X-API-Key`, throws on non-OK.
**Apply to:** `setBrandActive` and all history calls. No per-call error handling beyond catching the thrown Error.

### Reopen-without-rescrape
**Source:** `SearchPage` useEffect (`App.tsx:651-660`), `CrossMarketplacePage` useEffect (`~974-985`).
**Apply to:** HIST-02. Do NOT touch the SKU handler (its full-dict contract is already correct). Feed `preloadedJobId` from App; child's `getHistoryDetail` + `setResults` does the rest.

### Backend test idiom
**Source:** `tests/test_brand_active.py` — in-memory service via `__new__`, mocked I/O, monkeypatched module singleton, `asyncio.run(route_fn(...))`, plain asserts in `class Test*`.
**Apply to:** `tests/test_search_history_comparative.py`.

### CSS class vocabulary (hand-rolled, NOT Tailwind)
**Source:** `frontend/src/App.css` + components `GlassCard`/`StatusBanner`. Row vocab from SettingsPage (1421-1450).
**Apply to:** `HistoryList` + SettingsPage rows. Classes: `.brand-item`, `.brand-info`, `.brand-name-text`, `.brand-domain-text`, `.brand-actions`, `.btn-icon`, `.text-error`, `.monitor-badge`, `.empty-state`, `.animate-spin`, `.status-banner`. Status tokens `--success`/`--error`/`--warning`; accent `--primary`.

---

## No Analog Found

None. Every file maps to an existing in-repo analog. The only genuinely new artifact is the `HistoryList` presentational component, which still reuses the SettingsPage `.brand-item` row geometry and the SearchPage reopen `useEffect` contract.

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| — | — | — | — |

---

## Metadata

**Analog search scope:** `api/routes_search.py`, `tests/`, `frontend/src/api/client.ts`, `frontend/src/App.tsx`
**Files scanned (read this session):** 5 (routes_search.py ×2 ranges, test_brand_active.py, App.tsx ×3 ranges, client.ts)
**Pattern extraction date:** 2026-06-20
**Highest-risk pattern:** HIST-01 stored-result-shape — store the INNER list, not the `ComparisonResult` wrapper (Pitfall 1). All other edits are verbatim-analog or additive.
