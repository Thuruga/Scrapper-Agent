# Phase 38: UX de Busca & Monitoramento — Quick Wins - Research

**Researched:** 2026-07-01
**Domain:** React/TypeScript frontend (hand-rolled CSS) + FastAPI/Pydantic backend — 6 targeted UX/data fixes, no new capabilities.
**Confidence:** HIGH

## Summary

This phase is six independent, well-scoped fixes across a codebase whose conventions are already fully established (no new libraries, no new architectural patterns). `38-CONTEXT.md` already nailed the file:line references and decisions (D-01 through D-09); this research fills the specific gaps the orchestrator flagged: existing CSS breakpoint conventions, backend/frontend test patterns to follow, the SKU regex convention, and — most importantly — two facts that change how the plan should be written:

1. **The category auto-sweep (UX-08) backend trigger already exists and already fires.** `POST /monitor/category` (`backend/api/routes_monitor.py:59-76`) calls `background_tasks.add_task(run_category_scan, row)` on every creation — today. The gap is entirely on the frontend: `handleSubmit` (`App.tsx:2673-2686`) never surfaces this, there is no spinner, and — critically — **`MonitoredCategoriesPage` has no polling mechanism at all** (unlike `MonitorPage`, which polls `GET /monitors` every 5s). The plan must add a lightweight poll/refetch after submit to detect scan completion; nothing today updates the table once `run_category_scan` finishes in the background.
2. **`price_discount` in this codebase means "discount amount," not "discounted price."** Every engine that populates it (VTEX `vtex_api_scraper.py:349`, Mercado Livre `mercado_livre_engine.py:632`, Shopify `shopify_api_client.py:211`) computes `price_discount = list_price - sale_price` (a small positive delta) while `price_full` holds the **current/selling price** the customer pays. The frontend already renders this correctly at `App.tsx:3009-3018` (`price_full + price_discount` = pre-discount price, `price_full` = current price shown bold). This is the OPPOSITE of what the field names suggest, and the opposite of how `RawProductBronze.calculate_landed_price` (`backend/core/models.py:136-149`) and `shipping/base.py:117` treat it (they use `price_discount` directly AS the base/selling price if present — a **pre-existing, out-of-scope bug** that this phase must not copy into the new monitor fields).

**Primary recommendation:** Follow the exact rendering pattern already proven at `App.tsx:3009-3018` for UX-02, extend `PriceMonitorConfig`/`PriceHistoryEntry` with two new fields that mirror `RawProductBronze`'s `price_full`/`price_discount` semantics (delta convention, not discounted-price convention), add a `.grid-category` media query mirroring the existing `768px`/`980px` breakpoint pattern already in `App.css`, and lift `HistoryList`'s `collapsed` state to be controllable from a new top-right icon in the shared `content-header` (already `justify-content: space-between` with an empty right slot on every tab).

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Cálculo do preço de promoção no monitor (UX-02)**

Achado de código confirmado: hoje `backend/services/price_monitor_service.py:178` grava `current_price = product.price_full` como `last_price` — `price_discount` nunca é lido do produto raspado nem persistido em `PriceMonitorConfig`/`PriceHistoryEntry` (`backend/core/models.py:281-313`). A detecção de mudança (`has_change`, linha 193) só compara `price_full`.

