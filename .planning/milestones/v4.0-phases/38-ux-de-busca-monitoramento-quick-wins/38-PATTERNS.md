# Phase 38: UX de Busca & Monitoramento — Quick Wins - Pattern Map

**Mapped:** 2026-07-01
**Files analyzed:** 8 (all existing files modified — no new files)
**Analogs found:** 8 / 8 (all analogs are in-file, sibling patterns in the same modified files)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `frontend/src/App.css` (`.grid-category` block, ~366-370) | config/style | transform (CSS layout) | `App.css:1052-1057` (`.search-main-row`/`.search-control-row` 980px breakpoint) | exact |
| `frontend/src/App.tsx` (`MonitorPage` `.monitor-pricing`, 417-434) | component | request-response (render of polled data) | `App.tsx:3009-3018` (category-monitor product-card promo render) | exact |
| `frontend/src/App.tsx` (`HistoryList` + new top-right icon, 779-885 / 3215-3231 `content-header`) | component | event-driven (toggle state) | `HistoryList`'s own header button (834-862) + `content-header` right slot (3215-3231) | role-match |
| `frontend/src/App.tsx` (`CrossMarketplacePage` SKU field, 2139-2166) | component | request-response (form validation) | `App.tsx:1487-1522` (CEP inline validation, comparative search) | exact |
| `frontend/src/App.tsx` (`MonitoredCategoriesPage.handleSubmit`, 2673-2686) | component | event-driven (submit → background task → poll) | `MonitorPage`'s `setInterval(refreshMonitors, 5000)` polling pattern (same file, ~200-234) + `handleViewProducts` (2698-2722) for reuse | role-match |
| `backend/core/models.py` (`PriceMonitorConfig`/`PriceHistoryEntry`, 281-319) | model | CRUD (persisted JSON schema) | Same class block — sibling fields `last_price`, `available_colors`/`available_sizes` (293-317) | exact |
| `backend/services/price_monitor_service.py` (`_monitor_loop`, 175-231) | service | event-driven (poll-scan-diff-notify loop) | Same function — existing `has_change`/`available_colors` diff blocks (191-203) | exact |
| `backend/tests/test_price_monitor.py` / `backend/tests/test_brand_active.py` (new tests) | test | request-response (unit) | Existing test classes in same files (hermetic async mock style; `TestMarketplacesInBrandsJson`) | exact |

**No new file created for `test_category_monitor.py`** — confirmed via Glob it does not exist yet; if a Wave 0 task adds a `run_category_scan` unit test, `backend/tests/test_price_monitor.py`'s hermetic mock style is the closest analog (no existing category-monitor test file to copy from directly).

## Pattern Assignments

### `frontend/src/App.css` — `.grid-category` responsive fix (UX-01)

**Analog:** `App.css:1052-1057` (existing `980px` breakpoint for `.search-main-row`/`.search-control-row`)

**Current unbreakpointed rule** (`App.css:366-370`):
```css
.grid-category {
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: 2rem;
}
```

**Pattern to copy** (existing sibling breakpoint elsewhere in the same file):
```css
/* App.css:1052-1057 */
@media (max-width: 980px) {
  .search-main-row,
  .search-control-row {
    grid-template-columns: 1fr;
  }
}
```

**New rule to add** (colocate near this block or near the existing 768px blocks at `App.css:181-206` / `1270-1279`):
```css
@media (max-width: 768px) {
  .grid-category {
    grid-template-columns: 1fr;
  }
}
```
Also verify the products-modal grid at `App.tsx:2983` (`gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))'`) for overflow at 768px — if needed, add a scoped class override to `minmax(200px, 1fr)` rather than duplicating inline styles.

---

### `frontend/src/App.tsx` — `MonitorPage` promo price (UX-02)

**Analog:** `App.tsx:3009-3018` (category-monitor product card — already renders `price_full`/`price_discount` correctly)

