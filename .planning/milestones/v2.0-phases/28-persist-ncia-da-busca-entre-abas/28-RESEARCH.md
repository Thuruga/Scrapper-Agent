# Phase 28: Persistência da Busca Entre Abas — Research

**Pesquisado:** 2026-06-21
**Domínio:** React state management (zustand), AbortController, WebSocket cleanup, AnimatePresence
**Confiança geral:** HIGH

---

<user_constraints>
## Restrições do Usuário (de 28-CONTEXT.md)

### Decisões Travadas

- **D-01:** Persistência somente em `SearchPage` (busca Comparativa) e `CrossMarketplacePage` (busca por SKU).
- **D-02:** `CategoryPage` recebe apenas o fix de WS cleanup (5 linhas de `useEffect` no unmount). Estado do scrape NÃO persiste.
- **D-03:** Persiste estado completo por aba: inputs + filtros + resultados + seleção.
  - Comparativa: `query`, `sort`, `inStock`, `zipcode`, `selectedBrands`, `results`, `loading`.
  - SKU: `targetSku`, `zipcode`, `results`, `selectedItems`, `selectionMode`, `loading`.
- **D-04:** Toast global via `sonner` (já dependência) disparado SEMPRE ao concluir busca. Comportamento novo.
- **D-05:** Apenas memória — zustand module-scoped SEM middleware `persist`. Zera em reload/refresh.
- **D-06:** Store zustand module-scoped — NÃO React Context, NÃO Redux.
- **D-07:** Manter `AnimatePresence mode="wait"` — não remover animação de transição.
- **D-08:** Busca permanece síncrona (`await ApiClient.search/...`) — NÃO converter para async/polling.
- **D-09:** Fix WS cleanup da `CategoryPage` vem ANTES do store zustand, na mesma phase.
- **D-10:** `zustand` precisa ser adicionado ao `frontend/package.json` — hoje ausente.
- **D-11:** Store coexiste com `preloadedJobId` (Phase 27). Reabrir busca do histórico não pode quebrar.

### Autonomia do Claude (Claude's Discretion)

- Estrutura interna: store unificado vs slices/stores por aba.
- Implementação do cancelamento via AbortController.
- Prevenção de duplo-fetch no mount/remount (React 19 StrictMode).
- Onde exatamente o toast de conclusão é disparado.
- Forma exata do `useEffect` de cleanup do WS.

### Ideias Adiadas (FORA DO ESCOPO)

- Persistir progresso do scrape da `CategoryPage` entre abas.
- Sobrevivência a reload/refresh via `sessionStorage`/`localStorage`.
</user_constraints>

<phase_requirements>
## Requisitos da Phase

| ID | Descrição | Suporte da Pesquisa |
|----|-----------|---------------------|
| PERS-01 | Busca em andamento sobrevive à troca de abas — progresso e resultados disponíveis ao voltar, sem cancelamento nem perda de estado (estado movido dos componentes que desmontam para um store global). | Store zustand module-scoped; AbortController para cancelamento de busca anterior; guarda anti-duplo-fetch; cleanup de WS no unmount. |
</phase_requirements>

---

## Sumário

O problema é estrutural: `AnimatePresence mode="wait"` com `key={activeTab}` em `App.tsx:2127-2137` desmonta e remonta o componente de página a cada troca de aba, destruindo todo o `useState` local. A solução travada (D-06) é mover o estado das duas páginas de busca (`SearchPage` e `CrossMarketplacePage`) para um store zustand module-scoped — o store sobrevive ao ciclo de vida dos componentes porque vive no escopo do módulo JS, fora da árvore React.

A implementação se decompõe em quatro blocos independentes que o planner deve ordenar: (1) fix do WS cleanup na `CategoryPage` (prerequisito isolado, ~5 linhas — D-09); (2) instalação do zustand e criação do store; (3) migração de `SearchPage` e `CrossMarketplacePage` para ler/escrever no store; (4) toast de conclusão global via `sonner`.

O maior risco de implementação é o duplo-fetch no React 19 StrictMode: ao remontar uma aba que já tem busca em voo no store, o `useEffect` de preloadedJobId não deve disparar novo fetch se `loading === true` no store. O AbortController vive dentro da action do store (`startSearch`) e cancela o request anterior ao iniciar uma nova busca.

**Recomendação principal:** Store unificado com slices nomeados por aba (`search` e `cross`); um único `useSearchStore`. Cada componente subscreve apenas os campos do seu slice via seletores atômicos.

---

