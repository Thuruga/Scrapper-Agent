# Phase 45: Análise de Sortimento - Research

**Researched:** 2026-07-05
**Domain:** JSON-backed assortment analytics, category batch snapshots, and dashboard delivery
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

### Persistência analítica
- **D-01:** A fonte de verdade da análise de sortimento será **JSON local**, não SQLite. Esta decisão sobrescreve a redação antiga do roadmap da Phase 45 e segue o veto explícito da Phase 37.
- **D-02:** Cada execução gera **um arquivo por categoria por execução**, em vez de um arquivo único agregando todas as categorias do cron.
- **D-03:** A localização do snapshot anterior usa **nome canônico de arquivo + manifesto/índice leve**, para manter auditabilidade e leitura rápida.
- **D-04:** Cada snapshot guarda **agregados + evidência mínima**. Não persistir a lista completa do catálogo normalizado; manter apenas informação suficiente para explicar os buckets e comparar execuções.

### Fonte das categorias
- **D-05:** O sortimento mantém **lista própria de categorias**, separada da lista de monitoramento de preço.
- **D-06:** Essa lista própria é alimentada por **sincronização automática one-way** a partir de `backend/data/monitored_categories.json`, servindo como ponto de partida para o cadastro do sortimento.
- **D-07:** Categorias sincronizadas entram no cadastro de sortimento **desativadas por padrão**. O operador decide quando cada uma passa a rodar no cron de sortimento.

### Recorte inicial do relatório
- **D-08:** A v1 do sortimento analisa apenas um conjunto enxuto e padronizado de dimensões: **cor, tamanho e composição**.
- **D-09:** Valores ausentes, vazios ou muito sujos devem ser agrupados como **`não informado`**, em vez de serem descartados da contagem.
- **D-10:** As análises e deltas da v1 são calculados **por dimensão separada** (`available_colors`, `available_sizes`, `composition`), e não por combinações cartesianas entre dimensões.

### Superfície de consumo
- **D-11:** A primeira versão já nasce com **tela na UI**, não apenas com endpoint/export backend.
- **D-12:** Essa tela será uma **nova aba/página própria de sortimento**, separada da área de monitoramento de categoria.
- **D-13:** A experiência principal da página será um **dashboard visual com cards e gráficos**, reaproveitando a linguagem visual já existente no frontend.
- **D-14:** O dashboard deve mostrar **ambos**: no topo, os deltas entre snapshots; abaixo, a distribuição atual da categoria pelos atributos selecionados.

### Comparação entre snapshots
- **D-15:** A comparação padrão ao abrir a página será **último snapshot vs snapshot anterior**.
- **D-16:** Quando ainda não existir snapshot anterior, a UI mostra o retrato atual com estado explícito de **`baseline inicial`**, sem tentar fabricar delta.
- **D-17:** Os deltas devem ser exibidos em **valor absoluto + percentual**, não apenas um dos dois.

### the agent's Discretion
- Esquema exato dos arquivos JSON e do manifesto/índice, desde que preserve: um arquivo por categoria por execução, nome canônico e lookup rápido do snapshot anterior.
- Local do código backend que será dono do cadastro de sortimento, da sincronização one-way com o monitor e da geração dos snapshots.
- Nomes finais dos endpoints, tipos TypeScript e modelos de resposta para a página de sortimento.
- Tipos de gráfico, layout visual e composição dos cards do dashboard, desde que a página mantenha o contrato de produto discutido: deltas no topo e distribuição atual abaixo.
- Formato da evidência mínima persistida por bucket, desde que permaneça leve e auditável.
- Frequência exata do cron de sortimento e a presença ou não de gatilho manual complementar, desde que o fluxo continue batch e separado do monitor de 10 minutos.

### Deferred Ideas (OUT OF SCOPE)
- Drill-down por combinações de dimensões (`cor + tamanho + composição`) — deixado para evolução futura; a v1 calcula tudo por dimensão separada.
- Comparação arbitrária entre quaisquer dois snapshots do histórico — a v1 abre em `último vs anterior`.
- Primeira entrega backend-only/export-only — rejeitada nesta discussão em favor de página dedicada na UI desde a v1.

### Reviewed Todos (not folded)
- `.planning/todos/pending/hugoboss-vtex-io-category-scan.md` — permanece como dependência/risk note para confiabilidade de scans Hugo Boss; não foi dobrado como feature nova da Phase 45.
- `.planning/todos/pending/audit-category-mappings-all-brands.md` — auditoria ampla de mappings/categorias fica fora do escopo da phase; Phase 45 consome categorias confiáveis, não vira projeto de saneamento global.
- `.planning/todos/pending/zara-comp07-deferred.md` — trata de cobertura/anti-bot da Zara, não de analytics de sortimento.
- `.planning/todos/pending/reforcar-discriminacao-modelo.md` — trata de relevância/discriminação de modelo em busca SKU, fora do domínio desta phase.
</user_constraints>