**Analog excerpt (copy this conditional structure verbatim, adapting field names per D-04):**
```tsx
// App.tsx:3009-3018 — WORKING reference pattern
{p.price_discount && p.price_discount > 0 ? (
  <>
    <span className="price-original" style={{ textDecoration: 'line-through', color: '#999', fontSize: '0.85em' }}>
      R$ {(p.price_full + p.price_discount).toFixed(2)}
    </span>
    <span className="price-current">R$ {p.price_full?.toFixed(2)}</span>
  </>
) : (
  <span className="price-current">R$ {p.price_full?.toFixed(2) || '0.00'}</span>
)}
```

**Target site — current gap** (`App.tsx:417-434`, `.monitor-pricing`):
```tsx
<div className="monitor-pricing">
  {m.last_price ? (
    <div className="monitor-price-value">R$ {m.last_price.toFixed(2)}</div>
  ) : (m.last_status === 'blocked' || m.last_status === 'error') ? (
    <div className="monitor-price-blocked" title={m.last_error || 'Não foi possível ler o produto.'}>
      {m.last_status === 'blocked' ? 'Bloqueado (anti-bot)' : 'Indisponível'}
    </div>
  ) : (
    <div className="monitor-price-pending">Pendente...</div>
  )}
  <div className="monitor-badge">...</div>
</div>
```
Insert the strikethrough span (analog pattern) above/beside `.monitor-price-value` when `m.last_price_discount > 0` (or whatever D-04 field name is chosen), keeping the existing `flex-direction: column; align-items: flex-end` layout (stack, not the horizontal layout used in the product-card analog). Same field must be added to `PriceMonitorConfig` (see backend section below) and flow through `GET /monitors` with zero new network call.

---

### `frontend/src/App.tsx` — `HistoryList` top-right icon (UX-06)

**Analog A — `HistoryList`'s own internal header/badge pattern** (`App.tsx:834-862`, reuse the badge visual, do not duplicate the fetch):
```tsx
// App.tsx:851-857 — badge pattern to mirror on the new external icon button
<History size={16} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
<span style={{ fontWeight: 700, fontSize: '0.875rem', flex: 1 }}>Histórico de buscas</span>
{filteredCount > 0 && (
  <span className="monitor-badge" style={{ color: 'var(--primary)', fontSize: '0.7rem', background: 'rgba(99,102,241,0.12)', padding: '2px 8px', borderRadius: '20px' }}>
    {filteredCount}
  </span>
)}
```
`filteredCount` is `items.length` AFTER the type filter (`App.tsx:787`, `all.filter((h: any) => h.type === type)`) — the new icon's badge must replicate this exact type-scoped count, not the raw unfiltered list length (see Pitfall 3 in RESEARCH.md).

**Analog B — insertion point, shared right-aligned slot** (`App.tsx:3215-3231`, `content-header`):
```tsx
<header className="content-header">
  <div style={{ display: 'flex', alignItems: 'center' }}>
    <button className="mobile-header-toggle" onClick={() => setIsMobileSidebarOpen(true)}>
      <Menu size={24} />
    </button>
    <h1>{/* per-tab title */}</h1>
  </div>
  {/* NEW: right-aligned icon-only button goes here — content-header already
      has justify-content: space-between (App.css:230-235), left side is
      the div above, right side is currently empty on every tab */}
</header>
```
`collapsed` state currently lives inside `HistoryList` (`useState(true)`, line 781) — per RESEARCH.md Pattern 4, lift it (prop-drill to `SearchPage`/`CrossMarketplacePage`) or expose an imperative toggle; both instances (`App.tsx:1602` search tab, `App.tsx:2177` cross tab) must wire identically, only the `type` prop differs.

---

### `frontend/src/App.tsx` — SKU field validation + CEP row (UX-07)

**Analog:** `App.tsx:1487-1522` (CEP inline validation, comparative search — exact pattern to replicate)

