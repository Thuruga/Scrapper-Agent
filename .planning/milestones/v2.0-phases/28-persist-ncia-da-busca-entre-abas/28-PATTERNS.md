# Phase 28: Persistência da Busca Entre Abas — Mapa de Padrões

**Mapeado:** 2026-06-21
**Arquivos analisados:** 5 (3 novos/modificados + 2 de referência)
**Análogos encontrados:** 3 / 4 (store é greenfield)

---

## Classificação de Arquivos

| Arquivo Novo/Modificado | Role | Data Flow | Análogo Mais Próximo | Qualidade |
|-------------------------|------|-----------|----------------------|-----------|
| `frontend/src/stores/searchStore.ts` | store | request-response | **Nenhum** — primeiro store do projeto | greenfield |
| `frontend/src/App.tsx` (CategoryPage — fix WS) | componente | event-driven (WebSocket) | `App.tsx:374-491` (o próprio wsRef/onmessage) | self-analog |
| `frontend/src/App.tsx` (SearchPage — migração useState → store) | componente | request-response | `App.tsx:830-911` (o próprio SearchPage) | self-analog |
| `frontend/src/App.tsx` (CrossMarketplacePage — migração useState → store) | componente | request-response | `App.tsx:1105-1182` (o próprio CrossMarketplacePage) | self-analog |
| `frontend/src/api/client.ts` (adicionar `signal?: AbortSignal`) | cliente HTTP | request-response | `App.tsx:21-45` (o próprio `request()`) | self-analog |
| `frontend/package.json` (adicionar zustand) | config | — | `frontend/package.json` existente | exact |

---

## Atribuições de Padrão

### `frontend/src/stores/searchStore.ts` (store, request-response)

**Análogo:** NENHUM — greenfield. Não existe nenhum store de estado global no projeto hoje. O diretório `frontend/src/stores/` não existe e deve ser criado. Ver seção "Sem Análogo" abaixo para instrução ao planner.

**Estrutura de módulo a copiar de `frontend/src/api/client.ts` (linhas 1-5):**
```typescript
/* eslint-disable @typescript-eslint/no-explicit-any */
// Padrão do projeto: comentário eslint-disable no topo de arquivos com `any`
// e constantes de ambiente via import.meta.env
const API_BASE_URL = import.meta.env.VITE_API_URL || '';
const API_KEY = import.meta.env.VITE_API_KEY || 'dev-api-key';
```

**Padrão de import do `toast` a copiar de `App.tsx` (linha 36):**
```typescript
import { toast } from 'sonner';
```

**Padrão de import do `ApiClient` a copiar de `App.tsx` (linha 385):**
```typescript
// Em App.tsx, ApiClient é usado diretamente em componentes internos.
// No store, o import será:
import { ApiClient } from '../api/client';
```

**Estado que migra para o store — extraído de `App.tsx:831-839` (SearchPage):**
```typescript
// ANTES (useState local em SearchPage — App.tsx:831-839):
const [query, setQuery] = useState('');
const [results, setResults] = useState<any>(null);
const [loading, setLoading] = useState(false);
const [sort, setSort] = useState('relevance');
const [inStock, setInStock] = useState(false);
const [zipcode, setZipcode] = useState('');
const [selectedBrands, setSelectedBrands] = useState<string[]>([]);
// NÃO migra: [exporting] e [historyRefreshKey] — UI transiente, manter como useState local
```

**Estado que migra para o store — extraído de `App.tsx:1106-1114` (CrossMarketplacePage):**
```typescript
// ANTES (useState local em CrossMarketplacePage — App.tsx:1106-1114):
const [targetSku, setTargetSku] = useState('');
const [zipcode, setZipcode] = useState('');
const [loading, setLoading] = useState(false);
const [results, setResults] = useState<any>(null);
const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
const [selectionMode, setSelectionMode] = useState(false);
// NÃO migra: [exporting], [loadingShipping], [historyRefreshKey] — UI transiente
```

