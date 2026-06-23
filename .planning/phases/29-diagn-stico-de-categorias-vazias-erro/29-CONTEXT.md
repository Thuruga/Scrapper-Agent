# Phase 29: Diagnóstico de Categorias Vazias/Erro - Context

**Gathered:** 2026-06-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Entregar um **serviço de diagnóstico de saúde de categorias** que, por **marca/motor**, classifica cada categoria mapeada em três estados distintos e não intercambiáveis — **`ok` / `vazia` / `erro`** — incluindo `http_status` e `error_detail` quando aplicável, exposto por um **endpoint** e visível num **painel novo na UI** (DIAG-01, DIAG-02).

O propósito é **observabilidade operacional**: o operador identifica rapidamente quais categorias estão quebradas (erro real) vs vazias (possivelmente sazonais/legítimas) **sem precisar rodar uma busca/varredura completa**.

**Fora de escopo (desta phase):**
- **Auto-desativar** categorias com base em "vazia" — DIAG **só reporta, não age** (REQUIREMENTS Out of Scope; categorias sazonalmente vazias são legítimas).
- Probe de motores **não-VTEX** (Shopify, marketplaces virtuais ML/Amazon/Netshoes, engine `"unknown"`) — o probe real desta phase é **VTEX-only**; essas marcas aparecem com marcador "sem probe", mas não são verificadas.
- Construir/alterar engines, motor de relevância, frete por checkout (Phase 30) ou persistência de histórico de diagnóstico.
- Reclassificação periódica de engine das marcas (Phase 25 é add-time only).
</domain>

<decisions>
## Implementation Decisions

### Escopo & gatilho
- **D-01:** O diagnóstico cobre **todas as marcas registradas, incluindo inativas** — via `brand_service.list_brands()` com **`active_only=False`** (default). **Bypassa deliberadamente** o chokepoint `active_only=True` porque é uma ferramenta de **observabilidade**: o operador precisa enxergar marcas inativas/problemáticas, não escondê-las. (Exceção consciente ao padrão [ARCH] da Phase 25, que vale para busca/scheduler/export — não para diagnóstico.)
- **D-02:** Marcas em **motor não-VTEX** ou **sem de/para mapeado** (marketplaces virtuais, Shopify, engine `"unknown"`, ou marca VTEX com `mappings: []` e sem categoria canônica hardcoded) **aparecem no relatório com um marcador especial** (ex.: "sem categorias mapeadas" / "motor não suportado pelo diagnóstico") e **não sofrem probe**. Transparente e honesto: o probe é VTEX-only nesta phase. (Forma exata do marcador a critério do planner.)
- **D-03:** O relatório **sinaliza visualmente marcas inativas** de forma distinta — para não confundir "inativa" com "com erro". Consistente com a distinção visual de inativas já feita na `SettingsPage` (Phase 27, MGMT-02, opacity 0.55).
- **D-04:** **Gatilho on-demand** com duas granularidades: **botão por marca** (atende literalmente o critério 1 — "ao acionar o diagnóstico para uma marca") **+ "Diagnosticar todas"** no topo. Resultado sempre fresco a cada acionamento.
- **D-05:** **Execução síncrona** — o endpoint dispara os probes (concorrentes, ~6 categorias/marca) e **retorna o relatório completo na própria resposta**. Sem job assíncrono, sem WebSocket, sem estado de job. Justificativa: probes são leves (1 req/categoria), casa com "identificar rapidamente" (critério 3) e evita a infra de job da `scrape-category-multi`.
- **D-06:** **Resultados são efêmeros** — não há persistência/cache nem timestamp de "última verificação" armazenado no backend. Coerente com a execução síncrona on-demand (D-05); a UI exibe o resultado fresco da chamada atual. (Cache/agendamento foi considerado e adiado — ver Deferred.)

