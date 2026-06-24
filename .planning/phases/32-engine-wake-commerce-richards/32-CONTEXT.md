# Phase 32: Engine Wake Commerce — Richards - Context

**Gathered:** 2026-06-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Confirmar empiricamente o fluxo **GraphQL + `TCS-Access-Token`** da Wake contra a **Richards** (spike gating, Wave 0 → veredito GO/NO-GO) e, **se validado**, entregar o `WakeEngine` plugado na `EngineFactory` para que o operador onboarde e busque produtos da Richards via a API GraphQL da Wake — **não** via o caminho VTEX (que retorna 0 produtos para lojas Wake). Substitui o guard `wake` que hoje lança `NotImplementedError` em `factory.py:57-60` (deixado explicitamente pela Phase 30/31 como o slot desta phase). Atende COMP-04.

**Fronteiras travadas (ROADMAP / REQUIREMENTS / PROJECT — não reabrir):** apenas **busca (catálogo + preço)** da Richards via GraphQL público da Wake. O build do engine é **internamente gated** pelo spike de confirmação (Wave 0): se o spike der NO-GO, o engine é **deferido** (não construído sobre caminho não-provado). Detecção do engine `wake` já está pronta (Phase 30, `fbitsstatic.net`) — esta phase não mexe em detecção.

</domain>

<decisions>
## Implementation Decisions

### Gate de confirmação (Wave 0 — spike)
- **D-01:** O build do `WakeEngine` é gated por um **spike de confirmação (Wave 0)** que deve demonstrar que o endpoint GraphQL da Wake retorna **produtos reais** (título + URL + preço) quando recebe o header `TCS-Access-Token` da loja. **Alvo primário: Richards.** **Fallback:** se a Richards bloquear/falhar o spike, validar contra **Shop2gether** (também Wake) para provar o fluxo genérico — SC-1 permite explicitamente qualquer das duas.
- **D-02 [GO threshold]:** **≥1 produto** com título + URL + preço retornado via GraphQL conta como **GO**. O spike é um *gate*, não um teste de carga — basta provar o caminho fim-a-fim.
- **D-03 [NO-GO]:** Se o spike reprovar, **para no gate**: registra o veredito NO-GO e **defere o `WakeEngine` para uma phase de follow-up**. Não construir o engine completo sobre um caminho não-provado. (O operador/usuário não precisa decidir no momento — a regra já está travada aqui.)
- **D-04 [estrutura do spike]:** O spike segue a **convenção de spikes existente** (`.planning/spikes/`, espelhando 003-006): script isolado e reprodutível (ex.: `experiment.py`) + `REPORT.md` com **veredito explícito** (GO/NO-GO + evidência: produto(s) extraído(s), token usado, endpoint). Fica **fora** de `backend/` até o GO. O planner deve sequenciar: spike (Wave 0) → engine (waves seguintes), gated.

### Aquisição & configuração do token (SC-4)
- **D-05 [estratégia]:** **Auto-extrair** o `TCS-Access-Token` do storefront por loja (token **público** de storefront, normalmente presente no JS da página) → onboarding zero-config — com **override manual** quando o site mudar. É **por loja** por construção (satisfaz SC-4: não hardcoded global). O spike valida que a auto-extração é viável.
- **D-06 [armazenamento do override]:** O override manual mora num **campo opcional na marca** em `data/brands.json` (ex.: `wake_access_token`), ao lado de `vtex_account`/`review_store_id`. Por ser o token **público** de storefront (o mesmo entregue no JS a qualquer visitante), commitar um override é aceitável; normalmente o campo fica **vazio** porque o auto-extract resolve. Adicionar o campo a `DynamicBrandCreate`/`DynamicBrand` (`core/models.py`) como opcional, sem quebrar marcas existentes.
- **D-07 [semântica de falha — SC-4]:** Quando o token **não pode ser resolvido** (auto-extract falha **E** sem override válido), o engine produz um **erro claro e diagnosticável** — **no momento da busca**, capturado pelo `try/except` de `_search_one` (`factory.py:92-105`) como `BrandSearchResult.error`. **Nunca 0 produtos silenciosos.** Onboarding fica desacoplado (a detecção da Phase 30 já rotulou a marca como `wake`).

### Escopo do engine (contrato `BaseEngine`)
- **D-08:** O `WakeEngine` entrega **busca real** (catálogo + preço via GraphQL) e **stubs graciosos** para `discover_categories`/`get_catalog` (retornam `[]` sem crash) e `calculate_shipping` → `None`. Implementa **todo** o contrato `BaseEngine` (sem `TypeError`). Espelha o `SFCCEngine` (D-04/D-06/D-09 da Phase 31) e cobre exatamente SC-2/SC-3 do ROADMAP (que só pedem busca retornando itens reais). Monitoramento de categorias Wake fica **deferido** (ver `<deferred>`).
- **D-09 [factory wiring]:** O `WakeEngine` é instanciado pela `EngineFactory.get_engine` para `engine_type == "wake"`, **substituindo** o guard `NotImplementedError` (`factory.py:57-60`). **Import lazy** dentro de `get_engine` (mesmo padrão do `SFCCEngine` em `factory.py:48-50`, para preservar segurança contra import circular). O `TCS-Access-Token` por loja é enviado em **cada** requisição GraphQL (SC-3).