**Padrão de lógica de busca a encapsular — extraído de `App.tsx:867-891` (handleSearch):**
```typescript
// ANTES (handleSearch em SearchPage — App.tsx:867-891):
const handleSearch = async (e: React.FormEvent) => {
  e.preventDefault();
  if (onClearPreloadedJob) onClearPreloadedJob();
  setLoading(true);
  setResults(null);
  try {
    const data = await ApiClient.search({
      query,
      sort,
      only_in_stock: inStock,
      brands: selectedBrands.length > 0 ? selectedBrands : undefined,
      zipcode: zipcode.replace(/\D/g, '').length === 8 ? zipcode.replace(/\D/g, '') : undefined,
      include_shipping: zipcode.replace(/\D/g, '').length === 8 ? true : undefined
    });
    setResults(data);
    setHistoryRefreshKey(k => k + 1);
  } catch (err: any) {
    console.error(err);
    toast.error("Erro na busca: " + err.message);
    setResults(null);
  } finally {
    setLoading(false);
  }
};
// DEPOIS: lógica de setLoading/setResults/ApiClient.search migra para action do store (startSearch).
// `toast.error` permanece na action do store. `toast.success` é adicionado (D-04).
// `setHistoryRefreshKey` permanece no componente (não migra).
// AbortController é adicionado para cancelamento (D-discretion).
```

**Padrão de erro existente a preservar — extraído de `App.tsx:884-888`:**
```typescript
// Padrão de toast.error já em uso (App.tsx:886):
toast.error("Erro na busca: " + err.message);
// A action do store deve manter este padrão para erros reais.
// Adicionar: if (err.name === 'AbortError') return; — antes do toast.error.
```

---

### `frontend/src/App.tsx` — Fix de Cleanup de WebSocket na CategoryPage

**Análogo:** O próprio `wsRef` e `ws.onmessage` na `CategoryPage` (`App.tsx:374`, `App.tsx:467-491`).

**Gap identificado — `App.tsx:476-479` (único ponto de fechamento do WS hoje):**
```typescript
// HOJE: WS só fecha dentro do onmessage quando recebe 'done' ou 'error_done' (App.tsx:476-479):
} else if (msg.type === 'done' || msg.type === 'error_done') {
  setIsScraping(false);
  ws.close();           // ← único close existente
  // ...
}
// PROBLEMA: se o usuário trocar de aba durante scrape, este branch nunca é alcançado
// e o WS fica aberto com handlers chamando setState em componente desmontado.
```

**Padrão de `useEffect` existente na CategoryPage a usar como referência de posicionamento — `App.tsx:378-380`:**
```typescript
// Existe apenas este useEffect hoje na CategoryPage (App.tsx:378-380):
useEffect(() => {
  logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
}, [logs]);
// O novo useEffect de cleanup deve ser adicionado APÓS os useState/useRef e ANTES do return.
```

**`wsRef` e inicialização — `App.tsx:374`, `468`:**
```typescript
const wsRef = useRef<WebSocket | null>(null);  // App.tsx:374
// ...
wsRef.current = ws;                             // App.tsx:468 — no startScrape()
```

**O `useEffect` de cleanup a ADICIONAR (5 linhas) imediatamente após os useRef existentes:**
```typescript
// ADICIONAR após linha 376 (após useRef<HTMLDivElement>) e antes de fetchBrandCategories:
useEffect(() => {
  return () => {
    if (wsRef.current) {
      wsRef.current.onmessage = null;  // previne setState após unmount
      wsRef.current.close();
      wsRef.current = null;
    }
  };
}, []);  // array vazio = executa apenas no unmount
```

---

### `frontend/src/App.tsx` — Migração SearchPage (`useState` → store)

**Análogo:** O próprio SearchPage (`App.tsx:830-1101`).

**Props atuais que PERMANECEM inalteradas — `App.tsx:829-830`:**
```typescript
type SearchPageProps = { brands: any[], preloadedJobId?: string | null, onClearPreloadedJob?: () => void, onReopen?: (jobId: string) => void };
const SearchPage = ({ brands, preloadedJobId, onClearPreloadedJob, onReopen }: SearchPageProps) => {
```

**`useEffect` do `preloadedJobId` que DEVE SER PRESERVADO — `App.tsx:841-851`:**
```typescript
useEffect(() => {
  if (preloadedJobId) {
    setLoading(true);
    ApiClient.getHistoryDetail(preloadedJobId).then(res => {
      setResults({ results: res.results, query: res.query, brands_searched: res.brands });
      if (res.query) setQuery(res.query);
    }).catch(() => toast.error("Erro ao carregar resultados do histórico"))
      .finally(() => { setLoading(false); if (onClearPreloadedJob) onClearPreloadedJob(); });
  }
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [preloadedJobId]);
// APÓS migração: setLoading/setResults/setQuery → setCross do store.
// A estrutura do useEffect e o .finally(() => onClearPreloadedJob()) DEVEM ser preservados (D-11).
// Guarda anti-duplo-fetch: adicionar `if (useSearchStore.getState().search.loading) return;`
// no início do bloco `if (preloadedJobId)`.
```