### Mecanismo de probe
- **D-07:** **Probe dedicado e leve**, NÃO reuso de `engine.search()` nem de `run_bulk_scrape`. Faz **1 chamada à VTEX Search API no path da categoria mapeada** (`/api/catalog_system/pub/products/search/{path}?_from=0&_to=N`), **sem** o pipeline de reviews/frete/NLP/filtro mens-fashion. Crucial: **sem o fallback full-text** do `search()` ([vtex_api_scraper.py:833](services/vtex_api_scraper.py#L833)) — esse fallback re-busca sem o path da categoria e **mascararia** uma categoria "vazia" ou de "erro" trazendo produtos via busca textual.
- **D-08:** **Requisição crua que reporta o `http_status` real** — **sem** retries automáticos, **sem** fallback de domínio estável por-categoria, **sem** fallback Playwright em 403. O auto-heal do `_request_json` ([vtex_api_scraper.py:228-294](services/vtex_api_scraper.py#L228-L294)) esconderia exatamente a falha que o diagnóstico precisa medir. O probe NÃO deve passar por `_request_json`.
- **D-09:** **Sinal ok/vazia:** pede só a **primeira página** (`_from=0`); **lista não-vazia → `ok`**, **lista vazia com HTTP 200 → `vazia`**. Lê o header **`resources`** (formato `x-y/total`) da resposta VTEX para extrair a **contagem total** e exibi-la no painel (contagem "de graça", sem paginar).

### Taxonomia (3 estados) e casos de borda
- **D-10:** **Resolve o base URL correto da marca UMA VEZ por marca** (domínio público vs domínio estável `*.vtexcommercestable.com.br`) **antes** dos probes crus por categoria — reusando a lógica de auto-discovery existente ([vtex_api_scraper.py:75-96](services/vtex_api_scraper.py#L75-L96) / `fetch_categories`). **Por quê:** lojas VTEX headless/FastStore só respondem JSON no domínio estável e devolvem HTML no público; um probe 100% cru no domínio público marcaria **todas** as categorias dessas marcas como "erro" — falso positivo sistêmico. A resolução de domínio é **uma vez por marca** (não auto-heal por-categoria), preservando o `http_status` real de cada categoria (D-08).
- **D-11:** **Tudo que não é HTTP 200 (ou resposta 200 não-parseável como JSON) → `erro`**, com `http_status` + `error_detail` capturando a nuance: 404/500 (explícitos no critério 2), **403** (anti-bot), **429** (rate limit), **timeout**, **erro de rede**, **HTML-em-vez-de-JSON**. Mantém o **contrato de 3 estados** dos critérios de sucesso — a granularidade vive no `error_detail`, não em estados extras.
- **D-12:** **Mapping stale** (path errado que responde 200 + 0 produtos, indistinguível de vazia sazonal) é classificado como **`vazia`**, independente da causa — fiel ao spec ("DIAG só reporta, não age"). O painel **expõe a URL/path que foi probado** para o operador flagrar a olho um de/para errado (decisão de detalhe ligada a D-15).

### Painel UI (DIAG-02)
- **D-13:** **Nova aba "Diagnóstico"** (ex.: "Saúde de Categorias") no sidebar, ao lado de "Monitor de Categorias" — capacidade de observabilidade própria, não polui telas existentes. Nova entrada no `renderTab` switch e no sidebar ([App.tsx:2109-2170](frontend/src/App.tsx#L2109-L2170)).
- **D-14:** **Layout: lista agrupada por marca** — cada marca é um bloco/card; dentro, suas categorias mapeadas com um **chip de status (ok/vazia/erro)**. Lida naturalmente com o escopo heterogêneo (marca "sem mapeamento", inativa) e segue o padrão de lista do projeto (`SettingsPage`/`MonitoredCategoriesPage`). (Matriz/heatmap foi considerada e preterida — ficaria "ragged" com muitas células N/A, pois nem toda marca mapeia toda categoria.)
- **D-15:** **Linha expansível por categoria** — a linha mostra o chip de status; ao expandir/clicar, revela **`http_status`, `error_detail` e a URL probada**. Limpo por padrão, detalhe sob demanda.
- **D-16:** **Acionamento: botão "Diagnosticar" por marca + "Diagnosticar todas" no topo**, com **estado de loading** durante a chamada síncrona (spinner/desabilita o botão da marca em execução).

### Claude's Discretion
- **Resolução exata path→URL** por marca/categoria: reusar `resolve_category_for_brands` ([services/category_mapping.py:191](services/category_mapping.py#L191)), que já devolve `{url, path, label}` por marca a partir do slug canônico (índice hardcoded + `DynamicBrand.mappings`). Tratamento de mappings `vtex_fq` (`C:/`/`B:`) vs path amigável fica a critério do planner.
- **Grau de concorrência** dos probes (semáforo / `asyncio.gather` com limite) e respeito a rate-limit — a critério do planner, mantendo D-05 (síncrono, leve).
- **Forma exata do marcador "sem mapeamento / motor não suportado"** (D-02) no contrato de resposta e na UI.
- **Quantos itens pedir na página 0** (`_to=0` vs `_to=9`) para o sinal de presença (D-09), desde que leia o header `resources` para a contagem.
- **Nome/forma exata** do endpoint e dos modelos Pydantic de resposta (sugestão: rota fina em `api/`, lógica no serviço — ver code_context), desde que entregue por categoria: `status`, `http_status`, `error_detail`, contagem e URL probada.
- **Filosofia de teste:** seguir o padrão offline/determinístico do projeto — teste de contrato do classificador (200+itens→ok / 200+vazio→vazia / 404/500/403/timeout→erro) **sem rede/WAF**, mockando a resposta HTTP. (ver `.planning/codebase/TESTING.md`.)
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & requisitos (LOCKED)
- `.planning/ROADMAP.md` §"Phase 29: Diagnóstico de Categorias Vazias/Erro" — goal, dependências (Phase 26 fornece as marcas/mappings; Phase 25 garante que engines `"unknown"` não geram resultado enganoso) e os **3 success criteria** (estados ok/vazia/erro distintos; 404/500→erro, 200+0→vazia, 200+produtos→ok; painel por marca/motor).
- `.planning/REQUIREMENTS.md` — **DIAG-01** (linha 32: três estados com status + código HTTP + detalhe, distinguindo "vazia sazonal" de "erro real") e **DIAG-02** (linha 33: painel de saúde por marca/motor); §Out of Scope linha 78 ("Auto-desativar categorias com base em vazia" — DIAG só reporta).
- `.planning/PROJECT.md` — contexto do milestone v2.0; "Diagnóstico de motores: identificar categorias sem produtos e com erro, de forma rastreável".

### Decisões herdadas (dependência direta)
- `.planning/phases/26-onboarding-das-5-marcas-vtex/26-CONTEXT.md` — **D-04/D-07** (de/para canônico ancorado em `_RAW_CATEGORIES` + `DynamicBrand.mappings`); a "Descoberta-chave" que registra explicitamente que **os mappings alimentam este diagnóstico** (não a busca por query). Fonte das categorias a probar.
- `.planning/phases/25-funda-o-de-motores/25-CONTEXT.md` — chokepoint `list_brands(active_only)` e engine `"unknown"`→inativo; contexto p/ D-01 (o diagnóstico opta por `active_only=False`).
- `.planning/STATE.md` §"Accumulated Context › Decisions" — `[ARCH]` enforcement de `is_active` no chokepoint (que o diagnóstico **conscientemente não aplica**, D-01).

### Código consumido / a estender — Backend
- `services/vtex_api_scraper.py` — `fetch_categories` + módulo de auto-discovery público↔estável (L46-130; reusar p/ a **resolução de domínio 1x/marca**, D-10); `_request_json` (L228-294; o auto-heal/retry/Playwright que o probe **NÃO** deve usar, D-08); `scrape_category_paged` (L472-675; referência do endpoint search-by-path e do header `resources`, D-09); `search` (L677-852; o **fallback full-text L833** que o probe **NÃO** deve usar, D-07).
- `services/category_mapping.py` — `resolve_category_for_brands` (L191; devolve `{url, path, label}` por marca — paths a probar), `get_canonical_categories` (L143; merge hardcoded + dinâmico), `_RAW_CATEGORIES` (taxonomia canônica).
- `services/engines/vtex_engine.py` — `discover_categories`/`get_catalog` (árvore de categorias, p/ eventual validação de path) e `search` (L62; contraste com o probe dedicado).
- `services/engines/factory.py` — `engine_factory.get_engine` (resolve motor por marca; p/ decidir VTEX vs "sem probe", D-02).
- `services/brand_service.py` — `list_brands(active_only=False)` (D-01) e `get_brand`/`domain`.
- `api/routes_category.py` — padrão de **rota fina** + `ScrapeMultiBrandRequest`/validação de marcas (referência de estrutura p/ o novo endpoint de diagnóstico).
- `core/models.py` — `DynamicBrand` / `CategoryMapping` (`canonical_slug`/`vtex_fq_path`/`label`); padrão p/ os novos modelos Pydantic de resposta do diagnóstico.

### Código consumido / a estender — Frontend
- `frontend/src/App.tsx` — estrutura de abas: `renderTab` switch (L2109-2114) e sidebar (L2139-2170) p/ a nova aba (D-13); `SettingsPage` (L1611; distinção visual de inativas, D-03); `MonitoredCategoriesPage` (L1754; padrão de lista por marca, D-14).
- `frontend/src/api/client.ts` — `ApiClient` (adicionar método que chama o endpoint de diagnóstico).

### Filosofia de teste
- `.planning/codebase/TESTING.md` — testes offline/determinísticos (sem rede/WAF); base p/ o teste de contrato do classificador (Claude's Discretion).
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`resolve_category_for_brands(slug, [brand])`** ([services/category_mapping.py:191](services/category_mapping.py#L191)) — já resolve, por marca, o `{url, path, label}` de um slug canônico a partir do índice hardcoded e dos `DynamicBrand.mappings`. É a fonte natural das categorias e URLs a probar; o serviço de diagnóstico itera os slugs canônicos da marca e usa isso.
- **`get_canonical_categories()`** ([services/category_mapping.py:143](services/category_mapping.py#L143)) — lista as categorias canônicas (hardcoded + dinâmicas das marcas), agrupadas; útil p/ saber quais slugs cada marca tem.
- **Auto-discovery de domínio VTEX** (`fetch_categories` / `_discover_account_from_html`, [vtex_api_scraper.py:46-130](services/vtex_api_scraper.py#L46-L130)) — lógica pronta para descobrir o domínio estável quando o público devolve HTML; reusar **1x por marca** (D-10), não por-categoria.
- **Header `resources`** já é lido (e hoje comentado) em `scrape_category_paged` ([vtex_api_scraper.py:546-559](services/vtex_api_scraper.py#L546-L559)) — fornece o total real de produtos da categoria (D-09).
- **Padrão de rota fina** (`api/routes_category.py`) + validação de marcas (`scrape_category_multi`) — modelo para o novo endpoint.

### Established Patterns
- **Rotas finas em `api/`, lógica em `services/`** — o novo endpoint delega a um serviço de diagnóstico; zero regra de negócio na camada de rota (consistente com Phase 25 D-06).
- **Probe deve evitar o caminho resiliente** — `_request_json` foi feito p/ *sobreviver* a bloqueios (retry, domínio estável, Playwright); o diagnóstico quer o oposto: **fidelidade do status** (D-08). Esses dois objetivos não se misturam no mesmo helper.
- **`VTEXEngine.search()` tem fallback full-text** que mascara categoria vazia/quebrada (D-07) — motivo central de o probe ser dedicado.
- **Distinção visual de inativas** já existe na `SettingsPage` (opacity inline, Phase 27 MGMT-02) — reusar o padrão no painel (D-03).
- **Stack frontend:** React 19 + TS + Vite + Tailwind; lista/card como padrão de página; `sonner` p/ toasts de erro.

### Integration Points
- **Backend:** novo serviço de diagnóstico (ex.: `services/category_diagnostic_service.py`) + novo endpoint em `api/` (rota fina). Consome `list_brands(active_only=False)`, `engine_factory.get_engine` (decidir VTEX vs "sem probe"), `resolve_category_for_brands` (paths) e o probe cru novo.
- **Frontend:** nova aba no `renderTab`/sidebar de `App.tsx` (D-13) + novo método em `ApiClient` (`client.ts`) que chama o endpoint; componente de painel agrupado por marca com chips e linha expansível.
- **Resposta do endpoint:** por categoria — `status` (`ok`/`vazia`/`erro`), `http_status`, `error_detail`, contagem total e URL probada; mais o marcador "sem probe" para marcas D-02 e o flag de inativa (D-03).
</code_context>

<specifics>
## Specific Ideas

- O probe é a **negação intencional** da resiliência do scraper: requisição crua, status real, sem auto-heal (D-08) — exceto a resolução de domínio **uma vez por marca** (D-10), que é o que separa "marca headless legítima" de "categoria quebrada".
- A **URL probada exposta no painel** (D-12/D-15) é o mecanismo barato para o operador distinguir, a olho, um de/para errado de uma categoria genuinamente vazia — sem o backend tentar adivinhar.
- Contrato three-state é **inviolável** (critério de sucesso 2): toda nuance extra (403/429/timeout) vai no `error_detail`, nunca num quarto estado (D-11).
</specifics>

<deferred>
## Deferred Ideas

- **Persistência/cache de resultados + agendamento em background** — um job periódico (estilo `category_monitor_service`, a cada 10min) que armazena o último estado de saúde e faz o painel abrir instantâneo. Considerado e adiado: a execução síncrona on-demand (D-05/D-06) já atende os critérios; cache é evolução futura.
- **Probe de motores não-VTEX** (Shopify, marketplaces virtuais, engine `"unknown"`) — fora do escopo; o probe é VTEX-only nesta phase (D-02). Candidato a phase própria quando houver engines não-VTEX com catálogo navegável.
- **Validar o path contra a árvore de categorias** para distinguir mapping stale de vazia sazonal (marcaria path inexistente como "erro") — preterido por +1 req/categoria e +código; aceito "vazia" + URL exposta (D-12). Reabrir se o ruído de mappings stale incomodar na prática.
- **Auto-ação sobre categorias vazias/erro** (desativar, alertar, abrir ticket) — explicitamente Out of Scope (REQUIREMENTS): DIAG só reporta.

</deferred>

---

*Phase: 29-diagn-stico-de-categorias-vazias-erro*
*Context gathered: 2026-06-22*
