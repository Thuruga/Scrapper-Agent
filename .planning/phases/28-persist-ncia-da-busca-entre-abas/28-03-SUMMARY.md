---
phase: 28-persist-ncia-da-busca-entre-abas
plan: "03"
subsystem: ui
tags: [zustand, react, state-management, search, migration]

# Dependency graph
requires:
  - phase: 28-persist-ncia-da-busca-entre-abas/28-01
    provides: WebSocket cleanup fix in CategoryPage (prerequisite D-07)
  - phase: 28-persist-ncia-da-busca-entre-abas/28-02
    provides: useSearchStore zustand store with search/cross slices + AbortController signal support in ApiClient
provides:
  - SearchPage (Comparativa) migrated from useState to useSearchStore slice 'search'
  - CrossMarketplacePage (busca por SKU) migrated from useState to useSearchStore slice 'cross'
  - Anti-double-fetch guards in both preloadedJobId useEffects
  - Error handling consolidated to toast.error in store actions (replaces legacy alert() in CrossMarketplacePage)
affects: [frontend state persistence, tab switching, search lifecycle, preloadedJobId regression]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Atomic selectors for heavy-render fields (loading, results); useShallow for grouped inputs"
    - "Anti-double-fetch guard: if (useSearchStore.getState().<slice>.loading) return; at top of preloadedJobId useEffect"
    - "Store action owns try/catch/toast/AbortController; component only calls startSearch/startCrossSearch"
    - "Local useState retained for UI-transient fields: historyRefreshKey, exporting, loadingShipping"

key-files:
  created: []
  modified:
    - frontend/src/App.tsx

key-decisions:
  - "[28-03/Task2]: error handling in CrossMarketplacePage consolidated to toast.error in the store action (startCrossSearch) — replaces the legacy alert() that existed in the component's handleSearch. Intentional unification with Comparativa's error pattern."
  - "[28-03/Task1]: historyRefreshKey and exporting remain useState local in SearchPage per D-03 (UI-transient, not search state)"
  - "[28-03/Task2]: loadingShipping, exporting, historyRefreshKey remain useState local in CrossMarketplacePage per D-03"
  - "[28-03/UAT]: Manual UAT (Task 3) deferred by user — 5 behavioral verification procedures are PENDING, not approved"

patterns-established:
  - "Pattern: store action owns all async lifecycle (loading flag, results write, AbortController, toast); component calls action and bumps historyRefreshKey"
  - "Pattern: getState() guard (not hook) used in non-reactive useEffect context to read loading flag without triggering renders"

requirements-completed: [PERS-01]

# Metrics
duration: ~30min (code tasks only; UAT pending)
completed: "2026-06-21"
---

# Phase 28 Plan 03: SearchPage + CrossMarketplacePage migradas para useSearchStore — UAT manual PENDENTE

**SearchPage e CrossMarketplacePage migradas de useState local para zustand module-scoped store; estado de busca sobrevive ao unmount; build verde. UAT comportamental (4 critérios + regressão D-11) PENDENTE — deferred pelo usuário.**

## Performance

- **Duration:** ~30 min (Tasks 1 e 2 automatizadas); Task 3 (UAT) ainda não executada
- **Started:** 2026-06-21
- **Completed (código):** 2026-06-21
- **Tasks:** 2 de 3 completas (Task 3 deferred)
- **Files modified:** 1 (frontend/src/App.tsx)

## Accomplishments

- SearchPage: `query`, `results`, `loading`, `sort`, `inStock`, `zipcode`, `selectedBrands` migrados do useState para o slice `search` do useSearchStore; `handleSearch` chama `startSearch(payload)`; `useEffect([preloadedJobId])` preservado com guarda anti-duplo-fetch; `historyRefreshKey` e `exporting` permanecem useState local.
- CrossMarketplacePage: `targetSku`, `zipcode`, `loading`, `results`, `selectedItems`, `selectionMode` migrados para o slice `cross`; `handleSearch` chama `startCrossSearch(payload)`; `useEffect([preloadedJobId])` preservado com guarda anti-duplo-fetch; `loadingShipping`, `exporting`, `historyRefreshKey` e `withDisplayOrder` permanecem locais.
- Build `npm run build` verde após ambas as tasks (código e estrutura estática confirmados). 17 referências a `useSearchStore` em App.tsx verificadas.

## Task Commits

1. **Task 1: Migrar SearchPage (Comparativa) para useSearchStore** - `787b0e4` (feat)
2. **Task 2: Migrar CrossMarketplacePage (busca por SKU) para useSearchStore** - `168b797` (feat)
3. **Task 3: UAT manual dos 4 critérios** - PENDENTE (deferred — não executado)

**Checkpoint pause state:** `f870e77` (docs: record checkpoint pause state)

## Files Created/Modified

- `frontend/src/App.tsx` — SearchPage e CrossMarketplacePage migradas para useSearchStore; props e AnimatePresence inalteradas (D-07/D-11)

## Decisions Made