## Mapa de Responsabilidade Arquitetural

| Capacidade | Tier Primário | Tier Secundário | Racional |
|------------|--------------|-----------------|----------|
| Estado de busca persistente | Frontend (store zustand) | — | Estado de UI; não pertence ao backend |
| Fetch da busca (síncrono) | Frontend (store action) | Backend (API) | Action chama `ApiClient`, resultado salva no store |
| Cancelamento de request anterior | Frontend (AbortController na action) | — | Client-side: aborta fetch antes de iniciar novo |
| Toast de conclusão | Frontend (store action → sonner) | — | Global observer do sonner; independe de componente ativo |
| Cleanup WS | Frontend (CategoryPage useEffect) | — | Isolado do store; componente fecha seu próprio WS ao desmontar |
| Animação de transição | Frontend (framer-motion AnimatePresence) | — | Permanece — o store desacopla estado do ciclo de vida |
| Propagação de preloadedJobId | Frontend (App.tsx → page props) | — | Fluxo da Phase 27 mantido; lógica de history load nos componentes |

---

## Stack Padrão

### Core

| Biblioteca | Versão | Propósito | Por que usar |
|-----------|--------|-----------|-------------|
| `zustand` | `5.0.14` [VERIFIED: npm registry] | Store de estado global module-scoped | API mínima, sem Provider, TypeScript nativo, React 19 compatível |
| `sonner` | `^2.0.7` [VERIFIED: package.json] | Toast global de conclusão (D-04) | Já instalado; `toast()` pode ser chamado fora de componentes React |

### Dependências Existentes (não alterar)

| Biblioteca | Versão | Relevância na Phase |
|-----------|--------|---------------------|
| `framer-motion` | `^12.38.0` | `AnimatePresence` permanece (D-07) |
| `react` | `^19.2.5` | StrictMode ativo — duplo-mount em dev |

### Instalação

```bash
cd frontend
npm install zustand@5.0.14
```

**Verificação de versão:** `npm view zustand version` retornou `5.0.14` (2026-06-21). Peer dependencies: `react >= 18.0.0` (compatível com React 19.2.5). [VERIFIED: npm registry]

---

## Auditoria de Legitimidade de Pacotes

> Nota: slopcheck avaliou `zustand` como `[SLOP]` porque verificou no registry **PyPI** (Python), não no npm. Isso é falso positivo por confusão de ecossistema — `zustand` é um pacote npm, não Python. Verificação manual no registry correto realizada abaixo.

| Pacote | Registry | Idade | Downloads | Repositório | slopcheck | Disposição |
|--------|----------|-------|-----------|-------------|-----------|------------|
| zustand | npm | ~7 anos (criado 2019-04-09) | Altíssimo (top state mgmt libs) | github.com/pmndrs/zustand | FALSO POSITIVO (ecosystem mismatch — PyPI) | Aprovado [VERIFIED: npm registry] |

**Verificação manual npm:**
- `npm view zustand version` → `5.0.14`
- `npm view zustand time.modified` → `2026-05-28` (ativo)
- `npm view zustand repository.url` → `git+https://github.com/pmndrs/zustand.git`
- Homepage oficial: `https://github.com/pmndrs/zustand` [CITED: npmjs.com/package/zustand]

**Pacotes removidos por slopcheck [SLOP]:** nenhum (veredicto foi falso positivo).
**Pacotes com aviso [SUS]:** nenhum.

---

## Padrões de Arquitetura

### Diagrama de Fluxo

```
Usuário clica "Buscar"
        │
        ▼
[SearchPage / CrossMarketplacePage]
  handleSearch()
        │
        ▼
[useSearchStore.getState().startSearch(payload)]
  1. aborta AbortController anterior (se existir)
  2. cria novo AbortController, salva no store
  3. set loading=true, results=null
  4. await ApiClient.search({...payload, signal})
        │
   ┌────┴────┐
   │sucesso  │erro/abort
   ▼         ▼
set results  set loading=false
set loading  (AbortError: ignora;
=false       outro: propaga toast.error)
toast.success("Busca concluída")
        │
        ▼
Usuário navega outra aba
[AnimatePresence desmonta componente]
[store sobrevive no escopo do módulo JS]
        │
        ▼
Usuário retorna à aba
[AnimatePresence remonta componente]
[useSearchStore lê estado existente: loading/results]
[NÃO dispara novo fetch — loading ou results já presentes]
```

### Estrutura de Arquivos Recomendada

