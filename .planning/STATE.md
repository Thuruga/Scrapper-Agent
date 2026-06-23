---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: Expansão Multi-Plataforma de Concorrentes & Frete VTEX
status: planning
last_updated: "2026-06-23T13:39:57.403Z"
last_activity: 2026-06-23
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State: Intelligence Scraper

## Project Reference

See: [.planning/PROJECT.md](file:///c:/Users/arthur.correia/Documents/Pessoal/scrapper/.planning/PROJECT.md) (updated 2026-06-18)

**Core value:** Extração automatizada e resiliente de dados de mercado com mínima intervenção humana e alta fidelidade de dados.
**Current focus:** v3.0 — definindo requisitos

## Current Milestone: v3.0 Expansão Multi-Plataforma de Concorrentes & Frete VTEX

**Goal:** Onboardar marcas concorrentes que rodam fora do VTEX (engines SFCC e Wake Commerce) e entregar o cálculo de frete VTEX pendente do v2.0.
**Phases:** definindo (roadmap pendente)
**Progress:** [░░░░░░░░░░] 0%

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-06-23 — Milestone v3.0 started

## Performance Metrics

**Velocity:**

- Total plans completed: 11 (neste milestone)
- Average duration: —

**By Phase (milestones anteriores):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 22 | 1/1 | - | - |
| 23 | 2/2 | - | - |
| Phase 22-gate-de-marca P01 | 3m | 3 tasks | 4 files |
| Phase 23-discrimina-o-de-modelo P01 | 1m | 1 tasks | 1 files |
| Phase 23-discrimina-o-de-modelo P02 | 5m | 2 tasks | 2 files |
| Phase 24 P02 | 15m | 2 tasks | 2 files |
| Phase 24 P03 | 25m | 2 tasks | 3 files |
| 24 | 3 | - | - |
| Phase 25 P00 | 8m | 2 tasks | 2 files |
| Phase 25 P02 | 8m | 2 tasks | 1 files |
| Phase 25 P03 | 15m | 2 tasks | 4 files |
| 25 | 4 | - | - |
| Phase 26 P01 | 8m | 1 tasks | 1 files |
| Phase 26 P02 | 12m | 2 tasks | 1 files |
| Phase 27-hist-rico-completo-gest-o-de-marcas-na-ui P00 | 2m | 1 tasks | 1 files |
| Phase 27-hist-rico-completo-gest-o-de-marcas-na-ui P01 | 5m | 1 tasks | 1 files |
| Phase 27-hist-rico-completo-gest-o-de-marcas-na-ui P02 | 10m | 2 tasks | 2 files |
| Phase 27-hist-rico-completo-gest-o-de-marcas-na-ui P03 | 10m | 2 tasks | 1 files |
| 27 | 4 | - | - |
| Phase 28-persist-ncia-da-busca-entre-abas P01 | 5m | 1 tasks | 1 files |
| Phase 28-persist-ncia-da-busca-entre-abas P02 | 3m | 2 tasks | 4 files |
| Phase 28-persist-ncia-da-busca-entre-abas P03 | 30min | 2 tasks | 1 files |
| 28 | 3 | - | - |

## Accumulated Context

### Decisions

- [v2.0 scope]: Apenas 5 marcas VTEX confirmadas são onboardadas (Levi's, Calvin Klein, Zapalla, Austral, Track & Field). Richards (Wake), Lacoste/Hugo Boss (SFCC), Zara (Inditex) **não** são registradas neste milestone — movidas para Future Requirements (COMP-FUT-01/02/03). Se um operador tentar adicioná-las, a detecção COMP-02 (Phase 25) impede o cadastro silencioso como VTEX.
- [v2.0 scope]: Auth permanece API key compartilhada — perfis de acesso (PROFILE-FUT-01) adiados.
- [v2.0 scope]: Engine Wake Commerce não construído neste milestone — é risco conhecido para marcas que dependam dele.
- [v2.0 scope]: FRET-05 cobre apenas sites de marca VTEX. FRET-06 (Shopify shipping) permanece adiado por incerteza de viabilidade.
- [ARCH]: `is_active` enforcement vai no chokepoint único `brand_service.list_brands(active_only=True)` — NÃO por call site.
- [ARCH]: Estado de busca migra para store zustand module-scoped — NÃO remover AnimatePresence, NÃO converter busca para async job/polling.
- [ARCH]: VTEX shipping continua via `VtexApiClient` interno — NÃO rotear pelo hook `calculate_shipping` para evitar regressão.
- [PERS-01]: Prerequisito: fix do WebSocket cleanup em `CategoryPage` (5 linhas de useEffect) vem ANTES do store zustand, na mesma phase.
- [D-07/25-02]: `list_brands` default `active_only=False` mantido — flip para True quebraria GET /brands/ e a management UI.
- [D-05/25-02]: `set_active` apenas seta o flag `is_active` e persiste via `_save`; NÃO cancela monitores ativos (isso é responsabilidade de `delete_brand`).
- [D-06/25-02]: `set_active` é um set idempotente, não um toggle — chamar duas vezes com o mesmo valor é semanticamente no-op.
- [OQ2/25-03]: `scrape_category_multi` enforces `active_only=True` — inactive brands are not valid scan targets (consistency with search).
- [D-06/25-03]: `BrandActiveUpdate` placed in `core/models.py` near `DynamicBrand`; PATCH route is thin — zero business logic in route layer.
- [Phase ?]: Derived VALID_SLUGS from _RAW_CATEGORIES (not hardcoded set) to stay in sync with the canonical source (D-04 anchor)
- [Phase ?]: Script imports detect_engine inside onboard_brand (not top-level) to avoid heavy import-time side effects; mirrors PATTERNS.md
- [Phase ?]: engine='vtex' assigned ONLY when detect_engine reconfirms it in onboard_vtex_brands.py — no manual override permitted (D-11)
- [Phase ?]: Resolution A (HIST-01 shape contract): stored comparative results must be the inner List[BrandSearchResult] array, not the ComparisonResult wrapper
- [Phase ?]: Module-level import of search_history_service in routes_search.py (27-01): lazy import inside function would shadow the injected singleton and break monkeypatching
- [27-02/MGMT-02]: VIRTUAL guard ['mercado_livre','netshoes','amazon'] defined inside SettingsPage.brands.map — hides toggle for virtual marketplaces that have no backend brand record (PATCH would 404)
- [27-02/MGMT-02]: Inactive distinction uses inline style opacity 0.55 on .brand-info (not a new CSS class) to avoid App.css modification while meeting D-09
- [Phase ?]: [27-03/HIST-02]: refreshKey prop pattern chosen — parent page owns historyRefreshKey counter, bumps after successful handleSearch; HistoryList useEffect dep on refreshKey triggers refetch (Pitfall 4 resolution)
- [Phase ?]: [27-03/HIST-02]: deleteTick internal counter in HistoryList — setDeleteTick(t=>t+1) in delete handler triggers same useEffect as refreshKey, avoids exposing imperative refetch
- [28-02/D-05]: No persist middleware — selectedItems is Set<string> (non-serializable); store is memory-only, zeroes on reload
- [28-02/D-06]: Single useSearchStore with two slices (search + cross) — no separate stores, simplifies cross-slice observation
- [28-02/Padrao 2]: signal spread as ...(signal ? { signal } : {}) — undefined signal never passed to fetch options
- [Phase ?]: [28-03/Task2]: CrossMarketplacePage error handling consolidated to toast.error in store action — replaces legacy alert(); intentional unification with Comparativa's error pattern
- [Phase ?]: [28-03/UAT]: Manual UAT (Task 3) deferred by user — 5 behavioral verification procedures PENDING (criteria #1 tab-switch, #2 cross-tab toast, #3 no-double-fetch, #4 WS cleanup reconfirm, D-11 preloadedJobId regression)

### Pending Todos

- Nenhum pendente de milestones anteriores.

### Blockers/Concerns

- Lacoste/Hugo Boss: confiança MÉDIA na detecção de plataforma (sites retornaram 403). Estão fora do escopo (Future); se forem tentadas no onboarding, COMP-02 deve identificá-las como plataforma não suportada.
- FRET-06 (Shopify): adiado para milestone futuro — smoke test necessário antes de comprometer (sessão/cookie no AJAX Cart pode requerer Playwright). FRET-05 (sites VTEX) é o único frete no escopo do v2.0.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260615-dkc | No caso, todos devem mostrar o nome da lojista | 2026-06-15 | 717beb9 | [260615-dkc-no-caso-todos-devem-mostrar-o-nome-da-lo](./quick/260615-dkc-no-caso-todos-devem-mostrar-o-nome-da-lo/) |
| 260616-eib | na busca do SKU, a selecao dos produtos a exportar para o excel so deve aparecer quando o user clicar primeiro em exportar para o excel | 2026-06-16 | 945844a | [260616-eib-na-busca-do-sku-a-selecao-dos-produtos-a](./quick/260616-eib-na-busca-do-sku-a-selecao-dos-produtos-a/) |

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Identidade de Produto | IDENT-01 (sinal além do EAN) | Deferred (research) | v1.11 init |
| Exportação | EXPORT-HIST-01 (export do histórico) | Deferred | v1.12 init |
| Exportação | EXPORT-UNIFY-01 (unificar com export por marca) | Deferred | v1.12 init |
| Concorrentes | COMP-FUT-01 (Richards/Wake Commerce) | Deferred to v3.0 | v2.0 init |
| Concorrentes | COMP-FUT-02 (Lacoste/Hugo Boss SFCC) | Deferred (spike) | v2.0 init |
| Concorrentes | COMP-FUT-03 (Zara/Inditex IOP) | Deferred | v2.0 init |
| Acesso | PROFILE-FUT-01 (perfis por equipe) | Deferred (v3.0) | v2.0 init |
| Frete | FRET-06 (Shopify checkout shipping) | Deferred (viabilidade) | v2.0 init |
| Banners | BANNER-FUT-01 (banners→SharePoint) | Deferred (estudo) | v2.0 init |

## Session Continuity

Last session: 2026-06-22T13:13:06.243Z
Stopped at: Phase 29 (Diagnóstico) removida — Frete (nova Phase 29) ainda não planejada
Resume file: (nenhum — Phase 29 Frete ainda não tem contexto)

## Operator Next Steps

- Start the next milestone with /gsd-new-milestone
