# Phase 27: Histórico Completo + Gestão de Marcas na UI - Context

**Gathered:** 2026-06-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Tornar **todo** o histórico de buscas visível e reabrível na interface, e dar um **lugar único** para gerir marcas. Três entregas:

1. **HIST-01** — A busca comparativa por marca passa a ser salva no histórico (hoje só a busca por SKU é persistida).
2. **HIST-02** — Qualquer busca salva (comparativa ou por SKU) pode ser reaberta a partir do histórico e ter seus resultados reexibidos sem nova raspagem (corrigindo a propagação de `preloadedJobId` a partir de `App.tsx`).
3. **MGMT-02** — Um campo unificado de gestão de marcas (adicionar / remover / ativar-desativar) num só lugar, sem navegação extra.

**Fora de escopo:** persistência de busca viva ao trocar de aba (PERS-01 → Phase 28), onboarding de novas marcas (COMP-01 → Phase 26), diagnóstico de motores (Phase 29), relevância/discriminação de modelo (Phase 23).
</domain>

<decisions>
## Implementation Decisions

### Superfície do histórico
- **D-01:** Histórico apresentado **seccionado por tipo de busca** — NÃO uma aba dedicada unificada no sidebar. O histórico de buscas **comparativas** vive dentro da aba de busca por marca (`SearchPage`); o histórico de buscas **por SKU** vive dentro da aba de SKU (`CrossMarketplacePage`). Cada seção lista apenas as buscas daquele tipo. (Decisão do usuário sobre o critério #2 do roadmap: a "aba correta" é inerente ao histórico seccionado.)

### Conteúdo e ações da entrada
- **D-02:** Cada entrada exibe **rótulo + badge de tipo + data/hora + status**. A comparativa é rotulada por marcas/termo (ex.: "Reserva, Aramis · 3 marcas"); a SKU mantém o rótulo atual `"SKU: {query}"`. O badge distingue Comparativa vs SKU. O status (Concluída / Falhou / Em andamento) é visível.
- **D-03:** Ações por entrada: **reabrir** (clique na entrada) + **excluir** (`DELETE /history/{job_id}`, já existente).

### Comportamento ao reabrir
- **D-04:** Clicar numa entrada reexibe os resultados salvos **sem nova raspagem**, na aba correspondente (que é a própria aba onde a seção vive). A correção da propagação de `preloadedJobId` a partir de `App.tsx` para o componente de destino (`SearchPage` / `CrossMarketplacePage`) é **obrigatória** — o componente já tem o `useEffect` que carrega o detalhe, falta o App alimentar a prop.
- **D-05:** Ao reabrir, **sobrescreve direto** a busca/resultado atualmente exibido na aba. Risco baixo porque agora TODA busca fica salva (HIST-01) — nada é perdido, dá pra reabrir depois.
- **D-06:** Apenas entradas **COMPLETED** reabrem. FAILED aparece com badge de erro e NÃO reabre (não há resultados a exibir); PENDING aparece com indicador "em andamento". Sem cliques quebrados.

### Persistência da busca comparativa (HIST-01)
- **D-07:** `POST /search` (comparativa) passa a persistir no histórico com `type="search"`. Hoje só `POST /search/cross-marketplace` persiste (`type="cross"`). Os resultados são salvos para reexibição sem re-raspagem. Como o endpoint comparativo é síncrono, criar+concluir o job no mesmo request é aceitável (detalhe a critério do planner) — o que importa é que a entrada apareça no histórico já COMPLETED e seja reabrível. Padrão de referência: o trecho que a busca por SKU já usa (`create_job(..., type="cross")` → `update_job(..., "COMPLETED", results=...)`).

### Gestão de marcas (MGMT-02)
- **D-08:** Unificar add/remover/ativar-desativar **estendendo a aba "Marcas" existente** (`SettingsPage`, `App.tsx:1344`). Mantém o formulário de adicionar; em cada linha da lista existente adiciona um **toggle ativo/inativo** + botão excluir. Mínima reescrita.
- **D-09:** A lista mostra **TODAS** as marcas (ativas e inativas) com **distinção visual** (badge/opacidade) para as inativas. `GET /brands/` já retorna inativas (opt-in feito na Phase 25). Necessário para poder reativar.
- **D-10:** **Toggle = `is_active` on/off** (reversível, instantâneo via `PATCH /brands/{key}/active`). **Excluir = `DELETE` permanente, exige confirmação.** Duas ações distintas e claras.

### Claude's Discretion
- Posição/forma exata da seção de histórico dentro de cada página (topo, painel colapsável, etc.) — a critério do UI-SPEC/planner.
- Formato preciso do rótulo da comparativa (marcas + termo) e estilo do badge — a critério do UI-SPEC.
- Estado vazio do histórico; limite/paginação de itens exibidos.
- Mecânica de propagação do job ao reabrir (estado em `App.tsx` vs estado local da página) — desde que o componente de destino reexiba sem raspar e a propagação a partir de `App.tsx` (critério #2) seja honrada.
- Adição da nova chamada `PATCH` no `frontend/src/api/client.ts` (hoje ausente; existem GET/POST/DELETE de brands).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & requisitos
- `.planning/ROADMAP.md` (seção "Phase 27: Histórico Completo + Gestão de Marcas na UI") — goal, dependências (Phase 25) e os 3 success criteria.
- `.planning/REQUIREMENTS.md` — definições de HIST-01, HIST-02 (linha 27-28) e MGMT-02 (linha 19).

### Fase anterior (dependência)
- `.planning/phases/25-funda-o-de-motores/25-CONTEXT.md` — decisões da Phase 25: `PATCH /brands/{key}/active`, `list_brands(active_only=True)` como chokepoint, `detect_engine`. O toggle da UI consome o endpoint criado ali (MGMT-01).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`SearchPage` (`frontend/src/App.tsx:641`) e `CrossMarketplacePage` (`App.tsx:910`)** — já aceitam as props `preloadedJobId` + `onClearPreloadedJob` e têm `useEffect` que busca `getHistoryDetail` quando `preloadedJobId` é setado (App.tsx:652 e :977). Falta apenas o `App` passar as props.
- **`ApiClient` (`frontend/src/api/client.ts`)** — `getHistoryList()`/`getHistoryDetail(jobId)`/`deleteHistory(jobId)` já existem (linhas 91-103); `getBrands()`/`saveBrand()`/`deleteBrand()` existem (50-65). **Falta** um método `PATCH` para `set active`.
- **`SettingsPage` "Marcas" (`App.tsx:1344-1454`)** — form de criar marca (esq.) + lista de marcas com botão excluir (dir.). Base a estender com o toggle.
- **Backend `SearchHistoryService` (`services/search_history_service.py`)** — `create_job(job_id, query, brands, type)`, `update_job(job_id, status, results, error)`, `list_jobs()`, `delete_job()`, `cleanup_old_records()` (30 dias). Storage JSON em `data/search_history.json`.

### Established Patterns
- **Modelo `SearchHistory` (`core/models.py`)** — campo `type` discrimina `"search"` (comparativa) vs `"cross"` (SKU); `status` ∈ PENDING/COMPLETED/FAILED; `results` guarda o resultado completo.
- **Persistência já feita na SKU** (`api/routes_search.py`, `POST /search/cross-marketplace`) — sequência `create_job(type="cross")` → busca → `update_job("COMPLETED", results=...)` → retorna com `job_id`. É o template para HIST-01 na comparativa.
- **Brands** — `core/models.py`: `DynamicBrand` (campos: `brand_key`, `brand_name`, `domain`, `engine`, `logo_url`, `is_active`), `BrandActiveUpdate{is_active}`. Endpoints em `api/routes_brands.py` (GET/POST/DELETE/`PATCH {key}/active`/mappings). Serviço `services/brand_service.py` (`list_brands(active_only=False)`).
- **Frontend** — React + TypeScript + Tailwind (`clsx`/`tailwind-merge`); chamadas via wrapper `ApiClient.request`.

### Integration Points
- `api/routes_search.py` `POST /search` (~131-179) — adicionar persistência de histórico (HIST-01).
- `frontend/src/App.tsx` `renderTab()` (cases `'search'` e `'cross'`, ~1798) — passar `preloadedJobId` + `onClearPreloadedJob`; adicionar estado `preloadedJobId` + handler de clique no histórico (HIST-02).
- `frontend/src/api/client.ts` — adicionar método `PATCH /brands/{key}/active` (MGMT-02).
- `SettingsPage` linhas da lista (`App.tsx:1421-1450`) — adicionar toggle ativo/inativo + distinção visual de inativas.

### Nota
- Resultados da comparativa (`ComparisonResult`) podem ser grandes ao serem salvos no JSON do histórico — comportamento consistente com o que a busca por SKU já faz hoje.
</code_context>

<specifics>
## Specific Ideas

- O rótulo da SKU no histórico (`"SKU: {query}"`) permanece como está; a comparativa ganha rótulo baseado em marcas/termo.
- O toggle de ativar/desativar reaproveita o endpoint `PATCH /brands/{key}/active` da Phase 25 (não criar endpoint novo).
</specifics>

<deferred>
## Deferred Ideas

Nenhuma sugestão de scope creep surgiu durante a discussão.

### Reviewed Todos (not folded)
- **"Reforçar discriminação de modelo (model-words + visual como desempate)"** (`.planning/todos/pending/reforcar-discriminacao-modelo.md`) — pertence ao domínio de relevância de busca (Phase 23 / MODEL-01/02), fora do escopo de histórico/gestão de marcas/UI desta fase. Mantido no backlog.

</deferred>

---

*Phase: 27-hist-rico-completo-gest-o-de-marcas-na-ui*
*Context gathered: 2026-06-20*
