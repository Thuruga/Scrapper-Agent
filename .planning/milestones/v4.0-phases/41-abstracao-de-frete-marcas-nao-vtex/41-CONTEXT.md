# Phase 41: Abstracao de Frete & Marcas Nao-VTEX - Context

**Gathered:** 2026-06-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Entregar uma camada de frete por engine para marcas nao-VTEX, cobrindo Wake e Shopify sem mexer no caminho VTEX ja validado. A fase fecha o gap de frete para Richards (Wake) e Buckman/BCK (Shopify), preservando o contrato visual e de dados criado na Phase 33: `shipping_options` com todas as modalidades validas, `shipping` como opcao primaria, `shipping_price`, `is_free_shipping` e estados explicitos para falha/indisponibilidade.

O frete VTEX continua no `VtexApiClient` e no modulo puro `services/vtex_shipping.py`. Esta fase nao reabre a decisao da Phase 33 de manter VTEX fora do hook generico `BaseEngine.calculate_shipping`.

**Fronteiras travadas:**
- VTEX permanece no `VtexApiClient`; nao mover nem rotear VTEX pela nova abstracao.
- Wake e Shopify entram por `services/shipping/` com provider resolver por engine.
- Buckman/BCK e Shopify, nao VTEX. O texto do roadmap que chama Buckman de VTEX deve ser tratado como erro de contexto.
- SFCC fica explicitamente sem frete nesta fase; nada de checkout/frete para Lacoste/SFCC.
- Marketplaces ficam para Phase 42; nao misturar Mercado Livre, Netshoes ou Amazon nesta fase.
- A fase pode iniciar com spike-gate curto por provider. Provider sem GO fica como nao suportado/indisponivel com evidencia, sem frete falso.

</domain>

<decisions>
## Implementation Decisions

### Arquitetura de frete
- **D-01 [abstracao nao-VTEX]:** Criar `backend/services/shipping/` com `BaseShipping` e implementacoes por provider (`WakeShipping`, `ShopifyShipping`). Um resolver seleciona o provider pelo `engine` da marca. A logica de selecao deve ficar centralizada; callers nao devem espalhar `if engine == ...` pela aplicacao.
- **D-02 [VTEX inalterado]:** O frete VTEX permanece exclusivamente no `VtexApiClient` (`simulate_shipping`, `_fetch_shipping`, `calculate_for_brand`) e nos helpers puros de `services/vtex_shipping.py`. A nova abstracao nao substitui, nao encapsula e nao altera esse caminho. Regressao VTEX precisa ser coberta por testes.
- **D-03 [contrato comum de resultado]:** Providers nao-VTEX devem retornar a mesma forma conceitual do VTEX: `{"state": str, "shipping_options": List[ShippingInfo]}`. Estados minimos: `available`, `unavailable_for_cep`, `temporary_failure`, `unsupported`. Quando `available`, `shipping_options` vem ordenado por preco e depois prazo; a primeira opcao popula `shipping`, `shipping_price` e `is_free_shipping`.
- **D-04 [sem frete falso]:** `0.0` significa frete gratis; `None` significa nao calculado/sem valor. Nunca representar falha, provider nao suportado ou ausencia de cotacao como frete gratis. Este contrato herdado da Phase 33 continua obrigatorio.

### Buckman / Shopify
- **D-05 [Buckman e Shopify]:** Buckman/BCK deve ser tratado como Shopify. Evidencia local em 2026-06-29: `detect_engine("buckmanbck.com.br") => "shopify"`, `detect_engine("www.buckmanbck.com.br") => "shopify"`, `/collections.json` responde HTTP 200 com payload Shopify, e `backend/data/brands.json` ja registra `bck` com `engine="shopify"`.
- **D-06 [correcao do roadmap]:** A mencao do roadmap a "Buckman (VTEX)" e incorreta para planejamento. Nao corrigir Buckman para VTEX e nao tentar usar `VtexApiClient` para BCK.
- **D-07 [alvo Shopify primario]:** O alvo primario de validacao Shopify e `bck` / Buckman. `ricardoalmeida` tambem e Shopify e pode ser alvo secundario se Buckman bloquear ou nao retornar produtos/cotacao durante o spike.

### Wake / Richards
- **D-08 [alvo Wake primario]:** O alvo primario de validacao Wake e `richards`, que ja esta ativo como `engine="wake"` com `wake_access_token` configurado. A busca Wake atual retorna catalogo + preco via GraphQL; o frete precisa descobrir se ha caminho publico de carrinho/checkout/cotacao.
- **D-09 [token Wake]:** Reusar a resolucao de token ja existente no `WakeEngine` quando o provider Wake precisar falar com APIs Wake. Token continua por loja (`wake_access_token` override ou auto-resolve); nao criar token global.

