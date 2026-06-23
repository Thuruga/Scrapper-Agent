# Phase 28: Persistência da Busca Entre Abas - Context

**Gathered:** 2026-06-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Tornar uma busca em andamento **sobrevivente à troca de abas**: o estado sai dos componentes de página (que desmontam ao trocar de aba) para um **store zustand module-scoped**. Ao sair para outra aba e voltar, progresso, resultados e estado de seleção continuam disponíveis — sem cancelamento, sem perda de estado e sem dupla execução. Inclui o **fix do cleanup de WebSocket na `CategoryPage`** (critério #4), que é prerequisito e vem antes do store.

**Causa-raiz:** `AnimatePresence mode="wait"` com `key={activeTab}` (`frontend/src/App.tsx:2127-2137`) desmonta o conteúdo da aba a cada troca. Como cada página guarda todo o seu estado em `useState` local, trocar de aba destrói o estado e qualquer fetch em voo perde o destino do `setState`.

**Fora de escopo:**
- Persistência do estado do scrape da `CategoryPage` (apenas o WS cleanup entra — ver D-02).
- Sobrevivência a reload/refresh da página ou entre sessões do navegador (ver D-05).
- Converter a busca em job assíncrono/polling (ver D-08).
- Replay/snapshot de WebSocket no backend (mudança de backend; fora desta phase frontend).
- Diagnóstico de categorias (Phase 29), frete checkout (Phase 30), relevância/discriminação de modelo (Phase 23).
</domain>

<decisions>
## Implementation Decisions

### Escopo da persistência
- **D-01:** A persistência aplica-se **somente às buscas Comparativa** (`SearchPage`, `App.tsx:830`) **e por SKU** (`CrossMarketplacePage`, `App.tsx:1105`). Ambas são `await ApiClient.search/...` síncrono guardado em `useState` que se perde no unmount — mesmo problema, mesma solução, UX consistente.
- **D-02:** A `CategoryPage` **NÃO persiste** o estado do scrape. Recebe **apenas** o fix de WS cleanup do critério #4: um `useEffect` que fecha o WebSocket no unmount do componente. O job de scrape continua rodando no backend, mas o feed ao vivo se perde ao trocar de aba. **Por quê:** persistir o progresso do scrape exigiria manter o WebSocket vivo entre abas (movê-lo para o store), o que é o oposto do critério #4 ("fechar o WS ao desmontar"); como o endpoint `/ws/${jobId}` aparenta só transmitir eventos ao vivo (sem replay), reconectar-ao-voltar não recuperaria o histórico sem mudança de backend. O usuário optou por manter o design travado no STATE.md — só o cleanup.

### O que persiste ao trocar de aba
- **D-03:** Persiste o **estado completo por aba** — inputs + filtros + resultados + estado de seleção — mesmo sem busca rodando. Voltar à aba = exatamente como o usuário deixou. Atende "estado de seleção preservado" do goal.
  - **Comparativa (`SearchPage`):** `query`, `sort`, `inStock`, `zipcode`, `selectedBrands` (filtro de marcas), `results`, `loading`.
  - **SKU (`CrossMarketplacePage`):** `targetSku`, `zipcode`, `results`, `selectedItems` + `selectionMode` (seleção de export), `loading`.

### Notificação de conclusão fora da aba (critério #2)
- **D-04:** **Toast global** via `sonner` (já é dependência — `package.json`; já usado para erros) disparado **sempre** ao concluir uma busca. Por ser global, o toast aparece em qualquer aba — cobre o caso "concluir enquanto o usuário está em outra aba" sem lógica extra de comparação de aba-atual. Comportamento **novo**: hoje a busca síncrona não emite toast de conclusão.

### Fronteira da persistência
- **D-05:** **Apenas memória** — store zustand module-scoped. Sobrevive à troca de aba; **zera num reload/refresh** da página. **Sem** middleware `persist` (sem `sessionStorage`/`localStorage`). Casa exatamente com o escopo "entre abas" (PERS-01), é o mais simples e evita serializar o `ComparisonResult` (que pode ser grande, conforme nota da Phase 27).

### Arquitetura (travada antes desta discussão — `STATE.md`)
Decisões herdadas, **não re-discutidas**; carregadas adiante para o planner respeitar:
- **D-06:** Store **zustand module-scoped** — NÃO React Context, NÃO Redux. (`STATE.md [ARCH]`)
- **D-07:** **Manter `AnimatePresence`** (`App.tsx:2127`) — não remover a animação de transição entre abas. (`STATE.md [ARCH]`)
- **D-08:** **NÃO converter a busca para job assíncrono/polling** — o fetch continua síncrono; só migra do `useState` do componente para o store. (`STATE.md [ARCH]`)
- **D-09:** O fix do **WS cleanup na `CategoryPage` vem ANTES** do store zustand, na **mesma phase** (prerequisito ~5 linhas de `useEffect`). (`STATE.md [PERS-01]`)
- **D-10:** **zustand precisa ser adicionado** ao `frontend/package.json` — hoje **ausente** das dependências.
- **D-11:** O store **coexiste com `preloadedJobId`** (já flui por `App.tsx` desde a Phase 27 — `App.tsx:2015`, `:2043-2044`). Reabrir busca do histórico continua funcionando; a migração de estado não pode quebrar a propagação do `preloadedJobId`.

### Claude's Discretion
- Estrutura interna do store: um store unificado vs slices/stores por aba — a critério do researcher/planner.
- Semântica de **cancelamento** (AbortController) ao iniciar nova busca antes do término da anterior — critério #3, implementação.
- Prevenção de **duplo-fetch** no mount/remount (React 19 StrictMode, deps de `useEffect`, guarda de "já buscando") — critério #3, implementação.
- Onde exatamente o toast de conclusão é disparado (dentro da action do store vs no componente que observa o store) — desde que dispare globalmente (D-04).
- Forma exata do `useEffect` de cleanup do WS na `CategoryPage` — desde que feche `wsRef.current` e não deixe handlers chamando `setState` após o unmount.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & requisitos
- `.planning/ROADMAP.md` (seção "Phase 28: Persistência da Busca Entre Abas") — goal, dependência (Phase 27) e os **4 success criteria** (incl. critério #3 duplo-fetch/cancelamento e critério #4 WS cleanup da CategoryPage).
- `.planning/REQUIREMENTS.md` — definição de **PERS-01** (linha 23): estado movido dos componentes que desmontam para um store global.

### Decisões arquiteturais travadas (dependência direta)
- `.planning/STATE.md` (seção "Accumulated Context › Decisions") — decisões `[ARCH]` e `[PERS-01]`: store zustand module-scoped, manter AnimatePresence, não converter para async/polling, WS cleanup da CategoryPage antes do store.

### Fase anterior (dependência)
- `.planning/phases/27-hist-rico-completo-gest-o-de-marcas-na-ui/27-CONTEXT.md` — D-04/D-05 e code_context: `preloadedJobId` é dono em `App.tsx` e propagado a `SearchPage`/`CrossMarketplacePage`; o store desta phase deve coexistir com esse fluxo.

### Sem ADRs/specs externos
- Não há ADRs ou specs externos — os requisitos estão totalmente capturados nas decisões acima.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`sonner` toast** (`frontend/package.json` → `"sonner": "^2.0.7"`; importado como `toast` em `App.tsx`) — infra de notificação global já existente; reusar para o toast de conclusão (D-04).
- **`ApiClient.search` / `ApiClient.searchCrossMarketplace`** (`frontend/src/api/client.ts`) — chamadas síncronas que retornam os resultados diretamente; permanecem como estão (D-08), só mudam de quem dispara/guarda (componente → store).
- **`preloadedJobId` + `onClearPreloadedJob`** — props já aceitas por `SearchPage` (`App.tsx:830`) e `CrossMarketplacePage` (`App.tsx:1105`), com `useEffect` que carrega `getHistoryDetail` (`App.tsx:841` e `:1171`). A migração para o store deve preservar esse fluxo (D-11).

### Established Patterns
- **Estado de página em `useState` local** — `SearchPage` (`query`, `results`, `loading`, `selectedBrands`, `sort`, `inStock`, `zipcode`, `historyRefreshKey`) e `CrossMarketplacePage` (`targetSku`, `results`, `selectedItems`, `selectionMode`, `loading`, `exporting`). É esse estado que precisa migrar para o store (D-03).
- **Render de aba via `switch`** (`App.tsx:2040 renderTab`) dentro de `AnimatePresence mode="wait"` keyed em `activeTab` (`App.tsx:2127-2137`) — a fonte do unmount. Permanece (D-07); o store é que torna o estado independente do ciclo de vida do componente.
- **WebSocket na `CategoryPage`** (`App.tsx:374 wsRef`, conexão em `App.tsx:467-487`) — hoje o WS **só** fecha dentro de `ws.onmessage` num `done`/`error_done` (`App.tsx:478`); **não há `useEffect` de cleanup no unmount**. Esse é o gap do critério #4 (D-02/D-09).
- **Stack frontend:** React 19 + TypeScript + Vite + Tailwind; `framer-motion` para animações. **Sem** biblioteca de state management hoje — zustand é introdução nova (D-10).

### Integration Points
- `frontend/package.json` — adicionar `zustand` às dependências (D-10).
- `frontend/src/App.tsx` — novo(s) store(s) zustand; `SearchPage` e `CrossMarketplacePage` passam a ler/escrever no store em vez de `useState`; `CategoryPage` ganha `useEffect` de cleanup do WS.
- Disparo do toast de conclusão (D-04) no ponto onde a busca resolve (action do store ou componente observador).

### Nota
- O `ComparisonResult` da Comparativa pode ser grande em memória — aceitável no store em memória (D-05 evita serializá-lo em storage).
</code_context>

<specifics>
## Specific Ideas

- O toast de conclusão reaproveita o `sonner` já em uso (não introduzir outra lib de notificação).
- O WS cleanup da `CategoryPage` é um `useEffect` de ~5 linhas que fecha `wsRef.current` no unmount — explicitamente o "prerequisito antes do store" do `STATE.md`.
- A migração não pode quebrar a reabertura de histórico via `preloadedJobId` (Phase 27).
</specifics>

<deferred>
## Deferred Ideas

- **Persistir o progresso do scrape da `CategoryPage` entre abas** — surgiu na discussão de escopo; descartado porque exigiria manter o WS vivo entre abas (conflita com o critério #4) e/ou replay de estado no backend (fora do escopo frontend). Candidato a phase própria se houver demanda.
- **Sobrevivência a reload/refresh da página (sessionStorage/localStorage)** — considerado e descartado: fora do escopo "entre abas" do PERS-01 e custo de serializar resultados grandes. Reabrir do histórico já cobre recuperação pós-reload.

### Reviewed Todos (not folded)
- **"Reforçar discriminação de modelo (model-words + visual como desempate)"** (`.planning/todos/pending/reforcar-discriminacao-modelo.md`) — match por palavras-chave genéricas (phase, marca, busca), mas pertence ao domínio de relevância de busca (Phase 23 / MODEL-01/02), sem relação com persistência de estado/UI. Já revisado-e-não-incorporado na Phase 27 pela mesma razão. Mantido no backlog.

</deferred>

---

*Phase: 28-persist-ncia-da-busca-entre-abas*
*Context gathered: 2026-06-21*
