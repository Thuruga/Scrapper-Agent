---
phase: 28-persist-ncia-da-busca-entre-abas
verified: 2026-06-21T00:00:00Z
status: passed
score: 9/9 must-haves verified (7 automated + 2 behavioral confirmed by user UAT 2026-06-22)
human_uat: approved 2026-06-22 (see 28-HUMAN-UAT.md)
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 5/9
  gaps_closed:
    - "CR-01: post-await readback e re-wrap de resultados em CrossMarketplacePage.handleSearch — CORRIGIDO em commit 9ff516e"
    - "WR-01/WR-02: identity guard ausente nas actions do store — CORRIGIDO"
    - "WR-03: preloadedJobId silenciosamente descartado enquanto loading=true — CORRIGIDO"
    - "WR-04: cleanup do WS não nulava onopen/onerror/onclose — CORRIGIDO"
    - "WR-05: JSON.parse sem try/catch no onmessage — CORRIGIDO"
    - "WR-06: setHistoryRefreshKey incondicional após action que swallows erro/abort — CORRIGIDO"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Critério #1 — Estado sobrevive à troca de aba (Comparativa)"
    expected: "Iniciar busca Comparativa longa (muitas marcas); com spinner ativo, trocar para outra aba e voltar: spinner ainda ativo, query preenchida, selectedBrands preservados, busca NÃO reiniciada. Após conclusão: toast 'Busca Comparativa concluída' + resultados visíveis."
    why_human: "Frontend sem framework de teste automatizado (sem Jest/Vitest/Playwright); requer interação real com a UI e observação de DevTools"

  - test: "Critério #1 — Estado sobrevive à troca de aba (SKU)"
    expected: "Iniciar busca por SKU; com spinner ativo, trocar de aba e voltar: targetSku preservado, loading ativo, busca NÃO reiniciada. Após conclusão: toast 'Busca por SKU concluída' + resultados visíveis."
    why_human: "Mesmo que acima"

  - test: "Critério #2 — Toast de conclusão fora da aba"
    expected: "Iniciar busca, navegar para outra aba antes de concluir. Toast de sucesso deve aparecer na aba atual (não na aba de busca). Ao voltar: resultados disponíveis."
    why_human: "Notificação visual global; requer observação fora da aba de busca em runtime"

  - test: "Critério #3 — Sem duplo-fetch + cancelamento correto"
    expected: "DevTools > Network: iniciar busca, trocar aba, voltar → apenas 1 request POST /search. Cancelamento: iniciar busca A, antes de concluir iniciar busca B → request A = 'Canceled', B prossegue, apenas toast de B aparece. Resultado exibido é de B, NÃO de A."
    why_human: "Requer inspeção de DevTools Network em runtime. CR-01 foi corrigido em 9ff516e — este UAT confirma o comportamento correto em execução real."

  - test: "Critério #4 — WS cleanup da CategoryPage"
    expected: "DevTools > Console e Network > WS. Aba Categorias, iniciar varredura; com WS ativo, navegar para outra aba: nenhum log novo após a troca; Network > WS = 'Closed'."
    why_human: "Requer observação de comportamento em runtime com DevTools"

  - test: "Regressão D-11 — preloadedJobId"
    expected: "Reabrir busca salva do histórico (comparativa e SKU): leva à aba correta, resultados reexibidos sem nova raspagem. Trocar de aba e voltar não recarrega histórico por cima de busca nova."
    why_human: "Requer interação real com histórico e troca de abas em runtime"
---

# Phase 28: Persistência da Busca Entre Abas — Verification Report (Re-verificação)

**Phase Goal:** Uma busca em andamento continua ativa ao navegar para outra aba e ao voltar — progresso, resultados parciais e estado de seleção são preservados sem cancelamento nem dupla execução.
**Verified:** 2026-06-21
**Status:** human_needed
**Re-verification:** Sim — após correção do CR-01 e warnings WR-01..06 (commit 9ff516e)

---

## Re-verification Summary

A re-verificação foi disparada pelo commit `9ff516e` que corrigiu o BLOCKER CR-01 (post-await readback em `CrossMarketplacePage.handleSearch`) e todos os 6 warnings (WR-01..06). O gap estático foi fechado. O único item pendente restante é o UAT comportamental (Gap 2 da verificação anterior), que permanece PENDENTE por decisão explícita do usuário e não dispõe de framework de testes automatizados.