**Analog excerpt (copy structure verbatim, substitute SKU regex/copy):**
```tsx
// App.tsx:1487-1522
<div className="search-field">
  <label className="search-field-label" htmlFor="cep-input">CEP de entrega (opcional)</label>
  <div className={`search-input-wrapper${cepFieldError ? ' cep-input-error' : ''}`}>
    <MapPin className="search-icon" size={20} aria-hidden="true" />
    <input
      id="cep-input"
      ref={cepFieldRef}
      type="text"
      inputMode="numeric"
      autoComplete="postal-code"
      className="search-input"
      placeholder="00000-000"
      value={zipcode}
      aria-invalid={cepFieldError ? 'true' : 'false'}
      aria-describedby={cepFieldError ? 'cep-error-msg' : 'cep-helper-msg'}
      onChange={(e) => { /* normalize + clear error on edit */ }}
    />
  </div>
  {cepFieldError ? (
    <p id="cep-error-msg" className="cep-helper cep-helper-error" role="alert" aria-live="polite">
      <AlertTriangle size={12} aria-hidden="true" />
      {cepFieldError}
    </p>
  ) : (
    <p id="cep-helper-msg" className="cep-helper">Informe para calcular o frete junto da busca...</p>
  )}
</div>
```

**Target site — current gap** (`App.tsx:2139-2166`, `CrossMarketplacePage`, uses raw inline style instead of the `.search-*` classes):
```tsx
<div className="form-group" style={{ display: 'flex', gap: '16px' }}>
  <div style={{ flex: 1 }}>
    <label className="label">SKU Alvo (Aramis)</label>
    <input type="text" className="input" placeholder="Ex: ML.05.0326046" value={targetSku}
      onChange={e => setCross({ targetSku: e.target.value })} required />
  </div>
  <div style={{ width: '200px' }}>
    <label className="label">CEP (Opcional)</label>
    <input type="text" className="input" placeholder="Ex: 01001-000" value={zipcode}
      onChange={e => { /* CEP mask, no error state */ }} />
  </div>
</div>
```
Migrate to `.search-main-row` / `.search-field` / `.search-field-label` / `.search-input-wrapper` / `.search-input` classes (same as the CEP analog) so both tabs share the `980px` breakpoint. Validate `^ML\.05\.\d{7}$` on blur + submit; reuse `.cep-input-error`/`.cep-helper`/`.cep-helper-error` classes verbatim (no new CSS). Submit button (`App.tsx:2170-2173`) must be `disabled` when SKU is invalid.

---

### `frontend/src/App.tsx` — `MonitoredCategoriesPage.handleSubmit` auto-sweep (UX-08)