- **D-01:** A detecção de mudança de preço (histórico + notificação WebSocket `price_update`) passa a usar o **preço efetivo**: `current_price = price_discount if price_discount > 0 else price_full`. Uma promoção que altera só o desconto (preço cheio inalterado) agora deve gerar entrada de histórico e notificação.
- **D-02:** Monitores já ativos não têm `price_discount` histórico. É aceitável que o dado só passe a existir a partir da **próxima checagem agendada** de cada monitor — sem re-scraping retroativo, sem forçar recheck de todos os monitores ativos.
- **D-03:** A mensagem WebSocket `price_update` passa a incluir `price_discount` (e o preço cheio) no payload ao vivo, seguindo o padrão já usado para `price`, `available`, `available_colors`, `available_sizes`.
- **D-04 (Claude's discretion):** nomes exatos dos novos campos em `PriceMonitorConfig`/`PriceHistoryEntry` ficam a critério do planner/executor — desde que `last_price` continue representando o preço efetivo (compatibilidade com o frontend atual que já lê `last_price`).

**Comportamento após a 1ª varredura automática (UX-08)**

- **D-05:** Ao terminar a primeira varredura automática (disparada pelo `handleSubmit` de `MonitoredCategoriesPage`, `App.tsx:2673-2686`), o **modal de produtos abre automaticamente**.
- **D-06:** O modal de cadastro de categoria **fecha imediatamente** após o `Salvar`; a varredura roda em background. A linha da categoria mostra o spinner (`<RefreshCw className="animate-spin" size={14} />`) até a varredura concluir — só então o modal de produtos abre sozinho.

**Textos de toast/tooltip (confirmados sem alteração)**

- **D-07:** Tooltip do ícone de histórico (ambas as abas): `title="Ver histórico de buscas"`.
- **D-08:** Toast de sucesso do auto-sweep: "Categoria adicionada. Iniciando primeira varredura…". Toast de falha: "Categoria salva, mas a primeira varredura falhou. Tente novamente na lista."
- **D-09:** Erro inline do SKU inválido: "Formato inválido. Use o padrão ML.05.XXXXXXX (ex: ML.05.0326046)."

### Claude's Discretion

- Nomes exatos dos novos campos de preço no backend (D-04).
- Estrutura interna de como o `handleSubmit` de `MonitoredCategoriesPage` orquestra fechar o modal + disparar sweep + atualizar spinner + abrir modal de produtos ao final (D-05/D-06) — desde que a sequência observável pelo operador seja a descrita.
- Qual endpoint/serviço de "scan agora" já existente é reaproveitado para disparar a primeira varredura (não criar um novo se já existir um usado por `handleViewProducts`/scan manual).
- Todos os detalhes visuais, de layout e de responsividade já travados em `38-UI-SPEC.md` (UX-01, UX-06, UX-07, COMP-08).

### Deferred Ideas (OUT OF SCOPE)

- Paginação do histórico de buscas (`cap-search-history-list.md`) — capacidade nova, não parte do escopo desta phase.
- Qualquer melhoria de mapeamento de categorias entre marcas, precisão de modelo/NLP, engine Zara ou bug de scan VTEX-IO Hugo Boss — nada disso pertence à Phase 38.

**Design contract note:** `38-UI-SPEC.md` is already approved (status: approved 2026-07-01) and locks ALL visual/copy/layout decisions for UX-01, UX-06, UX-07, COMP-08. It is the canonical source for spacing, color, typography, and copywriting — this research does not re-derive those; see `<canonical_refs>` below.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UX-01 | Monitor de categoria e varredura por categoria são responsivos em viewports menores | `.grid-category` root cause confirmed at `App.css:366-370` (no media query); exact breakpoint pattern to mirror documented below (`Architecture Patterns` → Pattern 1). |
| UX-02 | Lista de monitoramento exibe o valor da promoção (`price_discount`) além do preço cheio | Backend field-shape gap confirmed (`price_monitors.json` has only `last_price`); `price_discount` semantics (delta, not discounted price) confirmed against 3 engines; existing render pattern at `App.tsx:3009-3018` to reuse; backend test pattern documented from `test_price_monitor.py`. |
| UX-06 | Histórico de busca acessível por ícone no canto superior direito, em ambas as abas de busca | `content-header` (`App.css:230-235`) confirmed as the shared right-aligned slot across ALL tabs; `HistoryList`'s internal `collapsed` state (line 781) confirmed as needing to be lifted for icon-driven control. |
| UX-07 | Campo de SKU valida o padrão `ML.05.XXXXXXX`; CEP na mesma linha do SKU | Existing CEP validation pattern at `App.tsx:1487-1522` (`cepFieldError`, `.cep-input-error`, `.cep-helper`) fully documented as the exact pattern to replicate for SKU; current SKU input (`App.tsx:2142-2150`) confirmed as unvalidated plain text field. |
| UX-08 | Selecionar categoria dispara a 1ª varredura automaticamente | **Backend trigger already exists** (`routes_monitor.py:73-75`, `background_tasks.add_task(run_category_scan, row)`) — confirmed via code read. Gap is 100% frontend: no spinner, no completion detection (no polling in `MonitoredCategoriesPage`), no auto-open of the products modal. |
| COMP-08 | Lacoste não aparece em nenhuma superfície de busca — regressão coberta por teste | `list_brands(active_only=True)` chokepoint confirmed as single source of truth (`test_brand_active.py`); existing regression-test pattern (`TestListBrandsActiveOnly`, `TestMarketplacesInBrandsJson`) is the template for the new COMP-08-specific regression test. |

</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Responsive grid layout (UX-01) | Browser / Client (CSS) | — | Pure CSS media-query fix; no data or logic changes. |
| Promo price display (UX-02) | API / Backend (data shape) | Browser / Client (render) | Backend must persist/serialize the discount field; frontend only renders what's already in the polled `GET /monitors` payload — no new network call. |
| Search history icon (UX-06) | Browser / Client | — | Pure UI state/layout change; reuses existing `ApiClient.getHistoryList()` call and `HistoryList` component, only the trigger/position and state ownership move. |
| SKU pattern validation (UX-07) | Browser / Client | — | Frontend-only regex validation; no backend contract change (backend `RawProductBronze`/SKU-search endpoint already accepts free text — validation is a UX gate, not a data-integrity gate). |
| Auto-sweep trigger (UX-08) | API / Backend (already implemented) | Browser / Client (surface it) | Backend fire-and-forget scan already exists (`background_tasks.add_task`); frontend must add completion detection (poll) and UI feedback (spinner + auto-open modal) — no new backend endpoint needed. |
| Brand exclusion (COMP-08) | API / Backend (chokepoint) | Browser / Client (test coverage of surfaces) | `list_brands(active_only=True)` is already the single enforcement point (STATE.md `[ARCH]`); this phase adds a regression test, not new filtering logic. |

## Standard Stack

No new libraries are introduced by this phase. All required capabilities are already covered by dependencies present in `frontend/package.json` and the backend's existing stack.

### Core (existing, reused)
| Library | Version | Purpose | Why Standard (for this phase) |
|---------|---------|---------|--------------------------------|
| `lucide-react` | `^1.14.0` (installed) | Icons (`History`, `AlertTriangle`, `RefreshCw`) | Already imported in `App.tsx:2-41`; `History` and `AlertTriangle` are already in the import list — zero new imports needed. |
| `sonner` | `^2.0.7` (installed) | Toast notifications (D-08 auto-sweep toasts) | Already the app-wide toast pattern (`toast.success`/`toast.error`, e.g. `App.tsx:1972`, `2079`). |
| `pydantic` | (backend, installed) | New `PriceMonitorConfig`/`PriceHistoryEntry` fields | Existing model layer; no schema-migration tooling needed since data is JSON-file-persisted, not a real DB. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual poll after auto-sweep (setInterval/setTimeout) | WebSocket push for category-scan completion | WS would require a new message type + connection wiring in `MonitoredCategoriesPage` (currently has none) — out of proportion for a "quick win" phase; polling mirrors the proven `MonitorPage` pattern (`setInterval(refreshMonitors, 5000)`) with zero new infrastructure. |
| CSS Grid breakpoint fix | CSS Container Queries | Container queries would be a new pattern not used anywhere else in `App.css` (all existing responsiveness is `@media (max-width: Npx)`) — inconsistent with established convention for a one-line fix. |

**Installation:** None required — no new packages.

## Package Legitimacy Audit

Not applicable. This phase installs zero external packages (frontend and backend both use only already-installed dependencies). No `npm install` / `pip install` step exists in any plan for this phase.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────── Browser (React) ───────────────────────────┐
│                                                                          │
│  MonitoredCategoriesPage          MonitorPage            SearchPage /   │
│  ┌──────────────────┐            ┌──────────────┐        CrossMarket-  │
│  │ handleSubmit()    │            │ refreshMonitors│      placePage     │
│  │  1. POST /monitor/│            │  (poll 5s)     │      ┌───────────┐│
│  │     category ──┐  │            │  GET /monitors │      │ SKU input ││
│  │  2. close modal │  │            │  reads          │      │ + regex   ││
│  │  3. row spinner │  │            │  last_price,    │      │ validator ││
│  │  4. [NEW] poll  │  │            │  last_price_    │      │ (UX-07)   ││
│  │     until        │  │           │  discount        │      └───────────┘│
│  │     last_scraped_│  │           │  (new fields)    │      ┌───────────┐│
│  │     at changes   │  │           └───────┬──────────┘      │ History   ││
│  │  5. auto-open    │  │                   │                 │ icon      ││
│  │     products modal│ │                   │                 │ top-right ││
│  └────────┬──────────┘  │                   │                 │ (UX-06)   ││
│           │              │                   │                 └─────┬─────┘│
└───────────┼──────────────┼───────────────────┼───────────────────────┼──────┘
            │              │                   │                       │
            ▼              ▼                   ▼                       ▼
  ┌───────────────────────────────────────────────────────────────────────┐
  │                          FastAPI Backend                                │
  │                                                                          │
  │  POST /monitor/category ──background_tasks──▶ run_category_scan()      │
  │    (routes_monitor.py:59)                       (category_monitor_     │
  │         │                                        service.py:43)        │
  │         │ writes monitored_categories.json       │                     │
  │         │ (status, last_scraped_at)               ▼                     │
  │         │                                  writes monitored_products_   │
  │         ▼                                  {id}.json + stock summary    │
  │  GET /monitor/categories ◀── polled by frontend after submit (NEW)     │
  │                                                                          │
  │  price_monitor_service._monitor_loop()  ──▶  PriceMonitorConfig         │
  │    reads product.price_full/price_discount     .last_price (existing)  │
  │    (RawProductBronze, D-01 formula)             .last_price_discount   │
  │         │                                        (NEW field, D-04)      │
  │         ▼                                                                │
  │  GET /monitors  ──▶  polled by MonitorPage every 5s (existing)         │
  │  WS price_update ──▶  D-03 adds discount field (not consumed by UI     │
  │                        today — MonitorPage reads via poll, not WS)      │
  │                                                                          │
  │  brand_service.list_brands(active_only=True) ──▶ single chokepoint     │
  │    for ALL brand-selector surfaces (COMP-08, unchanged this phase)     │
  └───────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

No new files/folders — all changes are edits to existing files:
```
frontend/src/
├── App.tsx              # MonitorPage, MonitoredCategoriesPage, CrossMarketplacePage, SearchPage — all 6 fixes land here
├── App.css              # New @media (max-width: 768px) block for .grid-category; reuse .cep-input-error/.cep-helper for SKU
└── api/client.ts         # No new methods expected (createMonitoredCategory, getMonitoredCategoryProducts already exist)

backend/
├── core/models.py                        # PriceMonitorConfig + PriceHistoryEntry: add discount field(s) (D-04)
├── services/price_monitor_service.py     # _monitor_loop: D-01 effective-price formula, D-03 WS payload field
├── data/price_monitors.json              # Shape evolves automatically via Pydantic — no migration script needed (D-02: lazy population)
└── tests/test_price_monitor.py           # Extend with D-01/D-03 coverage, following existing test style
```

### Pattern 1: Responsive grid breakpoint (UX-01)

**What:** Add a `max-width: 768px` media query that collapses `.grid-category`'s two-column layout to one column, mirroring the app's existing breakpoint conventions.
**When to use:** Any fixed multi-column grid without an existing mobile/tablet fallback.
**Existing convention (confirmed in `App.css`):**
```css
/* Existing pattern already in App.css:1052-1066 (comparative search) */
@media (max-width: 980px) {
  .search-main-row,
  .search-control-row {
    grid-template-columns: 1fr;
  }
}

/* Root cause — .grid-category has NO breakpoint at all (App.css:366-370) */
.grid-category {
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: 2rem;
}

/* Fix — colocate near existing 768px block at App.css:181-206 (sidebar) or
   1270-1279 (banner-gallery), following the same max-width: 768px convention
   already used elsewhere in the file for tablet-width fixes */
@media (max-width: 768px) {
  .grid-category {
    grid-template-columns: 1fr;
  }
}
```
Also check (per UI-SPEC contract): products-modal grid `gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))'` (`App.tsx:2983`) for overflow at 768px — UI-SPEC prescribes reducing to `minmax(200px, 1fr)` via a scoped class at ≤768px if overflow is observed, not inline-style duplication.

### Pattern 2: CEP-style inline validation, applied to SKU (UX-07)

**What:** Regex-validate an input on blur + submit, using the exact visual/ARIA pattern already proven for CEP.
**Existing pattern to replicate (confirmed, `App.tsx:1487-1522`):**
```tsx
// Source: frontend/src/App.tsx:1487-1522 (existing CEP field, comparative search)
<div className="search-field">
  <label className="search-field-label" htmlFor="cep-input">CEP de entrega (opcional)</label>
  <div className={`search-input-wrapper${cepFieldError ? ' cep-input-error' : ''}`}>
    <MapPin className="search-icon" size={20} aria-hidden="true" />
    <input
      id="cep-input"
      ref={cepFieldRef}
      type="text"
      inputMode="numeric"
      className="search-input"
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
**Apply to SKU (`App.tsx:2142-2150`, `CrossMarketplacePage`):** same wrapper classes (`.search-input-wrapper`, `.cep-input-error` — UI-SPEC explicitly says reuse `.cep-input-error`/`.cep-helper`, do not invent new classes), same `role="alert"`/`aria-live` pattern, validated against `^ML\.05\.\d{7}$` on blur AND submit (not per-keystroke). CSS classes are named `cep-*` but are validated by the UI-SPEC contract as the correct reuse target for SKU too (`38-UI-SPEC.md` §4) — no CSS rename needed.

**Layout migration required:** the SKU form currently uses raw inline `style={{ display: 'flex', gap: '16px' }}` (`App.tsx:2139`) instead of `.search-main-row`/`.search-field` classes — UI-SPEC requires migrating to the shared classes so both tabs collapse identically at the existing `980px` breakpoint (`App.css:1052-1057`).

### Pattern 3: Fire-and-forget backend task + frontend completion polling (UX-08)

**What:** The backend already runs the scan as a `BackgroundTasks` job when the category is created; the frontend needs a short-lived poll to detect completion (no WebSocket infra exists for this surface).
**Confirmed existing backend behavior (`backend/api/routes_monitor.py:59-76`):**
```python
# Source: backend/api/routes_monitor.py — ALREADY IMPLEMENTED, no backend change needed for the trigger itself
@router.post("/category", response_model=CategoryMonitorResponse)
async def create_category_monitor(
    data: CategoryMonitorCreate, background_tasks: BackgroundTasks
):
    row = {"id": str(uuid.uuid4()), "url": data.url, "brand": data.brand, "status": "active"}
    local_data = _load_local()
    local_data.append(row)
    _save_local(local_data)

    from services.category_monitor_service import run_category_scan
    background_tasks.add_task(run_category_scan, row)   # <-- fires immediately, no manual "scan now" needed
    return CategoryMonitorResponse(**row)
```
`run_category_scan` (`backend/services/category_monitor_service.py:43-93`) writes `last_scraped_at` and `last_stock_summary` onto the monitor row in `monitored_categories.json` once finished — this is the signal the frontend must poll for.

**Frontend gap (confirmed, `App.tsx:2673-2686`):** `handleSubmit` only calls `createMonitoredCategory`, closes the modal, and calls `fetchCategories()` ONCE (a single snapshot, not a poll). There is no existing polling mechanism on this page (contrast with `MonitorPage`'s `setInterval(refreshMonitors, 5000)` at `App.tsx:230-234`, which is the pattern to imitate).

**Suggested approach (Claude's discretion per CONTEXT.md):**
```tsx
// Sketch — not prescriptive on variable names, mirrors MonitorPage's setInterval(refreshMonitors, 5000) pattern
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  setSubmitting(true);
  try {
    const created = await ApiClient.createMonitoredCategory(newCategory); // row has no last_scraped_at yet
    setIsModalOpen(false);          // D-06: close immediately
    fetchCategories();               // shows new row with spinner (last_scraped_at == null/undefined)
    toast.success('Categoria adicionada. Iniciando primeira varredura…'); // D-08
    pollForScanCompletion(created.id); // NEW — short poll, e.g. every 3-5s, stop when last_scraped_at appears
  } catch (err: any) {
    toast.error('Erro ao adicionar: ' + err.message);
  } finally {
    setSubmitting(false);
  }
};
```
Row-level spinner condition: render `<RefreshCw className="animate-spin" size={14} />` (existing pattern, `App.tsx:2911`) when `category.last_scraped_at == null`. On first poll tick where `last_scraped_at` is populated, stop polling, call `handleViewProducts(category)` to auto-open the modal (D-05).

**Reused, not new:** `ApiClient.getMonitoredCategoryProducts` (`client.ts:370-372`) and `ApiClient.getMonitoredCategoryStockSummary` (`client.ts:374-378`) are the exact calls `handleViewProducts` already makes (`App.tsx:2698-2722`) — reuse this function verbatim for the auto-open, do not duplicate its fetch logic.

### Pattern 4: Lifting `HistoryList`'s collapsed state (UX-06)

**What:** `HistoryList` (`App.tsx:779-`) owns `collapsed` internally (`useState(true)`, line 781) with its own toggle button (line 834). The new top-right icon must control the same boolean from outside.
**Confirmed integration points:** rendered at `App.tsx:1602` (`SearchPage`, `type="search"`) and `App.tsx:2177` (`CrossMarketplacePage`, `type="cross"`). Both are siblings of a `page-content` div, NOT currently wrapped in anything with a header row of their own — the natural target for the icon is the shared, app-level `content-header` at `App.tsx:3215` (`<header className="content-header">`), which already has `justify-content: space-between` (`App.css:230-235`) and currently only renders the page `<h1>` on the left, leaving the right side empty on every tab.
**Two viable implementation shapes (executor's discretion per CONTEXT.md):**
1. Lift `collapsed` out of `HistoryList` into the parent page (`SearchPage`/`CrossMarketplacePage`) as a controlled prop, and render the icon button in the shared `content-header` (requires passing a callback up to the top-level component that owns `content-header`, since `content-header` lives in the outermost app shell, not inside `SearchPage`/`CrossMarketplacePage`).
2. Keep `HistoryList` self-contained but expose an imperative toggle (e.g., `forwardRef` + `useImperativeHandle`, or a small module-level/zustand toggle akin to the existing `useSearchStore` pattern already in the codebase) that the top-right icon calls without needing to lift full state to the app shell.

Given the existing `useSearchStore`/`zustand` pattern already used for search state (`frontend/src/stores/searchStore.ts`, referenced at `App.tsx:54`), option 2 via a small store slice (or a simple prop-drilled callback if the icon can live inside `SearchPage`/`CrossMarketplacePage` rather than the outer shell) is likely the lowest-friction fit — but this is explicitly Claude's discretion, not a locked decision.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Detecting when a background scan finishes | A new WebSocket channel for category-scan status | Short-interval polling of `GET /monitor/categories`, same pattern as `MonitorPage`'s existing `setInterval(refreshMonitors, 5000)` | No WS infra exists for this page today; adding one is disproportionate to a "quick win" phase and duplicates working polling infra a few hundred lines away. |
| SKU format validation | A generic form-validation library (e.g. zod, yup) | A single `RegExp.test()` call against `^ML\.05\.\d{7}$`, mirroring the existing manual CEP-digit validation already in `handleSearch`/`handleExport` | The codebase has zero validation libraries installed; one regex for one field does not justify a new dependency. |
| Brand exclusion enforcement | A new client-side Lacoste-specific filter/blocklist | The existing `list_brands(active_only=True)` chokepoint (already the sole enforcement point per STATE.md `[ARCH]`) | Per COMP-08's own requirement text and Phase 36's confirmed decision — any new client-side name-based filter would be the exact regression this phase's test guards against. |

**Key insight:** every one of the six requirements in this phase has a working analog already in the codebase (CEP validation → SKU validation; category-products render → monitor-list render; `MonitorPage` polling → category polling; `768px`/`980px` breakpoints → `.grid-category` breakpoint). The work is disciplined reuse, not invention — deviating into new patterns (new state libraries, new WS channels, new CSS methodologies) would be over-engineering for this phase's scope.

## Common Pitfalls

### Pitfall 1: Confusing `price_discount`'s semantics when naming/using the new monitor fields (D-04)
**What goes wrong:** Assuming `price_discount` is "the discounted/selling price" (the intuitive reading of the name) and writing `current_price = price_discount` directly as the new selling price, when the codebase convention (VTEX/ML/Shopify engines) is `price_discount` = discount amount and `price_full` = actual selling price.
**Why it happens:** The field names are genuinely misleading, and a second convention exists elsewhere in the SAME codebase (`RawProductBronze.calculate_landed_price`, `shipping/base.py:117`) that treats `price_discount` as if it WERE the selling price — this is an existing, unresolved inconsistency, not a spec to follow.
**How to avoid:** Follow the CONTEXT.md-locked formula literally: D-01 says `current_price = price_discount if price_discount > 0 else price_full`. Read this as: "if there's a discount amount, the effective/current price is different from price_full" — but per the actual scraped-data convention, `product.price_full` from `RawProductBronze` (as consumed in `_monitor_loop`, `price_monitor_service.py:178`) IS ALREADY the selling price. This means D-01's formula, applied verbatim against `RawProductBronze` fields, needs the executor to look at what `product.price_discount` actually contains for THIS specific case (it is `Optional[float]`, a delta) before wiring the comparison — do not assume `price_discount` alone represents a final price without checking against `price_full` first, exactly as the already-locked D-01 formula specifies.
**Warning signs:** If a test asserts `last_price_discount == 479.0` for a `price_full=479.0, price_discount=None` product with no scraped discount, that's correct (delta convention). If a test expects `price_discount` to equal a full standalone price (e.g. `319.90`) for a discounted item, verify against the actual engine output shape first — VTEX would produce something like `price_full=319.90, price_discount=160.00` (delta), not `price_discount=319.90`.

### Pitfall 2: Building a new "scan now" endpoint when one already exists
**What goes wrong:** UX-08 sounds like it needs a manual trigger endpoint; without reading `routes_monitor.py`, an implementer might add `POST /monitor/category/{id}/scan`.
**Why it happens:** CONTEXT.md's D-05/D-06 focus on frontend sequencing and leave "which endpoint" to discretion, which can read as "build one if needed."
**How to avoid:** `POST /monitor/category` ALREADY triggers the scan via `background_tasks.add_task(run_category_scan, row)` on creation (confirmed, `routes_monitor.py:73-75`) — this is not a "scan now" endpoint separate from creation, it's baked into the creation route itself. No new endpoint is needed; the only backend gap (if any) is none — the entire gap is frontend detection/feedback.
**Warning signs:** A plan task titled "add scan-trigger endpoint" or "add POST /monitor/category/{id}/scan" is very likely unnecessary — verify against `routes_monitor.py` before writing it.

### Pitfall 3: `HistoryList`'s two independent instances silently diverging
**What goes wrong:** Since `HistoryList` is mounted twice (once per tab, `type="search"` and `type="cross"`), a naive icon implementation might create two separate toggle mechanisms with subtly different behavior (e.g., one badge shows unfiltered count, the other filtered).
**Why it happens:** `HistoryList` fetches ALL history via `ApiClient.getHistoryList()` and filters client-side by `type` (`App.tsx:787`, `all.filter((h: any) => h.type === type)`) — the badge count (`filteredCount`, line 821) is already type-scoped, but a new external badge on the icon button must replicate this same filtered count, not the raw unfiltered list length.
**How to avoid:** Reuse `HistoryList`'s existing filtered `items.length` (or replicate the exact same filter) for the icon's corner badge — do not badge with the raw `getHistoryList()` response length.
**Warning signs:** Badge count on the SKU tab's icon shows the SAME number as the comparative tab's icon (would indicate the filter was dropped).

### Pitfall 4: `.grid-category` fix breaking the category-monitor's own internal spinner/loading states
**What goes wrong:** Adding `grid-template-columns: 1fr` at 768px could visually break child elements that assumed a fixed 350px sidebar width (e.g., the category-tree `<select>` dropdown, which may have `min-width` or overflow assumptions tied to the 350px column).
**Why it happens:** `.grid-category` is shared by BOTH `MonitoredCategoriesPage` and `CategoryPage` (category sweep) — a fix validated only on one surface might not generalize to the other.
**How to avoid:** UI-SPEC explicitly calls out verifying `.modal-content` and the products-modal grid (`App.tsx:2983`) at 768px as part of the same fix — test both `MonitoredCategoriesPage` AND `CategoryPage` (category sweep) at exactly 768px, not just one.
**Warning signs:** One of the two `.grid-category` consumers still shows horizontal scroll at 768px after the fix.

## Code Examples

### Existing promo-price render pattern to replicate for `MonitorPage` (UX-02)
```tsx
// Source: frontend/src/App.tsx:3009-3018 (category-monitor products, ALREADY WORKING)
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
Apply the same conditional structure inside `.monitor-pricing` (`App.tsx:417-434`), substituting `p.price_full`/`p.price_discount` for whatever field names D-04 chooses on `PriceMonitorConfig` (e.g. `m.last_price`/`m.last_price_discount`), and per UI-SPEC §2, stack vertically (`flex-direction: column`) instead of the horizontal layout used in the product-card version, to fit `.monitor-pricing`'s narrower column.