**Propagação do `preloadedJobId` via `renderTab` — `App.tsx:2043` (não muda):**
```typescript
case 'search': return <SearchPage brands={brands} preloadedJobId={preloadedJobId} onClearPreloadedJob={() => setPreloadedJobId(null)} onReopen={(jobId) => handleReopen(jobId, 'search')} />;
```

---

### `frontend/src/App.tsx` — Migração CrossMarketplacePage (`useState` → store)

**Análogo:** O próprio CrossMarketplacePage (`App.tsx:1105-1260`).

**Props atuais que PERMANECEM inalteradas — `App.tsx:1104-1105`:**
```typescript
type CrossMarketplacePageProps = { preloadedJobId?: string | null, onClearPreloadedJob?: () => void, onReopen?: (jobId: string) => void };
const CrossMarketplacePage = ({ preloadedJobId, onClearPreloadedJob, onReopen }: CrossMarketplacePageProps) => {
```

**`useEffect` do `preloadedJobId` que DEVE SER PRESERVADO — `App.tsx:1170-1182`:**
```typescript
useEffect(() => {
  if (preloadedJobId) {
    setLoading(true);
    ApiClient.getHistoryDetail(preloadedJobId).then(res => {
      setResults(withDisplayOrder(res.results));
      if (res.query) setTargetSku(res.query.replace('SKU: ', ''));
      setSelectionMode(false);
      setSelectedItems(new Set());
    }).catch(() => toast.error("Erro ao carregar resultados do histórico"))
      .finally(() => { setLoading(false); if (onClearPreloadedJob) onClearPreloadedJob(); });
  }
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [preloadedJobId]);
// APÓS migração: setLoading/setResults/setTargetSku/setSelectionMode/setSelectedItems → setCross do store.
// Guarda anti-duplo-fetch: adicionar `if (useSearchStore.getState().cross.loading) return;`
```

**Propagação via `renderTab` — `App.tsx:2044` (não muda):**
```typescript
case 'cross': return <CrossMarketplacePage preloadedJobId={preloadedJobId} onClearPreloadedJob={() => setPreloadedJobId(null)} onReopen={(jobId) => handleReopen(jobId, 'cross')} />;
```

---

### `frontend/src/api/client.ts` (adicionar `signal?: AbortSignal`)

**Análogo:** O próprio método `request()` (`client.ts:21-45`).

**Assinatura atual — `client.ts:21-31`:**
```typescript
public static async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers: any = {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
    ...options.headers,
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });
```

**Modificação mínima a aplicar (parâmetro opcional, sem quebrar callers existentes):**
```typescript
// DEPOIS — adicionar terceiro parâmetro opcional:
public static async request<T>(endpoint: string, options: RequestInit = {}, signal?: AbortSignal): Promise<T> {
  const headers: any = {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
    ...options.headers,
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
    ...(signal ? { signal } : {}),  // signal passado ao fetch nativo
  });
  // ... resto permanece igual a client.ts:33-45
```

**Métodos que recebem assinatura com `signal` — `client.ts:77-96`:**
```typescript
// ANTES (client.ts:77-83):
static crossMarketplaceSearch(payload: { target_sku: string; search_query?: string; broad_query?: string; min_score?: number; zipcode?: string }) {
  return this.request<any>('/search/cross-marketplace', { method: 'POST', body: JSON.stringify(payload) });
}

// ANTES (client.ts:91-96):
static search(payload: { query: string; brands?: string[]; max_per_brand?: number; sort?: string; only_in_stock?: boolean; zipcode?: string; include_shipping?: boolean }) {
  return this.request<any>('/search', { method: 'POST', body: JSON.stringify(payload) });
}

// DEPOIS — adicionar signal opcional nos dois:
static crossMarketplaceSearch(payload: {...}, signal?: AbortSignal) {
  return this.request<any>('/search/cross-marketplace', { method: 'POST', body: JSON.stringify(payload) }, signal);
}
static search(payload: {...}, signal?: AbortSignal) {
  return this.request<any>('/search', { method: 'POST', body: JSON.stringify(payload) }, signal);
}
```

---

### `frontend/package.json` (adicionar zustand)

**Análogo:** O próprio `package.json`.

**Estado atual das dependências — `package.json:14-21`:**
```json
"dependencies": {
  "clsx": "^2.1.1",
  "framer-motion": "^12.38.0",
  "lucide-react": "^1.14.0",
  "react": "^19.2.5",
  "react-dom": "^19.2.5",
  "recharts": "^3.8.1",
  "sonner": "^2.0.7",
  "tailwind-merge": "^3.5.0"
}
```

**Entrada a adicionar (via `npm install zustand@5.0.14` no Wave 0):**
```json
"zustand": "^5.0.14"
```

