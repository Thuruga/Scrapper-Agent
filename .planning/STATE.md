---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: Expansão Multi-Plataforma de Concorrentes & Frete VTEX
status: executing
stopped_at: Phase 32 context gathered
last_updated: "2026-06-24T18:06:50.305Z"
last_activity: 2026-06-24 -- Phase 31 complete
progress:
  total_phases: 6
  completed_phases: 3
  total_plans: 10
  completed_plans: 10
  percent: 50
---

# Project State: Intelligence Scraper

## Project Reference

See: [.planning/PROJECT.md](file:///c:/Users/arthur.correia/Documents/Pessoal/scrapper/.planning/PROJECT.md) (updated 2026-06-23)

**Core value:** Extração automatizada e resiliente de dados de mercado com mínima intervenção humana e alta fidelidade de dados.
**Current focus:** Phase 32 — engine-wake-commerce-richards (next)

## Current Milestone: v3.0 Expansão Multi-Plataforma de Concorrentes & Frete VTEX

**Goal:** Onboardar marcas concorrentes fora do VTEX, entregar o frete VTEX pendente e automatizar a extração de banners desktop com publicação no SharePoint.
**Phases:** 6 (30-35) — Phase 34 planejada em 4 waves
**Progress:** [███████░░░] 71%

## Current Position

Phase: 31 (engine-sfcc-browser-p-blico-lacoste-hugoboss) — COMPLETE ✅
  Waves: 3/3 merged. 225/225 tests passing. REVIEW.md + VERIFICATION.md written.
  CRITICAL open item: double-www bug in SFCC URL construction — fix before first live run.
Next: Phase 32 (engine-wake-commerce-richards) — spike-gated GO/NO-GO on GraphQL token
Last activity: 2026-06-24 -- Phase 31 complete

## Performance Metrics

**Velocity:**

- Total plans completed (v2.0): 11
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
| Phase 30-detec-o-de-engine-sfcc-wake P01 | 10m | 2 tasks | 1 files |
| 30 | 3 | - | - |

## Accumulated Context

### Decisions

- [30-01/D-05]: Wake branch returns 'wake' — fbitsstatic.net probe now labels Richards correctly; D-04 auto-deactivation no longer fires for Wake brands.
- [30-01/D-02+D-07]: SFCC browser probe uses exclusive demandware.static/demandware.edgesuite.net markers and is last-resort (after Shopify, VTEX, HTML probes); SC-4 guaranteed.
- [30-01/D-03]: BrowserManager imported lazily inside try block in detect_engine; Playwright-absent startup does not break module load.
- [v3.0 roadmap]: 6 phases, 30-35. COMP-05→Phase 30 (detecção SFCC/Wake), COMP-03→Phase 31 (engine SFCC), COMP-04→Phase 32 (engine Wake, spike-gated), FRET-05→Phase 33 (frete VTEX), BANNER-01..04→Phase 34 (extração desktop), BANNER-05..06→Phase 35 (SharePoint). Cobertura 10/10.
- [v3.0 ordering]: Phase 30 (detecção) é pré-requisito compartilhado das Phases 31 e 32 — sem rotular `sfcc`/`wake`, as marcas seriam auto-desativadas no cadastro (regra D-04). Phases 33 (frete VTEX) e 34 (extração de banners) são ortogonais e podem rodar em paralelo; Phase 35 depende da 34.
- [v3.0 COMP-04]: O build do engine Wake é gated por um spike de confirmação (Wave 0 da Phase 32) do fluxo GraphQL + `TCS-Access-Token` contra a Richards/Shop2gether — Wake é HIGH confidence documentalmente mas NÃO foi testado empiricamente. GO/NO-GO registrado antes do engine completo.
- [v3.0 COMP-03]: Caminho SFCC é público via browser (JSON-LD/OpenGraph), validado por spikes 003-006 — HTTP direto é 403. Escopo: catálogo + preço APENAS. SEM frete/checkout, estoque por CEP, OCAPI/SCAPI ou bypass de anti-bot.
- [v3.0 FRET-05]: Frete VTEX continua via `VtexApiClient` interno — NÃO rotear pelo hook `calculate_shipping` (decisão arquitetural herdada do v2.0 para evitar regressão).
- [v3.0 scope]: Zara/Inditex IOP (COMP-FUT-03) permanece deferido (sem caminho público validado). Auth segue API key compartilhada (PROFILE-FUT-01 adiado); FRET-06 (Shopify shipping) segue Future.
- [v3.0 banners]: BANNER-FUT-01 foi promovido para BANNER-01..06. Phase 34 entrega extração desktop (todos os slides de imagem do hero, arquivos originais, metadados e relatório); Phase 35 entrega publicação idempotente no SharePoint com gate de acesso/permissões.
- [v3.0 banners scope]: Viewport desktop `1366×768` apenas. Mobile, download de vídeos e agendamento recorrente ficam fora do milestone; vídeos intercalados são contabilizados para que a navegação não pare antes de banners posteriores.
- [v3.0 banners spike]: Protótipo `testes/extrair_banners.py` validado em 13/13 sites ativos: 37 imagens extraídas, 3 slides em vídeo identificados e zero falhas de download na rodada de 2026-06-23.
- [v2.0 scope]: Apenas 5 marcas VTEX confirmadas foram onboardadas (Levi's, Calvin Klein, Zapalla, Austral, Track & Field). Richards/Lacoste/Hugo Boss/Zara ficaram fora do v2.0 — agora COMP-FUT-01/02 viram COMP-03/04 no v3.0.
- [v2.0 scope]: Auth permanece API key compartilhada — perfis de acesso (PROFILE-FUT-01) adiados.
- [ARCH]: `is_active` enforcement vai no chokepoint único `brand_service.list_brands(active_only=True)` — NÃO por call site.
- [ARCH]: Estado de busca migra para store zustand module-scoped — NÃO remover AnimatePresence, NÃO converter busca para async job/polling.
- [ARCH]: VTEX shipping continua via `VtexApiClient` interno — NÃO rotear pelo hook `calculate_shipping` para evitar regressão.
- [v2.0/PERS-01]: Prerequisito: fix do WebSocket cleanup em `CategoryPage` (5 linhas de useEffect) vem ANTES do store zustand, na mesma phase.
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

- [v3.0/COMP-04] Wake/Richards: fluxo GraphQL + `TCS-Access-Token` é HIGH confidence documentalmente (wakecommerce.readme.io) mas NÃO testado empiricamente. Phase 32 deve iniciar pelo spike de confirmação (Wave 0) com decisão GO/NO-GO antes do engine completo.
- [v3.0/COMP-03] Lacoste/HugoBoss (SFCC): HTTP direto é 403; extração validada apenas pela via pública browser-rendered (JSON-LD/OpenGraph). Escopo limitado a catálogo + preço — sem frete/checkout/estoque por CEP.
- [31-REVIEW/HIGH] SFCC double-www: `DynamicBrand.clean_domain` não remove prefixo `www.` — `"www.lacoste.com.br"` construído como `"https://www.www.lacoste.com.br/..."`. Corrigir com `re.sub(r"^www\.", "", domain)` em `sfcc_engine.py:149` e `:379` antes do primeiro live run. Testes passam (browser mockado) mas produção quebraria com 404.
- FRET-06 (Shopify): permanece adiado — smoke test necessário antes de comprometer (sessão/cookie no AJAX Cart pode requerer Playwright). Fora do escopo do v3.0.
- [v3.0/BANNER-05] SharePoint: site/biblioteca de destino, credenciais e permissões ainda não foram fornecidos. Phase 35 deve começar por um gate de conectividade e acesso antes do publicador completo.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260615-dkc | No caso, todos devem mostrar o nome da lojista | 2026-06-15 | 717beb9 | [260615-dkc-no-caso-todos-devem-mostrar-o-nome-da-lo](./quick/260615-dkc-no-caso-todos-devem-mostrar-o-nome-da-lo/) |
| 260616-eib | na busca do SKU, a selecao dos produtos a exportar para o excel so deve aparecer quando o user clicar primeiro em exportar para o excel | 2026-06-16 | 945844a | [260616-eib-na-busca-do-sku-a-selecao-dos-produtos-a](./quick/260616-eib-na-busca-do-sku-a-selecao-dos-produtos-a/) |
| 260623-lho | Mudar padrão do nome dos banners para mês ano marca | 2026-06-23 | 95b068e | [260623-lho-mudar-padr-o-do-nome-dos-banners-para-m-](./quick/260623-lho-mudar-padr-o-do-nome-dos-banners-para-m-/) |
| 260624-d65 | Na tela de adicionar marcas, retire cadastrar nova marca e deixe como gerenciar marcas. Com as ações de apagar e desativar. | 2026-06-24 | 43dd369 | [260624-d65-na-tela-de-adicionar-marcas-retire-cadas](./quick/260624-d65-na-tela-de-adicionar-marcas-retire-cadas/) |

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Identidade de Produto | IDENT-01 (sinal além do EAN) | Deferred (research) | v1.11 init |
| Exportação | EXPORT-HIST-01 (export do histórico) | Deferred | v1.12 init |
| Exportação | EXPORT-UNIFY-01 (unificar com export por marca) | Deferred | v1.12 init |
| Concorrentes | COMP-FUT-03 (Zara/Inditex IOP) | Deferred | v2.0 init |
| Acesso | PROFILE-FUT-01 (perfis por equipe) | Deferred | v2.0 init |
| Frete | FRET-06 (Shopify checkout shipping) | Deferred (viabilidade) | v2.0 init |

## Session Continuity

Last session: 2026-06-24T18:06:50.298Z
Stopped at: Phase 32 context gathered
Resume file: .planning/phases/32-engine-wake-commerce-richards/32-CONTEXT.md

## Operator Next Steps

- Fix SFCC double-www bug (`sfcc_engine.py:149` and `:379`) before first live Lacoste/HugoBoss run
- Phase 32: `/gsd-plan-phase 32` (Wake Commerce engine — spike-gated)
- Phase 33: `/gsd-plan-phase 33` (Frete VTEX via checkout — orthogonal to engines, can run in parallel)