**Resultado:** Sem gaps de código. Status evolui de `gaps_found` para `human_needed`.

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | WS cleanup na CategoryPage (onmessage/onopen/onerror/onclose = null antes de close()) | VERIFIED | App.tsx:384-397 — useEffect com dep [] nula todos os quatro handlers antes de `close()` e anula `wsRef.current`. WR-04 corrigido em 9ff516e. |
| 2 | Um store zustand module-scoped existe com slices search + cross (D-03) | VERIFIED | searchStore.ts — `useSearchStore` exportado via `create<SearchStoreState>()`, slices `search` e `cross` com todos os campos de D-03, incluindo `abortController`, `loadingPreloadId` e `selectedItems: Set`. |
| 3 | startSearch/startCrossSearch cancelam request anterior via AbortController e retornam SearchOutcome | VERIFIED | searchStore.ts:101-133, 136-171 — ambas as actions: `abort()` na controller anterior, nova controller, identity guard `get().<slice>.abortController !== controller` em success e error paths, retornam `{status:'success'|'aborted'|'error'}`. WR-01/WR-02 corrigidos. |
| 4 | AbortError silenciado (return {status:'aborted'}); toast.success disparado globalmente na action | VERIFIED | searchStore.ts:127 (search) e 165 (cross) — `if (err.name === 'AbortError') return { status: 'aborted' }`. toast.success em linhas 124 e 162. Toast vive dentro da action, funciona de qualquer aba (D-04). |
| 5 | ApiClient.search e ApiClient.crossMarketplaceSearch aceitam signal?: AbortSignal | VERIFIED | Estrutura verificada na verificação inicial; sem alteração em 9ff516e. |
| 6 | SearchPage e CrossMarketplacePage leem do useSearchStore em vez de useState local | VERIFIED | App.tsx — seletores atômicos e useShallow em ambas as páginas; sem useState para campos migrados. `historyRefreshKey` e `exporting` permanecem estado local (D-03 correto). |
| 7 | Não ocorre re-wrap de resultados cruzados; handleSearch é condicional ao SearchOutcome | VERIFIED | **CR-01 CORRIGIDO.** App.tsx:1305-1323 — `const outcome = await startCrossSearch(...)` sem leitura de `getState().cross.results` após o await. `setHistoryRefreshKey` apenas em `outcome.status === 'success'` (WR-06 corrigido). searchStore.ts:157-161 — `withDisplayOrder` aplicado internamente dentro da action, antes de `set()`, com identity guard. Comentário em App.tsx:1310-1311 é impreciso (diz "aplicado aqui" mas o código não chama `withDisplayOrder` em handleSearch — aplicação real é na action), porém não é um defeito de comportamento. |
| 8 | Busca sobrevive à troca de aba e ao voltar (comportamental) | UNCERTAIN — aguarda UAT | Estrutura do store module-scoped verificada estaticamente. Comportamento em runtime requer UAT manual (28-VALIDATION.md). CR-01 que comprometeria este critério foi corrigido. |
| 9 | Toast de conclusão aparece fora da aba + preloadedJobId sem duplo-fetch | UNCERTAIN — aguarda UAT | toast.success dentro da action verificado estaticamente (D-04). preloadedJobId: guarda `loadingPreloadId === preloadedJobId` em ambas as páginas (WR-03 corrigido). Comportamento em runtime requer UAT manual. |

