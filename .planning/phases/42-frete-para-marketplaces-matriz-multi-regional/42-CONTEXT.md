# Phase 42: Frete para Marketplaces & Matriz Multi-Regional - Context

**Gathered:** 2026-07-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Duas entregas independentes, ambas de frete:

1. **FRET-08 — Frete para marketplaces:** cálculo de frete (custo + prazo) para os três marketplaces virtuais (Mercado Livre, Netshoes, Amazon), preenchendo `shipping_cost`/`shipping_time` quando o CEP padrão está configurado.
2. **FRET-09 — Matriz de Frete Multi-Regional:** o operador solicita, para um produto específico, o custo/prazo de frete nos CEPs-chave das 5 regiões do Brasil (Sul, Sudeste, Centro-Oeste, Nordeste, Norte), de forma on-demand/batched, nunca inline em busca ao vivo, com throttle e cache por `(sku, cep)`.

**Fronteiras travadas (pelo ROADMAP/REQUIREMENTS/STATE):**
- Matriz é **on-demand/batched**, nunca inline durante varredura ou busca ao vivo — garantido por guard na chamada e coberto por teste (critério de sucesso #4).
- Lista de CEPs vive em `backend/data/cep_matrix.json` (caminho já nomeado pelo roadmap).
- Cache por `(sku, cep)`: a segunda solicitação do mesmo par é servida do cache sem nova requisição.
- Throttle entre requisições da matriz é obrigatório.
- Marca/engine já resolvido — este é o segundo momento do eixo de frete (Phase 41 fechou não-VTEX/VTEX; esta fase fecha marketplaces + a camada de matriz regional que se aplica a qualquer engine).

</domain>

<decisions>
## Implementation Decisions

### Frete de marketplaces (FRET-08)

- **D-01 [Netshoes — tentar ao vivo, cair em `blocked`]:** Não hard-codar Netshoes como `unsupported` de saída. Reusar o fluxo Playwright existente (`_run_playwright_shipping`/CEP modal) e, quando falhar — cenário já confirmado e documentado em `.planning/debug/monitor-marketplace-pendente.md` (Akamai bloqueia no edge tanto `curl_cffi` quanto Playwright headless com "Access Denied" antes de qualquer conteúdo) — cair em estado `blocked` explícito, nunca em frete falso/zero. Mesma filosofia do spike-gate da Phase 41 (D-12/D-14): tentar, documentar evidência, declarar estado real.
- **D-02 [Prazo de entrega — melhor esforço por marketplace]:** Extrair `estimated_delivery_days`/texto de prazo nos 3 marketplaces, não só custo. Mercado Livre já tem prazo estruturado na resposta de `/shipping_options` (`api.mercadolibre.com/items/{id}/shipping_options`) — usar isso em vez de só `is_free_shipping`/preço. Amazon já lê texto de entrega via `_read_delivery_text` (`#deliveryBlockMessage`, `#contextualIngressPtLabel_deliveryShortLine`, etc.) — estender `_parse_shipping_text` para também extrair prazo, não só preço/gratuidade. Netshoes recebe o mesmo tratamento quando não estiver bloqueada (D-01); se bloqueada, não há prazo (estado `blocked` cobre custo e prazo juntos).
- **D-03 [Consolidar no `BaseShipping`]:** Confirma a decisão arquitetural já registrada em `[v4.0 ARCH/shipping]` (STATE.md): "marketplace" é um provider previsto do `BaseShipping` desde a Phase 41. Criar providers novos (`MercadoLivreShipping`, `AmazonShipping`, `NetshoesShipping` — nomes exatos a critério do planner) em `backend/services/shipping/`, registrados em `resolve_shipping_provider` (hoje só resolve `shopify`/`wake`, cai em `UnsupportedShipping` para o resto). Os providers devem **reusar** a lógica ad-hoc já validada em cada engine (`calculate_shipping`/`calculate_shipping_advanced`, incluindo o parsing de CEP/Playwright já funcional para ML/Amazon confirmados ao vivo), adaptando a saída para o contrato `ShippingCalculation`/`ShippingInfo` (`state` + `shipping_options` ordenado por preço/prazo) em vez do dict solto atual (`{"is_free_shipping":..., "shipping_price":...}`).
- **D-04 [Endpoint único]:** `/search/calculate-shipping-brand` (criado na Phase 41, D-17) passa a suportar também `engine in {mercadolivre, amazon, netshoes}` via o resolver. O endpoint legado genérico `/search/calculate-shipping` (que chama `engine.calculate_shipping_advanced` direto, sem passar pelo resolver) pode continuar existindo como está usado hoje pela UI de busca cross-marketplace (D-05), mas não deve ganhar lógica nova — lógica nova de estado/contrato vive só no resolver novo.
- **D-05 [UI cross-marketplace já existe]:** O botão "Calcular Frete" por item já existe na tela de busca cross-marketplace (`frontend/src/App.tsx`, ~L2525, chave `${marketplace}-${item.url}`) e em `_enrich_pdp_and_shipping` (`cross_marketplace_service.py`) para preencher frete inline na busca cruzada. Esta fase deve garantir que esse caminho também preencha prazo (D-02) e trate o estado `blocked` da Netshoes sem quebrar a UI — não precisa criar um botão novo para o caso "custo+prazo por marketplace".

### Matriz de Frete Multi-Regional (FRET-09)

- **D-06 [Ponto de entrada — reusar botões existentes]:** A ação "Matriz Regional" aparece ao lado dos botões "Calcular Frete" já existentes nas superfícies onde eles já vivem: busca comparativa VTEX, busca por SKU e resultado cross-marketplace (`frontend/src/App.tsx`, pontos ~L1777 e ~L2525). Não criar um painel/tela dedicada nova.
- **D-07 [Escopo de engines — todos, sempre]:** O botão/ação aparece para qualquer engine com provider de frete implementado (VTEX, Wake, Shopify, Mercado Livre, Amazon, Netshoes), inclusive quando o resultado esperado é `unsupported`/`blocked` em todas as 5 regiões (ex.: Netshoes). A resposta sempre mostra o estado real por região — nunca esconder a ação para evitar uma falha esperada. Engines sem provider algum (ex.: SFCC) ficam com o mesmo estado `unsupported` que já usam para frete simples.
- **D-08 [CEPs — capitais por região, curados por Claude]:** `backend/data/cep_matrix.json` começa com um CEP representativo por capital/região (ex.: São Paulo-SP/Sudeste, Porto Alegre-RS/Sul, Brasília-DF/Centro-Oeste, Salvador-BA/Nordeste, Manaus-AM/Norte) como default inicial — a curadoria exata (CEP específico de cada capital) fica a critério do planner/pesquisa, e o arquivo é editável depois pelo operador.
- **D-09 [Cache — TTL curto]:** O cache por `(sku, cep)` expira sozinho depois de um tempo curto configurável (horas, não permanente) — segue o padrão de configs conservadoras já usadas em `config.py` (`STOCK_PROBE_THROTTLE_SECONDS`, `MAX_REVIEW_PAGES`, etc.). Valor exato do TTL fica a critério do planner; deve ser exposto como setting nomeado (não hardcoded inline).
- **D-10 [Guard contra execução inline]:** A chamada de matriz precisa de um guard explícito e testado que impede sua execução a partir do fluxo de varredura/busca ao vivo (`cross_marketplace_search`, `run_category_scan`, etc.) — só é alcançável pela ação on-demand "Matriz Regional" por produto.

### Claude's Discretion
- Nomes exatos das classes/arquivos dos novos providers de marketplace em `services/shipping/`.
- Forma exata de extrair prazo por marketplace (seletor/regex/campo de API) — desde que preserve `raw_text` quando não houver parse confiável, igual ao padrão VTEX/Wake/Shopify.
- Layout exato da UI da Matriz Regional (tabela de 5 linhas, modal, tooltip, etc.) — manter consistência visual com o app.
- Valor exato do TTL do cache (D-09), do throttle entre requisições da matriz e dos CEPs de cada capital (D-08).
- Se o cache/summary da matriz fica em JSON local ou seguindo o padrão SQLite da Phase 37 (Phase 37 ainda não foi entregue — `[ ]` no roadmap — verificar estado real antes de escolher persistência, mesmo cuidado já registrado em `44-CONTEXT.md` D-16).
- Decomposição exata de `resolve_shipping_provider` para os 3 novos engines (classes separadas vs. uma `MarketplaceShipping` parametrizada por engine).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requisito e roadmap
- `.planning/ROADMAP.md` §"Phase 42: Frete para Marketplaces & Matriz Multi-Regional" — goal, depends on Phase 41, success criteria #1-4 (custo+prazo nos 3 marketplaces, matriz por produto nas 5 regiões, CEPs curados + throttle + cache, guard contra execução inline).
- `.planning/REQUIREMENTS.md` — `FRET-08`, `FRET-09` e os guard-rails de FRET-09 (on-demand/batched, throttle, cache por sku+cep, lista curada).
- `.planning/PROJECT.md` — milestone v4.0, eixo "D — Frete (cobertura total)".
- `.planning/STATE.md` — decisões acumuladas `[v4.0 ARCH/shipping]` (marketplace como provider futuro do `BaseShipping`), `[v4.0 FRET-09/guard-rails]` (guard-rails da matriz já travados), `[41/FRET-07-complete]` (estado atual do endpoint `/search/calculate-shipping-brand`).

### Fase anterior obrigatória (fundação de frete não-VTEX)
- `.planning/phases/41-abstracao-de-frete-marcas-nao-vtex/41-CONTEXT.md` — contrato `BaseShipping`/`ShippingCalculation`, estados (`available`/`unavailable_for_cep`/`temporary_failure`/`unsupported`), resolver central por engine, endpoint `/search/calculate-shipping-brand`, e a decisão explícita de deferir marketplaces para esta fase (seção `<deferred>`).

### Investigação viva relevante (branch atual)
- `.planning/debug/monitor-marketplace-pendente.md` — investigação completa e resolvida do fluxo de monitor de preço para os 3 marketplaces: ML e Amazon confirmados funcionando ao vivo (incluindo fallback Playwright para o desafio Anubis do ML); Netshoes bloqueada no edge pelo Akamai (curl_cffi 403 E Playwright "Access Denied", ~343 bytes) — limitação de infra (reputação de IP), não de parser/seletor. Base de evidência para D-01.

### Código a alterar/reusar
- `backend/services/shipping/base.py` — `BaseShipping`, `ShippingCalculation`, `ShippingState`, `apply_shipping_calculation`, `sorted_shipping_options`, `is_url_allowed_for_brand`.
- `backend/services/shipping/resolver.py` — `resolve_shipping_provider(brand)`; hoje só resolve `shopify`/`wake`, precisa ganhar `mercadolivre`/`amazon`/`netshoes`.
- `backend/services/engines/mercado_livre_engine.py` — `calculate_shipping` (API real `/shipping_options`), `_run_playwright_shipping` (fallback), `_extract_item_id`.
- `backend/services/engines/amazon_engine.py` — `calculate_shipping_advanced`, `_parse_shipping_text`, `_read_delivery_text` (seletores de prazo já existentes), tratamento de CAPTCHA/bloqueio (`{"error": ...}`).
- `backend/services/engines/netshoes_engine.py` — `calculate_shipping`/`calculate_shipping_advanced`, `_run_playwright_shipping` (modal de CEP).
- `backend/services/cross_marketplace_service.py` — `_enrich_pdp_and_shipping` (L480+), ponto onde frete inline já é calculado por engine na busca cruzada.
- `backend/api/routes_search.py` — `/search/calculate-shipping-brand` (D-17 da Phase 41), `/search/calculate-shipping` (endpoint legado genérico), modelos `CalculateBrandShippingRequest`/`ShippingCalculationResponse`.
- `backend/core/models.py` — `ShippingInfo` (`price`, `status`, `estimated_delivery_days`, `raw_text`, `service_name`, `service_id`).
- `backend/config.py` — padrão de constantes conservadoras (`STOCK_PROBE_THROTTLE_SECONDS`, `MAX_REVIEW_PAGES`, `DEFAULT_CEP`) para modelar o throttle/TTL da matriz.
- `backend/data/brands.json` — entradas `mercado_livre`/`netshoes`/`amazon` (promovidas a marcas reais na Phase 40), `engine` de cada uma.
- `frontend/src/App.tsx` — botões "Calcular Frete" existentes (~L1777 busca comparativa/SKU, ~L2525 cross-marketplace) — ponto de inserção da ação "Matriz Regional" (D-06).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Mercado Livre já tem frete real via API pública (`api.mercadolibre.com/items/{id}/shipping_options`) com fallback Playwright robusto para o desafio Anubis — não precisa reescrever do zero, só adaptar a saída para `ShippingCalculation`.
- Amazon já lê o bloco de mensagem de entrega da PDP (`_read_delivery_text`) e trata CAPTCHA como erro explícito — falta só extrair prazo estruturado além de custo.
- Netshoes já tem um fluxo Playwright de CEP modal (`_run_playwright_shipping`) — mesmo que hoje sempre resulte em bloqueio, a mecânica de tentativa+estado explícito já existe e deve ser reusada, não recriada.
- `services/shipping/resolver.py` e `base.py` (Phase 41) já definem o contrato e o padrão de estados — os 3 novos providers seguem o mesmo molde de `WakeShipping`/`ShopifyShipping`.
- `config.py` já tem um padrão claro de constantes de throttle/limite conservador nomeadas (Phase 44) — replicar esse padrão para a matriz em vez de introduzir um mecanismo novo.

### Established Patterns
- Estado explícito nunca vira frete falso/zero (`0.0` = grátis confirmado; `None`/estado dedicado = não calculado) — regra herdada de Phase 33/41/44, vale igual para marketplaces e para a matriz.
- Falha por produto/engine não deve derrubar o lote (`asyncio.gather` com erro isolado por item) — vale para a matriz rodar as 5 regiões sem uma falha travar as demais.
- Testes de rede são herméticos com fake session/fixtures; comportamento ao vivo (Netshoes bloqueada, Anubis do ML) fica documentado em debug/spike, não testado contra rede real.
- CEP e payload de frete não devem aparecer em logs de info/error (herdado de D-21 da Phase 41).

### Integration Points
- `resolve_shipping_provider` é o único ponto de decisão engine→provider; a matriz deve chamar esse mesmo resolver 5 vezes (uma por CEP da região), não reimplementar a seleção de provider.
- `_enrich_pdp_and_shipping` (cross_marketplace_service) e o endpoint `/search/calculate-shipping-brand` são os dois callers atuais de frete "single-shot" — a matriz é um terceiro caller que itera CEPs com throttle e cache, reusando o mesmo provider por chamada.
- Cache por `(sku, cep)` precisa de uma chave de produto estável entre chamadas — verificar se `SearchProductResult` já expõe um identificador estável (ex.: URL normalizada) reusável como parte da chave, já que "sku" nem sempre existe fora de VTEX.

</code_context>

<specifics>
## Specific Ideas

- CEPs sugeridos por região (capitais, a validar/ajustar pelo planner): Sudeste → São Paulo-SP; Sul → Porto Alegre-RS; Centro-Oeste → Brasília-DF; Nordeste → Salvador-BA; Norte → Manaus-AM.
- Ação "Matriz Regional" fica visualmente ao lado do botão "Calcular Frete" já existente, não substituindo-o — frete simples (1 CEP, inline na tela) e matriz (5 CEPs, batched) continuam sendo ações distintas.
- Estado `blocked` para Netshoes deve reaproveitar a mesma semântica de mensagem já usada no monitor de preço ("Bloqueado (anti-bot)"), para consistência de vocabulário na UI.

</specifics>

<deferred>
## Deferred Ideas

- Proxy residencial/pago ou qualquer bypass de anti-bot para desbloquear a Netshoes de verdade — fora desta fase (mesma fronteira já travada para Lacoste/SFCC nas Phases 36/41).
- Migrar a matriz para SQLite de forma definitiva antes da Phase 37 existir de fato — se a Phase 37 ainda não estiver pronta no momento do planejamento, seguir em JSON local (mesmo cuidado já registrado em `44-CONTEXT.md` D-16).
- UI de analytics/dashboard sobre a matriz (histórico de variação de frete por região ao longo do tempo) — além do necessário para operar a ação on-demand desta fase.
- Ampliar a matriz para múltiplos produtos de uma vez (lote) — o roadmap trava "para um produto"; lote fica para eventual fase futura se necessário.

### Reviewed Todos (not folded)
- `.planning/todos/pending/reforcar-discriminacao-modelo.md` — pontuou 0.6 no match automático (palavras-chave "phase/busca/sku"), mas é sobre precisão de discriminação de modelo/marca na busca por SKU, não sobre frete. Não pertence a esta fase.
- `.planning/todos/pending/audit-category-mappings-all-brands.md`, `.planning/todos/pending/hugoboss-vtex-io-category-scan.md`, `.planning/todos/pending/zara-comp07-deferred.md` — matches de baixa pontuação (0.2, só por conterem a palavra "phase"); pertencem a paridade de atributos/Hugo Boss/Zara, não a frete.

</deferred>

---

*Phase: 42-Frete para Marketplaces & Matriz Multi-Regional*
*Context gathered: 2026-07-01*