### Busca via GraphQL (extração)
- **D-10 [forma da busca]:** **Uma única query GraphQL de busca** (search/productList do storefront Wake) retorna título + URL + preço **diretamente** — **sem enriquecimento por produto** (diferente do round-trip por PDP do SFCC). O nome exato da query e dos campos é **confirmado pelo spike** Wave 0.
- **D-11 [transporte HTTP]:** Reusar o `SessionManager.get_session()` (`aiohttp.ClientSession` compartilhado) para o **POST GraphQL** — **sem browser** (a Wake é API pública, não exige render). Espelha o uso de HTTP-API dos engines VTEX/Shopify (vs. o caminho browser do SFCC). Passar produtos pelos Quality Gates (`validate_single`/`validate_and_filter`) e por `filter_mens_fashion` (CAT-01) antes do retorno, como os demais engines.

### Claude's Discretion
- Threshold do spike acima do mínimo (D-02, ≥1) — pode subir se a GraphQL trivialmente retornar mais produtos.
- Nome exato do campo de token na marca (`wake_access_token` é sugestão) e nomes de classes/constantes/markers seguem convenções do repo.
- **Unidade/formato do preço** retornado pela GraphQL da Wake (numérico via API; provável reais como float) — confirmar no spike; o parser segue a evidência. (Contraste: a Phase 33 frete-VTEX tem contrato centavos→reais explícito; aqui o preço vem **estruturado** da API, não raspado de texto.)
- **Cache** do token auto-extraído (evitar re-extrair a cada requisição) — detalhe de implementação.
- **Estratégia concreta de auto-extração** (de onde no HTML/JS o token aparece) — research/spike.
- Se a Richards é **semeada** em `brands.json` pela phase ou **cadastrada via UI** pelo operador — detalhe do planner; o engine deve funcionar uma vez que a Richards esteja cadastrada com `engine="wake"`.
- `only_in_stock` / `sort` / `max_results`: passar à GraphQL se suportado, senão filtrar client-side — planner decide conforme o que a API expõe.
- Forma exata do retorno de `calculate_shipping` (None vs. ausência explícita) — espelhar `ShopifyEngine`/`SFCCEngine`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requisito & Roadmap
- `.planning/ROADMAP.md` §"Phase 32: Engine Wake Commerce — Richards" — Goal, Depends on (Phase 30), 4 Success Criteria + gate Wave 0 interno.
- `.planning/REQUIREMENTS.md` — **COMP-04** (onboard + busca Richards via GraphQL + `TCS-Access-Token` por loja; gated por spike) e **COMP-05** validado (detecção `wake`).
- `.planning/PROJECT.md` §"Current Milestone v3.0" — escopo Engine Wake (Richards via GraphQL, token por loja, precedido de spike de confirmação).

### Código a ser alterado / reusado
- `backend/services/engines/factory.py` L57-60 — guard `wake` que hoje lança `NotImplementedError`; ponto onde `WakeEngine(brand_key)` passa a ser instanciado (import lazy, como o `SFCCEngine` em L48-50). `_search_one` (L92-105) captura o erro de token (D-07).
- `backend/services/engines/base_engine.py` — contrato `BaseEngine` (`run_bulk_scrape`/`discover_categories`/`get_catalog`/`search`/`get_product_details`/`calculate_shipping`/`get_engine_name`) + `validate_and_filter`/`validate_single` (Quality Gates) + `filter_mens_fashion` (CAT-01).
- `backend/services/engines/sfcc_engine.py` — **analog estrutural mais recente** (engine novo plugado na factory, stubs graciosos D-06, `calculate_shipping`→None D-09, parser separado em módulo próprio). `backend/services/engines/shopify_engine.py` — analog de **transporte** (engine não-VTEX via API HTTP, `search()`→`BrandSearchResult`).
- `backend/core/session_manager.py` — `SessionManager.get_session()` (aiohttp compartilhado) para o POST GraphQL (D-11).
- `backend/core/models.py` — `DynamicBrand`/`DynamicBrandCreate` (adicionar campo opcional de token Wake, D-06); `BrandSearchResult`/`SearchProductResult`/`RawProductBronze` (alvo dos Quality Gates e do retorno da busca).
- `backend/services/brand_service.py` — `brand_service.get_brand`/`save_brand` (persistência em `data/brands.json`); fonte do domínio/token por marca.
- `backend/api/routes_brands.py` L49-53 — `detect_engine` já rotula `wake` via `fbitsstatic.net`; `create_brand` (onboarding da Richards).