```
frontend/src/
├── stores/
│   └── searchStore.ts       # zustand store unificado (slices search + cross)
├── App.tsx                  # migração de useState → store; CategoryPage WS fix
└── api/
    └── client.ts            # adicionar signal?: AbortSignal ao request()
```

### Padrão 1: Store Unificado com Slices por Aba

**O quê:** Um único `useSearchStore` com dois slices (`search` e `cross`) no mesmo objeto de estado. Evita dependências circulares e simplifica o código — o planner não precisa coordenar dois stores.

**Por que não dois stores separados:** O toast de conclusão e o `preloadedJobId` podem precisar observar ambas as abas; um store unificado facilita isso. Slices no zustand são convenção de organização, não stores separados.

```typescript
// frontend/src/stores/searchStore.ts
// Fonte: padrão documentado em github.com/pmndrs/zustand [CITED]

import { create } from 'zustand'
import { useShallow } from 'zustand/react/shallow'
import { toast } from 'sonner'
import { ApiClient } from '../api/client'

// --- Tipos ---

interface SearchSlice {
  query: string
  sort: string
  inStock: boolean
  zipcode: string
  selectedBrands: string[]
  results: any | null
  loading: boolean
  abortController: AbortController | null
}

interface CrossSlice {
  targetSku: string
  zipcode: string
  results: any | null
  selectedItems: Set<string>
  selectionMode: boolean
  loading: boolean
  abortController: AbortController | null
}

interface SearchStoreState {
  search: SearchSlice
  cross: CrossSlice
  // Actions
  setSearch: (patch: Partial<SearchSlice>) => void
  setCross: (patch: Partial<CrossSlice>) => void
  startSearch: (payload: any) => Promise<void>
  startCrossSearch: (payload: any) => Promise<void>
}

// --- Store ---

export const useSearchStore = create<SearchStoreState>()((set, get) => ({
  search: {
    query: '',
    sort: 'relevance',
    inStock: false,
    zipcode: '',
    selectedBrands: [],
    results: null,
    loading: false,
    abortController: null,
  },
  cross: {
    targetSku: '',
    zipcode: '',
    results: null,
    selectedItems: new Set(),
    selectionMode: false,
    loading: false,
    abortController: null,
  },

  setSearch: (patch) =>
    set((s) => ({ search: { ...s.search, ...patch } })),

  setCross: (patch) =>
    set((s) => ({ cross: { ...s.cross, ...patch } })),

  startSearch: async (payload) => {
    // Cancela request anterior se existir
    get().search.abortController?.abort()
    const controller = new AbortController()

    set((s) => ({
      search: {
        ...s.search,
        loading: true,
        results: null,
        abortController: controller,
      },
    }))

    try {
      const data = await ApiClient.search(payload, controller.signal)
      set((s) => ({
        search: { ...s.search, loading: false, results: data, abortController: null },
      }))
      toast.success('Busca Comparativa concluída')   // D-04 — global, funciona em qualquer aba
    } catch (err: any) {
      if (err.name === 'AbortError') return          // Cancelamento intencional — não notifica
      set((s) => ({ search: { ...s.search, loading: false, abortController: null } }))
      toast.error('Erro na busca: ' + err.message)
    }
  },

  startCrossSearch: async (payload) => {
    get().cross.abortController?.abort()
    const controller = new AbortController()

    set((s) => ({
      cross: {
        ...s.cross,
        loading: true,
        results: null,
        selectedItems: new Set(),
        selectionMode: false,
        abortController: controller,
      },
    }))

    try {
      const data = await ApiClient.crossMarketplaceSearch(payload, controller.signal)
      set((s) => ({
        cross: { ...s.cross, loading: false, results: data, abortController: null },
      }))
      toast.success('Busca por SKU concluída')       // D-04
    } catch (err: any) {
      if (err.name === 'AbortError') return
      set((s) => ({ cross: { ...s.cross, loading: false, abortController: null } }))
      toast.error('Erro na busca: ' + err.message)
    }
  },
}))
```

**Subscrição com seletores atômicos (evita re-renders desnecessários):**

```typescript
// Dentro de SearchPage — subscreve apenas os campos necessários
const loading   = useSearchStore((s) => s.search.loading)
const results   = useSearchStore((s) => s.search.results)
const query     = useSearchStore((s) => s.search.query)
const setSearch = useSearchStore((s) => s.setSearch)

// Para múltiplos campos do mesmo slice, usar useShallow:
import { useShallow } from 'zustand/react/shallow'
const { query, sort, inStock, zipcode, selectedBrands } = useSearchStore(
  useShallow((s) => s.search)
)
```

