# Phase 31: Engine SFCC (Browser Público) — Lacoste & HugoBoss - Context

**Gathered:** 2026-06-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Construir um novo `SFCCEngine` (extração **browser-rendered** via JSON-LD / OpenGraph, reusando o `BrowserManager` existente) e plugá-lo na `EngineFactory`, de modo que um operador consiga **onboardar Lacoste e HugoBoss** e **buscar seus produtos (título, URL, preço)**. Substitui o guard atual de `factory.py` que hoje lança `NotImplementedError` para `engine="sfcc"`.

**Fronteiras travadas (REQUIREMENTS / PROJECT — não reabrir):** apenas **catálogo + preço via via pública browser-rendered**. SEM frete/checkout, SEM estoque por CEP, SEM OCAPI/SCAPI (exige credenciais), SEM bypass de anti-bot / proxy / stealth / CAPTCHA / WAF. HTTP direto é 403 — só o DOM renderizado serve.

**Expansão decidida nesta discussão (acima das SC-1..4):** entregar também `discover_categories()`/`get_catalog()` reais para que Lacoste/HugoBoss apareçam na tela de **monitoramento de categorias** (como VTEX/Shopify) — **gated por research**, com fallback para stub gracioso se a descoberta da árvore SFCC pública for inviável. Ver D-05/D-06.

</domain>

<decisions>
## Implementation Decisions

### Locale & moeda
- **D-01:** Onboardar os **storefronts BR** de cada marca — `lacoste.com.br` e `hugoboss.com.br` (usuário confirmou que HugoBoss tem loja BR). Extrair **preço em reais nativamente**, sem conversão de câmbio. Motivo: o preço útil para monitoramento de concorrência é o praticado no Brasil. Os spikes 004-006 validaram as lojas **US** (USD `$119.00`); a Phase 31 muda o alvo para `.com.br`.
- **D-02:** O parser de preço deve tratar o formato **BR** (`R$ 1.234,56` — ponto de milhar, vírgula decimal), não o `$119.00` dos spikes. Preferir padrões de dinheiro explícitos (evitar números genéricos de texto de acessibilidade — Pitfall do Spike 006).

### Semântica da busca
- **D-03:** A busca por termo (SC-1) é atendida renderizando a **página de busca nativa** da loja (query → página de resultados renderizada → cards), e então **enriquecendo via PDP** (ver D-07). Escolhido sobre "navegação por categoria" (não casa com query livre) e sobre "busca + fallback categoria" (escopo extra não pedido).

### Escopo de catálogo / categorias
- **D-04:** O `SFCCEngine` implementa **todo o contrato do `BaseEngine`** (`run_bulk_scrape`, `discover_categories`, `get_catalog`, `search`, `get_product_details`, `calculate_shipping`, `get_engine_name`).
- **D-05:** Decisão do usuário (**opção B**): entregar `discover_categories()`/`get_catalog()` **reais** — Lacoste/HugoBoss entram na tela de monitoramento de categorias como VTEX/Shopify fazem. Isto **expande além das SC-1..4** (que só cobrem busca/preço) e **não foi validado pelos spikes** (eles percorreram uma categoria já dada → PDP; nunca descobriram a árvore de categorias pelo menu).
- **D-06 [guard pragmático]:** A entrega de catálogo completo (D-05) é **gated por research**: se a descoberta da árvore de categorias SFCC pela home/menu renderizado se mostrar inviável publicamente ou cara demais, a Phase 31 **cai para o stub gracioso** (`discover_categories`/`get_catalog` retornam vazio sem crash) e o catálogo completo vira uma phase de follow-up — para a Phase 31 ainda fechar pela busca (SC-1..4). O planner deve sequenciar a busca (núcleo, SC-1..4) **antes** do catálogo (expansão, D-05).