**Analog 1 — polling pattern to imitate** (`MonitorPage`'s existing `setInterval(refreshMonitors, 5000)`, same file ~200-234) — `MonitoredCategoriesPage` currently has **no polling at all**.

**Analog 2 — reuse verbatim for auto-open** (`App.tsx:2698-2722`, `handleViewProducts`):
```tsx
const handleViewProducts = async (monitor: any) => {
  setSelectedMonitor(monitor);
  setLoadingProducts(true);
  setSelectedMonitorStockSummary(null);
  try {
    const prods = await ApiClient.getMonitoredCategoryProducts(monitor.id);
    setMonitorProducts(prods);
    try {
      const summary = await ApiClient.getMonitoredCategoryStockSummary(monitor.id);
      setSelectedMonitorStockSummary(summary);
    } catch (summaryErr: any) { /* ... */ }
  } catch (err: any) {
    alert("Erro ao buscar produtos: " + err.message);
    setMonitorProducts([]);
    setSelectedMonitorStockSummary(null);
  } finally {
    setLoadingProducts(false);
  }
};
```
Call this function verbatim on poll-detected completion (D-05) — do not duplicate its fetch logic.

**Current gap** (`App.tsx:2673-2686`):
```tsx
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  setSubmitting(true);
  try {
    await ApiClient.createMonitoredCategory(newCategory);
    setNewCategory({ url: '', brand: brands.length > 0 ? brands[0].brand_key : '' });
    setIsModalOpen(false);
    fetchCategories();
  } catch (err: any) {
    alert("Erro ao adicionar: " + err.message);
  } finally {
    setSubmitting(false);
  }
};
```
Note: uses `alert()`, not `toast` — D-08 requires switching this flow to `toast.success`/`toast.error` (sonner), matching the app-wide pattern used elsewhere (`App.tsx:1972`, `2079`), not the legacy `alert()` used in this specific handler today.

**Backend trigger already exists — no new endpoint** (`backend/api/routes_monitor.py:59-76`):
```python
@router.post("/category", response_model=CategoryMonitorResponse)
async def create_category_monitor(
    data: CategoryMonitorCreate, background_tasks: BackgroundTasks
):
    row = {"id": str(uuid.uuid4()), "url": data.url, "brand": data.brand, "status": "active"}
    local_data = _load_local()
    local_data.append(row)
    _save_local(local_data)

    from services.category_monitor_service import run_category_scan
    background_tasks.add_task(run_category_scan, row)
    return CategoryMonitorResponse(**row)
```
`GET /monitor/categories` (`routes_monitor.py:79-81`) is the poll target — `run_category_scan` writes `last_scraped_at` onto the row once finished; poll this endpoint (mirroring `MonitorPage`'s 5s interval) until the new row's `last_scraped_at` is non-null, then stop and call `handleViewProducts`. Spinner condition: render `<RefreshCw className="animate-spin" size={14} />` (existing pattern already used at `App.tsx:2911` for "Carregando árvore de categorias...") while `last_scraped_at == null`.

---

### `backend/core/models.py` — new discount fields (UX-02, D-04)

**Analog:** Same class block, sibling optional fields already following this exact convention

**Current `PriceHistoryEntry`** (`models.py:281-290`):
```python
class PriceHistoryEntry(BaseModel):
    """Registro de uma variação de preço ou disponibilidade no tempo."""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    price: float
    available: bool
    available_colors: List[str] = Field(default_factory=list)
    available_sizes: List[str] = Field(default_factory=list)
```

**Current `PriceMonitorConfig`** (`models.py:293-318`):
```python
class PriceMonitorConfig(BaseModel):
    """Configuração e estado de um monitoramento ativo."""
    job_id: str
    url: str
    brand: str
    interval_minutes: int = 10
    duration_hours: int = 24
    start_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_price: Optional[float] = None
    last_status: Optional[str] = None
    last_error: Optional[str] = None
    last_checked_at: Optional[str] = None
    history: List[PriceHistoryEntry] = Field(default_factory=list)
    active: bool = True
    image_url: Optional[str] = None
    product_name: Optional[str] = None
    available_colors: List[str] = Field(default_factory=list)
    available_sizes: List[str] = Field(default_factory=list)
```
Add `last_price_discount: Optional[float] = None` to both classes (RESEARCH.md's recommendation — single new field, delta convention, `last_price` continues meaning "effective/current price" per D-01, front renders pre-discount price as `last_price + last_price_discount` exactly like the `App.tsx:3009-3018` analog). Field naming/count is Claude's discretion (D-04) — this is the minimal-change recommendation, not a lock.

---

### `backend/services/price_monitor_service.py` — D-01/D-03 monitor loop changes (UX-02)

**Analog:** Same function's existing diff/notify blocks (`_monitor_loop`, lines 175-231) — copy this exact structure for the new discount-aware comparison.

**Current gap** (`price_monitor_service.py:178, 193, 206-225`):
```python
current_price = product.price_full          # line 178 — ignores product.price_discount entirely
...
if config.last_price is None or config.last_price != current_price:   # line 193
    has_change = True
...
if has_change:                                # line 206
    entry = PriceHistoryEntry(
        price=current_price,
        available=bool(available),
        available_colors=current_colors,
        available_sizes=current_sizes
    )
    config.history.append(entry)
    config.last_price = current_price

    await manager.send_message({
        "type": "price_update",
        "price": current_price,
        "available": available,
        "available_colors": current_colors,
        "available_sizes": current_sizes,
        "history": [e.model_dump() for e in config.history],
        "message": f"Mudança detectada! Preço: R$ {current_price:.2f} | Tamanhos: {len(current_sizes)}"
    }, job_id)
```
D-01 formula (verbatim from CONTEXT.md): `current_price = product.price_discount if product.price_discount and product.price_discount > 0 else product.price_full`. **Caution (RESEARCH.md Pitfall 1):** verify against the actual per-engine `price_discount` convention (delta amount, not discounted price) before wiring — do not take the D-01 formula as license to treat `price_discount` as a standalone selling price. Extend the `has_change` check to also compare a new discount-delta field, add `last_price_discount` to the `PriceHistoryEntry(...)` constructor call and the `price_update` WS payload dict (D-03), mirroring exactly how `available_colors`/`available_sizes` are already threaded through both structures.

---

### `backend/tests/test_price_monitor.py` — D-01/D-03 test (UX-02)

**Analog:** Existing hermetic async test style in the same file (mocked engine, mocked WS, mocked `_save_monitors`, `asyncio.sleep` side-effect to stop loop after one iteration) — pattern already fully sketched in RESEARCH.md's Code Examples section; copy verbatim, adapting field names to whatever D-04 chooses.

### `backend/tests/test_brand_active.py` — COMP-08 regression test

**Analog:** `TestMarketplacesInBrandsJson` (existing class in same file) — reads real `brands.json` via the real `brand_service` singleton, asserts on the filtered key set, no mocking needed:
```python
class TestLacosteExcludedFromActiveOnly:
    """COMP-08: Lacoste (is_active=False) nunca aparece em list_brands(active_only=True)."""
    def test_lacoste_absent_from_active_only(self):
        from services.brand_service import brand_service
        active_brands = brand_service.list_brands(active_only=True)
        active_keys = {b.brand_key for b in active_brands}
        assert "lacoste" not in active_keys, (
            f"Lacoste nao deve aparecer em list_brands(active_only=True). Keys ativas: {sorted(active_keys)}"
        )
```

## Shared Patterns

### Toast feedback (sonner)
**Source:** `App.tsx:1972`, `2079` (`toast.success(...)`/`toast.error(...)`)
**Apply to:** `MonitoredCategoriesPage.handleSubmit` (D-08) — this handler currently uses `alert()` (line 2682, 2694, 2716 area), which is the OLD pattern in this specific component; migrate to `toast` to match the rest of the app. Error strings must follow the existing prefix convention: `"Erro ao " + <ação> + ": " + err.message`.

### CEP-style inline validation (`.cep-input-error` / `.cep-helper` / `.cep-helper-error`)
**Source:** `App.css:1281-1305`, `App.tsx:1487-1522`
**Apply to:** New SKU field validation (UX-07) — reuse classes verbatim, do not invent new ones (UI-SPEC explicitly requires this).

### Spinner (`RefreshCw` animate-spin)
**Source:** `App.tsx:2911` ("Carregando árvore de categorias...")
**Apply to:** New category-row loading state during auto-sweep (UX-08, D-06).

### Responsive breakpoint convention (`@media (max-width: Npx)`)
**Source:** `App.css:1052-1057` (980px), `App.css:181-206`/`1270-1279` (768px)
**Apply to:** New `.grid-category` breakpoint (UX-01) — no container queries, no new methodology.

### WebSocket payload field-parity
**Source:** `price_monitor_service.py:217-225` (`price_update` message already carries `price`, `available`, `available_colors`, `available_sizes` together)
**Apply to:** D-03 — add the new discount field to this same payload dict, not a separate message type.

## No Analog Found

None — all 6 requirements have a direct, working analog already in the same file/module (per RESEARCH.md's own conclusion: "every one of the six requirements in this phase has a working analog already in the codebase").

## Metadata

**Analog search scope:** `frontend/src/App.tsx`, `frontend/src/App.css`, `backend/core/models.py`, `backend/services/price_monitor_service.py`, `backend/api/routes_monitor.py`, `backend/tests/test_price_monitor.py`, `backend/tests/test_brand_active.py`
**Files scanned:** 8 (all files that will be modified; no new files in this phase)
**Pattern extraction date:** 2026-07-01