### Existing backend test pattern to extend for D-01/D-03 (UX-02)
```python
# Source: backend/tests/test_price_monitor.py — existing style, hermetic (no real I/O)
@pytest.mark.asyncio
async def test_price_monitor_promo_only_change_triggers_history():
    """D-01: uma queda de price_discount (com price_full inalterado) deve
    gerar entrada de historico e notificacao — hoje isso e silenciosamente ignorado."""
    service = PriceMonitorService()
    job_id = "test-promo-only"
    config = PriceMonitorConfig(
        job_id=job_id, url="http://example.com", brand="test-brand",
        interval_minutes=1, duration_hours=1, active=True,
        last_price=100.0,  # price_full inalterado
        # last_price_discount=0.0,  # campo novo (D-04) — nome exato a definir
    )
    service.monitors[job_id] = config

    mock_engine = MagicMock()
    mock_engine.get_pdp_product = AsyncMock(return_value={
        "url": "http://example.com", "brand": "test-brand",
        "raw_title": "Produto Teste", "raw_description": "Descricao Teste",
        "price_full": 100.0, "price_discount": 20.0,  # NOVO desconto, price_full igual
        "image_url": "http://example.com/img.jpg", "stock_availability": True,
    })

    async def stop_after_first(*a, **kw):
        config.active = False

    with patch("services.price_monitor_service.engine_factory.get_engine", return_value=mock_engine), \
         patch("services.price_monitor_service.manager.send_message", new_callable=AsyncMock) as mock_ws, \
         patch.object(service, "_save_monitors"), \
         patch("services.price_monitor_service.asyncio.sleep", new=AsyncMock(side_effect=stop_after_first)):
        await service._monitor_loop(job_id)

    assert len(config.history) == 1, "Mudanca so no desconto deve gerar historico (D-01)"
    # Verifica payload WS inclui o campo de desconto (D-03)
    price_update_calls = [c.args[0] for c in mock_ws.await_args_list if c.args[0].get("type") == "price_update"]
    assert price_update_calls, "Deveria emitir price_update"
    assert "price_discount" in price_update_calls[0], "D-03: payload WS deve incluir price_discount"
```
Follow the same hermetic style already used (in-memory `PriceMonitorConfig`, mocked `engine_factory.get_engine`, mocked `manager.send_message`, `patch.object(service, "_save_monitors")` to avoid file I/O, `asyncio.sleep` side-effect to stop the loop after one iteration).