[CITED: github.com/pmndrs/zustand README — selector pattern com `useShallow`]

### Padrão 2: AbortController no `ApiClient.request`

O `ApiClient.request` atual não aceita `signal`. É necessário adicionar o parâmetro opcional para que o store passe o sinal ao fetch:

```typescript
// frontend/src/api/client.ts — modificação mínima
public static async request<T>(
  endpoint: string,
  options: RequestInit = {},
  signal?: AbortSignal   // novo parâmetro opcional
): Promise<T> {
  const headers: any = { 'Content-Type': 'application/json', 'X-API-Key': API_KEY, ...options.headers }
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
    signal,              // passado ao fetch nativo
  })
  // ... resto permanece igual
}

// Métodos que a action usa — assinatura com signal:
static search(payload: {...}, signal?: AbortSignal) {
  return this.request<any>('/search', { method: 'POST', body: JSON.stringify(payload) }, signal)
}

static crossMarketplaceSearch(payload: {...}, signal?: AbortSignal) {
  return this.request<any>('/search/cross-marketplace', { method: 'POST', body: JSON.stringify(payload) }, signal)
}
```

[ASSUMED — padrão consolidado de AbortController com fetch; MDN documenta o pattern: signal passado nas options do fetch nativo]

### Padrão 3: Guarda Anti-Duplo-Fetch (React 19 StrictMode)

React 19 StrictMode em dev monta, desmonta e remonta componentes para detectar efeitos com cleanup incorreto. O risco: ao remontar `SearchPage` que já tem `loading=true` no store, um `useEffect` ingênuo poderia disparar segunda busca.

**Guarda correta — verificar estado do store antes de buscar:**

```typescript
// SearchPage — handleSearch não precisa de guarda extra;
// o guarda vive na action do store:
startSearch: async (payload) => {
  // A linha abaixo já garante anti-duplicata:
  // abort() do controller anterior + set loading=true
  // Se já loading=true quando componente remonta, handleSearch
  // só é chamado por ação explícita do usuário (submit do form)
  // — NÃO há useEffect que chama handleSearch automaticamente.
}
```

**Para o `useEffect` de preloadedJobId (herdado da Phase 27):**

```typescript
// SearchPage — useEffect do preloadedJobId (herdado, preservar D-11)
useEffect(() => {
  if (!preloadedJobId) return
  // Não buscar se já loading (busca em voo no store)
  if (useSearchStore.getState().search.loading) return

  setSearch({ loading: true })
  ApiClient.getHistoryDetail(preloadedJobId)
    .then(res => {
      setSearch({
        results: { results: res.results, query: res.query, brands_searched: res.brands },
        query: res.query || '',
        loading: false,
      })
    })
    .catch(() => toast.error("Erro ao carregar resultados do histórico"))
    .finally(() => { onClearPreloadedJob?.() })
// eslint-disable-next-line react-hooks/exhaustive-deps
}, [preloadedJobId])
```

**Nota StrictMode:** O padrão recomendado pelo React é usar o cleanup function de `useEffect` com `AbortController` (ver Pattern 1 acima). O store action já faz `abort()` do controller anterior, então o duplo-mount do StrictMode resulta em: (1ª invocação abortada pelo cleanup) → (2ª invocação prossegue). Isso é o comportamento correto. [VERIFIED: React docs via WebFetch]

### Padrão 4: WebSocket Cleanup na `CategoryPage` (D-02, D-09)

**Gap atual:** `wsRef.current` só é fechado dentro do handler `ws.onmessage` quando recebe `done`/`error_done` (App.tsx:476-479). Se o usuário navegar para outra aba enquanto o scrape está rodando, o WS fica aberto e os handlers continuam chamando `setState` em um componente desmontado.

```typescript
// CategoryPage — adicionar ANTES do return:
useEffect(() => {
  return () => {
    if (wsRef.current) {
      wsRef.current.onmessage = null   // previne setState após unmount
      wsRef.current.close()
      wsRef.current = null
    }
  }
}, [])  // array vazio = só roda no unmount
```

**Por que `onmessage = null` antes do `close()`:** O `close()` pode ser assíncrono; atribuir `null` ao handler garante que nenhuma mensagem em trânsito dispare `setState` após o componente já ter desmontado. [ASSUMED — padrão idiomatic de cleanup de WebSocket em React]

### Padrão 5: Coexistência com `preloadedJobId` (D-11)

