---
gsd_state_version: 1.0
milestone: v4.0
milestone_name: Paridade de Dados, Cobertura Total de Frete & Inteligência Competitiva
status: executing
stopped_at: Phase 45 plan 03 complete
last_updated: "2026-07-06T03:06:51Z"
last_activity: 2026-07-06 -- Completed Phase 45 plan 03: dedicated sortiment dashboard UI
progress:
  total_phases: 9
  completed_phases: 9
  total_plans: 32
  completed_plans: 32
  percent: 100
---

# Project State: Intelligence Scraper

## Project Reference

See: [.planning/PROJECT.md](file:///c:/Users/arthur.correia/Documents/Pessoal/scrapper/.planning/PROJECT.md) (updated 2026-07-02)

**Core value:** Extração automatizada e resiliente de dados de mercado com mínima intervenção humana e alta fidelidade de dados.
**Current focus:** Phase 45 — an-lise-de-sortimento

## Current Milestone: v4.0 Paridade de Dados, Cobertura Total de Frete & Inteligência Competitiva

**Goal:** Nivelar a extração de atributos entre todas as marcas, fechar lacunas de cobertura (Hugo Boss por categoria, Zara, frete universal) e adicionar camadas de inteligência competitiva (MAP, promoções, ruptura de estoque, sortimento, avaliações).
**Phases:** 9 (37-45)
**Progress:** [██████████] 100%

## Current Position

Phase: 45 (an-lise-de-sortimento) — COMPLETE
Plan: 3 of 3
Status: Phase 45 complete
Last activity: 2026-07-06 -- Completed Phase 45 plan 03: dedicated sortiment dashboard UI

## Performance Metrics

**Velocity:**

- Total plans completed (v2.0): 11 + 4 (v4.0 Phase 40 P01-P04)
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
| Phase 40 P04 | 25m | 2 tasks | 5 files |
| 40 | 5 | - | - |
| Phase 44 P01 | 9 min | 3 tasks | 7 files |
| Phase 44 P02 | 11 min | 2 tasks | 6 files |
| Phase 44 P03 | 9 min | 3 tasks | 9 files |
| Phase 44 P04 | 68 min | 3 tasks | 7 files |
| Phase 44 P05 | 12 min | 2 tasks | 3 files |
| Phase 38-ux-de-busca-monitoramento-quick-wins P01 | 25min | 3 tasks | 5 files |
| Phase 38-ux-de-busca-monitoramento-quick-wins P02 | 20min | 2 tasks | 2 files |
| Phase 38 P38-03 | 35min | 3 tasks | 1 files |
| 38 | 3 | - | - |
| 45 | 3 | - | - |

## Accumulated Context

### Roadmap Evolution

- Phase 36 adicionada (2026-06-25): Onboarding das Marcas Concorrentes Restantes — Lacoste (anti-bot SFCC) com gate de viabilidade GO/NO-GO + reavaliação Zara/Inditex. Endereça o gap da Lacoste (COMP-03) e COMP-FUT-03. Hugo Boss (VTEX) e Richards (Wake) já entregues e ativos neste ciclo.
- Phase 36 concluída (2026-06-25): Lacoste NO-GO dentro do envelope público stealth permitido; 36-02/36-03 pulados por gate; Zara promovida para fase futura dedicada.
- v4.0 Roadmap criado (2026-06-26): 9 phases (37-45). PARID-01..04 fundacional (Phase 37); UX quick wins + COMP-08 (Phase 38); Hugo Boss + Zara spike (Phase 39); onboarding URL + workflows (Phase 40); shipping abstraction (Phase 41); marketplace shipping + CEP matrix (Phase 42); MAP + promos (Phase 43); stock rupture + reviews (Phase 44); assortment cron (Phase 45). Cobertura 24/24.

### Decisions

- [45-03/dedicated-page]: Sortiment operations live on a dedicated `Sortimento` sidebar page instead of being nested under monitoring or category-scan surfaces.
- [45-03/backend-dashboard-truth]: The frontend renders backend-owned `baseline`, `deltas`, and `current_distribution` payloads directly and does not recompute snapshot comparison rules in the browser.
- [45-03/id-bounded-actions]: Sortiment page actions stay inside the typed API boundary by sending only persisted category IDs and explicit enabled booleans; URL and brand remain server-owned registry data.
- [45-02/dashboard-backend-owned]: Sortiment dashboard payloads are assembled from `latest_snapshot`/`previous_snapshot` on the backend, with explicit `baseline` semantics when no previous snapshot exists.
- [45-02/overlap-guard]: Manual and cron sortiment runs share one asyncio guard; overlapping manual calls return `status="busy"` and the scheduler job is registered with `max_instances=1` + `coalesce=True`.
- [45-01/json-only-foundation]: Phase 45 storage is local JSON only; sortiment registry, snapshots, and manifests do not introduce SQLite or analytics.db revival.
- [45-01/source-monitor-sync]: Sortiment registry sync is keyed by `source_monitor_id`, preserves operator-owned `enabled` state, updates URL/brand/status from the monitor source, and keeps the monitor file read-only.
- [40-04/marketplace-brand-keys]: Preserved brand_keys mercado_livre/netshoes/amazon from Plan 02 runtime injection — engine values mercadolivre/netshoes/amazon (no underscore) matching engine class naming; _ENGINE_MAP is the single authoritative source.
- [40-04/_inject_engines-helper]: Tests use _inject_engines(service, engines_dict) helper: sets _by_display and monkey-patches _active_engines() — hermetic, no brands.json disk access in tests.
- [40-03/dedup-return]: start_monitor retorna (PriceMonitorConfig, status_str) em todos os caminhos; status ∈ {created, already_active, reactivated}; POST /monitor/start retorna config.job_id (id canônico: existente ou novo) + campo status.
- [40-03/lazy-import]: normalize_url importado dentro do corpo de start_monitor para evitar risco de import-cycle; espelha recomendação do PATTERNS.md.
- [40-02/detect_engine-tuple]: detect_engine retorna tuple[str, str|None] em todos os caminhos. Steps 1-2 (API probes) retornam (engine, None). Step 3 salva html em _step3_html e cai para o browser probe quando nenhum marcador casa (evita bloquear detecção SFCC quando HTTP retorna página 403 sem marcadores). Step 7 carrega _step3_html para infer_brand_name.
- [40-02/infer_brand_name-accepts-soup]: infer_brand_name aceita html como str | BeautifulSoup | None — o scaffold de test Wave-0 passa um objeto BeautifulSoup; aceitar ambos evita quebrar o scaffold enquanto mantém a assinatura pública str|None documentada.
- [40-02/identify-dry-run]: POST /brands/identify nunca chama brand_service.add_brand (D-02); SSRF mitigation via stdlib ipaddress + scheme whitelist antes de qualquer fetch (T-40-SSRF); engine='unknown' emite warning mas não bloqueia onboarding (D-03).
- [40-01/literal-www-strip]: normalize_url usa `host[len("www."):]` e não `str.lstrip("www.")` — lstrip remove o char-set {w,.} e corrompe hosts como `wwww.example.com`; o slice literal é o único approach correto (D-08).
- [40-01/xfail-guard]: test_brand_identify.py usa guard de importabilidade + xfail(strict=False): verifica em runtime se `identify_brand`/`infer_brand_name` existem em `api.routes_brands`; se não, xfail — suite sempre verde antes do Plan 02.
- [40-01/composite-tracking-filter]: normalize_url aplica `k.lower() not in _TRACKING_PARAMS` E `not k.lower().startswith("utm_")` — composite + prefix check para cobrir variantes dinâmicas de utm_ não na frozenset hardcoded.
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
- [v3.0 scope]: Zara/Inditex IOP (COMP-FUT-03) permanece fora do milestone, mas Phase 36 encontrou páginas públicas carregáveis; promover para fase futura dedicada. Auth segue API key compartilhada (PROFILE-FUT-01 adiado). FRET-06 foi absorvido por FRET-07 na Phase 41.
- [v3.0 banners]: BANNER-FUT-01 foi promovido para BANNER-01..06. Phase 34 entrega extração desktop (todos os slides de imagem do hero, arquivos originais, metadados e relatório); Phase 35 entrega publicação idempotente no SharePoint com gate de acesso/permissões.
- [v3.0 banners scope]: Viewport desktop `1366×768` apenas. Mobile, download de vídeos e agendamento recorrente ficam fora do milestone; vídeos intercalados são contabilizados para que a navegação não pare antes de banners posteriores.
- [v3.0 banners spike]: Protótipo `testes/extrair_banners.py` validado em 13/13 sites ativos: 37 imagens extraídas, 3 slides em vídeo identificados e zero falhas de download na rodada de 2026-06-23.
- [v4.0 ARCH/SQLite]: Dados analíticos (assortment snapshots, review corpora, price/stock series) migram para SQLite (stdlib, zero-dep); JSON permanece para config (brands, monitors, MAP rules, CEP matrix). Introduzido na Phase 37; consumido por Phase 45.
- [v4.0 ARCH/shipping]: Abstração `BaseShipping` em `services/shipping/`; VTEX permanece em `VtexApiClient` (D-03 herdada); novos providers (Wake, Shopify, marketplace) implementam a interface. Introduzida na Phase 41.
- [41/FRET-07-complete]: Shopify/Buckman e Wake/Richards têm frete real via providers não-VTEX; `/search/calculate-shipping-brand` valida marca, CEP e host persistido; estados unsupported/temporary nunca viram frete grátis; VTEX segue em `/search/calculate-shipping-vtex`.
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
- [Phase ?]: 44-01/persistence-reality: backend/data/analytics.db, backend/services/*analytics*.py, and Phase 37 artifacts were absent; Plan 44-01 used JSON/local helpers and did not create SQLite schema.
- [Phase ?]: 44-01/stock-summary-input: compute_stock_summary consumes only normalized product-level stock_availability; SKU/item/variant arrays are intentionally ignored.
- [Phase ?]: 44-01/shopify-d04: Shopify availability now derives from variants[].available when variants are exposed; suggest.json without variants preserves the prior default available=True.
- [Phase ?]: 44-01/non-vtex-variation-audit: Wake, SFCC, and Zara scan paths currently expose scalar/text stock signals rather than variation arrays; no D-04 parser change was made for those engines.
- [Phase 44]: 44-02/manual-scan-id: manual category summaries use scan_id='{job_id}:{brand_key}' and persist all brand summaries under category_scan_summaries_{job_id}.json. — This keeps multi-brand scan auditability while preserving one shared manual job artifact.
- [Phase 44]: 44-02/hugo-boss-risk: automated STOCK-01 proof uses synthetic/working-brand fixtures; Hugo Boss zero-product scans remain a UAT dependency risk until the pending VTEX-IO category-scan todo is resolved. — The phase plan explicitly prohibits treating zero Hugo Boss products as STOCK-01 success.
- [Phase 44]: 44-02/summary-source: scheduled and manual summary wiring consumes product-level stock_availability only through compute_stock_summary; routes never recompute summary math. — Plan 44-02 wired all category scan surfaces to the shared helper and read endpoints to persisted artifacts.
- [Phase ?]: 44-03/provider-scope: stock-depth resolver returns a real provider only for engine='vtex'; wake/shopify/sfcc/marketplace/unknown engines return explicit unsupported. — Plan 44-03 implements VTEX as the only proved cart-probe provider and uses explicit unsupported states for other engines.
- [Phase ?]: 44-03/identity-boundary: stock-depth API accepts only monitor_id and scan_product_id; product URL, brand domain, quantity, and provider are resolved from persisted artifacts/settings. — This enforces STOCK-02/T-44-09 by rejecting caller-supplied URL/domain/quantity/provider and validating persisted product URL against the persisted brand domain.
- [Phase ?]: 44-03/non-false-states: blocked, temporary_failure, and unsupported persist stock_depth_estimate=None; unavailable may persist zero only when provider evidence is reliable. — This preserves D-08/D-09 semantics so failures, blocks, timeouts, and unsupported engines never become false quantity zero.
- [Phase ?]: [44-04/comments-on-demand-boundary] — Normal search and VTEX search remain summary-only through get_bulk_reviews/get_single_review; full comments are reachable only through the monitor scan-product reviews action.
- [Phase ?]: [44-04/provider-audit-explicit] — Aramis remains the only Trustvox-supported brand with store_id 78800 and recorded evidence; every other registered brand is review_provider='none' with unsupported rationale unless future evidence proves support.
- [Phase ?]: [44-04/compact-comments] — Provider responses are normalized to ReviewComment fields and deduped before persistence; no raw provider payload fields are introduced.
- [Phase ?]: [44-04/scan-product-identity] — Review comments resolve brand/product identity from persisted monitor artifacts and review_product_id; the route accepts no provider, domain, URL, product_id override, or raw payload.
- [Phase ?]: [44-05/modal-only-actions] — Stock-depth and full review comment calls are wired only from the monitored category product modal, never from normal search/export flows.
- [Phase ?]: [44-05/typecheck-tdd] — Frontend has no test runner, so TDD coverage uses a committed TypeScript compile-time contract file plus npm run build.
- [Phase ?]: [44-05/client-boundary] — Phase 44 frontend methods accept only monitor_id, scan_product_id, and optional max_pages; no URL/domain/provider/quantity payload is exposed.
- [Phase 38-01]: last_price_discount: single delta field added to both PriceMonitorConfig and PriceHistoryEntry; last_price keeps meaning effective/current price for frontend back-compat (D-04)
- [Phase 38-01]: has_change now also fires on config.last_price_discount != current_discount, so a promo-only change (price_full unchanged, discount added) is no longer silently dropped (D-01)
- [Phase ?]: [38-02/icon-placement]: History icon placed page-local (top of SearchPage/CrossMarketplacePage own page-content) instead of lifting to shared app-shell content-header - avoids new cross-component state plumbing for a two-tab feature
- [Phase ?]: [38-02/dual-mode-controlled]: HistoryList made dual-mode controlled/uncontrolled (optional collapsed/onToggleCollapsed props) so the internal toggle still works if a future caller omits the new props - avoids a breaking API change

### Pending Todos

- Nenhum pendente de milestones anteriores.

### Blockers/Concerns

- [v4.0/COMP-07 — Zara REVISADO 2026-07-01] Phase 39-02's spike 010 NO-GO (2026-06-29) has been **reversed** by operator live retest: Zara BR product+price extraction confirmed working (category scan export `dados_zara_categoria.xlsx`). `ZaraEngine`/`zara_parser.py` built and committed; `brands.json` `zara` entry (`is_active: true`) — already present since commit `d05b6eb` — is now backed by a real implementation (that commit had wired `factory.py`'s zara branch and activated the brand without ever committing the engine module, leaving this branch broken for any Zara search since 2026-06-29). No fresh automated spike report was produced for the reversal (unlike Lacoste's spike 009); `proxy_url` remains unset, so the same IP-reputation anti-bot risk documented for Lacoste applies if run from a datacenter/corporate egress. See `.planning/todos/pending/zara-comp07-deferred.md`.
- [v3.0/COMP-03 — Lacoste REVISADO 2026-06-25 (spike 009)] Lacoste (`sfcc`) permanece **inativa em produção**, mas o NO-GO da Phase 36 foi **REVERTIDO**: o anti-bot Akamai é por **reputação de IP** (não fingerprint — stealth não muda nada). De um **IP limpo (4G)** a busca retorna **32 produtos reais server-side**. O NO-GO original vinha de DUAS causas: (1) IP corporativo da Aramis bloqueado; (2) URL de busca errada. Host canônico: `www.lacoste.com/br/` (o `lacoste.com.br` redireciona à home e perde o `?q=`); endpoint `…/search?q=`. **Engine SFCC já CORRIGIDA e testada offline** contra o HTML real capturado: `parse_search_tiles` (extrai do tile), `brand.search_url_template`, hook `brand.proxy_url`→`BrowserManager` (259 testes verdes). Trava ÚNICA p/ ativar — sobretudo no **Azure (IP datacenter, bloqueado mais forte)**: **egress de IP limpo** (proxy residencial/móvel barato OU dispositivo dedicado em link residencial). Sem verba no momento → mantida dormente; setar `proxy_url` + validar D-06 ao vivo antes de `is_active=true`. Evidência: `.planning/spikes/009-lacoste-headed-mobile/FINDINGS.md`.
- [31-REVIEW/HIGH — RESOLVIDO 2026-06-25] SFCC double-www: corrigido em `sfcc_engine.py` (helper `_strip_www` remove prefixo `www.` antes dos builders de search/home URL + teste de regressão `test_search_url_no_double_www_when_domain_has_www`). Commit 83dfdba. O bloqueio remanescente da Lacoste é anti-bot, não mais o double-www.
- [Phase 41] Manual browser UAT de frete ainda é desejável: inspecionar um produto Buckman e um Richards com CEP válido no frontend, além de um smoke VTEX, para confirmar a experiência visual em ambiente rodando. A evidência automatizada e o spike live estão verdes.
- [v3.0/BANNER-05] SharePoint: site/biblioteca de destino, credenciais e permissões ainda não foram fornecidos. Phase 35 deve começar por um gate de conectividade e acesso antes do publicador completo.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260615-dkc | No caso, todos devem mostrar o nome da lojista | 2026-06-15 | 717beb9 | [260615-dkc-no-caso-todos-devem-mostrar-o-nome-da-lo](./quick/260615-dkc-no-caso-todos-devem-mostrar-o-nome-da-lo/) |
| 260616-eib | na busca do SKU, a selecao dos produtos a exportar para o excel so deve aparecer quando o user clicar primeiro em exportar para o excel | 2026-06-16 | 945844a | [260616-eib-na-busca-do-sku-a-selecao-dos-produtos-a](./quick/260616-eib-na-busca-do-sku-a-selecao-dos-produtos-a/) |
| 260623-lho | Mudar padrão do nome dos banners para mês ano marca | 2026-06-23 | 95b068e | [260623-lho-mudar-padr-o-do-nome-dos-banners-para-m-](./quick/260623-lho-mudar-padr-o-do-nome-dos-banners-para-m-/) |
| 260624-d65 | Na tela de adicionar marcas, retire cadastrar nova marca e deixe como gerenciar marcas. Com as ações de apagar e desativar. | 2026-06-24 | 43dd369 | [260624-d65-na-tela-de-adicionar-marcas-retire-cadas](./quick/260624-d65-na-tela-de-adicionar-marcas-retire-cadas/) |
| 20260705 | Sistema de notificações: alertas de mudança de preço (produto único + categoria, somente quando o preço muda) e término de varreduras; sino com central no header | 2026-07-05 | 5ebd8f0 | [20260705-price-change-notifications](./quick/20260705-price-change-notifications/) |
| 260705-up8 | Deixar mais clara a passagem de tempo nos graficos de historico de preco | 2026-07-06 | c237664 | [260705-up8-deixar-mais-clara-a-passagem-de-tempo-no](./quick/260705-up8-deixar-mais-clara-a-passagem-de-tempo-no/) |

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Identidade de Produto | IDENT-01 (sinal além do EAN) | Deferred (research) | v1.11 init |
| Exportação | EXPORT-HIST-01 (export do histórico) | Deferred | v1.12 init |
| Exportação | EXPORT-UNIFY-01 (unificar com export por marca) | Deferred | v1.12 init |
| Acesso | PROFILE-FUT-01 (perfis por equipe) | Deferred | v2.0 init |
| Frete | FRET-06 (Shopify checkout shipping) | Absorbed by FRET-07 | Phase 41 |
| Banners | BANNER-05/06 (SharePoint) | Blocked (credenciais/permissões) | v4.0 init |

## Session Continuity

Last session: 2026-07-06T03:06:51Z
Stopped at: Phase 45 plan 03 complete
Resume file: .planning/phases/45-an-lise-de-sortimento/45-03-SUMMARY.md

## Operator Next Steps

- v4.0 milestone complete: audit the shipped milestone and prepare the next roadmap slice before starting new execution work
- Phase 37: ainda aberto no roadmap; revisar antes de qualquer trabalho que dependa diretamente de atributos canônicos/SQLite
- Phase 35: ainda pendente (banners SharePoint) — gate de acesso ao SharePoint necessário primeiro
- Lacoste: ativar quando houver egress de IP limpo (proxy residencial/móvel); setar `proxy_url` e validar D-06 ao vivo antes de `is_active=true`