### Existing regression-test pattern to extend for COMP-08
```python
# Source: backend/tests/test_brand_active.py:184-231 — template for the new COMP-08 test
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
This mirrors `TestMarketplacesInBrandsJson`'s structure exactly (reads real `brands.json` via the real `brand_service` singleton, asserts on the filtered key set) — no mocking needed since `brands.json` already has `lacoste.is_active=false` persisted (per STATE.md blocker note).

## State of the Art

Not applicable — this phase does not involve external libraries or APIs whose best practices have shifted; it is entirely internal-convention work.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The lowest-friction way to lift `HistoryList`'s `collapsed` state is via a small zustand slice (mirroring `useSearchStore`) rather than prop-drilling to the app shell | Architecture Patterns → Pattern 4 | If wrong, the executor may prop-drill instead — functionally equivalent, slightly more boilerplate; no behavioral risk, purely an implementation-shape suggestion already marked as Claude's discretion in CONTEXT.md. |
| A2 | Polling every 3-5 seconds (mirroring `MonitorPage`'s `5000`ms interval) is an acceptable cadence for auto-sweep completion detection | Architecture Patterns → Pattern 3 | If the actual category scan takes much longer than expected (e.g., large catalogs), a longer poll interval or a max-attempts/timeout guard may be needed — not specified in CONTEXT.md, left to executor judgment. |

**If this table is empty:** N/A — two low-risk implementation-shape assumptions are logged above; neither affects a locked decision from CONTEXT.md.

## Open Questions

1. **Exact field names for D-04 (`last_price_full`/`last_price_discount` vs. alternatives)**
   - What we know: CONTEXT.md explicitly defers this to Claude's discretion; the only hard constraint is that `last_price` must keep meaning "effective/current price" for frontend backward-compatibility.
   - What's unclear: Whether to add ONE new field (`last_price_discount`, delta-only, computing "original price" via `last_price + last_price_discount` the same way `App.tsx:3009-3018` already does) or TWO new fields (`last_price_full` + `last_price_discount`, mirroring `RawProductBronze` exactly).
   - Recommendation: Add a single `last_price_discount: Optional[float] = None` field to `PriceMonitorConfig` (and to `PriceHistoryEntry` for historical accuracy), keep `last_price` as the effective/current price per D-01's formula — this is the minimal change that satisfies D-01/D-02/D-03 and reuses the exact `App.tsx:3009-3018` rendering formula (`last_price + last_price_discount` = pre-discount price) without introducing a redundant `last_price_full` that would need to always equal the pre-D-01-formula value.

2. **Poll cadence and termination condition for UX-08's completion detection**
   - What we know: No existing polling mechanism exists on `MonitoredCategoriesPage`; `MonitorPage`'s analogous poll runs indefinitely every 5s with no stop condition (it's a persistent dashboard).
   - What's unclear: The auto-sweep poll should almost certainly STOP once `last_scraped_at` appears (unlike `MonitorPage`'s permanent poll) — CONTEXT.md doesn't specify a timeout for pathological cases (e.g., a scan that never completes due to anti-bot blocking).
   - Recommendation: Poll every 3-5s, stop on first successful detection of a non-null `last_scraped_at` for the new category's `id`, AND add a reasonable max-attempts cap (e.g., 20 attempts / ~60-100s) that silently stops polling and leaves the row's spinner in place (the operator can still manually refresh/reopen later) — avoids an infinite client-side timer if a scan hangs.

## Environment Availability

Skipped — this phase has no new external dependencies (no new packages, no new services, no new CLI tools). All required tooling (Node/npm, Python/pytest) is already installed and used by the existing test suite, confirmed working (`python -m pytest tests/test_price_monitor.py -q` → 6 passed).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Backend framework | pytest + pytest-asyncio (confirmed: `backend/tests/test_price_monitor.py` runs green, `6 passed in 1.34s`) |
| Backend config file | none found (no `pytest.ini`/`pyproject.toml` at `backend/` root) — discovery relies on default pytest conventions (`test_*.py` in `backend/tests/`) |
| Frontend framework | **none** — no test runner in `frontend/package.json` (confirmed: only `dev`/`build`/`lint`/`preview` scripts). Matches STATE.md `[44-05/typecheck-tdd]` precedent: "Frontend has no test runner, so TDD coverage uses a committed TypeScript compile-time contract file plus `npm run build`." |
| Quick run command (backend) | `cd backend && python -m pytest tests/test_price_monitor.py tests/test_brand_active.py -q` |
| Full suite command (backend) | `cd backend && python -m pytest -q` |
| Frontend verification | `cd frontend && npm run build` (TypeScript compile + Vite build catches type errors; no unit-test assertions possible without adding a runner, which is out of scope for a UX quick-win phase) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|--------------------|--------------|
| UX-01 | `.grid-category` collapses to 1 column at ≤768px | manual (visual, viewport resize) | N/A — CSS-only, no automated DOM/viewport test infra exists | N/A — manual UAT required (see Phase 44 precedent for `44-HUMAN-UAT.md` pattern) |
| UX-02 | Promo change with unchanged `price_full` generates history + WS `price_update` with discount field | unit | `pytest tests/test_price_monitor.py::test_price_monitor_promo_only_change_triggers_history -x` | ❌ Wave 0 — new test to add, following existing file's style |
| UX-02 | Monitor list payload includes new discount field(s) with no new network call | unit/contract | `pytest tests/test_price_monitor.py -k discount -x` | ❌ Wave 0 |
| UX-06 | History icon toggles panel, badge count matches type-filtered items | manual (visual) | N/A — no frontend test runner | Manual UAT |
| UX-07 | SKU regex rejects non-matching input on blur/submit, accepts valid pattern | manual (visual) + `npm run build` (type-check only) | `cd frontend && npm run build` | Manual UAT for behavior; build for type-safety |
| UX-08 | Category creation auto-triggers scan, row shows spinner, modal auto-opens on completion | integration (backend: scan fires) + manual (frontend: UI sequence) | `pytest tests/test_category_monitor.py -k auto_scan -x` (backend trigger already covered implicitly by `routes_monitor.py`'s existing behavior — new test should assert `background_tasks.add_task` is called, or that `run_category_scan` populates `last_scraped_at`) | ❌ Wave 0 — no `test_category_monitor.py` currently exists (verify via `Glob` before creating) |
| COMP-08 | Lacoste absent from `list_brands(active_only=True)` | unit | `pytest tests/test_brand_active.py::TestLacosteExcludedFromActiveOnly -x` | ❌ Wave 0 — new test class, following `TestMarketplacesInBrandsJson`'s exact pattern |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_price_monitor.py tests/test_brand_active.py -q` (backend tasks); `cd frontend && npm run build` (frontend tasks)
- **Per wave merge:** `cd backend && python -m pytest -q` (full backend suite) + `cd frontend && npm run build`
- **Phase gate:** Full backend suite green + successful frontend build + manual UAT for UX-01/UX-06/UX-07/UX-08 visual/interaction behaviors before `/gsd-verify-work` (mirrors `44-HUMAN-UAT.md` precedent for phases with unavoidable manual verification steps).