---

## Padrões Compartilhados

### Toast de erro (padrão já estabelecido)
**Fonte:** `App.tsx:886` (SearchPage), `App.tsx:1162` (CrossMarketplacePage), `App.tsx:847` (preloadedJobId)
**Aplicar em:** action do store (`startSearch`, `startCrossSearch`) e `useEffect` do preloadedJobId
```typescript
toast.error("Erro na busca: " + err.message);
toast.error("Erro ao carregar resultados do histórico");
toast.error('Erro ao exportar: ' + err.message);
```

### Toast de conclusão (NOVO — D-04)
**Fonte:** Nenhuma — comportamento novo a adicionar dentro das actions do store.
**Aplicar em:** `startSearch` e `startCrossSearch` do store, no bloco `try` após `set(results)`.
```typescript
toast.success('Busca Comparativa concluída');  // startSearch
toast.success('Busca por SKU concluída');      // startCrossSearch
```

### AnimatePresence (permanece intacta — D-07)
**Fonte:** `App.tsx:2127-2137`
**NÃO modificar:** A troca de aba com `key={activeTab}` continua desmontando componentes — o store é que desacopla o estado do ciclo de vida.
```typescript
<AnimatePresence mode="wait">
  <motion.div
    key={activeTab}
    initial={{ opacity: 0, x: 10 }}
    animate={{ opacity: 1, x: 0 }}
    exit={{ opacity: 0, x: -10 }}
    transition={{ duration: 0.2 }}
  >
    {renderTab()}
  </motion.div>
</AnimatePresence>
```

### Import de `toast` (padrão estabelecido)
**Fonte:** `App.tsx:36`
**Aplicar em:** `searchStore.ts` (import direto — `toast()` do sonner pode ser chamado fora de componentes React)
```typescript
import { toast } from 'sonner';
```

### Convenção de import de `ApiClient`
**Fonte:** `App.tsx` usa `ApiClient` diretamente (importado implicitamente — está no mesmo arquivo monolítico).
**No store:** import explícito necessário:
```typescript
import { ApiClient } from '../api/client';
```

### Comentário `eslint-disable` (convenção do projeto)
**Fonte:** `App.tsx:1`, `client.ts:1`
**Aplicar em:** `searchStore.ts` (contém campos `any`)
```typescript
/* eslint-disable @typescript-eslint/no-explicit-any */
```

---

## Sem Análogo Encontrado

| Arquivo | Role | Data Flow | Razão |
|---------|------|-----------|-------|
| `frontend/src/stores/searchStore.ts` | store | request-response | Primeiro e único store do projeto — nenhuma biblioteca de estado global existe hoje (`frontend/package.json` não tem zustand, Redux, Jotai ou qualquer outra). O diretório `src/stores/` não existe. Planner deve usar os padrões do RESEARCH.md (Padrão 1 — Store Unificado com Slices) como referência primária para este arquivo. |

---

## Pontos de Atenção para o Planner

1. **Ordem obrigatória:** Fix do WS cleanup da CategoryPage (D-09) ANTES da migração do store. São independentes no código, mas a decisão está travada no STATE.md.

2. **`historyRefreshKey` e `exporting` NÃO migram:** Permanecem como `useState` local em cada componente. Ver `App.tsx:839` e `App.tsx:834` respectivamente. A lista D-03 não os inclui.

3. **`withDisplayOrder` permanece local em CrossMarketplacePage:** Função utilitária pura (`App.tsx:1116-1125`) — não é estado, não migra para o store.

4. **`loadingShipping` permanece local em CrossMarketplacePage:** Estado UI transiente por item (`App.tsx:1110`), não listado em D-03.

5. **Guarda anti-duplo-fetch no `useEffect` de preloadedJobId:** Adicionar `if (useSearchStore.getState().search.loading) return;` (para SearchPage) e `.cross.loading` (para CrossMarketplacePage) no início do bloco `if (preloadedJobId)`, antes do `setLoading(true)`.

6. **`AbortController` no store, não nos componentes:** Os componentes chamam `startSearch(payload)` — o cancelamento do request anterior é responsabilidade da action.

7. **Criar diretório `frontend/src/stores/`:** O planner deve incluir a criação do diretório antes de criar `searchStore.ts`.

---

## Metadados

**Escopo de busca:** `frontend/src/` (App.tsx, api/client.ts), `frontend/package.json`
**Arquivos lidos:** 4 (CONTEXT.md, RESEARCH.md, App.tsx — 5 seções, client.ts, package.json)
**Data do mapeamento:** 2026-06-21
