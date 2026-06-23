import { create } from 'zustand'
import { toast } from 'sonner'
import { ApiClient } from '../api/client'

export type BannerRunStatus = 'RUNNING' | 'REVIEW' | 'COMPLETED' | 'PARTIAL' | 'CANCELLED' | 'FAILED'
export type BannerBrandStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'

export interface BannerCandidate {
  banner_id: string
  brand_key: string
  brand_name: string
  slide_order: number
  friendly_filename: string
  source_url: string
  rendered_url: string
  click_url?: string | null
  alt_text?: string | null
  dom_kind: string
  rendered_width?: number | null
  rendered_height?: number | null
  natural_width?: number | null
  natural_height?: number | null
  asset: { sha256: string; extension: string; content_type: string; byte_count: number }
}

export interface BannerBrandProgress {
  brand_key: string
  brand_name: string
  status: BannerBrandStatus
  banner_count: number
  video_count: number
  error?: string | null
  screenshot_asset?: unknown
}

export interface BannerRun {
  run_id: string
  selected_brands: string[]
  status: BannerRunStatus
  brand_progress: Record<string, BannerBrandProgress>
  banners: BannerCandidate[]
  created_at: string
  approved_at?: string | null
  error?: string | null
}

export interface BannerHistoryItem {
  run_id: string
  created_at: string
  approved_at: string
  banner_count: number
  brand_count: number
  status: 'COMPLETED'
}

interface BannerStoreState {
  selectedBrands: string[]
  selectionInitialized: boolean
  activeJobId: string | null
  run: BannerRun | null
  selectedBannerIds: string[]
  seenBannerIds: string[]
  history: BannerHistoryItem[]
  historyLoading: boolean
  setSelectedBrands: (brands: string[]) => void
  initializeBrands: (brands: string[]) => void
  start: () => Promise<void>
  stop: () => Promise<void>
  refresh: (jobId?: string) => Promise<void>
  toggleBanner: (bannerId: string) => void
  selectAllBanners: () => void
  clearBanners: () => void
  approve: () => Promise<void>
  loadHistory: () => Promise<void>
  reopenHistory: (jobId: string) => Promise<void>
  deleteHistory: (jobId: string) => Promise<void>
}

let pollGeneration = 0
const TERMINAL = new Set<BannerRunStatus>(['REVIEW', 'COMPLETED', 'PARTIAL', 'CANCELLED', 'FAILED'])

function selectionForRun(state: BannerStoreState, run: BannerRun) {
  const incoming = run.banners.map(item => item.banner_id)
  const fresh = incoming.filter(id => !state.seenBannerIds.includes(id))
  return {
    selectedBannerIds: [...new Set([...state.selectedBannerIds, ...fresh])],
    seenBannerIds: [...new Set([...state.seenBannerIds, ...incoming])],
  }
}

export const useBannerStore = create<BannerStoreState>()((set, get) => ({
  selectedBrands: [],
  selectionInitialized: false,
  activeJobId: null,
  run: null,
  selectedBannerIds: [],
  seenBannerIds: [],
  history: [],
  historyLoading: false,

  setSelectedBrands: (brands) => set({ selectedBrands: brands }),
  initializeBrands: (brands) => {
    if (!brands.length) return
    set(state => state.selectionInitialized
      ? state
      : { selectedBrands: brands, selectionInitialized: true })
  },

  start: async () => {
    const brands = get().selectedBrands
    if (!brands.length) return
    const generation = ++pollGeneration
    try {
      const response = await ApiClient.startBannerJob(brands)
      const run = response.run as BannerRun
      set({
        activeJobId: response.job_id,
        run,
        selectedBannerIds: [],
        seenBannerIds: [],
      })
      if (generation === pollGeneration) void get().refresh(response.job_id)
    } catch (error) {
      toast.error(`Erro ao iniciar extração: ${(error as Error).message}`)
    }
  },

  refresh: async (jobId) => {
    const target = jobId || get().activeJobId
    if (!target) return
    const generation = pollGeneration
    try {
      const run = await ApiClient.getBannerJob(target) as BannerRun
      if (get().activeJobId !== target || generation !== pollGeneration) return
      const selection = selectionForRun(get(), run)
      set({ run, ...selection })
      if (run.status === 'RUNNING') {
        window.setTimeout(() => {
          if (get().activeJobId === target && generation === pollGeneration) void get().refresh(target)
        }, 750)
      } else if (TERMINAL.has(run.status)) {
        if (run.status === 'REVIEW') toast.success('Extração concluída. Revise os banners antes de aprovar.')
        if (run.status === 'CANCELLED') toast.info('Extração interrompida.')
        if (run.status === 'PARTIAL' || run.status === 'FAILED') toast.error(run.error || 'A extração terminou com falhas.')
      }
    } catch (error) {
      if (get().activeJobId === target) toast.error(`Erro ao acompanhar extração: ${(error as Error).message}`)
    }
  },

  stop: async () => {
    const jobId = get().activeJobId
    if (!jobId) return
    try {
      await ApiClient.stopBannerJob(jobId)
      toast.info('Parada solicitada. Finalizando a etapa atual…')
      void get().refresh(jobId)
    } catch (error) {
      toast.error(`Não foi possível parar: ${(error as Error).message}`)
    }
  },

  toggleBanner: (bannerId) => set(state => ({
    selectedBannerIds: state.selectedBannerIds.includes(bannerId)
      ? state.selectedBannerIds.filter(id => id !== bannerId)
      : [...state.selectedBannerIds, bannerId],
  })),
  selectAllBanners: () => set(state => ({ selectedBannerIds: state.run?.banners.map(item => item.banner_id) || [] })),
  clearBanners: () => set({ selectedBannerIds: [] }),

  approve: async () => {
    const { activeJobId, selectedBannerIds } = get()
    if (!activeJobId || !selectedBannerIds.length) return
    try {
      const run = await ApiClient.approveBannerJob(activeJobId, selectedBannerIds) as BannerRun
      set({ run, selectedBannerIds: run.banners.map(item => item.banner_id), seenBannerIds: run.banners.map(item => item.banner_id) })
      toast.success(`${run.banners.length} banners aprovados e adicionados ao histórico.`)
      await get().loadHistory()
    } catch (error) {
      toast.error(`Erro ao aprovar banners: ${(error as Error).message}`)
    }
  },

  loadHistory: async () => {
    set({ historyLoading: true })
    try {
      const history = await ApiClient.getBannerHistory() as BannerHistoryItem[]
      set({ history, historyLoading: false })
    } catch (error) {
      set({ historyLoading: false })
      toast.error(`Erro ao carregar histórico: ${(error as Error).message}`)
    }
  },

  reopenHistory: async (jobId) => {
    const generation = ++pollGeneration
    try {
      const run = await ApiClient.getBannerHistoryDetail(jobId) as BannerRun
      if (generation !== pollGeneration) return
      const ids = run.banners.map(item => item.banner_id)
      set({ activeJobId: jobId, run, selectedBannerIds: ids, seenBannerIds: ids })
    } catch (error) {
      toast.error(`Erro ao reabrir extração: ${(error as Error).message}`)
    }
  },

  deleteHistory: async (jobId) => {
    try {
      await ApiClient.deleteBannerHistory(jobId)
      if (get().activeJobId === jobId) {
        ++pollGeneration
        set({ activeJobId: null, run: null, selectedBannerIds: [], seenBannerIds: [] })
      }
      await get().loadHistory()
    } catch (error) {
      toast.error(`Erro ao excluir histórico: ${(error as Error).message}`)
    }
  },
}))