- **[28-03/Task2] Consolidação de erro em CrossMarketplacePage:** o `alert("Erro ao buscar: " + err.message)` que existia em `handleSearch` foi eliminado. O tratamento de erro agora vive integralmente na action `startCrossSearch` do store, que usa `toast.error`. Isso unifica o padrão de erro entre Comparativa e SKU e é a mudança intencional documentada no plano.
- **[28-03/UAT] Deferral de UAT:** o usuário optou por não executar o UAT manual nesta sessão. Os 5 procedimentos de verificação estão documentados abaixo como PENDENTES e devem ser executados antes de considerar os critérios da phase como aprovados.

## Deviations from Plan

**1. [Intencional — documentado no plano] Substituição de alert() por toast.error em CrossMarketplacePage**
- **Found during:** Task 2
- **Issue:** O plano registra explicitamente que `handleSearch` de CrossMarketplacePage usava `alert()` em vez de `toast.error`. A action `startCrossSearch` do store (criada no Plan 02) já usa `toast.error`.
- **Fix:** A eliminação do `alert()` é a mudança intencional: o componente não duplica tratamento de erro; a action cuida de tudo.
- **Files modified:** frontend/src/App.tsx
- **Committed in:** `168b797` (Task 2)

---

**Total deviations:** 1 (intencional, documentada no plano)
**Impact on plan:** Sem impacto adverso — eliminar `alert()` em favor de `toast.error` na action era o objetivo do plano.

## Pending UAT — Task 3 DEFERRED

**Status: NÃO EXECUTADO — deferred pelo usuário. Os comportamentos abaixo NÃO foram verificados.**

Apenas build estático e estrutura de código foram confirmados. Os critérios comportamentais da phase estão não verificados:

### Procedimentos pendentes

**1. Critério #1 — Estado sobrevive à troca de aba**
- Iniciar busca Comparativa longa com spinner ativo; trocar para outra aba e voltar.
- Verificar: spinner ativo, `query` preenchida, `selectedBrands` preservados, busca NÃO reiniciada.
- Aguardar conclusão: toast "Busca Comparativa concluída" + resultados visíveis.
- Repetir para busca por SKU.

**2. Critério #2 — Toast fora da aba**
- Iniciar busca Comparativa; navegar para outra aba antes de concluir.
- Verificar que o toast de sucesso aparece na aba atual (não precisa estar na aba de busca).
- Voltar à Comparativa e confirmar resultados disponíveis.

**3. Critério #3 — Sem duplo-fetch + cancelamento**
- DevTools > Network: iniciar busca, trocar aba, voltar → apenas 1 request `POST /search` (não 2).
- Cancelamento: iniciar busca A; antes de concluir, iniciar busca B → request A aparece "Canceled", B prossegue, apenas o toast de B aparece.
- Repetir cancelamento para busca por SKU (`POST /search/cross-marketplace`).

**4. Critério #4 — WS cleanup (entregue no Plan 01, reconfirmar)**
- DevTools > Console: aba Categorias, iniciar varredura; com WS ativo, navegar para outra aba → nenhum log novo após a troca; Network > WS = "Closed".

**5. Regressão D-11 — preloadedJobId**
- Reabrir busca salva do histórico (comparativa e por SKU) → leva à aba correta, resultados reexibidos, sem nova raspagem.
- Trocar de aba e voltar não recarrega o histórico por cima de uma busca nova.

### Critérios de aceite pendentes

- Critério #1: busca em andamento continua executando ao trocar/voltar de aba; inputs, seleção e resultados parciais preservados; busca não reiniciada (Comparativa e SKU).
- Critério #2: toast de conclusão visível em qualquer aba; resultados disponíveis ao retornar.
- Critério #3: exatamente 1 request por busca ao trocar/voltar de aba; request anterior = "Canceled" ao iniciar nova busca; apenas o toast da busca vigente aparece.
- Critério #4: nenhum log novo da CategoryPage após a troca de aba; WS "Closed".
- Regressão D-11: reabrir do histórico funciona em ambas as abas e não é sobrescrito ao alternar abas.

## Issues Encountered

None during code tasks. UAT deferred — see Pending UAT section above.

## Next Phase Readiness

- Código migrado e build verde. As Tasks 1 e 2 estão tecnicamente prontas.
- **BLOQUEADOR (verificação humana):** Task 3 (UAT manual) está PENDENTE. Os 4 critérios comportamentais da phase e a regressão D-11 não foram verificados. Antes de avançar para a próxima phase, executar os 5 procedimentos UAT listados acima com `cd frontend && npm run dev`.
- Após aprovação do UAT, o SUMMARY pode ser atualizado para refletir a aprovação e o plano pode ser considerado 100% completo.

## Self-Check

**Automated scope: PASSED**
- Commit `787b0e4` (Task 1 — SearchPage): confirmed in git log.
- Commit `168b797` (Task 2 — CrossMarketplacePage): confirmed in git log.
- `frontend/src/App.tsx` modified in both commits.
- Build green confirmed by prior orchestrator verification.

**Manual UAT scope: PENDING**
- Task 3 not executed. 5 UAT procedures outstanding. Behavioral criteria #1–#4 and D-11 regression are UNVERIFIED.

---
*Phase: 28-persist-ncia-da-busca-entre-abas*
*Completed (code): 2026-06-21*
*UAT status: PENDING — deferred*
