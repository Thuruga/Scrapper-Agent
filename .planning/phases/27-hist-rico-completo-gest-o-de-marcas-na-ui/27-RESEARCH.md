# Phase 27: Histórico Completo + Gestão de Marcas na UI - Research

**Researched:** 2026-06-20
**Domain:** Full-stack feature wiring — FastAPI sync endpoint persistence + React/TS state propagation (no new libraries)
**Confidence:** HIGH (everything verified by direct code reading of the live repo)

## Summary

This phase is a **wiring + small-feature phase**, not a research-heavy one. All three deliverables are implementable with existing code patterns already present in the repo — no new dependencies, no new libraries, no external services. The work is: (1) mirror an existing persistence block into one more endpoint, (2) declare-and-pass two React props that the child components already expect, and (3) extend an existing settings list with a toggle and a new `ApiClient` method that calls an endpoint that already exists from Phase 25.

The single most important finding — and the biggest landmine — is a **result-shape mismatch between how the comparative search must be stored and how the cross-marketplace search is stored**. The two history consumers (`SearchPage` and `CrossMarketplacePage`) read the stored `results` field differently. If HIST-01 stores the wrong shape, the entry will save fine and even appear in the list, but reopening will silently render an empty result. This must be locked at plan time. See Pitfall 1 and the "Stored Result Shape Contract" table.

The second finding is that **no history-list UI exists anywhere in the frontend today** — only the `ApiClient` methods (`getHistoryList`/`getHistoryDetail`/`deleteHistory`) and the two preloaded `useEffect` hooks. So HIST-02 is not "reconnect an existing list"; it is "build a per-tab history list section from scratch and wire its click handler up through `App.tsx`." CONTEXT D-01 (history sectioned per tab) and the Claude's-discretion note about App-vs-local state both apply here.