## Project Constraints (from AGENTS.md)

No `AGENTS.md` file exists at the repository root, so there are no extra project-specific instructions beyond the phase artifacts. [VERIFIED: repository files]

No `.codex/skills/` or `.agents/skills/` directory exists in this repository, so there are no local project skills to apply. [VERIFIED: repository files]

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SORT-01 | Um cron de análise de sortimento varre a categoria/site e contabiliza produtos por atributo canônico (ex.: polos por cor/tecido), gerando snapshots por execução para identificar buracos no catálogo. [VERIFIED: repository files] | Backend cron isolation, separate assortment registry, per-category immutable JSON snapshots, delta computation against previous snapshot, and dedicated dashboard payload/UI all map directly to this requirement. [VERIFIED: planning files] |
</phase_requirements>

## Summary

Phase 45 is already tightly bounded by planning context: it must use local JSON snapshots instead of SQLite, keep an assortment registry separate from price-monitor categories, seed that registry one-way from `backend/data/monitored_categories.json`, and ship with a dedicated dashboard page that shows `latest vs previous` deltas plus current distribution for `available_colors`, `available_sizes`, and `composition`. [VERIFIED: planning files]

The repository already has the right seams to implement this without new infrastructure: `backend/app.py` starts an `AsyncIOScheduler` inside FastAPI lifespan, `backend/services/category_monitor_service.py` already performs category batch scraping and writes JSON artifacts, `backend/services/stock_summary_service.py` already encapsulates safe JSON artifact helpers, and the frontend is intentionally concentrated in `frontend/src/App.tsx` plus `frontend/src/api/client.ts`. [VERIFIED: repository files] FastAPI’s current documentation recommends the lifespan async-context-manager pattern for shared startup and shutdown resources. [CITED: https://fastapi.tiangolo.com/advanced/events/] APScheduler’s `AsyncIOScheduler` is documented as the scheduler for asyncio apps, with coroutine-job support and job-level controls such as `max_instances` and `coalesce`. [CITED: https://apscheduler.readthedocs.io/en/3.x/modules/schedulers/asyncio.html] [CITED: https://apscheduler.readthedocs.io/en/3.x/userguide.html]

The main planning risk is not mechanics, but data truthfulness. Phase 37 removed SQLite from the project and is still pending in traceability, while `SORT-01` still depends on canonical attributes being meaningfully populated. [VERIFIED: planning files] If brand/category scans produce sparse `available_colors`, `available_sizes`, or `composition`, the assortment dashboard will honestly collapse into `não informado`, which is acceptable behavior but weak operator value. [ASSUMED] Hugo Boss category reliability also remains an inherited UAT risk from the pending VTEX-IO category-scan todo; the planner should treat Hugo Boss as a confidence caveat, not as a new workstream. [VERIFIED: planning files]

**Primary recommendation:** Implement assortment as a new backend service and route pair with its own registry JSON and per-category snapshot directory, schedule it as a second APScheduler job with overlap protection, and render the dashboard from backend-computed aggregates instead of recomputing from raw snapshots in the browser. [CITED: https://apscheduler.readthedocs.io/en/3.x/userguide.html] [VERIFIED: repository files]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Assortment category registry and one-way sync from monitor categories | API / Backend | Database / Storage | The source file `backend/data/monitored_categories.json` and current CRUD patterns already live on the backend, so sync and registry state should remain server-owned. [VERIFIED: repository files] |
| Snapshot artifact writing and previous-snapshot lookup | Database / Storage | API / Backend | The phase requires immutable per-category JSON files plus a lightweight manifest/index, which is a storage concern executed by backend jobs. [VERIFIED: planning files] |
| Batch category scraping for assortment runs | API / Backend | — | Existing category scraping is performed by backend services and background jobs, not by the client. [VERIFIED: repository files] |
| Delta computation and current-distribution aggregation | API / Backend | Database / Storage | The browser should consume pre-aggregated payloads because the backend owns the source-of-truth artifacts and can enforce `não informado` and baseline semantics consistently. [VERIFIED: planning files] |
| Dashboard rendering, filters, cards, and charts | Browser / Client | API / Backend | The new dedicated assortment page belongs in the existing React shell, but it depends on backend-provided aggregate payloads. [VERIFIED: repository files] |
| Cron lifecycle and overlap safety | API / Backend | Database / Storage | The scheduler is started in FastAPI lifespan today, and APScheduler’s job controls belong there rather than in ad hoc loops. [VERIFIED: repository files] [CITED: https://fastapi.tiangolo.com/advanced/events/] [CITED: https://apscheduler.readthedocs.io/en/3.x/userguide.html] |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | Repo pin `>=0.110.0`; PyPI latest `0.139.0` uploaded `2026-07-01T16:35:32Z`. [VERIFIED: repository files] [VERIFIED: PyPI] | API surface, app lifespan, and scheduler bootstrap. [VERIFIED: repository files] | The repo already uses `FastAPI(lifespan=...)`, and FastAPI recommends the lifespan async context manager for shared startup/shutdown resources. [VERIFIED: repository files] [CITED: https://fastapi.tiangolo.com/advanced/events/] |
| APScheduler | Repo pin `>=3.10.0`; PyPI latest `3.11.3` uploaded `2026-06-28T19:39:20Z`. [VERIFIED: repository files] [VERIFIED: PyPI] | Independent assortment cron inside the existing backend process. [VERIFIED: repository files] | `AsyncIOScheduler` is already in use and is the documented scheduler for asyncio applications; job-level overlap controls are available in the existing stack. [VERIFIED: repository files] [CITED: https://apscheduler.readthedocs.io/en/3.x/modules/schedulers/asyncio.html] [CITED: https://apscheduler.readthedocs.io/en/3.x/userguide.html] |
| Pydantic | Repo pin `>=2.0`; PyPI latest `2.13.4` uploaded `2026-05-06T13:43:02Z`. [VERIFIED: repository files] [VERIFIED: PyPI] | Typed registry rows, snapshot manifests, and dashboard response payloads. [VERIFIED: repository files] | The codebase already models additive feature growth through Pydantic models, which is the safest pattern for new assortment artifacts and route responses. [VERIFIED: repository files] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Recharts | Repo lock `3.8.1`; npm package modified `2026-07-04T03:09:25Z`. [VERIFIED: repository files] [VERIFIED: npm registry] | Distribution and delta charts on the assortment page. [VERIFIED: repository files] | Use for the dedicated dashboard because it is already shipped in the frontend and `ResponsiveContainer` supports parent-sized responsive charts. [VERIFIED: repository files] [CITED: https://recharts.github.io/en-US/api/ResponsiveContainer/] |
| Zustand | Repo lock `5.0.14`; npm package modified `2026-05-28T10:17:58Z`. [VERIFIED: repository files] [VERIFIED: npm registry] | Optional local UI state if the assortment page needs shared filters or snapshot selection. [VERIFIED: npm registry] | Use only if assortment state must persist across tab interactions; otherwise local React state keeps the feature cheaper. [ASSUMED] |
| Sonner | Repo dependency `2.0.7`; npm package exists at that version. [VERIFIED: repository files] [VERIFIED: npm registry] | Operator feedback for manual sync/run actions if those are included. [VERIFIED: repository files] | Reuse existing toast patterns instead of inventing bespoke alert UX. [VERIFIED: repository files] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Separate assortment service + registry JSON | Extend `category_monitor_service.py` and `monitored_categories.json` directly | This would reduce file count, but it would violate D-05 to D-07 and couple assortment activation/history to price-monitor behavior. [VERIFIED: planning files] |
| APScheduler job | Custom `asyncio` loop with `sleep()` | A custom loop would duplicate scheduling concerns already handled by APScheduler and would lose built-in overlap/misfire controls. [VERIFIED: repository files] [CITED: https://apscheduler.readthedocs.io/en/3.x/userguide.html] |
| Backend-computed dashboard payload | Browser-side recomputation from raw snapshot files | Browser recomputation would duplicate business rules, inflate payload size, and make baseline/delta semantics harder to keep consistent. [VERIFIED: planning files] |

**Installation:**
```bash
# No new dependencies are recommended for Phase 45.
```

## Package Legitimacy Audit

No new external packages are recommended for Phase 45; extend the existing backend and frontend stack only. [VERIFIED: repository files]

## Architecture Patterns

### System Architecture Diagram

```text
backend/data/monitored_categories.json
            |
            v
   assortment sync service (one-way upsert, disabled by default)
            |
            v
 backend/data/assortment_categories.json
            |
            +------------------------------+
            |                              |
            v                              v
 manual "sync/run" endpoint         APScheduler assortment job
            |                              |
            +---------------+--------------+
                            |
                            v
                 engine.run_bulk_scrape(category_url)
                            |
                            v
                canonical product fields per product
                            |
                            v
            bucket aggregator (colors / sizes / composition)
                            |
                            +--> per-run snapshot JSON (immutable, one file per category)
                            |
                            +--> per-category manifest/index (points to previous snapshot)
                            |
                            v
              dashboard read model (latest, previous, deltas, baseline state)
                            |
                            v
                /assortment/* API endpoints
                            |
                            v
           frontend App.tsx assortment tab + Recharts cards/charts
```

### Recommended Project Structure

```text
backend/
├── api/
│   └── routes_assortment.py        # registry CRUD, sync trigger, snapshot reads
├── services/
│   └── assortment_service.py       # sync, run, aggregate, delta, manifest helpers
├── data/
│   ├── assortment_categories.json  # separate registry, source-tracked and disabled by default
│   └── assortment_snapshots/       # per-category immutable snapshot files + manifests
├── app.py                          # second scheduler job registration
└── config.py                       # assortment cron/settings knobs

frontend/
├── src/App.tsx                     # new sidebar tab and dedicated assortment page
├── src/App.css                     # page layout and chart containers
└── src/api/client.ts               # typed assortment endpoints
```

### Pattern 1: Separate Registry With One-Way Seed Sync
**What:** Keep assortment categories in a new registry file, and treat `backend/data/monitored_categories.json` only as an upstream seed source. [VERIFIED: planning files]
**When to use:** Always for Phase 45, because D-05 to D-07 require separate ownership and disabled-by-default activation. [VERIFIED: planning files]
**Example:**
```python
# Source pattern: backend/services/category_monitor_service.py
def sync_from_monitored_categories(monitored_rows, assortment_rows):
    # Recommendation: additive sync; do not auto-enable assortment jobs.
    by_source_key = {
        (row["brand"], row["url"]): dict(row)
        for row in assortment_rows
    }
    for monitor in monitored_rows:
        key = (monitor["brand"], monitor["url"])
        current = by_source_key.get(key, {})
        by_source_key[key] = {
            "id": current.get("id"),
            "brand": monitor["brand"],
            "url": monitor["url"],
            "source_monitor_id": monitor["id"],
            "source_status": monitor.get("status"),
            "enabled": current.get("enabled", False),
            "last_snapshot_at": current.get("last_snapshot_at"),
        }
    return list(by_source_key.values())
```

### Pattern 2: Immutable Snapshot Files Plus Lightweight Manifest
**What:** Write one immutable snapshot file per category per run and keep a small per-category manifest that points to `latest_snapshot` and `previous_snapshot`. [VERIFIED: planning files]
**When to use:** For every assortment execution, manual or scheduled, because D-02 and D-03 require per-run auditability plus fast lookup of the previous run. [VERIFIED: planning files]
**Example:**
```python
# Source pattern: backend/services/stock_summary_service.py
snapshot = {
    "category_id": category["id"],
    "brand": category["brand"],
    "captured_at": captured_at,
    "dimensions": {
        "available_colors": color_buckets,
        "available_sizes": size_buckets,
        "composition": composition_buckets,
    },
}
manifest = {
    "category_id": category["id"],
    "latest_snapshot": latest_name,
    "previous_snapshot": previous_name,
}
```

### Pattern 3: Backend-Owned Read Model for the Dashboard
**What:** The backend should load `latest_snapshot` and `previous_snapshot`, compute delta rows and baseline flags, and return a consolidated payload for the assortment page. [VERIFIED: planning files]
**When to use:** For the default page load and for any future manual rerun or category switch, because D-15 to D-17 define shared semantics the backend should enforce once. [VERIFIED: planning files]
**Example:**
```typescript
// Source pattern: frontend/src/api/client.ts
type AssortmentDashboardResponse = {
  category_id: string;
  baseline: boolean;
  latest_snapshot_at: string;
  previous_snapshot_at?: string | null;
  delta_cards: Array<{ dimension: string; bucket: string; delta_abs: number; delta_pct: number | null }>;
  distributions: {
    available_colors: Array<{ bucket: string; count: number; evidence: string[] }>;
    available_sizes: Array<{ bucket: string; count: number; evidence: string[] }>;
    composition: Array<{ bucket: string; count: number; evidence: string[] }>;
  };
};
```

### Likely File Touchpoints

- Existing files to modify: `backend/app.py`, `backend/config.py`, `backend/api/__init__.py`, `frontend/src/App.tsx`, `frontend/src/App.css`, and `frontend/src/api/client.ts`. [VERIFIED: repository files]
- Existing files to reuse without broadening scope: `backend/services/category_monitor_service.py`, `backend/services/stock_summary_service.py`, `backend/api/routes_category.py`, and `backend/core/models.py`. [VERIFIED: repository files]
- New files likely needed: `backend/services/assortment_service.py`, `backend/api/routes_assortment.py`, `backend/tests/test_assortment_service.py`, and `backend/tests/test_assortment_routes.py`. [ASSUMED]

### Recommended Plan Split

1. **Plan 45-01 — Backend foundation:** add assortment settings, separate registry JSON, one-way sync service, snapshot file naming, manifest/index helpers, and scheduler registration. [VERIFIED: planning files]
2. **Plan 45-02 — Snapshot execution + read APIs:** run category snapshots from the independent cron/manual trigger, aggregate color/size/composition buckets, compute previous-vs-latest deltas, and expose typed endpoints. [VERIFIED: planning files]
3. **Plan 45-03 — Frontend dashboard:** add sidebar navigation, dedicated assortment page, baseline state, delta cards, current-distribution charts/tables, and build-contract verification. [VERIFIED: planning files]

### Anti-Patterns to Avoid

- **Do not reuse `monitored_categories.json` as the assortment registry:** Phase 45 explicitly requires separate ownership and disabled-by-default activation. [VERIFIED: planning files]
- **Do not persist full normalized catalogs inside assortment snapshots:** D-04 requires aggregates plus minimal evidence only. [VERIFIED: planning files]
- **Do not compute cartesian bucket combinations in v1:** D-10 explicitly limits the first cut to per-dimension analysis. [VERIFIED: planning files]
- **Do not let the browser derive business logic from raw artifacts:** keep baseline and delta semantics centralized in backend payload assembly. [VERIFIED: planning files]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Recurring job orchestration | Custom background `while True: sleep()` loop | APScheduler `AsyncIOScheduler` already present in `backend/app.py` [VERIFIED: repository files] | Existing scheduler lifecycle, coroutine support, and overlap controls are already documented and available. [CITED: https://apscheduler.readthedocs.io/en/3.x/modules/schedulers/asyncio.html] [CITED: https://apscheduler.readthedocs.io/en/3.x/userguide.html] |
| Responsive chart rendering | Custom SVG/canvas dashboard primitives | Existing Recharts stack [VERIFIED: repository files] | Recharts is already in the repo and its responsive container model fits the existing dashboard approach. [CITED: https://recharts.github.io/en-US/api/ResponsiveContainer/] |
| Category-run persistence format | Ad hoc filename concatenation everywhere | Reuse the safe-artifact helper pattern from `stock_summary_service.py` [VERIFIED: repository files] | The repo already normalizes artifact IDs and centralizes JSON write/read helpers; duplicating this logic would multiply file-path bugs. [VERIFIED: repository files] |
| Missing-attribute handling | Silent drop of empty values | Explicit `não informado` bucket [VERIFIED: planning files] | The feature exists to surface catalog gaps, and dropped rows would hide both extraction gaps and assortment holes. [VERIFIED: planning files] |

**Key insight:** The hard part of Phase 45 is not chart rendering or scheduling; it is preserving truthful semantics while keeping assortment isolated from live monitor behavior and from the now-invalid SQLite assumption. [VERIFIED: planning files]

## Common Pitfalls

### Pitfall 1: Coupling Assortment Activation to Monitor Activation
**What goes wrong:** A category enabled for price monitoring starts producing assortment snapshots automatically, or assortment is disabled when the monitor is removed. [VERIFIED: planning files]
**Why it happens:** Both features begin from the same source file, which tempts implementers to share the same row as the source of truth. [VERIFIED: repository files]
**How to avoid:** Treat monitored categories as upstream seed input only, then persist assortment state in a separate registry with its own `enabled` flag. [VERIFIED: planning files]
**Warning signs:** Code mutates `backend/data/monitored_categories.json` for assortment-specific fields such as last snapshot timestamps or assortment enablement. [ASSUMED]

### Pitfall 2: Snapshot Bloat
**What goes wrong:** Snapshot files grow into full product dumps, becoming slow to read and expensive to diff. [VERIFIED: planning files]
**Why it happens:** The existing monitor feature already stores full product lists, so it is easy to copy that pattern uncritically. [VERIFIED: repository files]
**How to avoid:** Persist bucket counts plus small evidence samples only; keep the full product dump in monitor artifacts if operators need raw scan inspection. [VERIFIED: planning files]
**Warning signs:** Snapshot files include every product field or dozens of URLs per bucket. [ASSUMED]

### Pitfall 3: Misleading Coverage From Dropped Empty Attributes
**What goes wrong:** The dashboard appears healthier than the underlying data because unknown values disappear instead of being counted. [VERIFIED: planning files]
**Why it happens:** Engineers often filter falsy values before grouping. [ASSUMED]
**How to avoid:** Normalize blanks, nulls, and noisy values into `não informado` before counting. [VERIFIED: planning files]
**Warning signs:** Bucket totals do not add up to total scanned products for a dimension. [ASSUMED]

### Pitfall 4: Scheduler Overlap and Backfill Storms
**What goes wrong:** A slow assortment run overlaps with the next scheduled run, or restart/misfire behavior replays multiple runs and writes confusing artifacts. [CITED: https://apscheduler.readthedocs.io/en/3.x/userguide.html]
**Why it happens:** Assortment scans are batch jobs over live storefronts, so duration can exceed the interval or host restarts can queue missed runs. [VERIFIED: planning files]
**How to avoid:** Register the assortment job with explicit overlap controls such as `max_instances=1` and `coalesce=True`, and keep it separate from the 10-minute monitor schedule. [CITED: https://apscheduler.readthedocs.io/en/3.x/userguide.html]
**Warning signs:** Multiple snapshots for the same category have nearly identical timestamps or a single restart produces several consecutive runs. [ASSUMED]

### Pitfall 5: Hugo Boss Confidence Drift
**What goes wrong:** UAT uses Hugo Boss assortment output as if it were a clean proof point even when category scan reliability is still flagged. [VERIFIED: planning files]
**Why it happens:** Hugo Boss already exists as a monitored brand, so it looks like an obvious validation target. [VERIFIED: planning files]
**How to avoid:** Keep Hugo Boss as an inherited risk note only and prove the feature on a working-brand fixture first. [VERIFIED: planning files]
**Warning signs:** A zero-product Hugo Boss run is treated as a successful empty assortment instead of a scan-quality issue. [VERIFIED: planning files]

## Code Examples

Verified patterns from official sources and repository conventions:

### FastAPI Lifespan + Second Scheduler Job
```python
# Source: https://fastapi.tiangolo.com/advanced/events/
# Source: https://apscheduler.readthedocs.io/en/3.x/modules/schedulers/asyncio.html
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(category_monitor_job, "interval", minutes=10)
    scheduler.add_job(
        assortment_snapshot_job,
        "interval",
        minutes=settings.ASSORTMENT_CRON_MINUTES,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    yield
    scheduler.shutdown(wait=True)
```

### Safe JSON Artifact Pattern
```python
# Source: backend/services/stock_summary_service.py
def _safe_artifact_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value))

def _write_json(path: Path, payload: Any) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
```

### Recharts Responsive Container Rule
```tsx
// Source: https://recharts.github.io/en-US/api/ResponsiveContainer/
<div className="assortment-chart-shell">
  <ResponsiveContainer width="100%" minHeight={280}>
    <BarChart data={distributionData}>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey="bucket" />
      <YAxis />
      <Tooltip />
      <Bar dataKey="count" fill="var(--accent)" />
    </BarChart>
  </ResponsiveContainer>
</div>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Roadmap/STATE assumption that analytical data should migrate to SQLite | Phase 37 and Phase 45 context override analytics persistence to local JSON. [VERIFIED: planning files] | `37-CONTEXT.md` gathered `2026-07-03`; `45-CONTEXT.md` gathered `2026-07-05`. [VERIFIED: planning files] | Planner must not create `analytics.db` or SQLite tasks for this phase. [VERIFIED: planning files] |
| Shared monitor-oriented category ownership | Separate assortment registry seeded one-way from monitored categories. [VERIFIED: planning files] | `45-CONTEXT.md` gathered `2026-07-05`. [VERIFIED: planning files] | Assortment enablement, history, and UI must not be stored in monitor rows. [VERIFIED: planning files] |
| Analytics added as extensions of existing monitor/category screens | Dedicated assortment page in the main React shell. [VERIFIED: planning files] | `45-CONTEXT.md` gathered `2026-07-05`. [VERIFIED: planning files] | Frontend work belongs in `App.tsx`/`App.css`/`ApiClient`, not in a parallel app. [VERIFIED: repository files] |

**Deprecated/outdated:**
- SQLite as the source of truth for Phase 45 is outdated for this repository and is explicitly overridden by current context. [VERIFIED: planning files]
- Treating price-monitor categories as the execution registry for assortment is outdated because the context now requires one-way seeding only. [VERIFIED: planning files]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The monitored brands/categories that matter for Phase 45 already expose `available_colors`, `available_sizes`, and `composition` often enough for the dashboard to be operationally useful; otherwise the output will skew toward `não informado`. [ASSUMED] | Summary, Common Pitfalls | Medium: feature still works, but operator value drops sharply and UAT may reject the first cut. |
| A2 | A non-destructive one-way sync model that preserves assortment rows when the source monitor disappears is the safest default unless the user wants tighter coupling. [ASSUMED] | Open Questions, Architecture Patterns | Medium: if the user expects hard deletion, planners must add cleanup semantics and UAT cases. |
| A3 | A new backend service file plus route file is the least disruptive implementation shape; the repo does not already contain a hidden shared analytics abstraction that should own assortment instead. [ASSUMED] | Likely File Touchpoints | Low: planner can still adjust placement without changing phase scope. |

## Open Questions

1. **What should happen when a seeded monitor category is later deleted from `monitored_categories.json`?**
   - What we know: Phase 45 requires one-way seeding from monitor categories, but does not specify delete semantics. [VERIFIED: planning files]
   - What's unclear: Whether the assortment registry should preserve the row, mark it stale, or auto-disable it. [ASSUMED]
   - Recommendation: Preserve the row and expose a `source_missing` or `source_status` flag; do not auto-delete history. [ASSUMED]

2. **Should v1 include a manual “run snapshot now” trigger in addition to cron?**
   - What we know: The frequency and presence of a manual trigger are left to the agent’s discretion as long as the flow remains batch and separate from the 10-minute monitor. [VERIFIED: planning files]
   - What's unclear: Whether operator workflow needs immediate validation after enabling a category. [ASSUMED]
   - Recommendation: Include a manual trigger if backend cost is small, because it improves UAT and debug speed without changing the core architecture. [ASSUMED]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `python3` | Backend services, routes, scheduler | ✓ | `3.12.3` [VERIFIED: shell] | — |
| `node` | Frontend tooling and local GSD tooling | ✓ | `v20.20.2` [VERIFIED: shell] | — |
| `npm` | Frontend build verification | ✓ | `10.8.2` [VERIFIED: shell] | — |
| `git` | Planner/executor workflow and artifact commits | ✓ | `2.43.0` [VERIFIED: shell] | — |
| `pytest` module | Backend test execution | ✗ | — [VERIFIED: shell] | None in current environment; planner should account for Python test dependency bootstrap before execution. [VERIFIED: shell] |

**Missing dependencies with no fallback:**
- `pytest` is not installed in the current Python environment, so backend tests are configured in-repo but not runnable until the test dependency is installed. [VERIFIED: repository files] [VERIFIED: shell]

**Missing dependencies with fallback:**
- None. [VERIFIED: shell]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest` configured in `pytest.ini`, but not installed in the current environment. [VERIFIED: repository files] [VERIFIED: shell] |
| Config file | `pytest.ini` with `testpaths = backend/tests` and `pythonpath = backend`. [VERIFIED: repository files] |
| Quick run command | `python3 -m pytest backend/tests/test_assortment_service.py backend/tests/test_assortment_routes.py -x` [ASSUMED] |
| Full suite command | `python3 -m pytest` [VERIFIED: repository files] |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SORT-01 | One-way sync creates/upserts assortment rows from `monitored_categories.json` without auto-enabling them. [VERIFIED: planning files] | unit | `python3 -m pytest backend/tests/test_assortment_service.py::test_sync_from_monitored_categories_keeps_rows_disabled -x` [ASSUMED] | ❌ Wave 0 |
| SORT-01 | Snapshot run groups `available_colors`, `available_sizes`, and `composition`, normalizing blanks to `não informado`. [VERIFIED: planning files] | unit | `python3 -m pytest backend/tests/test_assortment_service.py::test_snapshot_groups_dimensions_with_nao_informado_bucket -x` [ASSUMED] | ❌ Wave 0 |
| SORT-01 | Dashboard API returns `baseline=true` when no previous snapshot exists and returns absolute+percent deltas otherwise. [VERIFIED: planning files] | integration | `python3 -m pytest backend/tests/test_assortment_routes.py::test_dashboard_payload_baseline_and_delta_semantics -x` [ASSUMED] | ❌ Wave 0 |
| SORT-01 | Frontend page renders the new tab, baseline state, and chart containers without type errors. [VERIFIED: planning files] | build/smoke | `cd frontend && npm run build` [VERIFIED: repository files] | ✅ existing build path |

### Sampling Rate

- **Per task commit:** `python3 -m pytest backend/tests/test_assortment_service.py backend/tests/test_assortment_routes.py -x` plus `cd frontend && npm run build` [ASSUMED] [VERIFIED: repository files]
- **Per wave merge:** `python3 -m pytest` plus `cd frontend && npm run build` [VERIFIED: repository files]
- **Phase gate:** Full backend suite green and frontend build green before `$gsd-verify-work`. [ASSUMED]

### Wave 0 Gaps

- [ ] `backend/tests/test_assortment_service.py` — sync, snapshot aggregation, manifest lookup, delta math. [ASSUMED]
- [ ] `backend/tests/test_assortment_routes.py` — registry CRUD, dashboard payload, manual-run endpoint if included. [ASSUMED]
- [ ] `pytest` environment bootstrap — current environment lacks the module even though the repo is configured for it. [VERIFIED: shell]
- [ ] Frontend contract coverage beyond build — there is no dedicated frontend test runner; Phase 44 precedent relies on type/build verification plus backend route tests. [VERIFIED: planning files] [VERIFIED: repository files]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Shared API-key auth on all protected API routers via `verify_api_key` and `api_router` dependencies. [VERIFIED: repository files] |
| V3 Session Management | no | The app uses API key headers and a WebSocket query param rather than user sessions. [VERIFIED: repository files] |
| V4 Access Control | yes | Assortment routes should inherit the protected API router and keep scan identity server-resolved, mirroring Phase 44 route boundaries. [VERIFIED: repository files] |
| V5 Input Validation | yes | Use Pydantic request/response models and safe artifact ID normalization for filenames. [VERIFIED: repository files] |
| V6 Cryptography | no | Phase 45 does not introduce new cryptographic requirements; do not hand-roll hashing beyond non-security artifact IDs already used for scan product keys. [VERIFIED: repository files] |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal or unsafe file naming in snapshot reads/writes | Tampering | Reuse safe artifact ID normalization and never accept raw client file paths. [VERIFIED: repository files] |
| Forged product/category identity in assortment actions | Spoofing | Resolve category identity and source URLs from persisted registry rows, not caller-supplied domain/path overrides. [VERIFIED: planning files] [VERIFIED: repository files] |
| Cron-induced denial of service from overlapping runs | DoS | Separate assortment interval from the 10-minute monitor and configure overlap controls. [VERIFIED: planning files] [CITED: https://apscheduler.readthedocs.io/en/3.x/userguide.html] |
| Excessive JSON artifact growth | DoS | Keep snapshots aggregate-only with minimal evidence; do not persist full normalized catalogs. [VERIFIED: planning files] |
| Misleading analytics from sparse or stale attributes | Integrity | Surface `não informado`, preserve baseline state, and document Hugo Boss scan reliability as an inherited risk. [VERIFIED: planning files] |

## Sources

### Primary (HIGH confidence)
- Repository planning and code files listed in the phase prompt — phase scope, overrides, implementation seams, tests, and current architecture. [VERIFIED: repository files]
- PyPI JSON API for `fastapi`, `APScheduler`, and `pydantic` — version and upload-date verification. [VERIFIED: PyPI]
- npm registry metadata for `react`, `recharts`, `zustand`, and `sonner` — package existence and current package metadata. [VERIFIED: npm registry]

### Secondary (MEDIUM confidence)
- FastAPI lifespan events documentation — https://fastapi.tiangolo.com/advanced/events/ [CITED: https://fastapi.tiangolo.com/advanced/events/]
- APScheduler AsyncIOScheduler reference — https://apscheduler.readthedocs.io/en/3.x/modules/schedulers/asyncio.html [CITED: https://apscheduler.readthedocs.io/en/3.x/modules/schedulers/asyncio.html]
- APScheduler user guide — https://apscheduler.readthedocs.io/en/3.x/userguide.html [CITED: https://apscheduler.readthedocs.io/en/3.x/userguide.html]
- Recharts `ResponsiveContainer` API — https://recharts.github.io/en-US/api/ResponsiveContainer/ [CITED: https://recharts.github.io/en-US/api/ResponsiveContainer/]

### Tertiary (LOW confidence)
- None. All non-recommendation factual claims above were verified against repository artifacts, package registries, or official documentation. [VERIFIED: repository files]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - the phase can stay on the repository’s existing FastAPI/APScheduler/Pydantic/React/Recharts stack with no new dependencies. [VERIFIED: repository files]
- Architecture: MEDIUM - the service/route split and additive sync strategy are strongly supported by current code patterns, but the exact file placement and sync-delete semantics remain discretionary. [VERIFIED: repository files] [ASSUMED]
- Pitfalls: HIGH - the main risks are directly evidenced in current planning artifacts: JSON-vs-SQLite conflict, separate-registry requirement, sparse-attribute truthfulness, and Hugo Boss scan reliability. [VERIFIED: planning files]

**Research date:** 2026-07-05
**Valid until:** 2026-07-12