### SFCC fora de escopo
- **D-10 [SFCC unsupported]:** SFCC nao ganha provider de frete nesta fase. `SFCCShipping` nao deve ser implementado como tentativa real de checkout. Se o resolver encontrar `engine="sfcc"`, deve retornar provider unsupported ou resultado `unsupported`, preservando produto sem `shipping_price`.
- **D-11 [Lacoste dormente]:** Lacoste continua inativa por anti-bot/IP e o caminho SFCC publico do projeto e catalogo + preco. Sem proxy residencial/pago, CAPTCHA, login, checkout privado ou browser headed para frete SFCC nesta fase.

### Spike-gate por provider
- **D-12 [spike antes de provider real]:** A fase deve comecar com um spike-gate curto para Wake/Richards e Shopify/Buckman, registrado em `.planning/spikes/011-non-vtex-shipping/REPORT.md` (ou caminho equivalente aprovado pelo planner). O spike testa produto real + CEP padrao contra caminho publico de frete.
- **D-13 [criterio de GO]:** GO por provider = pelo menos 1 produto real com cotacao de frete retornando preco (`0.0` permitido se explicitamente gratis) e prazo/texto de entrega, com repeticao bem-sucedida do mesmo caminho. Se o site retornar apenas indisponibilidade legitima para o CEP, o planner deve testar outro produto/CEP antes de declarar NO-GO.
- **D-14 [NO-GO provider]:** Em NO-GO, registrar endpoint/fluxo testado, resposta/assinatura do bloqueio e motivo. Implementar apenas provider unsupported/temporary failure para aquele engine, sem engine incompleto e sem dados falsos. A abstracao ainda deve existir se ao menos um provider tiver GO ou se ela for necessaria para padronizar o unsupported.
- **D-15 [baixo impacto]:** Spikes devem usar baixa frequencia, timeouts curtos, sem credenciais privadas e sem bypass anti-bot. Playwright pode ser usado apenas se o fluxo publico exigir sessao/cookie de storefront; preferir HTTP API quando disponivel.

### Inline e sob demanda
- **D-16 [dois caminhos]:** A Phase 41 deve suportar frete inline e sob demanda usando o mesmo resolver/provider:
  - inline: quando busca recebe `include_shipping=true` e CEP valido, preencher frete nos produtos Wake/Shopify suportados;
  - sob demanda: quando produto ja esta na tela ou veio do historico sem frete, permitir calcular frete para aquele produto com CEP informado.
- **D-17 [endpoint sob demanda]:** O planner pode escolher entre criar um endpoint novo para marca (`/search/calculate-shipping-brand`) ou generalizar o endpoint existente, mas nao deve quebrar `/search/calculate-shipping-vtex`. O contrato de resposta deve continuar retornando `state` + `shipping_options`.
- **D-18 [identidade do produto]:** Providers nao-VTEX devem aceitar a URL do produto como entrada primaria e descobrir internamente a identidade necessaria para carrinho/cotacao (variant id, alias, SKU Wake, etc.). Campos opcionais em `SearchProductResult` podem ser adicionados de forma aditiva se o spike provar necessidade, mas nao reutilizar `sku_id`/`seller_id` de VTEX com semantica ambigua sem documentar.

### UI e experiencia
- **D-19 [mesma UX do VTEX]:** Reusar a UI de `shipping_options` criada na Phase 33: lista de modalidades, destaque de "Frete Gratis", estados "Entrega indisponivel para este CEP" e "Frete temporariamente indisponivel", e fallback para historico antigo.
- **D-20 [preco separado]:** Manter preco do produto e frete visualmente separados na busca de marcas. Nao introduzir soma visual obrigatoria/valor final nesta fase.
- **D-21 [CEP]:** Reusar `DEFAULT_CEP`, validacao de CEP e fluxo de modal/estado ja existente. CEP nao deve ser logado em info/error nem interpolado em URL insegura; enviar em payload controlado pelo provider.