O fluxo da Phase 27 (`preloadedJobId` em `App.tsx:2015`, propagado via props em `:2043-2044`) **permanece via props** — a migração para o store não altera esse canal:

```
App.tsx
  preloadedJobId (useState local do App)
  handleReopen(jobId, type) → setActiveTab + setPreloadedJobId
         │
         ▼ (prop)
  SearchPage / CrossMarketplacePage
    useEffect([preloadedJobId]) → carrega via ApiClient.getHistoryDetail
    salva resultado no store (setSearch/setCross)
    chama onClearPreloadedJob()
         │
         ▼
  App.tsx seta preloadedJobId = null
```

O `useEffect` de preloadedJobId nos componentes continua existindo — ele escreve no store ao invés de `useState` local. **Nenhuma alteração em `App.tsx` no fluxo do preloadedJobId** além da já feita na Phase 27. [VERIFIED: leitura de App.tsx:2015-2044, SearchPage:841-851, CrossMarketplacePage:1170-1182]

### Anti-Padrões a Evitar

- **`useRef` como flag de anti-duplo-fetch:** (`hasRun.current = true`) mascara bugs do StrictMode em vez de corrigi-los. O store já provê a fonte de verdade (`loading`) para esse guarda.
- **Seletor no objeto inteiro do slice:** `useSearchStore((s) => s.search)` sem `useShallow` faz re-render a cada update de qualquer campo — usar seletores atômicos ou `useShallow`.
- **Disparar toast no componente que observa `loading`:** Usar `useEffect([loading])` no componente cria race conditions se o componente estiver desmontado quando a busca completa. Disparar o toast **dentro da action** do store é mais seguro e garantidamente global.
- **Não retornar cleanup no `useEffect` do WS:** O handler fica "órfão" e chama `setState` de componente desmontado — memory leak silencioso no dev, warnings no React 19.

---

## Não Construir do Zero

| Problema | Não construir | Usar | Por quê |
|----------|--------------|------|---------|
| State management global | Context + useReducer manual | `zustand` | Sem Provider, TypeScript nativo, seletores eficientes, React 19 compat |
| Cancelamento de request | Flag booleana local | `AbortController` (Web API nativa) | Cancela o fetch real na rede; flag só evita `setState` mas não libera recursos |
| Toast global | Implementação própria de notificação | `sonner` (já instalado) | `toast()` pode ser chamado de qualquer contexto JS, inclusive fora de componentes |
| WebSocket cleanup | Lógica complexa de reconexão | `useEffect` retornando `ws.close()` | 5 linhas; o backend continua o job — o componente apenas abandona o feed ao vivo |

**Insight chave:** A busca síncrona já funciona corretamente — o problema é exclusivamente de *onde* o estado é guardado (componente que desmonta vs. módulo que persiste). Não há necessidade de refatorar a lógica de negócio.

---

## Armadilhas Comuns

### Armadilha 1: Re-render Cascata por Seletor Ineficiente

**O que dá errado:** Componente subscreve o slice inteiro `useSearchStore((s) => s.search)` — qualquer update (ex.: loading toggle) re-renderiza todo o componente, inclusive subcomponentes pesados de resultado.

**Por que acontece:** Zustand usa comparação por referência padrão; um objeto novo `{ ...s.search, loading: true }` sempre é diferente do anterior.

**Como evitar:** Seletores atômicos por campo, ou `useShallow` para múltiplos campos.

**Sinais de alerta:** Rendering excessivo observável no React DevTools Profiler.

---

### Armadilha 2: `Set<string>` (selectedItems) não é serializable

**O que dá errado:** `Set<string>` não serializa para JSON. Se alguém tentar usar middleware `persist` (proibido por D-05, mas pode surgir como ideia futura), o Set se perde.

**Como evitar:** D-05 proíbe `persist` — manter apenas em memória. Documentar explicitamente no store que `selectedItems` é `Set<string>` e não compatível com serialização.

**Sinais de alerta:** `JSON.stringify(store.getState())` retorna `{}` para o Set.

---

### Armadilha 3: AbortError propagado como erro real

**O que dá errado:** O `catch` na action do store não distingue `AbortError` de erros de rede reais — dispara `toast.error("Erro na busca: AbortError")` ao iniciar nova busca antes da anterior terminar.

**Como evitar:** `if (err.name === 'AbortError') return` antes de processar o erro.

**Sinais de alerta:** Toast de erro aparece ao clicar "Buscar" rapidamente duas vezes.

---

### Armadilha 4: `onClearPreloadedJob` não chamado após load de histórico