### Decisões herdadas (Phase 30 / Phase 31)
- `.planning/phases/30-detec-o-de-engine-sfcc-wake/30-CONTEXT.md` — D-05 (rótulo `wake` via `fbitsstatic.net`), **D-06** (confirmação GraphQL+token é o spike Wave 0 **desta** phase), D-09/D-10 (guard da factory que esta phase substitui para `wake`).
- `.planning/phases/31-engine-sfcc-browser-p-blico-lacoste-hugoboss/31-CONTEXT.md` — padrão de engine novo: D-04 (contrato `BaseEngine` completo), D-06 (stub gracioso de categorias), D-09 (shipping None) e refs de código reusável.

### Externo (Wake — a confirmar empiricamente no spike)
- `https://wakecommerce.readme.io` — fluxo GraphQL + `TCS-Access-Token` (HIGH confidence **documental**, **NÃO** testado empiricamente). O spike Wave 0 é exatamente o que confirma isto antes de qualquer código de engine.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`SFCCEngine` / `ShopifyEngine`** — molde para o `WakeEngine`: `__init__(self, brand_key)` fino, `search()`→`BrandSearchResult`, `calculate_shipping`→None, stubs de categoria, uso de `validate_single`/`validate_and_filter` e `filter_mens_fashion`. SFCC é o analog estrutural (factory wiring + stubs); Shopify é o analog de transporte (HTTP API, não browser).
- **`SessionManager.get_session()`** (`core/session_manager.py`) — `aiohttp.ClientSession` compartilhado; suporta `.post()` para a query GraphQL — sem browser (D-11).
- **`BaseEngine.validate_and_filter` / `validate_single`** — Quality Gates Pydantic (`RawProductBronze`); passar produtos antes do retorno.
- **`BaseEngine.filter_mens_fashion`** — blocklist masculina (consistência CAT-01).
- **Convenção de spikes** (`.planning/spikes/` 003-006 + `MANIFEST.md`/`CONVENTIONS.md`) — `experiment.py` isolado + `REPORT.md` com veredito; molde para o spike Wave 0 da Wake (D-04).

### Established Patterns
- Engines resolvidos por **string do campo `engine`** da marca na `EngineFactory`; **import lazy por engine** para evitar import circular (ex.: `SFCCEngine` em `factory.py:48-50`). `wake` hoje bate no guard `NotImplementedError` (a substituir, D-09).
- `search()` retorna `BrandSearchResult` (`.products`, `.error`); `_search_one` (`factory.py:92-105`) captura exceções por marca sem derrubar o `asyncio.gather` → erro de token vira `BrandSearchResult.error` (D-07).
- Marcador exclusivo por plataforma já estabelecido; `fbitsstatic.net` rotula `wake` (Phase 30).
- Config **por marca** em `data/brands.json` (validado por `DynamicBrand`); campos opcionais como `vtex_account`/`review_store_id` são o padrão para config específica de engine — o token Wake segue esse padrão (D-06).

### Integration Points
- `EngineFactory.get_engine` (`factory.py`) — instanciar `WakeEngine(brand_key)` quando `engine_type == "wake"` (substituir guard L57-60).
- `_search_one` (`factory.py:92-105`) — try/except que captura o erro de token (D-07) sem quebrar o gather.
- `brand_service.list_brands(active_only=True)` — chokepoint que inclui a Richards (ativa, rotulada `wake`) na busca/scheduler.
- `create_brand` / `detect_engine` (`routes_brands.py`) — onboarding da Richards com `engine="wake"`.

</code_context>

<specifics>
## Specific Ideas

- Marca-alvo concreta: **Richards** (Wake Commerce); fallback de validação no spike: **Shop2gether** (também Wake). Richards **ainda não está** em `data/brands.json` — é cadastrada/semeada como marca de validação desta phase.
- O `TCS-Access-Token` é o **token público de storefront** da Wake (entregue no JS da página a qualquer visitante) — por isso **auto-extraível** e armazenável como config (não é segredo de servidor). Ainda assim é **por loja** (SC-4), não global.
- O caminho **VTEX retorna 0 produtos** para lojas Wake (motivo de existir o engine) — o `WakeEngine` deve usar a GraphQL da Wake, nunca o caminho VTEX.

</specifics>

<deferred>
## Deferred Ideas

- **Monitoramento de categorias Wake** (`discover_categories`/`get_catalog` reais) — fora de escopo nesta phase (stubs graciosos, D-08); vira follow-up se desejado, como o caminho SFCC D-05.
- **Frete/checkout Wake** — fora de escopo (`calculate_shipping`→None; sem checkout público comprometido).
- **`WakeEngine` completo se o spike der NO-GO** — deferido para phase de follow-up (D-03).
- **Enriquecimento por produto (detail query)** — não usado nesta phase (D-10, single-query); fallback futuro se a busca se mostrar esparsa.

### Reviewed Todos (not folded)
- *"Reforçar discriminação de modelo (model-words + visual como desempate)"* (`reforcar-discriminacao-modelo.md`, score 0.4) — match fraco por keywords genéricas ("phase/busca"). É sobre precisão da busca por SKU no `nlp_service`, **não** sobre o engine Wake. Fora do escopo da Phase 32 (mesma decisão das Phases 30 e 31).

</deferred>

---

*Phase: 32-Engine Wake Commerce — Richards*
*Context gathered: 2026-06-24*