### Claude's Discretion
- Nome exato das classes, dataclasses internas e arquivos em `services/shipping/`.
- Se o provider comum herda de ABC ou usa Protocol, desde que o contrato seja claro e testavel.
- Como normalizar prazos nao-VTEX para `estimate_display` e `estimated_delivery_days`, preservando `raw_text` quando nao houver parse confiavel.
- Se Wake/Shopify compartilham helpers de parse ou mantem parsers separados.
- Exata decomposicao do spike 011 em um arquivo unico ou dois sub-spikes.
- Numero de produtos testados alem do minimo de GO, se o caminho for barato/estavel.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requisito e roadmap
- `.planning/ROADMAP.md` - Phase 41: "Abstracao de Frete & Marcas Nao-VTEX"; success criteria de BaseShipping, Richards, Buckman e regressao VTEX.
- `.planning/REQUIREMENTS.md` - FRET-07 e limites de frete no milestone v4.0.
- `.planning/STATE.md` - decisao acumulada `[v4.0 ARCH/shipping]`: `BaseShipping` em `services/shipping/`; VTEX permanece em `VtexApiClient`.
- `.planning/PROJECT.md` - milestone v4.0, eixo "Frete (cobertura total)".

### Fases anteriores obrigatorias
- `.planning/phases/33-frete-via-checkout-nos-sites-vtex/33-CONTEXT.md` - contrato de frete VTEX, estados, `shipping_options`, CEP, UI e a decisao de nao rotear VTEX pelo hook generico.
- `.planning/phases/33-frete-via-checkout-nos-sites-vtex/33-PATTERNS.md` - helpers puros, fake sessions, serializacao Pydantic e UI patterns para shipping.
- `.planning/phases/33-frete-via-checkout-nos-sites-vtex/33-VERIFICATION.md` - criterios ja verificados que nao podem regredir.
- `.planning/phases/32-engine-wake-commerce-richards/32-CONTEXT.md` - Wake GraphQL, token por loja, `WakeEngine`, e decisao anterior de `calculate_shipping -> None` que esta fase substitui apenas se o spike der GO.
- `.planning/phases/32-engine-wake-commerce-richards/32-PATTERNS.md` - uso de `SessionManager`, token e estrutura de engine Wake.
- `.planning/phases/31-engine-sfcc-browser-p-blico-lacoste-hugoboss/31-CONTEXT.md` - SFCC como catalogo + preco, `calculate_shipping -> None`, e limites anti-bot.