**O que dá errado:** `preloadedJobId` não é limpo após carregar o histórico. Na próxima vez que o componente remontar (troca de aba), o `useEffect([preloadedJobId])` dispara novamente e recarrega o histórico, sobrescrevendo resultados de busca subsequentes.

**Como evitar:** Sempre chamar `onClearPreloadedJob?.()` no `.finally()` do fetch de histórico (já feito no código atual — preservar ao migrar).

**Sinais de alerta:** Resultados de busca nova são substituídos pelos do histórico ao trocar de aba.

---

### Armadilha 5: `wsRef` em CategoryPage — handler após close()

**O que dá errado:** `ws.close()` no cleanup do `useEffect` fecha a conexão, mas o browser ainda pode entregar mensagens enfileiradas ao handler existente, chamando `setLogs`/`setProgress` em componente desmontado.

**Como evitar:** Atribuir `wsRef.current.onmessage = null` antes de `wsRef.current.close()`.

**Sinais de alerta:** Warning "Can't perform a React state update on an unmounted component" no console (React 19 pode silenciar esse warning, mas o behavior persiste).

---

## Exemplos de Código

### Store — Uso nos Componentes

```typescript
// SearchPage — substituição dos useState
import { useSearchStore } from '../stores/searchStore'
import { useShallow } from 'zustand/react/shallow'

const SearchPage = ({ brands, preloadedJobId, onClearPreloadedJob, onReopen }) => {
  // Campos de input — useShallow porque são múltiplos do mesmo slice
  const { query, sort, inStock, zipcode, selectedBrands } = useSearchStore(
    useShallow((s) => ({
      query: s.search.query,
      sort: s.search.sort,
      inStock: s.search.inStock,
      zipcode: s.search.zipcode,
      selectedBrands: s.search.selectedBrands,
    }))
  )
  // Campos que causam renders pesados — seletores atômicos
  const loading   = useSearchStore((s) => s.search.loading)
  const results   = useSearchStore((s) => s.search.results)

  // Actions
  const setSearch     = useSearchStore((s) => s.setSearch)
  const startSearch   = useSearchStore((s) => s.startSearch)

  // REMOVER: todos os useState locais de SearchPage
  // MANTER: historyRefreshKey (controla HistoryList) — pode ficar em useState local
  //         exporting (estado UI local, não persiste) — pode ficar em useState local

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    onClearPreloadedJob?.()
    await startSearch({
      query, sort, only_in_stock: inStock,
      brands: selectedBrands.length > 0 ? selectedBrands : undefined,
      zipcode: zipcode.replace(/\D/g, '').length === 8 ? zipcode.replace(/\D/g, '') : undefined,
      include_shipping: zipcode.replace(/\D/g, '').length === 8 ? true : undefined,
    })
    setHistoryRefreshKey(k => k + 1)  // historyRefreshKey permanece local
  }
  // ...
}
```

### CategoryPage — WebSocket Cleanup

```typescript
// Em CategoryPage, adicionar após os useState/useRef existentes:
useEffect(() => {
  return () => {
    if (wsRef.current) {
      wsRef.current.onmessage = null
      wsRef.current.close()
      wsRef.current = null
    }
  }
}, [])
```

### ApiClient — Signal Opcional

```typescript
// Adição mínima ao client.ts:
public static async request<T>(
  endpoint: string,
  options: RequestInit = {},
  signal?: AbortSignal
): Promise<T> {
  const headers: any = {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
    ...options.headers,
  }
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
    ...(signal ? { signal } : {}),
  })
  // ... resto igual
}
```

---

## Estado da Arte

| Abordagem Antiga | Abordagem Atual | Quando Mudou | Impacto |
|-----------------|-----------------|--------------|---------|
| Redux + Provider obrigatório | Zustand sem Provider, module-scoped | 2019+ (v1 do zustand) | Zero boilerplate de contexto |
| `useState` local para estado de página | Store global module-scoped | Esta phase | Estado sobrevive ao unmount do componente |
| `use-sync-external-store` polyfill | React 19 `useSyncExternalStore` nativo | zustand v5 / React 18+ | Menor bundle size |
| Importar `{ create }` de `zustand` vs `zustand/vanilla` | v5 mantém o mesmo padrão | — | `create` de `zustand` → hook; `createStore` de `zustand/vanilla` → store sem hook |

**Descontinuado/obsoleto:**
- Default export do zustand (`import create from 'zustand'`) — removido no v5. Usar named import: `import { create } from 'zustand'`. [CITED: zustand v5 release notes]
- `connectDevtools` e APIs UMD — removidos no v5.

