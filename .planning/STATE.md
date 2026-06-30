---
gsd_state_version: 1.0
milestone: v4.0
milestone_name: Paridade de Dados, Cobertura Total de Frete & Inteligência Competitiva
status: executing
stopped_at: Phase 44 context gathered
last_updated: "2026-06-30T01:43:53.458Z"
last_activity: 2026-06-30
progress:
  total_phases: 9
  completed_phases: 2
  total_plans: 11
  completed_plans: 6
  percent: 22
---

# Project State: Intelligence Scraper

## Project Reference

See: [.planning/PROJECT.md](file:///c:/Users/arthur.correia/Documents/Pessoal/scrapper/.planning/PROJECT.md) (updated 2026-06-26)

**Core value:** Extração automatizada e resiliente de dados de mercado com mínima intervenção humana e alta fidelidade de dados.
**Current focus:** Phase 39 — cobertura-de-marcas-hugo-boss-zara

## Current Milestone: v4.0 Paridade de Dados, Cobertura Total de Frete & Inteligência Competitiva

**Goal:** Nivelar a extração de atributos entre todas as marcas, fechar lacunas de cobertura (Hugo Boss por categoria, Zara, frete universal) e adicionar camadas de inteligência competitiva (MAP, promoções, ruptura de estoque, sortimento, avaliações).
**Phases:** 9 (37-45)
**Progress:** [__________] 0%

## Current Position

Phase: 41
Plan: Not started
Status: Executing Phase 39
Last activity: 2026-06-30

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
| Phase 32-engine-wake-commerce-richards P01 | ~10m | 2 tasks | 2 files |
| Phase 32-engine-wake-commerce-richards P02 | ~5m | 3 tasks | 4 files |
| Phase 32-engine-wake-commerce-richards P03 | ~5m | 2 tasks | 1 files |
| 32 | 3 | - | - |
| Phase 33 P02 | 18 min | 2 tasks | 4 files |
| 33 | 3 | - | - |
| 39 | 3 | - | - |

## Accumulated Context

### Roadmap Evolution

- Phase 36 adicionada (2026-06-25): Onboarding das Marcas Concorrentes Restantes — Lacoste (anti-bot SFCC) com gate de viabilidade GO/NO-GO + reavaliação Zara/Inditex. Endereça o gap da Lacoste (COMP-03) e COMP-FUT-03. Hugo Boss (VTEX) e Richards (Wake) já entregues e ativos neste ciclo.
- Phase 36 concluída (2026-06-25): Lacoste NO-GO dentro do envelope público stealth permitido; 36-02/36-03 pulados por gate; Zara promovida para fase futura dedicada.
- v4.0 Roadmap criado (2026-06-26): 9 phases (37-45). PARID-01..04 fundacional (Phase 37); UX quick wins + COMP-08 (Phase 38); Hugo Boss + Zara spike (Phase 39); onboarding URL + workflows (Phase 40); shipping abstraction (Phase 41); marketplace shipping + CEP matrix (Phase 42); MAP + promos (Phase 43); stock rupture + reviews (Phase 44); assortment cron (Phase 45). Cobertura 24/24.

### Decisions

- [33-01/Backstage-exception]: Backstage MCP não configurado nesta sessão — operador aprovou exceção; convenções seguidas: stateless helper style vtex_parsing.py + Pydantic fields style models.py + test style test_vtex_api_client.py + Clean Code / refactoring.guru. VTEX-only boundary (D-03) re-afirmada.
- [33-01/is_free_shipping-em-ShippingInfo]: is_free_shipping adicionado ao ShippingInfo (além de SearchProductResult) para que cada opção em shipping_options carregue seu próprio flag sem lógica no caller.
- [33-01/filter_and_sort_slas-dict]: filter_and_sort_slas retorna dicts enriquecidos (price_reais, is_free_shipping, estimate_*) em vez de ShippingInfo, para que o caller Wave 2 construa os objetos Pydantic após ter o seller_id e service metadata completos.
- [onboarding-live/2026-06-25]: Cadastro ao vivo das marcas concorrentes restantes (persistido em backend/data/brands.json, commit adb9635). Richards → engine `wake`, `www.richards.com.br`, **ativa**, busca OK (3 produtos). **Hugo Boss → engine `vtex` (NÃO `sfcc` — correção empírica da suposição COMP-03/Phase 31), `www.hugoboss.com.br`, ativa, busca OK (3 produtos)**. Lacoste → engine `sfcc`, **inativa** (bloqueio anti-bot, ver Blockers). Engines de Richards/Lacoste atribuídos por evidência (spike 007 + marcadores HTML + assinatura 403), pois `detect_engine` retorna `unknown` sob anti-bot na Richards. `hugoboss.com.br` sem www NÃO resolve — usar `www.hugoboss.com.br`.
- [36-01/NO-GO]: Spike 008 testou Lacoste home/search (`polo`, `camisa`) com baseline Playwright e `playwright-stealth`; todos retornaram HTTP 403, 296B, `Access Denied`/Akamai. Decisão: manter `lacoste.is_active=false`, não implementar fetcher degradado, não executar 36-02/36-03.
- [36-01/Zara]: Recheck Zara carregou home e search públicos com stealth (HTTP 200, HTML grande). Não foi criado engine; COMP-FUT-03 deve virar fase futura dedicada para validar produto+preço e implementação. Promovida para COMP-07 no v4.0.
- [32-03/SC-2/SC-3/SC-4]: test_wake_engine.py criado com 11 testes herméticos (5 classes); mock seam SessionManager.get_session; guard test_factory_wake_still_raises já removido em 32-02; suite completa 235 testes verde.
- [32-02/SC-3]: EngineFactory.get_engine para engine='wake' agora retorna WakeEngine (import lazy) — NotImplementedError removido do branch wake em factory.py.
- [32-02/D-06]: Campo wake_access_token: Optional[str] = None adicionado em DynamicBrandCreate apos logo_url; herdado por DynamicBrand; marcas existentes sem o campo continuam validas.
- [32-02/D-07]: WakeEngine._resolve_token levanta ValueError se token nao resolvido — capturado por _search_one como BrandSearchResult.error (nunca 0 produtos silenciosos).
- [32-02/prices.price]: prices.price da Wake GraphQL e float em reais (confirmado spike 007: 479 = R$479); sem divisao por 100 (contraste com VTEX).
- [32-02/aliasComplete]: aliasComplete e relativo (e.g. "produto/camisa-123"); URL completa montada como f"https://{domain}/{alias.lstrip('/')}".
- [30-01/D-05]: Wake branch returns 'wake' — fbitsstatic.net probe now labels Richards correctly; D-04 auto-deactivation no longer fires for Wake brands.
- [30-01/D-02+D-07]: SFCC browser probe uses exclusive demandware.static/demandware.edgesuite.net markers and is last-resort (after Shopify, VTEX, HTML probes); SC-4 guaranteed.
- [30-01/D-03]: BrowserManager imported lazily inside try block in detect_engine; Playwright-absent startup does not break module load.
- [v3.0 roadmap]: 7 phases, 30-36. COMP-05→Phase 30 (detecção SFCC/Wake), COMP-03→Phase 31/36 (engine SFCC + Lacoste anti-bot gate), COMP-04→Phase 32 (engine Wake, spike-gated), FRET-05→Phase 33 (frete VTEX), BANNER-01..04→Phase 34 (extração desktop), BANNER-05..06→Phase 35 (SharePoint). Cobertura 10/10 comprometidos + COMP-FUT-03 reavaliado.
- [v3.0 ordering]: Phase 30 (detecção) é pré-requisito compartilhado das Phases 31 e 32 — sem rotular `sfcc`/`wake`, as marcas seriam auto-desativadas no cadastro (regra D-04). Phases 33 (frete VTEX) e 34 (extração de banners) são ortogonais e podem rodar em paralelo; Phase 35 depende da 34.
- [v3.0 COMP-04]: O build do engine Wake é gated por um spike de confirmação (Wave 0 da Phase 32) do fluxo GraphQL + `TCS-Access-Token` contra a Richards/Shop2gether — Wake é HIGH confidence documentalmente mas NÃO foi testado empiricamente. GO/NO-GO registrado antes do engine completo.
- [v3.0 COMP-03]: Caminho SFCC é público via browser (JSON-LD/OpenGraph), validado por spikes 003-006 — HTTP direto é 403. Escopo: catálogo + preço APENAS. SEM frete/checkout, estoque por CEP, OCAPI/SCAPI ou bypass de anti-bot.
- [v3.0 FRET-05]: Frete VTEX continua via `VtexApiClient` interno — NÃO rotear pelo hook `calculate_shipping` (decisão arquitetural herdada do v2.0 para evitar regressão).
- [v3.0 scope]: Zara/Inditex IOP (COMP-FUT-03) permanece fora do milestone, mas Phase 36 encontrou páginas públicas carregáveis; promover para fase futura dedicada. Auth segue API key compartilhada (PROFILE-FUT-01 adiado); FRET-06 (Shopify shipping) segue Future.
- [v3.0 banners]: BANNER-FUT-01 foi promovido para BANNER-01..06. Phase 34 entrega extração desktop (todos os slides de imagem do hero, arquivos originais, metadados e relatório); Phase 35 entrega publicação idempotente no SharePoint com gate de acesso/permissões.
- [v3.0 banners scope]: Viewport desktop `1366×768` apenas. Mobile, download de vídeos e agendamento recorrente ficam fora do milestone; vídeos intercalados são contabilizados para que a navegação não pare antes de banners posteriores.
- [v3.0 banners spike]: Protótipo `testes/extrair_banners.py` validado em 13/13 sites ativos: 37 imagens extraídas, 3 slides em vídeo identificados e zero falhas de download na rodada de 2026-06-23.
- [v4.0 ARCH/SQLite]: Dados analíticos (assortment snapshots, review corpora, price/stock series) migram para SQLite (stdlib, zero-dep); JSON permanece para config (brands, monitors, MAP rules, CEP matrix). Introduzido na Phase 37; consumido por Phase 45.
- [v4.0 ARCH/shipping]: Abstração `BaseShipping` em `services/shipping/`; VTEX permanece em `VtexApiClient` (D-03 herdada); novos providers (Wake, Shopify, marketplace) implementam a interface. Introduzida na Phase 41.
- [v4.0 COMP-07/spike-gate]: COMP-07 (Zara) é gated por spike de viabilidade GO/NO-GO (spike 010); engine só construído em GO — espelha o padrão da Phase 32 (Richards). Spike documenta produto+preço acessíveis publicamente antes de qualquer commit de engine.
- [v4.0 STOCK-02/guard-rails]: Cart-probe de 999 unidades usa sessões Playwright efêmeras e isoladas com cleanup garantido, throttle entre requisições, e é invocado APENAS em varreduras controladas explícitas — nunca inline em buscas ao vivo.
- [v4.0 FRET-09/guard-rails]: Matriz Multi-Regional é on-demand/batched, com throttle e cache por (sku, cep); lista de CEPs curada em `backend/data/cep_matrix.json`; nunca executada inline durante buscas.
- [v4.0 PARID/additive]: Normalização de atributos é ADITIVA — canonical keys adicionadas ao lado dos dados brutos em `specifications`, nunca substituindo o bag original. Garante backward-compatibility.
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

- [v3.0/COMP-03 — Lacoste REVISADO 2026-06-25 (spike 009)] Lacoste (`sfcc`) permanece **inativa em produção**, mas o NO-GO da Phase 36 foi **REVERTIDO**: o anti-bot Akamai é por **reputação de IP** (não fingerprint — stealth não muda nada). De um **IP limpo (4G)** a busca retorna **32 produtos reais server-side**. O NO-GO original vinha de DUAS causas: (1) IP corporativo da Aramis bloqueado; (2) URL de busca errada. Host canônico: `www.lacoste.com/br/` (o `lacoste.com.br` redireciona à home e perde o `?q=`); endpoint `…/search?q=`. **Engine SFCC já CORRIGIDA e testada offline** contra o HTML real capturado: `parse_search_tiles` (extrai do tile), `brand.search_url_template`, hook `brand.proxy_url`→`BrowserManager` (259 testes verdes). Trava ÚNICA p/ ativar — sobretudo no **Azure (IP datacenter, bloqueado mais forte)**: **egress de IP limpo** (proxy residencial/móvel barato OU dispositivo dedicado em link residencial). Sem verba no momento → mantida dormente; setar `proxy_url` + validar D-06 ao vivo antes de `is_active=true`. Evidência: `.planning/spikes/009-lacoste-headed-mobile/FINDINGS.md`.
- [31-REVIEW/HIGH — RESOLVIDO 2026-06-25] SFCC double-www: corrigido em `sfcc_engine.py` (helper `_strip_www` remove prefixo `www.` antes dos builders de search/home URL + teste de regressão `test_search_url_no_double_www_when_domain_has_www`). Commit 83dfdba. O bloqueio remanescente da Lacoste é anti-bot, não mais o double-www.
- FRET-06 (Shopify): permanece adiado — smoke test necessário antes de comprometer (sessão/cookie no AJAX Cart pode requerer Playwright). Fora do escopo do v3.0. Pode ser absorvido pela abstração de frete (FRET-07) no v4.0.
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
| Acesso | PROFILE-FUT-01 (perfis por equipe) | Deferred | v2.0 init |
| Frete | FRET-06 (Shopify checkout shipping) | Deferred (viabilidade) | v2.0 init; may absorb into FRET-07 |
| Banners | BANNER-05/06 (SharePoint) | Blocked (credenciais/permissões) | v4.0 init |

## Session Continuity

Last session: 2026-06-29T23:55:20.267Z
Stopped at: Phase 44 context gathered
Resume file: .planning/phases/44-ruptura-de-estoque-avalia-es-refor-adas/44-CONTEXT.md

## Operator Next Steps

- Phase 37: `/gsd-plan-phase 37` (Paridade de Atributos & Fundação SQLite — foundational, start here)
- Phase 38: pode rodar em paralelo lógico com Phase 37 (UX quick wins — frontend-only)
- Phase 35: ainda pendente (banners SharePoint) — gate de acesso ao SharePoint necessário primeiro
- Lacoste: ativar quando houver egress de IP limpo (proxy residencial/móvel); setar `proxy_url` e validar D-06 ao vivo antes de `is_active=true`