### Codigo a alterar/reusar
- `backend/core/models.py` - `ShippingInfo`, `SearchProductResult.shipping_options`, campos legados e possivel campo opcional de metadata de frete.
- `backend/services/vtex_api_scraper.py` - manter `simulate_shipping`, `_fetch_shipping`, `calculate_for_brand` inalterados exceto se teste/regressao exigir ajustes localizados.
- `backend/services/vtex_shipping.py` - contrato puro VTEX; nao importar Wake/Shopify aqui.
- `backend/services/engines/factory.py` - busca por engine e propagacao de `zipcode/include_shipping`.
- `backend/services/engines/wake_engine.py` - busca Wake, token, produto URL/alias; ponto para chamar `WakeShipping` quando `include_shipping`.
- `backend/services/engines/shopify_engine.py` e `backend/services/shopify_api_client.py` - busca Shopify e possivel enriquecimento com variant id via produto `.json`.
- `backend/api/routes_search.py` - modelos e endpoints de busca, config CEP, frete VTEX sob demanda e possivel endpoint nao-VTEX.
- `frontend/src/App.tsx`, `frontend/src/api/client.ts`, `frontend/src/stores/searchStore.ts`, `frontend/src/App.css` - UI e cliente de frete ja criados para VTEX.
- `backend/data/brands.json` - `bck` como Shopify, `richards` como Wake, `lacoste` como SFCC inativa.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SearchProductResult` ja tem `shipping_options`, `shipping`, `shipping_price`, `is_free_shipping` e `landed_price`. A fase deve usar esse contrato em vez de criar formato paralelo.
- `VtexApiClient.simulate_shipping` ja retorna `state` + `shipping_options`; e o melhor molde para o contrato dos providers nao-VTEX.
- `routes_search.py` ja tem `zipcode`, `include_shipping`, `GET /search/config`, `/calculate-shipping-vtex` e padrao de resposta para frete sob demanda.
- `ShopifyApiClient.get_product_by_url(product_url)` ja acessa `product.json`, que pode ser reutilizado para descobrir `variants[].id` se o spike Shopify precisar de variant id.
- `WakeEngine` ja resolve domain/brand_name/token e monta URL de produto a partir de `aliasComplete`; o provider Wake deve reutilizar isso ou extrair helper comum.
- A UI ja renderiza `shipping_options` e estados especiais; o trabalho frontend deve ser incremental, principalmente habilitando on-demand para nao-VTEX e garantindo que botoes aparecam para engines suportados.

### Current Constraints
- `BaseEngine.calculate_shipping` existe, mas VTEX nao usa esse hook. Phase 41 pode implementar o hook para Wake/Shopify ou chamar `services/shipping` diretamente nos engines, desde que o resolver central exista.
- `ShopifyEngine.search` hoje usa `suggest.json` primeiro; esse caminho pode nao expor variant id. O provider deve conseguir recalcular via URL ou fazer fallback para `product.json`.
- `WakeEngine.search` hoje nao guarda id de SKU/variant; se Wake shipping exigir id, o provider precisara buscar detalhes adicionais ou a query GraphQL precisara ser expandida de forma aditiva.
- `brands.json` contem `bck` como Shopify com mappings `/collections/...`; nao ha indicio local de que BCK deva ser VTEX.

### Established Patterns
- Spikes ficam em `.planning/spikes/NNN-*` com `experiment.py` e `REPORT.md`, veredito explicito GO/NO-GO e evidencia reprodutivel.
- Falha por marca/produto nao deve derrubar `asyncio.gather`; retornar erro/estado por produto.
- Testes de rede devem ser hermeticos com fake async session; rede ao vivo fica no spike/relatorio, nao em teste unitario.
- Campos novos em Pydantic devem ser aditivos com defaults seguros.
- Dados de CEP e payload de frete nao devem aparecer em logs de info/error.

### Integration Points
- `EngineFactory.search_all_brands(... zipcode, include_shipping)` ja propaga os parametros. Wake/Shopify precisam respeitar esses argumentos.
- `ShopifyEngine.calculate_shipping` e `WakeEngine.calculate_shipping` hoje retornam `None`; Phase 41 substitui por chamadas ao provider quando houver GO.
- Sob demanda deve resolver a marca persistida por `brand_key` e ancorar qualquer URL/host ao dominio da marca ou validar que a URL pertence ao dominio esperado, mitigando SSRF/open redirect.
- Exportacao/historico devem serializar `shipping_options` por Pydantic sem hand-serialization.

</code_context>

<specifics>
## Specific Ideas

- Pasta sugerida: `backend/services/shipping/`
  - `base.py` - `BaseShipping`, `ShippingResult` (se util), estados comuns.
  - `resolver.py` - `get_shipping_provider(brand)` ou `resolve_shipping_provider(engine, brand_key)`.
  - `wake.py` - `WakeShipping`.
  - `shopify.py` - `ShopifyShipping`.
  - `unsupported.py` - provider que retorna `unsupported`.
- Provider method sugerido:
  - `async calculate(product: SearchProductResult | dict, zipcode: str, brand: DynamicBrand) -> dict`
  - retorno: `{"state": "...", "shipping_options": [ShippingInfo(...)]}`
- Textos de estado:
  - unsupported: `Frete nao suportado para este engine`
  - temporary failure: `Frete temporariamente indisponivel`
  - unavailable: `Entrega indisponivel para este CEP`
- Spike 011 deve testar pelo menos:
  - Shopify/Buckman: produto encontrado pela busca atual -> product `.json` -> variant/cart/shipping rate publico (ou registrar bloqueio).
  - Wake/Richards: produto encontrado pela GraphQL atual -> possivel API/cart/checkout Wake com token -> cotacao (ou registrar bloqueio).
- Regressao obrigatoria:
  - Busca VTEX com frete continua passando nos testes Phase 33.
  - Busca Shopify/Wake sem CEP nao tenta frete.
  - Busca Shopify/Wake com CEP e provider unsupported nao marca frete gratis.
  - SFCC/Lacoste nao calcula frete e nao quebra.

</specifics>

<deferred>
## Deferred Ideas

- Frete para Mercado Livre, Netshoes e Amazon - Phase 42.
- Matriz multi-regional de CEPs - Phase 42.
- Frete SFCC/Lacoste - future, dependente de caminho publico confiavel e egress limpo; fora desta fase.
- Proxy residencial/pago, CAPTCHA solving, login ou credenciais privadas para frete - fora desta fase.
- Refatorar VTEX para dentro de `BaseShipping` - explicitamente nao fazer.
- Preco total visual/landed price como destaque principal - nao fazer nesta fase.

### Reviewed Todos (not folded)
- `.planning/todos/pending/cap-search-history-list.md` - historico/listagem; nao altera frete.
- `.planning/todos/pending/reforcar-discriminacao-modelo.md` - precisao de modelo/NLP; nao altera frete.
- `.planning/todos/pending/hugoboss-vtex-io-category-scan.md` - categoria Hugo Boss; pertence ao eixo Phase 39, nao frete nao-VTEX.

</deferred>

---

*Phase: 41-Abstracao de Frete & Marcas Nao-VTEX*
*Context gathered: 2026-06-29*