---

## Log de Suposições

| # | Afirmação | Seção | Risco se Errada |
|---|-----------|-------|-----------------|
| A1 | `ApiClient.request` aceita terceiro parâmetro `signal?: AbortSignal` sem quebrar callers existentes (parâmetro opcional) | Standard Stack / Padrão 2 | Baixo — é parâmetro opcional; callers existentes não passam signal, comportamento não muda |
| A2 | `onmessage = null` antes de `close()` previne delivery de mensagens enfileiradas | Padrão 4 (WS cleanup) | Baixo — pattern padrão; o browser pode variar, mas o efeito de segurança é garantido |
| A3 | `toast()` do sonner pode ser chamado fora de componentes React (dentro de action do store) | Padrão 1 / Don't Hand-Roll | Médio — confirmado por fonte secundária (Medium/Sonner docs descrição do observer pattern); não verificado via Context7 (indisponível) |
| A4 | `selectedItems: Set<string>` em CrossSlice não causa problemas no zustand puro em memória | Padrão 1 | Baixo — Set funciona normalmente em memória; problema só surge com middleware persist (proibido por D-05) |

---

## Perguntas em Aberto

1. **`historyRefreshKey` no store ou local?**
   - O que sabemos: `historyRefreshKey` controla o re-fetch da `HistoryList` após uma busca (Phase 27, refreshKey pattern). É um contador de UI, não estado de busca.
   - O que está indefinido: deve migrar para o store (para que a lista do histórico atualize mesmo se a aba estiver desmontada) ou permanecer `useState` local?
   - Recomendação: manter `useState` local. A `HistoryList` só renderiza quando a aba está ativa — sem benefício em persistir no store.

2. **`exporting` e `loadingShipping` migram para o store?**
   - O que sabemos: São estados de UI transiente (indicadores de carregamento de operações específicas). Definição de D-03 não os lista explicitamente como estado a persistir.
   - O que está indefinido: se o usuário está no meio de um export e troca de aba, ao voltar o estado de `exporting` importa?
   - Recomendação: deixar em `useState` local. Não estão na lista de D-03 e não se beneficiam da persistência.

---

## Disponibilidade de Ambiente

| Dependência | Necessária Para | Disponível | Versão | Fallback |
|-------------|----------------|-----------|--------|----------|
| Node.js / npm | Instalar zustand | Sim | (projeto ativo com node_modules) | — |
| zustand | Store de estado | Não instalada | — | Instalar: `npm install zustand@5.0.14` |
| sonner | Toast de conclusão | Sim (^2.0.7) | ^2.0.7 | — |
| framer-motion | AnimatePresence (permanece) | Sim (^12.38.0) | ^12.38.0 | — |

**Dependências ausentes sem fallback:** `zustand` — instalar no Wave 0 / Tarefa 0.

---

## Arquitetura de Validação

> `workflow.nyquist_validation: true` em `.planning/config.json` — seção obrigatória.

### Framework de Testes

| Propriedade | Valor |
|-------------|-------|
| Framework | Nenhum instalado (sem Jest, Vitest, Playwright) |
| Arquivo de config | Ausente |
| Comando rápido | N/A — testes são manuais (UAT) nesta phase |
| Comando completo | N/A |

> Este projeto frontend não possui infraestrutura de testes automatizados (`frontend/package.json` não tem Jest/Vitest). Os 4 critérios de sucesso são validados por UAT manual.

### Mapa de Requisitos → Testes

| Req ID | Comportamento | Tipo de Teste | Comando Automatizado | Arquivo Existe? |
|--------|--------------|---------------|---------------------|-----------------|
| PERS-01 / Critério #1 | Busca em andamento continua ao trocar e voltar de aba | UAT manual | — | N/A — manual |
| PERS-01 / Critério #2 | Toast de conclusão aparece ao concluir fora da aba | UAT manual | — | N/A — manual |
| PERS-01 / Critério #3 | Sem duplo-fetch; cancelamento ao iniciar nova busca | UAT manual + DevTools Network | — | N/A — manual |
| PERS-01 / Critério #4 | WS fecha ao desmontar CategoryPage; sem logs após saída | UAT manual + DevTools Console | — | N/A — manual |

### Procedimentos UAT por Critério