### Wave 0 Gaps
- [ ] Confirm whether `backend/tests/test_category_monitor.py` exists before Wave 0 (not found via initial glob — verify with fresh `Glob` at plan time, since `category_monitor_service.py` currently has no dedicated test file found in this research pass).
- [ ] New test: `test_price_monitor.py::test_price_monitor_promo_only_change_triggers_history` (D-01/D-03 coverage) — sketch provided above.
- [ ] New test class: `test_brand_active.py::TestLacosteExcludedFromActiveOnly` (COMP-08 regression) — sketch provided above.
- [ ] `38-HUMAN-UAT.md` — this phase needs a human-UAT artifact (mirroring `44-HUMAN-UAT.md`) for the 4 requirements with no automated test surface (UX-01 viewport check, UX-06 icon placement/badge, UX-07 inline error copy/behavior, UX-08 full modal-close→spinner→auto-open sequence).

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | Unchanged — existing shared API key auth, not touched by this phase. |
| V3 Session Management | No | Not touched. |
| V4 Access Control | No | Not touched — `active_only` chokepoint is a data-visibility filter, not an access-control boundary between users (single shared-key system). |
| V5 Input Validation | Yes | SKU regex (`^ML\.05\.\d{7}$`) is a **client-side UX validation**, not a security boundary — the backend SKU-search endpoint must continue to independently validate/sanitize input server-side (already the case; this phase does not change backend SKU handling). Frontend validation alone must never be treated as sufficient input sanitization. |
| V6 Cryptography | No | Not touched. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----------------------|
| Client-side-only validation bypass (SKU field) | Tampering | Confirm (out of scope to fix, but worth flagging for the plan) that the backend SKU-search route already validates/rejects malformed SKUs server-side independent of the new frontend regex — frontend validation is a UX improvement, not a security control, per ASVS V5 guidance. |
| Stale/cached brand list bypassing `active_only` filter on the client | Information Disclosure (minor) | None needed beyond existing chokepoint — `list_brands(active_only=True)` is always re-fetched per page load; no client-side caching of the brand list beyond component state was found. |