### Enriquecimento por PDP
- **D-07:** **Enriquecer todos** os resultados até `max_results` abrindo a PDP de cada um, para máxima fidelidade (preço + imagem sempre presentes). Motivo: valor central do projeto é alta fidelidade de dados; Lacoste não traz imagem no card e HugoBoss não traz preço na categoria — ambos só vêm da PDP.
- **D-08:** Por D-07 ser caro (cada PDP = uma navegação de browser), o planner deve manter `max_results` **modesto por padrão** (sugestão: 10) e usar **concorrência/throttle controlados** para limitar custo e exposição anti-bot. O número exato fica a critério do planner (ver Claude's Discretion).

### Frete (SC-4)
- **D-09:** `calculate_shipping` do `SFCCEngine` **não calcula frete** (escopo público sem checkout): retorna ausência explícita (None ou `ShippingInfo` de "não disponível"), **sem erro** e **sem badge de "Frete Grátis" indevido**. Espelha `ShopifyEngine.calculate_shipping` (que retorna `None`). Forma exata (None vs. ShippingInfo) a critério do planner.

### Claude's Discretion
- Valor padrão de `max_results` / profundidade de varredura (D-08) — usuário optou por não fixar; planner decide um default sensato.
- Forma exata do retorno de `calculate_shipping` (None vs. ShippingInfo de ausência) (D-09).
- Estratégia concreta de extração JSON-LD vs. OpenGraph vs. texto de card por marca (Spike 005: HugoBoss forte em ProductGroup JSON-LD na categoria; Lacoste forte em Product JSON-LD + OG na PDP) — implementação segue a evidência dos spikes.
- Nomes de classes/constantes/markers e estrutura dos testes seguem as convenções do repo.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requisito & Roadmap
- `.planning/ROADMAP.md` §"Phase 31: Engine SFCC (Browser Público) — Lacoste & HugoBoss" — Goal, Depends on (Phase 30), 4 Success Criteria.
- `.planning/REQUIREMENTS.md` — COMP-03 (onboard + busca SFCC catálogo+preço via browser público) e a seção "Out of Scope" (frete/checkout/OCAPI/SCAPI/anti-bot proibidos).
- `.planning/PROJECT.md` §"Current Milestone v3.0" — escopo SFCC público e fronteiras.

### Evidência do caminho browser-público (spikes)
- `.planning/spikes/MANIFEST.md` — índice e veredictos dos spikes 003-006.
- `.planning/spikes/004-sfcc-browser-public-probe/REPORT.md` — browser carrega Lacoste/HugoBoss e expõe sinais SFCC (VALIDATED_FOR_SFCC_PUBLIC_BROWSER).
- `.planning/spikes/005-sfcc-public-parser-prototype/REPORT.md` — estratégia de parsing: JSON-LD primeiro → OpenGraph suplementar → texto de card para discovery; Lacoste category card precisa de enriquecimento por PDP (imagem/estoque ausentes).
- `.planning/spikes/006-sfcc-live-browser-e2e-prototype/REPORT.md` — fluxo E2E categoria → até 3 PDPs/marca → 6 produtos bronze-ready; parsing de preço deve preferir padrão monetário; `experiment.py` (harness de validação reprodutível).

### Código a ser alterado / reusado
- `backend/services/engines/base_engine.py` — contrato `BaseEngine` que o `SFCCEngine` implementa; helpers `validate_and_filter`/`validate_single` (Quality Gates) e `filter_mens_fashion`.
- `backend/services/engines/factory.py` L42-56 — `EngineFactory.get_engine`; o guard `if engine_type in ("sfcc","wake"): raise NotImplementedError` (L51-54) é o ponto onde o `SFCCEngine` passa a ser instanciado para `engine="sfcc"`.
- `backend/services/engines/shopify_engine.py` — analog mais próximo (engine não-VTEX, `calculate_shipping` → None, padrão `search()`→`BrandSearchResult`).
- `backend/core/browser_manager.py` — infra Playwright a reusar para render das páginas SFCC (D-03 da Phase 30).
- `backend/core/models.py` — `RawProductBronze` (alvo dos Quality Gates), `BrandSearchResult`, `ShippingInfo`.
- `backend/api/routes_brands.py` — `detect_engine` (já rotula `sfcc` na Phase 30) e `create_brand` (onboarding); ponto de entrada do cadastro das marcas SFCC.

### Decisões herdadas (Phase 30 / v2.0)
- `.planning/phases/30-detec-o-de-engine-sfcc-wake/30-CONTEXT.md` — detecção SFCC via marcador exclusivo `demandware.static`/`demandware.edgesuite.net`; D-09/D-10 (guard da factory que esta phase substitui).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ShopifyEngine` (`shopify_engine.py`) — molde direto para o `SFCCEngine`: engine não-VTEX, `__init__(self, brand_key)`, `search()` retornando `BrandSearchResult`, `calculate_shipping` → None, uso de `validate_single`/`validate_and_filter`.
- `BrowserManager` (`core/browser_manager.py`) — render Playwright já usado pela detecção SFCC da Phase 30; reusar para render de busca/categoria/PDP.
- `BaseEngine.validate_and_filter` / `validate_single` — Quality Gates Pydantic (`RawProductBronze`); o `SFCCEngine` deve passar os produtos por eles antes do yield/retorno.
- `BaseEngine.filter_mens_fashion` — blocklist de moda masculina; aplicável aos resultados SFCC para consistência com CAT-01 (filtro masculino/infantil).
- `experiment.py` dos spikes 005/006 — lógica de parsing JSON-LD/OG/card já prototipada; ponto de partida para o parser do engine.

### Established Patterns
- Engines resolvidos por string do campo `engine` da marca na `EngineFactory`; `engine="sfcc"` hoje bate no guard `NotImplementedError` (a substituir).
- `search()` retorna `BrandSearchResult` (com `.products`, `.error`); `_search_one` na factory captura exceções por marca sem derrubar o `asyncio.gather`.
- Estratégia de parsing validada nos spikes: **JSON-LD primeiro → OpenGraph suplementar → texto de card só para discovery**; preço via padrão monetário explícito.

### Integration Points
- `EngineFactory.get_engine` (`factory.py`) — instanciar `SFCCEngine(brand_key)` quando `engine_type == "sfcc"` (remover/ramificar o guard).
- `brand_service.list_brands(active_only=True)` — chokepoint que já inclui marcas SFCC ativas (rotuladas na Phase 30) na busca/scheduler.
- Tela de monitoramento de categorias (frontend + rotas de categoria) — consome `get_catalog()`; só relevante se D-05 (catálogo completo) for confirmado pelo research (senão stub, D-06).

</code_context>

<specifics>
## Specific Ideas

- Marcas-alvo concretas e domínios: **Lacoste** → `https://www.lacoste.com.br/`; **HugoBoss** → `https://www.hugoboss.com.br/`.
- Sinais SFCC observados nos spikes (lojas US): hosts `demandware.static`/`demandware.edgesuite.net`, contagem alta de `demandware` no DOM (508 HugoBoss / 1729 Lacoste), JSON-LD `ProductGroup`/`Product`, OpenGraph de produto.
- Por marca (Spike 005/006): HugoBoss é mais forte no **nível de categoria** (ProductGroup JSON-LD), mas precisa da PDP para preço; Lacoste é mais forte no **nível de PDP** (Product JSON-LD + OG), e os cards de categoria precisam de enriquecimento (imagem/estoque ausentes).
- "Preço em reais" (`R$ x.xxx,yy`) é requisito de exibição (SC-3) — diferente do `$119.00` dos spikes US.

</specifics>

<deferred>
## Deferred Ideas

- **Frete/checkout/estoque por CEP para SFCC** — fora de escopo do milestone (exigiria OCAPI/SCAPI com credenciais).
- **OCAPI/SCAPI (APIs autenticadas SFCC)** — fora de escopo (sem credenciais comerciais).
- **Catálogo/monitoramento de categorias SFCC como follow-up** — só vira deferido SE o research (D-06) reprovar a descoberta da árvore SFCC pública; nesse caso, a entrega de catálogo completo (D-05) sai da Phase 31 e vira phase própria.
- **Zara / Inditex IOP** — COMP-FUT-03, deferido (sem caminho público validado; também responde 403 mas não é SFCC).

### Reviewed Todos (not folded)
- *"Reforçar discriminação de modelo (model-words + visual como desempate)"* (`reforcar-discriminacao-modelo.md`, score 0.4) — match fraco por keywords genéricas ("phase/busca"). É sobre precisão da busca por SKU (discriminação de modelo no `nlp_service`), **não** sobre o engine SFCC. Fora do escopo da Phase 31.

</deferred>

---

*Phase: 31-Engine SFCC (Browser Público) — Lacoste & HugoBoss*
*Context gathered: 2026-06-24*