**Critério #1 — Estado sobrevive à troca de aba:**
1. Iniciar busca Comparativa longa (muitas marcas / sem filtro de estoque).
2. Enquanto `loading` spinner ativo: clicar em outra aba (ex.: Monitor).
3. Clicar de volta em Comparativa.
4. Verificar: spinner ainda ativo, query preenchida, selectedBrands preservados.
5. Aguardar conclusão: toast "Busca Comparativa concluída" e resultados visíveis.
6. Repetir para busca por SKU.

**Critério #2 — Toast de conclusão fora da aba:**
1. Iniciar busca Comparativa.
2. Navegar para outra aba antes de concluir.
3. Verificar: toast de sucesso aparece na aba atual (não precisa estar na aba de busca).
4. Retornar à aba Comparativa: resultados disponíveis.

**Critério #3 — Sem duplo-fetch e cancelamento correto:**
- *Sem duplo-fetch:* Abrir DevTools > Network. Iniciar busca, trocar aba, voltar. Verificar: apenas 1 request `POST /search` na aba Network (não 2).
- *Cancelamento:* Iniciar busca A. Antes de concluir, iniciar busca B (nova query). Verificar: request A aparece como "Canceled" no DevTools Network; request B prossegue; apenas toast de B aparece.

**Critério #4 — WS cleanup sem vazamento:**
1. Abrir DevTools > Console.
2. Ir para aba Categorias e iniciar uma varredura.
3. Enquanto WS ativo (logs aparecendo), navegar para outra aba.
4. Verificar: nenhum novo log aparece no console após a troca de aba (handler null).
5. Verificar: DevTools > Network > WS mostra conexão como "Closed" após a navegação.

### Gaps do Wave 0

- Nenhuma infraestrutura de testes precisa ser criada — todos os testes são UAT manuais. Wave 0 pode focar na instalação do zustand e criação do arquivo do store.

---

## Domínio de Segurança

> Fase puramente de frontend state management — sem novas rotas, sem novos endpoints, sem autenticação nova, sem dados sensíveis.

| Categoria ASVS | Aplica | Controle |
|----------------|--------|---------|
| V2 Autenticação | Não | — |
| V3 Gerenciamento de Sessão | Não | — |
| V4 Controle de Acesso | Não | — |
| V5 Validação de Input | Não (inputs já validados no código existente) | — |
| V6 Criptografia | Não | — |

**Padrão de ameaça relevante:** Nenhum introduzido por esta phase. O `AbortController` não expõe estado sensível; o store em memória não persiste em storage.

---

## Fontes

### Primárias (confiança HIGH)
- `frontend/src/App.tsx` — leitura direta do código-fonte (App.tsx:374-491, 830-891, 1105-1260, 2010-2143)
- `frontend/package.json` — confirmação de dependências (sonner ^2.0.7; zustand ausente)
- `frontend/src/api/client.ts` — confirmação da assinatura de `request()` e métodos de busca
- `.planning/phases/28-persist-ncia-da-busca-entre-abas/28-CONTEXT.md` — decisões travadas D-01..D-11
- `npm view zustand` — versão 5.0.14, modified 2026-05-28, repo pmndrs/zustand [VERIFIED: npm registry]

### Secundárias (confiança MEDIUM)
- github.com/pmndrs/zustand README — padrões de store TypeScript, seletores, `useShallow`, `getState()` fora de componentes [CITED]
- pmnd.rs/blog/announcing-zustand-v5/ — breaking changes v5, React 19 compat, migration path [CITED]
- github.com/pmndrs/zustand discussions/2842 — confirmação React 19 compat [CITED]
- dev.to/pockit_tools — React 19 StrictMode double-mount e padrões AbortController [CITED]
- sonner.emilkowal.ski/toast — API de `toast.success()`, import pattern [CITED]

### Terciárias (confiança LOW — verificar antes de usar)
- medium.com/@reactjsbd — React 19 + Zustand patterns (fonte única, não verificada contra docs oficiais)

---

## Metadados

**Breakdown de Confiança:**
- Stack padrão (zustand v5): HIGH — verificado via npm registry + release notes oficiais
- Padrões de arquitetura (store shape, selectors): HIGH — baseado em docs oficiais do zustand
- AbortController integration: MEDIUM — padrão Web API padrão; integração específica com ApiClient é [ASSUMED]
- Pitfalls: HIGH — derivados diretamente da leitura do código-fonte e comportamento documentado do React 19
- Toast fora de componente: MEDIUM — confirmado por fonte secundária, não via Context7

**Data da pesquisa:** 2026-06-21
**Válido até:** 2026-07-21 (zustand é estável; React 19 recém-lançado — checar em mudanças de StrictMode behavior se >30 dias)