**Primary recommendation:** Three independent slices, sequenced HIST-01 → HIST-02 → MGMT-02. Lock the stored-result-shape contract for the comparative search before writing any code (store `ComparisonResult.model_dump()["results"]` — the inner list — OR change `SearchPage`'s preloaded handler; pick one, document it). Use App-level `preloadedJobId` state because Success Criterion #2 explicitly names `App.tsx` propagation.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Persist comparative search (HIST-01) | API / Backend (`routes_search.py`) | Storage (`search_history_service` → `data/search_history.json`) | The sync endpoint owns create+complete in one request; service owns JSON I/O |
| History list display per tab (HIST-02) | Browser / Client (`SearchPage`, `CrossMarketplacePage`) | API (`GET /history`) | List is a per-tab UI section; filtering by `type` is client-side |
| Reopen propagation (HIST-02) | Frontend container (`App.tsx`) | Browser components (child pages) | SC#2 explicitly requires `App.tsx` to own/propagate `preloadedJobId` |
| Brand active toggle (MGMT-02) | Browser / Client (`SettingsPage`) | API (`PATCH /brands/{key}/active`, exists) | UI control consuming an endpoint already shipped in Phase 25 |
| Brand list incl. inactive (MGMT-02) | API (`GET /brands/`, returns inactive) | Browser (`SettingsPage` visual distinction) | Backend already opt-out of `active_only`; UI only renders distinction |

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Histórico apresentado **seccionado por tipo de busca** — NÃO uma aba dedicada. Histórico de **comparativas** vive dentro de `SearchPage`; histórico de **SKU** vive dentro de `CrossMarketplacePage`. Cada seção lista apenas as buscas daquele tipo.
- **D-02:** Cada entrada exibe **rótulo + badge de tipo + data/hora + status**. Comparativa rotulada por marcas/termo (ex.: "Reserva, Aramis · 3 marcas"); SKU mantém `"SKU: {query}"`. Badge distingue Comparativa vs SKU. Status (Concluída / Falhou / Em andamento) visível.
- **D-03:** Ações por entrada: **reabrir** (clique) + **excluir** (`DELETE /history/{job_id}`, já existente).
- **D-04:** Clicar reexibe resultados salvos **sem nova raspagem**, na aba correspondente. A correção da propagação de `preloadedJobId` a partir de `App.tsx` é **obrigatória** — o componente já tem o `useEffect`, falta o App alimentar a prop.
- **D-05:** Ao reabrir, **sobrescreve direto** a busca/resultado atual na aba. Risco baixo porque agora TODA busca fica salva (HIST-01).
- **D-06:** Apenas entradas **COMPLETED** reabrem. FAILED aparece com badge de erro e NÃO reabre; PENDING aparece com indicador "em andamento". Sem cliques quebrados.
- **D-07:** `POST /search` (comparativa) passa a persistir com `type="search"`. Endpoint é síncrono → criar+concluir o job no mesmo request é aceitável. Padrão de referência: o bloco que `POST /search/cross-marketplace` já usa.
- **D-08:** Unificar add/remover/ativar-desativar **estendendo a aba "Marcas" existente** (`SettingsPage`, `App.tsx:1344`). Mantém o form de adicionar; em cada linha adiciona **toggle ativo/inativo** + botão excluir. Mínima reescrita.
- **D-09:** Lista mostra **TODAS** as marcas (ativas e inativas) com **distinção visual** para inativas. `GET /brands/` já retorna inativas.
- **D-10:** **Toggle = `is_active` on/off** (reversível, via `PATCH /brands/{key}/active`). **Excluir = `DELETE` permanente, exige confirmação.** Duas ações distintas.

### Claude's Discretion
- Posição/forma exata da seção de histórico dentro de cada página (topo, painel colapsável, etc.).
- Formato preciso do rótulo da comparativa (marcas + termo) e estilo do badge.
- Estado vazio do histórico; limite/paginação de itens exibidos.
- Mecânica de propagação do job ao reabrir (estado em `App.tsx` vs estado local) — desde que reexiba sem raspar e a propagação a partir de `App.tsx` (critério #2) seja honrada.
- Adição da nova chamada `PATCH` no `frontend/src/api/client.ts`.

### Deferred Ideas (OUT OF SCOPE)
- PERS-01 (busca viva sobrevive à troca de aba) → Phase 28.
- COMP-01 (onboarding de novas marcas) → Phase 26.
- Diagnóstico de motores → Phase 29.
- Relevância/discriminação de modelo (MODEL-01/02) → Phase 23.
- Reforço de discriminação de modelo (todo pendente) — mantido no backlog, fora do escopo.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HIST-01 | Buscas comparativas também salvas no histórico (hoje só SKU é persistido) | §"HIST-01 — Comparative Persistence": exact insertion points in `POST /search` (`routes_search.py:140-179`), mirror of cross-marketplace block (`routes_search.py:413-450`), stored-result-shape contract |
| HIST-02 | Reabrir qualquer busca salva e reexibir resultados (corrige `preloadedJobId` nunca propagado de `App.tsx`) | §"HIST-02 — Reopen Wiring": App-level `preloadedJobId` state, `renderTab` prop passing (`App.tsx:1798-1799`), child `useEffect` contracts (`App.tsx:651-660`, `:974-985`), per-tab history list (built from scratch) |
| MGMT-02 | Campo único de gestão de marcas (adicionar / remover / ativar-desativar) | §"MGMT-02 — Brand Management UI": new `ApiClient.setBrandActive` (PATCH), `SettingsPage` row toggle + inactive visual distinction, endpoint `PATCH /brands/{key}/active` confirmed live (`routes_brands.py:176-182`) |
</phase_requirements>

---

## Standard Stack

**No new packages.** This phase uses only what is already installed and in use.

### Core (existing, verified in repo)
| Library | Version (verified) | Purpose | Why Standard |
|---------|--------------------|---------|--------------|
| FastAPI | `>=0.110.0` (requirements.txt) | Routes `POST /search`, `PATCH /brands/{key}/active` | Already the API framework |
| Pydantic | `>=2.0` (requirements.txt) | `ComparisonResult`, `SearchHistory`, `BrandActiveUpdate` models | Already the model layer; `.model_dump(mode="json")` is the serialization tool |
| React | `^19.2.5` (frontend/package.json) | `SearchPage`/`CrossMarketplacePage`/`SettingsPage`/`App` | Already the UI framework |
| TypeScript | `~6.0.2` (frontend/package.json) | Type-checked build (`tsc -b`) | Already the build gate |
| sonner (`toast`) | `^2.0.7` | Error/success toasts on reopen + toggle | Already used in both child pages |
| lucide-react | `^1.14.0` | Icons for badges/toggle (e.g. `History`, `Power`, `Trash2`) | Already the icon set in `App.tsx` |

### Supporting (existing)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| clsx / tailwind-merge | `^2.1.1` / `^3.5.0` | Conditional classNames for active/inactive visual distinction | If using utility classes for the inactive badge/opacity |
| framer-motion | `^12.38.0` | Optional entry animation for history list / toggle | Discretionary polish only |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| App-level `preloadedJobId` state | Page-local state read from a shared store / URL param | SC#2 *explicitly names `App.tsx` propagation* — App-level state is the literal requirement; a store (zustand) is Phase 28's concern (PERS-01), do not pull it forward |
| Storing comparative results in history JSON | A real DB table | Out of scope; cross-marketplace already stores full results in the same JSON file — consistency wins (CONTEXT note) |

**Installation:** None. `npm install` / `pip install` are NOT part of this phase.

## Package Legitimacy Audit

> Not applicable — this phase installs **zero** external packages. All code reuses libraries already present in `requirements.txt` and `frontend/package.json`. slopcheck/registry verification skipped because nothing is being added.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
HIST-01 (persist comparative)
  Browser SearchPage.handleSearch
        │ POST /search { query, brands?, ... }
        ▼
  routes_search.py:search_products  (SYNC, single request)
        │ 1. create_job(job_id, label, brands, type="search")   ← NEW
        │ 2. search_all_brands(...)  (existing)
        │ 3. update_job(job_id, "COMPLETED", results=<inner list>) ← NEW
        │    (on exception → update_job("FAILED", error=str(e)))   ← NEW
        ▼
  search_history_service → data/search_history.json
        │ returns ComparisonResult (+ job_id echoed for client)
        ▼
  Browser renders results immediately (unchanged path)

HIST-02 (reopen)
  GET /history ─► [SearchHistory...]  (client filters type==="search" or "cross" per tab)
        │
  Browser per-tab History list (NEW UI)
        │ click entry (COMPLETED only) → onReopen(job_id)
        ▼
  App.tsx setPreloadedJobId(job_id) + setActiveTab(<inherent tab>)   ← FIX
        │ renderTab passes preloadedJobId + onClearPreloadedJob       ← FIX
        ▼
  Child useEffect([preloadedJobId]) → GET /history/{job_id}
        │ setResults(<shape per stored contract>)
        ▼
  Re-display WITHOUT re-scraping

MGMT-02 (brand mgmt)
  SettingsPage row
        │ toggle → ApiClient.setBrandActive(key, is_active)  ← NEW client method
        ▼  PATCH /brands/{key}/active { is_active }  (EXISTS, Phase 25)
  brand_service.set_active → persists is_active
        │ onRefresh() → GET /brands/ (returns inactive too)
        ▼  list re-renders with active/inactive visual distinction
```

### Stored Result Shape Contract (LANDMINE — decide at plan time)

The history `results` field is `Optional[Any]` (`core/models.py:255`) so anything serializes. The danger is the *consumer* contract, which differs per tab:

| Tab | Live search sets `results =` | Stored `results` today | Reopen handler reads | Expected stored shape |
|-----|------------------------------|------------------------|----------------------|------------------------|
| **SKU** (`cross`) | `data` = dict `{ results:[...], reference_product, job_id }` | the **full dict** (`update_job(results=result)`, `routes_search.py:441`) | `setResults(withDisplayOrder(res.results))` — uses `res.results` (the dict) and reads `.results` inside via `data.results` (`App.tsx:978`, `:921`) | **full dict** — already correct, do not touch |
| **Comparative** (`search`) | `data` = `ComparisonResult` `{ query, brands_searched, results:[BrandSearchResult] }` (`routes_search.py:175`); render reads `results.results` (`App.tsx:843,847`) | **nothing today** | `setResults({ results: res.results, query: res.query, brands_searched: res.brands })` (`App.tsx:655`) — wraps `res.results` as the inner `.results` array | **`res.results` MUST be the inner `List[BrandSearchResult]` array**, i.e. store `ComparisonResult.model_dump(mode="json")["results"]`, NOT the whole `ComparisonResult` object |

**Why this matters:** if HIST-01 stores the whole `ComparisonResult` (mirroring how cross stores the whole dict), then on reopen `res.results` would be `{query, brands_searched, results:[...]}`, and `SearchPage` would set `results.results = {query,...}` (an object, not an array). The render at `App.tsx:843` does `Array.isArray(results.results) ? ... : brands.map(...)` → it would fall through to "all brands, zero products" and **silently show empty columns**. The entry saves, lists, and clicks fine — it just shows nothing. This is the highest-risk bug in the phase.

**Two valid resolutions (planner picks ONE, documents it):**
- **(A) Store the inner list (recommended, zero frontend change):** `update_job(job_id, "COMPLETED", results=result.model_dump(mode="json")["results"])`. Matches the existing `SearchPage` preloaded `useEffect` exactly. `res.query`/`res.brands` come from the `SearchHistory` record's own `query`/`brands` fields, which the handler already reads.
- **(B) Store the whole object + adjust the handler:** store `result.model_dump(mode="json")` and change `App.tsx:655` to `setResults({ results: res.results.results, query: res.results.query, brands_searched: res.results.brands_searched })`. More change, more risk, no benefit.

Recommendation: **(A)**. `[VERIFIED: code read — routes_search.py:175,441; App.tsx:655,843,978]`

### Comparative History Label Derivation (D-02)

`POST /search` receives `request.query` (the term) and optional `request.brands` (list of brand keys). The `SearchHistory` model stores `query: str` and `brands: List[str]` independently. For the label "Reserva, Aramis · 3 marcas" the planner has two clean options:

- Store `query=request.query` (the raw term) and `brands=target_brands`; let the **frontend** compose the display label from `brands.length` + the term. This keeps `SearchHistory.query` clean and reusable (e.g. re-running). `target_brands` is already computed at `routes_search.py:157-161` (it resolves to all active brands + virtual marketplaces when `request.brands` is omitted). `[VERIFIED: routes_search.py:157-161]`
- OR pre-compose a display string into `query` (mirrors how cross stores `query="SKU: {display_query}"`, `routes_search.py:421`). Simpler frontend, but couples storage to presentation.

Recommendation: store `query=request.query` + `brands=target_brands`; compose label in the frontend (D-02 format is explicitly UI-SPEC discretion). Note the `SearchPage` reopen handler does `if (res.query) setQuery(res.query)` (`App.tsx:656`) — so keeping `query` as the raw term also correctly repopulates the search box on reopen. Storing a "Reserva, Aramis · 3 marcas" string into `query` would wrongly dump that into the search input. **This is a second reason to keep `query` raw.** `[VERIFIED: App.tsx:656]`

### App.tsx Reopen Wiring (HIST-02, SC#2)

Current state (verified):
- `App` (`App.tsx:1779`) declares `activeTab`, `brands`, sidebar flags — **no `preloadedJobId`**.
- `renderTab` (`App.tsx:1795`) renders `<SearchPage brands={brands} />` (`:1798`) and `<CrossMarketplacePage />` (`:1799`) — **neither passes `preloadedJobId` nor `onClearPreloadedJob`**.
- Both child pages already accept those props and have the loading `useEffect` (`App.tsx:641,651-660` and `:910,974-985`). They are dead props today.

Minimal fix (recommended pattern):
```tsx
// App.tsx — inside App()
const [preloadedJobId, setPreloadedJobId] = useState<string | null>(null);

// reopen handler given to the per-tab history lists:
const handleReopen = (jobId: string, type: 'search' | 'cross') => {
  setActiveTab(type === 'cross' ? 'cross' : 'search'); // tab is inherent (D-01)
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

**Edge case to guard:** a single shared `preloadedJobId` is fine because tabs are mutually exclusive (only one renders at a time) and `handleReopen` sets the correct tab. But because the same value feeds both pages, ensure the child clears it after consuming (the child's `handleSearch` already calls `onClearPreloadedJob()` at `App.tsx:678`). Consider also clearing `preloadedJobId` on tab switch to avoid a stale reopen firing when the user manually navigates. Low risk; planner's discretion (the `useEffect` only fires when `preloadedJobId` changes, and reopening sets it fresh each time). `[VERIFIED: App.tsx:678]`

Since the history list lives *inside* each page (D-01), an alternative is for each page to own its own list and a local `preloadedJobId`. **But SC#2 literally requires `App.tsx` propagation** ("o `preloadedJobId` é propagado corretamente por `App.tsx`"), so the App-level state above is the contract-satisfying choice. If the list is rendered inside the page, the page can call a prop callback `onReopen` that bubbles up to `App.handleReopen` — keeping the visual placement local while propagation stays at App level.

### Per-Tab History List (built from scratch)

`getHistoryList()` returns the full `[SearchHistory]` array (newest-first, `search_history_service.list_jobs()` sorts desc). The list is **not rendered anywhere today** (verified — only `getHistoryDetail` is consumed by the two `useEffect`s). Each tab must:
1. Call `ApiClient.getHistoryList()` (on mount + after a new search completes + after delete).
2. Filter client-side: `SearchPage` shows `type === 'search'`; `CrossMarketplacePage` shows `type === 'cross'`.
3. Render label + type badge + `created_at` (format) + status badge (D-02).
4. On click: only `status === 'COMPLETED'` triggers `onReopen(job_id, type)` (D-06). FAILED → error badge, no click; PENDING → "em andamento" indicator, no click.
5. Delete button → `ApiClient.deleteHistory(job_id)` → refresh list.

The list does not need a new endpoint; `GET /history` returns all and the client filters by `type`. (Optional future optimization: a `?type=` query param — out of scope, client filter is sufficient given 30-day retention bounds the list size.)

### MGMT-02 — Brand Management UI

`ApiClient` has no PATCH method. Add one mirroring the existing request pattern (`client.ts:21-45`):
```ts
// frontend/src/api/client.ts
static setBrandActive(brandKey: string, isActive: boolean) {
  return this.request(`/brands/${brandKey}/active`, {
    method: 'PATCH',
    body: JSON.stringify({ is_active: isActive }),
  });
}
```
`PATCH /brands/{brand_key}/active` exists and is live (`routes_brands.py:176-182`), body `{ is_active: boolean }` (`BrandActiveUpdate`, `models.py:235-238`), returns the updated `DynamicBrand`, 404 if missing. `[VERIFIED: routes_brands.py:176-182, models.py:235]`

`SettingsPage` (`App.tsx:1344-1453`) currently renders each brand row with only a delete button (`:1438-1446`). Extend the row (D-08/D-10):
- Add a toggle that calls `ApiClient.setBrandActive(b.brand_key, !b.is_active)` then `onRefresh()`.
- Keep delete as a separate confirm-gated action (`handleDeleteBrand` already `confirm()`s, `:1350`).
- Render inactive brands with visual distinction (opacity/badge) keyed off `b.is_active` (D-09). `GET /brands/` returns `is_active` on every `DynamicBrand`; the three injected virtual marketplaces (mercado_livre/netshoes/amazon, `routes_brands.py:103-129`) are constructed **without** `is_active` so they default to `True` — they should NOT show a toggle (they aren't real toggleable brands). Guard the toggle so it only renders for non-virtual brands, or accept that toggling a virtual marketplace 404s server-side (it isn't in `brand_service`). **Recommend: hide the toggle for the three virtual marketplace keys.** `[VERIFIED: routes_brands.py:103-129; models.py DynamicBrand.is_active default True]`

### Recommended Project Structure
No structural change. All edits land in existing files:
```
api/routes_search.py        # HIST-01: create_job/update_job in POST /search
frontend/src/App.tsx        # HIST-02: preloadedJobId state + renderTab props + per-tab history list; MGMT-02: SettingsPage toggle
frontend/src/api/client.ts  # MGMT-02: setBrandActive PATCH method
tests/test_search_history_comparative.py  # NEW: backend HIST-01 unit/integration test
```

### Anti-Patterns to Avoid
- **Storing the whole `ComparisonResult` then expecting `SearchPage` to render it** — shape mismatch, silent empty render (Pitfall 1).
- **Pre-composing the display label into `SearchHistory.query`** — pollutes the reopen search-box repopulation (`App.tsx:656`).
- **Introducing a zustand/global store for `preloadedJobId`** — that is Phase 28 (PERS-01) scope; SC#2 wants App.tsx state.
- **Making `POST /search` async/background** — STATE.md `[ARCH]` decision: do not convert search to async job/polling. Keep create+complete in the same sync request (D-07).
- **Rendering a toggle on virtual marketplaces** — they have no backend record; PATCH would 404.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Persisting a job | New persistence helper | `search_history_service.create_job` / `update_job` (exists, `search_history_service.py:52-65`) | Already handles JSON I/O + 30-day cleanup |
| Brand active toggle endpoint | New route | `PATCH /brands/{key}/active` (Phase 25, `routes_brands.py:176`) | Already shipped and tested (`tests/test_brand_active.py`) |
| History fetch/list/detail/delete | New client methods | `ApiClient.getHistoryList/getHistoryDetail/deleteHistory` (`client.ts:91-103`) | Already exist |
| Pydantic→JSON for storage | Manual dict building | `result.model_dump(mode="json")` | Handles datetime/nested models correctly; `_save_history` already uses `model_dump(mode="json")` |

**Key insight:** This phase is ~90% reuse. The only genuinely new code is the per-tab history list UI component and one `ApiClient` PATCH method. Everything else is connecting existing parts.

## Runtime State Inventory

> Not a rename/refactor/migration phase — this section is **N/A**. No stored keys, service configs, OS registrations, secrets, or build artifacts are being renamed. The only persisted data touched is `data/search_history.json`, which *gains* new `type="search"` records (additive, no migration of existing records needed). Existing `type="cross"` records remain valid and reopenable. **Verified: no destructive schema change — `SearchHistory.results` is `Optional[Any]`, so adding comparative records requires no model migration.**

## Common Pitfalls

### Pitfall 1: Comparative result shape mismatch (silent empty render)
**What goes wrong:** Mirroring the cross-marketplace block verbatim stores the full `ComparisonResult`; `SearchPage`'s reopen handler then wraps an object where it expects an array, and the render falls through to empty columns.
**Why it happens:** `update_job(results=result)` in cross stores a *dict whose `.results` is the list*; `SearchPage` expects `res.results` to *be* the list.
**How to avoid:** Store `result.model_dump(mode="json")["results"]` (Resolution A). Keep `SearchHistory.query`/`brands` for label + search-box repopulation.
**Warning signs:** Entry appears in history, click works, but all brand columns show "Nenhum resultado encontrado" despite a successful original search.

### Pitfall 2: Label string leaking into the search box on reopen
**What goes wrong:** If you store a composed label (e.g. "Reserva, Aramis · 3 marcas") in `SearchHistory.query`, reopening dumps that string into the `query` input (`App.tsx:656`).
**How to avoid:** Store the raw search term in `query`; compose the display label in the frontend from `brands` + `query`.

### Pitfall 3: FAILED/PENDING entries crashing reopen
**What goes wrong:** Clicking a FAILED entry calls `getHistoryDetail`, gets `results: null`, and the render reads `.results` of null → blank or error.
**Why it happens:** Only COMPLETED has results (D-06).
**How to avoid:** Gate the click handler on `status === 'COMPLETED'`; render FAILED/PENDING as non-clickable with their own badges.

### Pitfall 4: New search must refresh the per-tab history list
**What goes wrong:** User runs a comparative search; it persists server-side, but the on-screen history list doesn't show it until reload.
**How to avoid:** After a successful `handleSearch`, re-call `getHistoryList()` (or optimistically prepend). The backend already persisted it synchronously, so a refetch returns it immediately.

### Pitfall 5: Exception path must mark FAILED
**What goes wrong:** If `search_all_brands` throws, the job stays PENDING forever.
**How to avoid:** Wrap the search in try/except mirroring cross (`routes_search.py:444-450`): on exception `update_job("FAILED", error=str(e))` then re-raise. Note `POST /search` currently has **no try/except** (`routes_search.py:140-179`) — adding one is part of HIST-01.

### Pitfall 6: `POST /search` `job_id` not returned to client
**What goes wrong:** The current `POST /search` returns a bare `ComparisonResult` (no `job_id`). If the frontend wants to reflect the just-created entry it has no id.
**How to avoid:** Either refetch the list (Pitfall 4 approach, simplest) or echo `job_id`. Note `response_model=ComparisonResult` (`routes_search.py:133`) would strip extra fields — refetch is cleaner than changing the response model. **Recommend refetch.**

## Code Examples

### HIST-01 — persistence block to add in `POST /search` (`routes_search.py:140-179`)
```python
# Source: mirrors routes_search.py:413-450 (cross-marketplace), adapted for sync ComparisonResult
import uuid
from services.search_history_service import search_history_service

job_id = str(uuid.uuid4())
search_history_service.create_job(
    job_id=job_id,
    query=request.query,            # raw term (Pitfall 2)
    brands=target_brands,           # already computed at routes_search.py:157-161
    type="search",
)
try:
    brand_results = await engine_factory.search_all_brands(...)  # existing call
    result = ComparisonResult(
        query=request.query,
        brands_searched=target_brands,
        results=brand_results,
    )
    search_history_service.update_job(
        job_id=job_id,
        status="COMPLETED",
        results=result.model_dump(mode="json")["results"],  # inner list (Resolution A / Pitfall 1)
    )
    return result
except Exception as e:
    search_history_service.update_job(job_id=job_id, status="FAILED", error=str(e))
    raise
```

### MGMT-02 — `ApiClient.setBrandActive` (`frontend/src/api/client.ts`)
```ts
// Source: mirrors existing ApiClient.request pattern (client.ts:21-45, 61-65)
static setBrandActive(brandKey: string, isActive: boolean) {
  return this.request(`/brands/${brandKey}/active`, {
    method: 'PATCH',
    body: JSON.stringify({ is_active: isActive }),
  });
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Only SKU search persisted | Both SKU + comparative persisted | This phase (HIST-01) | History becomes complete |
| `preloadedJobId` props dead-wired | App.tsx owns + propagates state | This phase (HIST-02) | Reopen actually works |
| Brand active toggle backend-only | UI exposes toggle | This phase (MGMT-02) | Phase 25 endpoint finally consumed |

**Deprecated/outdated:** Nothing. No deprecated APIs involved.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The three virtual marketplaces (mercado_livre/netshoes/amazon) should NOT get an active toggle | MGMT-02 | If user expects to toggle them, UX gap — but they have no backend record so a toggle would 404; low risk, easily revisited |
| A2 | Refetching `GET /history` after a search is acceptable UX (vs. echoing `job_id`) | Pitfall 6 | Minor — if latency matters, echo job_id instead; cosmetic |
| A3 | Client-side `type` filtering of the full history list is sufficient (no `?type=` param) | Per-Tab History List | Only matters at very large history sizes; 30-day cleanup bounds it; low risk |

**All other claims are [VERIFIED] by direct code reading.** No package, compliance, retention, or security assumptions were made beyond the above.

## Open Questions

1. **Should the comparative history list and SKU history list share a presentational component?**
   - What we know: Both render label + badge + date + status + delete; only the label derivation and `type` filter differ.
   - What's unclear: Whether the planner wants one shared `<HistoryList type=... onReopen=... />` component or two inline blocks.
   - Recommendation: Build one reusable `HistoryList` component parameterized by `type` and label-renderer. Reduces duplication; visual placement still per-tab (D-01).

2. **Placement of the history section within each page (collapsible panel vs. always-visible sidebar column).**
   - This is explicitly Claude's-discretion / UI-SPEC territory (CONTEXT). No blocker; planner/UI-SPEC decides.

## Environment Availability

> This phase is code-only (Python edits + React/TS edits). It depends only on the already-running FastAPI app and the existing Vite/React toolchain — both confirmed present (`requirements.txt`, `frontend/package.json`). No new external tools, services, or runtimes are introduced.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python + FastAPI | HIST-01 backend edit | ✓ | fastapi >=0.110.0 | — |
| pytest | Backend tests | ✓ (`.pytest_cache/` present, `tests/` dir of passing tests) | not pinned in requirements.txt (dev tool) | — |
| Node + Vite + tsc | HIST-02/MGMT-02 frontend build | ✓ | vite ^8.0.10, typescript ~6.0.2 | — |

**Missing dependencies with no fallback:** none
**Missing dependencies with fallback:** none

## Validation Architecture

> `.planning/config.json` not separately inspected for `nyquist_validation`; treating as enabled (default). This section maps the 3 success criteria to tests.

### Test Framework
| Property | Value |
|----------|-------|
| Backend framework | pytest (in-repo `tests/` dir; pattern: in-memory service + direct async route-function call via `asyncio.run`, singletons monkeypatched — see `tests/test_brand_active.py`) |
| Backend config file | none (no `pytest.ini`/`pyproject.toml`); discovery by convention `tests/test_*.py` |
| Backend quick run | `python -m pytest tests/test_search_history_comparative.py -x` |
| Backend full suite | `python -m pytest tests/ -x` |
| Frontend framework | **NONE installed** — no vitest/jest, no `test` script in `frontend/package.json`. Frontend validation = `tsc -b` (type check) + `eslint .` + manual UAT |
| Frontend quick run | `cd frontend && npm run build` (runs `tsc -b && vite build` — type-check gate) + `npm run lint` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| HIST-01 | `POST /search` creates a `type="search"` history record | integration (route fn) | `pytest tests/test_search_history_comparative.py::test_post_search_persists_history -x` | ❌ Wave 0 |
| HIST-01 | Persisted record is COMPLETED with `results` = inner `List[BrandSearchResult]` (shape contract) | integration | `pytest tests/test_search_history_comparative.py::test_persisted_results_shape_is_inner_list -x` | ❌ Wave 0 |
| HIST-01 | On search exception, record is marked FAILED with `error` set | integration | `pytest tests/test_search_history_comparative.py::test_search_failure_marks_failed -x` | ❌ Wave 0 |
| HIST-01 | `create_job(type="search")` + `update_job` round-trip via service | unit | `pytest tests/test_search_history_comparative.py::test_history_service_search_type -x` | ❌ Wave 0 |
| HIST-02 | Reopen re-displays without re-scraping (`getHistoryDetail` → render shape) | manual UAT + type-check | `cd frontend && npm run build` (compile) + manual: run search, reopen entry, confirm results identical, confirm no network scrape | n/a (no FE test infra) |
| HIST-02 | `App.tsx` declares `preloadedJobId` and `renderTab` passes it to both pages | static / type-check | `cd frontend && npm run build` (props now type-required if typed) + code review | n/a |
| MGMT-02 | `PATCH /brands/{key}/active` toggles `is_active` (endpoint) | integration (already covered) | `pytest tests/test_brand_active.py -x` (existing) | ✅ exists |
| MGMT-02 | `ApiClient.setBrandActive` issues PATCH with correct body | manual + type-check | `cd frontend && npm run build` + manual: toggle a brand, confirm persistence after refresh | n/a |
| MGMT-02 | Inactive brands render with visual distinction; virtual marketplaces have no toggle | manual UAT | manual: deactivate a brand, confirm dimmed/badged; confirm ML/NS/AMZ rows have no toggle | n/a |

### Sampling Rate
- **Per task commit:** backend `pytest tests/test_search_history_comparative.py -x`; frontend `npm run build` (type gate) + `npm run lint`.
- **Per wave merge:** backend full suite `python -m pytest tests/ -x`; frontend `npm run build`.
- **Phase gate:** backend suite green + frontend builds clean + manual UAT of the 3 success criteria (reopen comparative, reopen SKU, brand toggle round-trip).

### Wave 0 Gaps
- [ ] `tests/test_search_history_comparative.py` — covers HIST-01 (persistence, shape contract, FAILED path, service round-trip). Follow the in-memory + monkeypatch-singleton pattern from `tests/test_brand_active.py` (patch `routes_search.search_history_service` and `routes_search.engine_factory`).
- [ ] No frontend test framework exists; **do not** add one in this phase (scope creep). HIST-02/MGMT-02 frontend behavior is validated by `tsc -b` build + `eslint` + scripted manual UAT. If the planner wants automated FE coverage, that is a separate decision (would require installing vitest + @testing-library/react — out of current scope and would trigger a package-legitimacy gate).
- [ ] Framework install: none needed (pytest already in use).

## Security Domain

> `security_enforcement` config not separately confirmed; treating as enabled. This phase adds no new auth surface, no new external input beyond what already exists, and no cryptography.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Unchanged — shared `X-API-Key` (legacy), no new auth |
| V3 Session Management | no | No sessions introduced |
| V4 Access Control | no | No new privilege boundaries; same API-key gate |
| V5 Input Validation | yes | `BrandActiveUpdate` (Pydantic, exists), `SearchRequest` (Pydantic, exists). New PATCH client method sends a validated boolean. `brand_key` path param is used in a dict lookup (`set_active`) → no injection (returns None for unknown key, 404) — already covered by `tests/test_brand_active.py::test_set_active_unknown_key_returns_none` |
| V6 Cryptography | no | None |

### Known Threat Patterns for FastAPI + React + JSON-file storage
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Arbitrary `brand_key` in PATCH path → data corruption | Tampering | `set_active` returns `None` for unknown key → route raises 404; no dict creation on miss (verified `routes_brands.py:179-181`) |
| Large `ComparisonResult` bloating `search_history.json` | DoS (disk) | Bounded by 30-day cleanup (`cleanup_old_records`) + `max_per_brand` cap (≤50, `SearchRequest`); consistent with existing cross-marketplace storage — no new risk |
| Stored search results re-rendered as HTML | XSS | React escapes by default; results render via JSX text/`src` attrs, not `dangerouslySetInnerHTML` (verified render block `App.tsx:850-902`) — no change |
| Excel formula injection (export path) | Tampering | Already mitigated via `_sanitize_cell` (`routes_search.py:98`); export is unchanged this phase |

---

## Sources

### Primary (HIGH confidence) — direct code reads in this session
- `api/routes_search.py` — `POST /search` (140-179), cross-marketplace persistence template (413-450), `_sanitize_cell` (98)
- `api/routes_history.py` — GET/GET{id}/DELETE history endpoints
- `api/routes_brands.py` — `PATCH /brands/{key}/active` (176-182), `GET /brands/` + virtual marketplaces (97-131)
- `services/search_history_service.py` — create_job/update_job/list_jobs/delete_job, 30-day cleanup, `model_dump(mode="json")` storage
- `services/brand_service.py` — signatures `list_brands(active_only=False)` (207), `set_active` (218), `delete_brand` (234)
- `core/models.py` — `ComparisonResult` (146-154), `BrandSearchResult` (136-143), `DynamicBrand`/`is_active` (228-232), `BrandActiveUpdate` (235-238), `SearchHistory` (245-256)
- `frontend/src/App.tsx` — `SearchPage` + reopen useEffect (641-660), render (838-905), `CrossMarketplacePage` + reopen useEffect (910-985), `SettingsPage` (1344-1453), `App`/`renderTab` (1779-1805)
- `frontend/src/api/client.ts` — request pattern (21-45), brands (50-65), history (91-103)
- `tests/test_brand_active.py` — backend test pattern (in-memory svc + monkeypatched singleton + `asyncio.run` route call)
- `frontend/package.json`, `requirements.txt` — dependency/version verification
- `.planning/phases/27-.../27-CONTEXT.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `.planning/phases/25-.../25-CONTEXT.md`

### Secondary / Tertiary
- None needed — no external/web research required; the phase is fully specified by in-repo code and locked CONTEXT decisions.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all versions read from manifests.
- Architecture / wiring: HIGH — every integration point read line-by-line and line-referenced.
- Pitfalls: HIGH — Pitfall 1 (shape mismatch) derived from reading both consumers and both storage paths.
- Validation: HIGH (backend) / MEDIUM (frontend) — frontend has no test framework, so FE criteria rely on type-check + manual UAT; this is a real gap, honestly flagged, and intentionally not closed in-phase to avoid scope creep.

**Research date:** 2026-06-20
**Valid until:** 2026-07-20 (stable; depends only on internal code, low churn)