## Sources

### Primary (HIGH confidence — direct code reads in this repository)
- `frontend/src/App.css` — lines 181-206, 366-370, 595-694, 1052-1133, 1270-1305 (breakpoint conventions, `.grid-category`, `.search-*` classes, `.cep-*` validation classes)
- `frontend/src/App.tsx` — lines 1-57 (imports), 200-234 (`MonitorPage` polling), 395-434 (`.monitor-pricing`), 770-885 (`HistoryList`), 1260-1310 (CEP validation logic), 1460-1610 (`SearchPage` render, `.search-main-row`), 2130-2180 (`CrossMarketplacePage` SKU/CEP), 2600-2940 (`MonitoredCategoriesPage` full lifecycle), 2984-3020 (product-card promo render), 3195-3231 (`content-header` app shell)
- `frontend/src/api/client.ts` — lines 351-380 (`ApiClient` monitored-category methods)
- `frontend/package.json` — confirmed no test runner installed
- `backend/api/routes_monitor.py` — full file (confirms auto-sweep trigger already exists)
- `backend/services/category_monitor_service.py` — full file (`run_category_scan` behavior, `last_scraped_at` write)
- `backend/services/price_monitor_service.py` — lines 140-239 (`_monitor_loop`, `has_change`/`current_price`/WS payload)
- `backend/core/models.py` — lines 95-170 (`RawProductBronze`, `price_discount` semantics, `calculate_landed_price`), 270-319 (`PriceMonitorConfig`/`PriceHistoryEntry`)
- `backend/services/vtex_api_scraper.py` — lines 330-350, 1000-1042 (`price_discount = list - sale`, confirms delta convention)
- `backend/services/engines/mercado_livre_engine.py` — line 632 (`price_discount=item.get("preco_desconto")`)
- `backend/services/shopify_api_client.py` — lines 209-213 (`price_discount` delta convention for Shopify)
- `backend/services/shipping/base.py` — line 117 (confirms the SECOND, inconsistent `price_discount`-as-selling-price convention — flagged as pre-existing, out-of-scope bug)
- `backend/api/routes_product.py` — lines 61-72 (`GET /monitors` returns raw `PriceMonitorConfig` list, confirms zero-route-change field propagation)
- `backend/tests/test_price_monitor.py` — full file (test style/pattern template)
- `backend/tests/test_brand_active.py` — full file (regression-test style/pattern template for COMP-08)
- `backend/data/price_monitors.json` — grepped, confirmed no `price_full`/`price_discount` keys currently persisted (only `last_price`)
- Live command run: `cd backend && python -m pytest tests/test_price_monitor.py -q` → `6 passed in 1.34s` (confirms test infra works as documented)
- Live command run: `node --version` (v24.13.1), `npm --version` (11.8.0) — confirms toolchain present

### Secondary (MEDIUM confidence)
- None — all findings in this research were directly verified against repository source, not inferred from external documentation (this phase has no external-library dependency to research).

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies; all reused libraries confirmed present in `package.json`/backend imports.
- Architecture: HIGH — every pattern cited was read directly from source, including the surprising discovery that UX-08's backend trigger already exists.
- Pitfalls: HIGH — the `price_discount` semantic confusion (Pitfall 1) was cross-verified against 4 independent source locations (VTEX, ML, Shopify engines + the contradicting `shipping/base.py`/`calculate_landed_price` usage).

**Research date:** 2026-07-01
**Valid until:** 2026-07-31 (30 days — stable internal codebase, no external API/library drift risk for this phase's scope)