**Score:** 7/9 truths verified (2 UNCERTAIN — comportamental, requer UAT manual)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/stores/searchStore.ts` | useSearchStore com slices search+cross, SearchOutcome, withDisplayOrder exportada, identity guard em todas as paths | VERIFIED | 173 linhas. SearchOutcome type (linhas 10-13). withDisplayOrder module-scoped + exported (linhas 55-64). startSearch retorna Promise<SearchOutcome> (linha 48). startCrossSearch idem (linha 49). Identity guards em success e error de ambas. |
| `frontend/src/api/client.ts` | request/search/crossMarketplaceSearch com signal?: AbortSignal opcional | VERIFIED | Sem alteração em 9ff516e; estrutura verificada anteriormente. |
| `frontend/package.json` | dependência zustand | VERIFIED | "zustand": "^5.0.14" em dependencies. Sem alteração. |
| `frontend/src/App.tsx` (CategoryPage) | useEffect[] de cleanup do WS — todos handlers nulados, incluindo onopen/onerror/onclose | VERIFIED | App.tsx:384-397 — WR-04 corrigido. Quatro handlers nulados antes de close(). |
| `frontend/src/App.tsx` (SearchPage) | handleSearch usa SearchOutcome; setHistoryRefreshKey condicional; preloadedJobId sem duplo-fetch | VERIFIED | App.tsx:921-937 — outcome.status==='success' em linha 934. App.tsx:873-903 — guarda `loadingPreloadId === preloadedJobId` em linha 878; abort de busca em voo em linha 881 (WR-03 corrigido). |
| `frontend/src/App.tsx` (CrossMarketplacePage) | handleSearch usa SearchOutcome; sem readback de store após await; sem aplicação de withDisplayOrder no caller | VERIFIED | App.tsx:1305-1323 — sem leitura de getState() após await; sem chamada a withDisplayOrder(); setHistoryRefreshKey condicional em linha 1320. CR-01 resolvido. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| CategoryPage useEffect cleanup | wsRef.current (todos handlers) | onmessage/onopen/onerror/onclose=null + close() + null no unmount | VERIFIED | App.tsx:389-394 — ordem correta, todos os 4 handlers nulados (WR-04 corrigido) |
| SearchPage.handleSearch | useSearchStore startSearch | await startSearch(payload) → SearchOutcome | VERIFIED | App.tsx:924; outcome.status branch em 934 |
| CrossMarketplacePage.handleSearch | useSearchStore startCrossSearch | await startCrossSearch(payload) → SearchOutcome, sem readback | VERIFIED | App.tsx:1312-1322; CR-01 corrigido — sem getState() nem setCross após await |
| startSearch/startCrossSearch | ApiClient.search/crossMarketplaceSearch | ApiClient.search(payload, controller.signal) | VERIFIED | searchStore.ts:117, 155 |
| startCrossSearch success branch | withDisplayOrder | aplicado internamente antes de set() | VERIFIED | searchStore.ts:160 — `results: withDisplayOrder(data)` dentro do identity-guard success branch |
| useEffect([preloadedJobId]) em ambas as páginas | loadingPreloadId no slice | guarda `slice.loading && slice.loadingPreloadId === preloadedJobId` | VERIFIED | App.tsx:878 (search), 1220 (cross) — WR-03 corrigido; abort de busca em voo antes da pré-carga |
| startSearch/startCrossSearch | sonner toast.success | toast.success no bloco try após identity guard e set() | VERIFIED | searchStore.ts:124, 162 |
| ws.onmessage handler | JSON.parse | try/catch envolve o parse | VERIFIED | App.tsx:488-493 — WR-05 corrigido; frame malformado retorna early |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produz dados reais | Status |
|----------|--------------|--------|--------------------|--------|
| SearchPage JSX | results (search.results) | await ApiClient.search() → identity guard → set() no store | Sim — endpoint POST /search real; identity guard impede clobber tardio | FLOWING |
| CrossMarketplacePage JSX | results (cross.results) | await ApiClient.crossMarketplaceSearch() → identity guard → withDisplayOrder dentro da action → set() | Sim — CR-01 corrigido; withDisplayOrder aplicado uma única vez, no momento correto | FLOWING |

---

### Behavioral Spot-Checks

Step 7b: SKIPPED — frontend sem framework de testes automatizados e sem entry point verificável sem servidor rodando. Única porta automatizada é `npm run build` (type-check). Build documentado como verde em 28-REVIEW-FIX.md (`tsc -b && vite build` green após commit 9ff516e).

---

### Probe Execution

Step 7c: Nenhum probe script declarado para esta phase. SKIPPED.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| PERS-01 | 28-01-PLAN, 28-02-PLAN, 28-03-PLAN | Uma busca em andamento sobrevive à troca de abas — progresso e resultados disponíveis ao voltar, sem cancelamento nem perda de estado | PARTIAL — aguarda UAT | Código migrado e CR-01 corrigido. Identity guards em todas as paths. withDisplayOrder como fonte única. historyRefreshKey condicional ao sucesso. Estrutura estática: VERIFIED. Comportamento em runtime (os 5 critérios de 28-VALIDATION.md): PENDING UAT manual. PERS-01 não pode ser marcado SATISFIED sem aprovação humana dos critérios comportamentais. |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| frontend/src/App.tsx | 1310-1311 | Comentário desatualizado: "withDisplayOrder é aplicado aqui" — o código NÃO aplica; a aplicação real é dentro da action | INFO | Enganoso mas inofensivo — o código imediatamente abaixo (1316-1322) documenta corretamente o comportamento real. Não é um defeito funcional. |

Nenhum marcador TBD/FIXME/XXX detectado nos arquivos modificados pela phase.

---

### Human Verification Required

As seguintes verificações são MANUAIS e requerem rodar o app (`cd frontend && npm run dev`). O UAT da Task 3 do Plan 03 está PENDENTE. CR-01 foi corrigido — todos os UATs podem agora ser executados sem risco de resultados cruzados.

#### 1. Critério #1 — Estado sobrevive à troca de aba (Comparativa e SKU)

**Test:** Iniciar busca Comparativa longa (muitas marcas, sem filtro de estoque); com o spinner ativo, trocar para outra aba (ex.: Monitor) e voltar à Comparativa. Repetir para busca por SKU.
**Expected:** Spinner ainda ativo; query preenchida; selectedBrands preservados; busca NÃO reiniciada; após conclusão, toast aparece e resultados estão visíveis.
**Why human:** Frontend sem framework de teste de UI; requer interação real de troca de aba e observação de estado.

#### 2. Critério #2 — Toast de conclusão fora da aba

**Test:** Iniciar busca Comparativa; navegar para outra aba antes de concluir. Observar se o toast de sucesso aparece na aba atual. Voltar à Comparativa e confirmar resultados disponíveis.
**Expected:** Toast "Busca Comparativa concluída" visível em qualquer aba; resultados disponíveis ao retornar.
**Why human:** Notificação visual global; requer observação em runtime fora da aba de busca.

#### 3. Critério #3 — Cancelamento sem corrupção de resultados

**Test:** DevTools > Network. (a) Sem duplo-fetch: iniciar busca, trocar aba, voltar → apenas 1 request POST /search. (b) Cancelamento: iniciar busca A; antes de concluir, iniciar busca B com query diferente → request A aparece "Canceled", B prossegue, apenas o toast de B aparece e o resultado exibido é de B (não de A).
**Expected:** Exatamente 1 request por busca; request anterior "Canceled"; apenas toast da busca vigente; resultado exibido é da busca atual.
**Why human:** Requer inspeção de DevTools Network em runtime. CR-01 corrigido em 9ff516e — este UAT confirma que a correção funciona em produção real.

#### 4. Critério #4 — WS cleanup da CategoryPage

**Test:** DevTools > Console e Network > WS. Aba Categorias, iniciar varredura; com WS ativo (logs aparecendo), navegar para outra aba.
**Expected:** Nenhum log novo da CategoryPage após a troca; Network > WS mostra conexão como "Closed".
**Why human:** Requer observação de comportamento em runtime com DevTools abertos.

#### 5. Regressão D-11 — preloadedJobId

**Test:** Reabrir busca salva do histórico (comparativa e SKU). Após carregamento, trocar de aba e voltar.
**Expected:** Leva à aba correta; resultados reexibidos sem nova raspagem; trocar de aba e voltar não recarrega histórico por cima de busca nova. Tentar reabrir histórico enquanto busca está em voo: busca em voo deve ser cancelada e histórico carregado (WR-03 corrigido).
**Why human:** Requer interação real com histórico e troca de abas em runtime; comportamento do abort-antes-de-preload não é verificável sem execução real.

---

### Gaps Summary

Nenhum gap de código bloqueador restante. O único item pendente é o UAT comportamental.

**CR-01 — FECHADO (commit 9ff516e):**
`CrossMarketplacePage.handleSearch` não mais lê `getState().cross.results` nem chama `withDisplayOrder` após o `await`. A action `startCrossSearch` agora: (1) aplica `withDisplayOrder` internamente antes de `set()`; (2) usa identity guard `get().cross.abortController !== controller` antes de qualquer terminal `set()`; (3) retorna `SearchOutcome` discriminado. O caller condiciona `setHistoryRefreshKey` exclusivamente em `outcome.status === 'success'`. O mecanismo de duplo-bump e re-wrap de resultados cruzados foi eliminado na raiz.

**WR-01..06 — FECHADOS (commit 9ff516e):**
Identity guard em ambas as paths de sucesso e erro de ambas as actions. JSON.parse guardado com try/catch. WS cleanup nula todos os handlers. preloadedJobId aborta busca em voo em vez de silenciar o pedido do usuário.

**UAT PENDENTE — único bloqueador restante:**
A phase goal é uma afirmação de comportamento em runtime. O código que deveria implementar esse comportamento está presente, correto estaticamente, e o defeito anterior (CR-01) foi resolvido. Porém nenhum dos 5 critérios comportamentais de 28-VALIDATION.md foi aprovado por humano. O frontend não possui framework de testes automatizados. O UAT manual completo é o gate restante para aprovação de PERS-01.

---

_Verified: 2026-06-21_
_Verifier: Claude (gsd-verifier)_
_Re-verification: após commit 9ff516e (CR-01 + WR-01..06 fixes)_
