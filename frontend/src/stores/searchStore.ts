/* eslint-disable @typescript-eslint/no-explicit-any */
import { create } from 'zustand'
import { toast } from 'sonner'
import { ApiClient } from '../api/client'

// --- Tipos ---

// Resultado discriminado das actions de busca (CR-01): o caller precisa distinguir
// conclusão real de cancelamento/erro para só então pós-processar e refazer o histórico.
export type SearchOutcome =
  | { status: 'success' }
  | { status: 'aborted' }
  | { status: 'error' }

interface SearchSlice {
  query: string
  sort: string
  inStock: boolean
  // CEP confirmado para a sessão (sem default — só o que o usuário digitar no modal de frete).
  // Memory-only (sem persist) — reseta no reload.
  zipcode: string
  selectedBrands: string[]
  results: any | null
  loading: boolean
  abortController: AbortController | null
  // Job de histórico cuja pré-carga (getHistoryDetail) está em voo. Distingue
  // "reabrir histórico em voo" de "busca normal em voo" na guarda anti-duplo-fetch (WR-03).
  loadingPreloadId: string | null
}

interface CrossSlice {
  targetSku: string
  zipcode: string
  results: any | null
  // NOTE: selectedItems é Set<string> e NÃO é serializável (JSON.stringify retorna {}).
  // Compatível apenas com store em memória. D-05 proíbe middleware persist por este motivo.
  selectedItems: Set<string>
  selectionMode: boolean
  loading: boolean
  abortController: AbortController | null
  loadingPreloadId: string | null
}

interface SearchStoreState {
  search: SearchSlice
  cross: CrossSlice
  // Actions
  setSearch: (patch: Partial<SearchSlice>) => void
  setCross: (patch: Partial<CrossSlice>) => void
  startSearch: (payload: any) => Promise<SearchOutcome>
  startCrossSearch: (payload: any) => Promise<SearchOutcome>
}

// Aplica _display_order aos resultados da busca por SKU, preservando a ordenação do backend.
// Module-scoped e exportada para que a action do store (fonte única — CR-01) e a pré-carga
// de histórico em App.tsx usem exatamente a mesma lógica (evita duplicação — IN-02).
export const withDisplayOrder = (data: any) => {
  if (!data || !Array.isArray(data.results)) return data
  return {
    ...data,
    results: data.results.map((item: any, index: number) => ({
      ...item,
      _display_order: item._display_order ?? index,
    })),
  }
}

// --- Store ---
// Store module-scoped (zustand): sobrevive ao ciclo de vida dos componentes,
// pois vive no escopo do módulo JS, fora da árvore React.
// NÃO usar middleware persist (D-05) — selectedItems (Set<string>) não é serializável
// e os resultados de busca não devem sobreviver a reload.

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
    loadingPreloadId: null,
  },
  cross: {
    targetSku: '',
    zipcode: '',
    results: null,
    selectedItems: new Set(),
    selectionMode: false,
    loading: false,
    abortController: null,
    loadingPreloadId: null,
  },

  setSearch: (patch) =>
    set((s) => ({ search: { ...s.search, ...patch } })),

  setCross: (patch) =>
    set((s) => ({ cross: { ...s.cross, ...patch } })),

  startSearch: async (payload) => {
    // Cancela request anterior se existir (AbortController vive na action, não nos componentes)
    get().search.abortController?.abort()
    const controller = new AbortController()

    set((s) => ({
      search: {
        ...s.search,
        loading: true,
        results: null,
        abortController: controller,
        loadingPreloadId: null,
      },
    }))

    try {
      const data = await ApiClient.search(payload, controller.signal)
      // Identity guard (WR-01/WR-02): um request mais novo já assumiu o controller.
      // Este resolveu tarde demais — não clobberar o estado do request vigente.
      if (get().search.abortController !== controller) return { status: 'aborted' }
      set((s) => ({
        search: { ...s.search, loading: false, results: data, abortController: null },
      }))
      toast.success('Busca Comparativa concluída')   // D-04 — global, funciona em qualquer aba
      return { status: 'success' }
    } catch (err: any) {
      if (err.name === 'AbortError') return { status: 'aborted' }  // cancelamento intencional — não notifica
      // Identity guard também no erro: só reporta/limpa se ainda for o request vigente.
      if (get().search.abortController !== controller) return { status: 'aborted' }
      set((s) => ({ search: { ...s.search, loading: false, abortController: null } }))
      toast.error('Erro na busca: ' + err.message)
      return { status: 'error' }
    }
  },

  startCrossSearch: async (payload) => {
    // Cancela request anterior se existir
    get().cross.abortController?.abort()
    const controller = new AbortController()

    set((s) => ({
      cross: {
        ...s.cross,
        loading: true,
        results: null,
        // Zera seleção ao iniciar nova busca (espelha reset que handleSearch da SKU faz hoje)
        selectedItems: new Set(),
        selectionMode: false,
        abortController: controller,
        loadingPreloadId: null,
      },
    }))

    try {
      const data = await ApiClient.crossMarketplaceSearch(payload, controller.signal)
      if (get().cross.abortController !== controller) return { status: 'aborted' }
      // CR-01: withDisplayOrder aplicado DENTRO da action (fonte única). O caller não
      // reescreve mais o store depois do await — elimina o re-wrap de resultados cruzados.
      set((s) => ({
        cross: { ...s.cross, loading: false, results: withDisplayOrder(data), abortController: null },
      }))
      toast.success('Busca por SKU concluída')       // D-04
      return { status: 'success' }
    } catch (err: any) {
      if (err.name === 'AbortError') return { status: 'aborted' }  // cancelamento intencional — não notifica
      if (get().cross.abortController !== controller) return { status: 'aborted' }
      set((s) => ({ cross: { ...s.cross, loading: false, abortController: null } }))
      toast.error('Erro na busca: ' + err.message)
      return { status: 'error' }
    }
  },
}))
