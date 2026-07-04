---
status: resolved
trigger: "Nenhum dos marketplaces estao funcionando"
created: 2026-06-30
updated: 2026-06-30
resolution: RESOLVIDO. ML + Amazon + identify + criação de monitor CONFIRMADOS ao vivo pelo usuário (Rounds 1-3). Netshoes = bloqueio Akamai no edge ("Access Denied" p/ curl E Playwright) = limitação de INFRA (requer proxy residencial), documentada; UX agora mostra "Bloqueado (anti-bot)" em vez de "Pendente" eterno. Suíte 463 verdes. Commitado LOCALMENTE (branch fix/marketplace-price-monitor, commit 2c98d31, NÃO enviado ao GitHub). Ver Rounds 1-3.
---

# Debug Session: monitor-marketplace-pendente

## Symptoms
- expected: No Painel de Monitoramento, ao adicionar um produto de marketplace (Mercado Livre, Amazon, Netshoes) por URL, o sistema deve identificar a marca, buscar e exibir o preço — como acontece com a marca própria Aramis (R$ 299,90, status ATIVO com preço).
- actual: Os três marketplaces (Mercado Livre, Amazon, Netshoes) ficam "Pendente..." PARA SEMPRE e nunca trazem preço. O Mercado Livre aparece sem preço algum; Amazon e Netshoes mostram "Pendente...". O título do card cai para o brand_key em maiúsculas ("MERCADO_LIVRE", "AMAZON", "NETSHOES") em vez do nome real do produto. O status do monitor é "ATIVO", mas o preço nunca resolve.
- timeline: Nunca funcionou. Os marketplaces nunca trouxeram preço neste fluxo de monitoramento; apenas marcas próprias (Aramis) funcionam.
- errors: Nenhum erro visível — nem no console do navegador, nem aparente na UI. O item simplesmente fica preso em "Pendente". (Toast de sucesso "Adicionado ao monitoramento (Amazon/Netshoes)" aparece ao criar.)
- reproduction: Painel de Monitoramento → seção "Monitorar Novo Produto" → colar a URL de um produto de marketplace (ML/Amazon/Netshoes) no campo "URL do Produto" → clicar "Identificar e Monitorar". O monitor é criado (toast de sucesso) e o card fica "Pendente..." indefinidamente, sem nunca exibir preço.

## Round 2 — Evidence da investigação em código (open questions resolvidas)
- timestamp: 2026-06-30 — investigation item #1 RESOLVIDO (UI gating, NÃO falha do engine ML). `frontend/src/App.tsx`:
  - `handleSubmit` (L298-315): cola URL → `ApiClient.identifyBrand(url)` → pega `identified.domain` → casa com marca cadastrada via `brands.find(b => normalizeDomain(b.domain) === targetDomain)`. SE não casar, NÃO chama `addToMonitor` (L307-314): apenas revela o select manual. Por isso NÃO houve POST /monitor/start para ML.
  - `normalizeDomain` (L190-193): só remove o prefixo LITERAL `www.` (`host.startsWith('www.') ? host.slice(4) : host`). NÃO remove outros subdomínios.
  - brands.json domains de marketplace: ML=`mercadolivre.com.br`, Amazon=`amazon.com.br`, Netshoes=`netshoes.com.br`.
  - Amazon URL → identify devolve domínio `www.amazon.com.br` → normaliza p/ `amazon.com.br` → CASA → monitor criado (bate com o log). Netshoes idem (`www.netshoes.com.br`→`netshoes.com.br`→casa). ML → identify devolve `produto.mercadolivre.com.br` → `normalizeDomain` NÃO tira `produto.` → fica `produto.mercadolivre.com.br` → NÃO casa `mercadolivre.com.br` → sem monitor (bate com o log: nenhum /monitor/start p/ ML). CAUSA-RAIZ do "ML não identificado".
  - FIX APLICADO (server-side, frontend intocado): identify_brand agora normaliza o `domain` de retorno p/ o registrável canônico do marketplace (produto.mercadolivre.com.br → mercadolivre.com.br) via `canonical_marketplace_domain`. O match por domínio EXISTENTE do frontend passa a resolver a marca ML cadastrada e dispara o /monitor/start. NÃO foi alterado App.tsx.
- timestamp: 2026-06-30 — investigation item #2 / hypothesis_A CONFIRMADO em código. `detect_engine` (routes_brands.py L104-206) só decide por MARCADORES DE PLATAFORMA: collections.json (L120), api/catalog_system (L130), fbitsstatic.net (L151), vtexassets/vtexcommercestable (L158), cdn.shopify/window.shopify (L162), static.zara/demandware (L166-198). NÃO há ramo domínio→engine de marketplace. Logo amazon/netshoes/ML caem em `unknown` (L206) → identify retorna `unknown` + título cai p/ brand_key (fallback de domínio em `infer_brand_name` L88-97).
- timestamp: 2026-06-30 — POST /monitor/start (routes_product.py L24-42) → `monitor_service.start_monitor(brand=request.brand)` → `_monitor_loop` resolve engine via `engine_factory.get_engine(config.brand)` (price_monitor_service.py L128). `factory.get_engine` (factory.py L23-29) usa `normalize_brand_key`: `mercadolivre`/`netshoes`/`amazon` → engine instances. Ou seja: a criação do monitor depende SOMENTE do `brand` string (não do identify); contanto que o frontend mande `brand="mercado_livre"`, o engine resolve. Confirma: o gap do ML é puramente o matcher de domínio do frontend.
- timestamp: 2026-06-30 — Strings de engine válidas (factory.py + brands.json): ML→`mercadolivre`, Amazon→`amazon`, Netshoes→`netshoes`. Qualquer um desses retornado por detect_engine é resolvível (factory) e, no identify, o brand_key casa por domínio no frontend. Decisão: o ramo domínio→engine deve devolver EXATAMENTE essas strings.
- timestamp: 2026-06-30 — Backstage MCP `backstage_get_coding_standards` NÃO disponível nesta sessão (sem `.mcp.json`, só o `.mcp.json.example`). Procedo seguindo Clean Code + convenções do código existente (estilo dos engines/rotas vizinhos), conforme constraint.

## reasoning_checkpoint (Round 2)
hypothesis: "Três causas independentes pós-Round-1: (A) detect_engine não mapeia domínio de marketplace→engine ⇒ identify=unknown e título cai p/ brand_key; (B) o frontend só casa marca por domínio com strip de `www.`, então `produto.mercadolivre.com.br` não casa `mercadolivre.com.br` ⇒ nenhum monitor ML é criado; (C) Netshoes get_pdp_product é curl_cffi-only e dead-ends em 403; Amazon get_pdp_product passa por Playwright mas não loga nada quando não extrai preço."
confirming_evidence:
  - "A: detect_engine (L104-206) não tem ramo de domínio de marketplace; log mostra os 3 domínios → 'unknown'."
  - "B: normalizeDomain (App.tsx L190-193) só remove 'www.'; handleSubmit (L307-314) não chama addToMonitor quando não casa; log confirma nenhum /monitor/start p/ ML mas sim p/ Amazon/Netshoes (hosts www.)."
  - "C-Netshoes: get_pdp_product (netshoes_engine.py L61-80) só curl_cffi; log confirma 403→None. C-Amazon: get_pdp_product faz Playwright mas _parse_pdp_html retorna None silenciosamente quando não acha preço (sem log no ramo no-price)."
falsification_test: "Se detect_engine já tivesse ramo de marketplace, identify NÃO teria devolvido 'unknown' p/ os 3 domínios (refuta A). Se normalizeDomain removesse subdomínios, o ML teria casado e o /monitor/start teria disparado (refuta B). Se Netshoes tivesse fallback, o 403 não dead-endaria; se Amazon logasse no-price, o log teria a pista (refuta C)."
fix_rationale: "A: adicionar lookup domínio→engine (detect_marketplace_engine) ANTES das probes de plataforma (marketplaces não respondem às probes), devolvendo as strings canônicas (mercadolivre/amazon/netshoes) — corrige identify e título. B (SERVER-SIDE, sem tocar no frontend): identify_brand NORMALIZA o `domain` de retorno para o registrável canônico do marketplace (produto.mercadolivre.com.br → mercadolivre.com.br) via canonical_marketplace_domain; assim o match por domínio EXISTENTE do frontend (normalizeDomain(b.domain) === normalizeDomain(identified.domain)) resolve a marca ML cadastrada e dispara o /monitor/start — testável em pytest, frontend intocado. C-Netshoes: espelhar o fallback Playwright (mesmo padrão do ML) p/ não dead-endar em 403, com WARNING nomeando o engine. C-Amazon: logar explicitamente quando título/preço não saem + seletores de preço robustos por contêiner (#corePriceDisplay/#corePrice .a-price .a-offscreen, priceblock_ourprice, fallback amplo) p/ o layout atual da PDP."
blind_spots: "Não consigo validar extração contra páginas vivas (sem rede/anti-bot neste ambiente): se a Netshoes bloquear também o Playwright (403/JS-challenge), ou se a Amazon servir CAPTCHA/layout diferente, o preço pode continuar sem resolver — isso exige iteração ao vivo. O match por sufixo de label em detect_marketplace_engine é anti-spoof (host === base || host.endsWith('.'+base)), então maliciousmercadolivre.com.br NÃO casa. A normalização de domínio no identify só afeta os 3 marketplaces (canonical_marketplace_domain retorna None p/ marcas próprias) — Aramis/VTEX intocado."

## Current Focus (ROUND 2 — pós teste ao vivo)
- status_note: ROUND 1 (contrato `get_pdp_product`, ver ## Resolution Round 1) ESTÁ aplicado e verde (436 testes). Mas o teste ao vivo do usuário FALHOU: "Nenhum funcionou, e links do mercado livre não está sendo identificado". NÃO re-investigar o contrato get_pdp_product — já corrigido. O fix de logging FUNCIONOU (falhas agora visíveis), o que revelou 3 novas causas-raiz.
- hypothesis_A (IDENTIFY — "ML não identificado"): `detect_engine` (routes_brands.py L104-206) só detecta PLATAFORMAS (shopify/vtex/wake/zara/sfcc) por marcadores de página; NÃO há mapeamento domínio→engine de MARKETPLACE. Logo amazon.com.br / netshoes.com.br / produto.mercadolivre.com.br caem em "unknown" (logs confirmam os 3 com "engine 'unknown' ... D-03"). Causa direta do "não identificado" e do título caindo p/ brand_key.
- hypothesis_B (NETSHOES — 403): `get_pdp_product` (netshoes_engine.py L61-80) é curl_cffi-only; tomou HTTP 403 (anti-bot) e retorna None SEM fallback Playwright (ML e Amazon têm fallback; Netshoes NÃO). 403 → None → Pendente. CONFIRMADO no log: "Netshoes PDP ...tenis-aramis-icon-light... retornou status 403".
- hypothesis_C (AMAZON — sem preço): `get_pdp_product` da Amazon passou pelo Playwright (BrowserManager navegou ao PDP 2x) mas NENHUM preço resultou e NENHUM WARNING foi logado. Parser pode não extrair do HTML renderizado real (seletor errado), ou caiu em captcha/layout diferente sem erro. NÃO verificado contra HTML ao vivo.
- next_action: (1) Mapear o caminho POST /monitor/start — como resolve URL→engine (funcionou p/ Amazon/Netshoes que navegaram ao PDP certo; mas ML NÃO criou monitor — investigar por quê: forma de URL `produto.mercadolivre.com.br`?). (2) Adicionar mapeamento de domínio de marketplace no identify/detect_engine. (3) Adicionar fallback Playwright no get_pdp_product da Netshoes. (4) Verificar/instrumentar o parser Amazon contra HTML real. NOTA: anti-bot (403) pode exigir iteração ao vivo com o usuário (não 100% resolúvel em código).

## Round 2 — Evidence do teste ao vivo (human verify, 2026-06-30 20:46, log do uvicorn)
- timestamp: 2026-06-30 20:46 — `identify_brand: engine 'unknown'` emitido para os TRÊS domínios: `www.amazon.com.br`, `www.netshoes.com.br`, `produto.mercadolivre.com.br`. detect_engine não reconhece marketplaces (sem marcador shopify/vtex/wake/zara/sfcc). → IDENTIFY quebrado p/ marketplace (hypothesis_A).
- timestamp: 2026-06-30 20:46:30 e 20:47:56 — `[WARNING] netshoes_engine: Netshoes PDP https://www.netshoes.com.br/p/tenis-aramis-icon-light-masculino-G06-75I1-006 retornou status 403`. curl_cffi bloqueado, sem fallback → None → Pendente (hypothesis_B). (O WARNING só aparece graças ao fix do Round 1 — antes era silencioso.)
- timestamp: 2026-06-30 20:47:08 — `BrowserManager [PLAYWRIGHT] Navegando para https://www.amazon.com.br/...B0FZD1GZHN` (PDP da Amazon). Monitor c42bf401 "concluído" logo após, SEM preço e SEM warning. Amazon não resolveu preço silenciosamente (hypothesis_C).
- timestamp: 2026-06-30 20:47:04 / 20:47:55 — POST /monitor/start CRIOU monitores para Amazon (c42bf401) e Netshoes (e93c1114) mesmo com identify=unknown → o caminho de criação de monitor NÃO depende do identify e resolve o engine por conta própria (navegou ao PDP certo). Mas para ML (produto.mercadolivre.com.br) NÃO houve POST /monitor/start após o identify — investigar se a UI bloqueou ou se a resolução de engine do ML falhou para essa forma de URL.
- timestamp: 2026-06-30 — Aramis (VTEX) continua funcionando (monitor e37105e8 concluído normalmente) — confirma que o Round 1 não regrediu marcas próprias.

## Evidence
- timestamp: 2026-06-30 — price_monitors.json: monitor `aramis` tem last_price 299.9 e history preenchido; os 3 monitores de marketplace (mercado_livre, amazon, netshoes) têm `last_price: null`, `history: []`, `product_name: null`. Confirma que o título cai para o brand_key porque `product_name` nunca é preenchido.
- timestamp: 2026-06-30 — price_monitor_service.py:127-131: `_monitor_loop` chama `engine.get_product_details(config.url)` e depois `RawProductBronze.model_validate(product_data)`.
- timestamp: 2026-06-30 — core/models.py:102-170: `RawProductBronze` EXIGE `url`, `brand`, `raw_title`, `raw_description`, `price_full`; field_validators rejeitam `price_full <= 0` (L151), `raw_title` vazio (L165) e `image_url` None/vazio/"None" (L158).
- timestamp: 2026-06-30 — mercado_livre_engine.py:106-117 e amazon_engine.py:62-71: `get_product_details` retorna `{"seller": ...}` ou `None`. netshoes_engine.py:50-86: retorna `{"seller": ..., "price": ...}`. NENHUM retorna `url`/`raw_title`/`raw_description`/`image_url` — então `model_validate` SEMPRE lança ValidationError.
- timestamp: 2026-06-30 — price_monitor_service.py:198-199: o except captura a ValidationError e só envia via WebSocket (`manager.send_message type="error"`). Sem cliente WS conectado, o erro é invisível; o loop apenas dorme e tenta de novo para sempre → "Pendente" eterno.
- timestamp: 2026-06-30 — vtex_engine.py:86-94: `get_product_details` retorna `validate_single(prod)` (payload completo). Por isso Aramis (VTEX) funciona.
- timestamp: 2026-06-30 — Callers de `get_product_details`: price_monitor_service.py:127 (espera produto completo), cross_marketplace_service.py:491 (lê só `.get("seller")`/`.get("price")` — tolerante), routes_search.py:365 (monta DataFrame de exportação Excel — espera shape de produto completo, hoje quebrado para marketplace).

## Specialist Review
- specialist: python (general-purpose, fix-direction review)
- verdict: SUGGEST_CHANGE
- pontos incorporados:
  1. Usar MÉTODO DEDICADO (não superset de `get_product_details`). Há TRÊS callers; superset forçaria os 3 a absorver reshape de uma vez. Método novo (`get_pdp_product`) deixa cross_marketplace e routes_search byte-for-byte intactos. Como `get_product_details` é `@abstractmethod`, o novo método precisa de default na base (`return None`) para não quebrar VTEX/Shopify/SFCC/Wake/Zara.
  2. `image_url` obrigatório no `RawProductBronze` é armadilha latente: um PDP válido sem imagem parseável seria rejeitado e re-criaria o stall. Tratar no caminho do monitor (não exigir imagem para resolver preço).
  3. NÃO reusar `validate_single` no monitor (engole ValidationError → cai no `else`, sem traceback). Corrigir o except do `_monitor_loop` para `logger.exception(...)` e capturar `ValidationError` de forma estreita; cuidar de `CancelledError` e ruído de log por retry.
  4. Testes atuais (test_price_monitor.py:47/91) refazem o corpo do loop à mão e não pegariam rename de método — adicionar teste que dirige o caminho do monitor com payload marketplace (seller-only) e assegura que NÃO trava.

## Eliminated
- Não é o mesmo bug de normalização de brand_key do fluxo cross-marketplace (slug: produto-unico-marketplace). `normalize_brand_key("mercado_livre")` → "mercadolivre" resolve o engine CORRETO no factory; o problema está no formato de retorno de `get_product_details`, não na resolução do engine.

## Resolution Round 1 (contrato get_pdp_product — APLICADO, mas insuficiente; ver Round 2)
root_cause: Os três engines de marketplace (Mercado Livre, Amazon, Netshoes) implementam `get_product_details()` apenas para o enriquecimento de seller do cross-marketplace, retornando `{"seller": ...}`/`{"seller": ..., "price": ...}`/`None` em vez do payload completo exigido por `RawProductBronze`. No `_monitor_loop`, `RawProductBronze.model_validate()` lança ValidationError (faltam `raw_title`/`raw_description`/`price_full`/`image_url`), que é silenciada (só vai pro WebSocket), então o monitor de marketplace nunca resolve preço e fica "Pendente" para sempre. VTEX (Aramis) funciona porque seu `get_product_details` retorna o produto completo.
fix: |
  Separar o CONTRATO de PDP completo (monitor) do contrato seller-only (cross-marketplace),
  sem tocar em get_product_details (que cross_marketplace_service.py:491 e o export de routes_search
  consomem com shape seller-only).
  - base_engine.py: novo método `get_pdp_product(url)` com default que DELEGA para
    `get_product_details` (assim VTEX/Shopify/SFCC/Wake/Zara, que já retornam produto completo,
    seguem funcionando sem alteração).
  - mercado_livre_engine.py: override `get_pdp_product` parseando JSON-LD `application/ld+json`
    Product (curl_cffi → fallback Playwright) → dict completo RawProductBronze.
  - netshoes_engine.py: override `get_pdp_product` parseando `window.__INITIAL_STATE__`
    Product.currentProduct (preço em saleInCents) → dict completo.
  - amazon_engine.py: override `get_pdp_product` parseando a PDP DOM (#productTitle, .a-offscreen,
    #landingImage, #availability) com curl_cffi → fallback Playwright/BrowserManager em CAPTCHA/503.
  - price_monitor_service.py: `_monitor_loop` agora chama `get_pdp_product` (não get_product_details);
    remove image_url ausente/inválida antes de validar (imagem não é obrigatória p/ resolver preço);
    captura `ValidationError` de forma estreita com `logger.warning` (não engole mais a causa);
    o except externo agora propaga `asyncio.CancelledError` e usa `logger.exception` (antes o erro
    só ia ao WebSocket — invisível sem cliente conectado, escondendo a causa do "Pendente" eterno).
  - import: `from pydantic import ValidationError` em price_monitor_service.py.
verification: |
  - Repro do bug ANTES do fix: RawProductBronze.model_validate({"seller":"X"}) → ValidationError
    (missing url/brand/raw_title/raw_description/price_full). Idem para Netshoes {"seller":...,"price":...}.
  - Testes de regressão adicionados em tests/test_price_monitor.py:
    * test_monitor_uses_get_pdp_product_not_get_product_details: dirige o _monitor_loop com engine
      mockado; assegura que get_pdp_product é AWAITED, get_product_details NÃO é chamado, preço resolve
      (199.9), product_name preenchido, history tem 1 entrada e NENHUM erro de validação emitido.
    * test_monitor_invalid_payload_does_not_crash_loop: payload seller-only → loop sobrevive
      (não levanta), last_price/product_name None, history vazio.
  - pytest: backend/tests COMPLETO = 436 passed (1 warning pré-existente de coroutine não-awaited
    nos testes de dedup que mockam create_task — não relacionado). test_price_monitor.py = 6 passed.
    test_cross_marketplace_service.py + test_brand_active.py = 19 passed (contrato get_product_details
    seller-only intacto → sem regressão no cross-marketplace/export).
  - Smoke dos 3 parsers reais: ML (JSON-LD), Netshoes (__INITIAL_STATE__) e Amazon (DOM) produzem
    dicts que validam em RawProductBronze (price_full/raw_title corretos). VTEX herda o default
    delegante (não sobrescreve get_pdp_product) → Aramis segue funcionando.
  - PENDENTE (validação humana): scraping end-to-end real contra ML/Amazon/Netshoes (rede/anti-bot)
    não roda neste ambiente. O fix garante o CONTRATO; a extração real de cada site (e ajuste fino
    de seletores) deve ser confirmada adicionando um monitor real de cada marketplace.
files_changed:
  - backend/services/engines/base_engine.py (novo get_pdp_product, default delega p/ get_product_details)
  - backend/services/engines/mercado_livre_engine.py (override get_pdp_product via JSON-LD + _build_pdp_product)
  - backend/services/engines/netshoes_engine.py (override get_pdp_product via __INITIAL_STATE__ + _build_pdp_product)
  - backend/services/engines/amazon_engine.py (override get_pdp_product via DOM + _parse_pdp_html)
  - backend/services/price_monitor_service.py (_monitor_loop usa get_pdp_product; ValidationError estreita; CancelledError propaga; logger.exception)
  - backend/tests/test_price_monitor.py (2 testes de regressão para o caminho do monitor)

## Resolution Round 2 (identify marketplace + anti-bot fallbacks — APLICADO; extração ao vivo PENDENTE)
root_cause_round_2: |
  QUATRO causas independentes reveladas pelo teste ao vivo (o fix de logging do Round 1 as tornou visíveis):
  A) IDENTIFY (backend): detect_engine (routes_brands.py) só reconhecia PLATAFORMAS (shopify/vtex/wake/
     zara/sfcc) por marcadores de página. Marketplaces não têm esses marcadores → "unknown" para
     amazon.com.br / netshoes.com.br / (produto.)mercadolivre.com.br. Quebrava o identify e o título caía
     para o brand_key em maiúsculas.
  B) NETSHOES: get_pdp_product era curl_cffi-only e tomava HTTP 403 (anti-bot) sem fallback.
  C) AMAZON: get_pdp_product passava pelo Playwright mas o parser não extraía preço do PDP real e não
     logava nada quando falhava (monitor "Pendente" indiagnosticável).
  D) ML monitor/start gap (frontend): o handleSubmit (App.tsx) casava a marca por IGUALDADE EXATA do
     domínio — brands.find(b => normalizeDomain(b.domain) === normalizeDomain(identified.domain)). O
     identify devolve o host como veio na URL: "produto.mercadolivre.com.br". A marca ML está cadastrada
     como "mercadolivre.com.br". normalizeDomain só stripa "www.", NÃO "produto." → não casava → o front
     NÃO chamava addToMonitor → NENHUM POST /monitor/start para o ML (bate exatamente com o log ao vivo:
     Amazon/Netshoes vieram como www.* e casaram após stripar www.; só o ML falhou). ESTA é a causa-raiz
     do "links do mercado livre não está sendo identificado" — é UI gating, não falha do engine ML.
     IMPORTANTE: a correção A (backend) sozinha NÃO resolve D — detect_engine devolve a STRING de engine,
     mas o campo `domain` do IdentifyResponse continua sendo o host cru (produto.mercadolivre.com.br); a
     igualdade exata do front ainda falharia. Por isso D exige uma mudança no FRONTEND. (A nota do prior
     agent dizendo "NÃO houve mudança no frontend" estava incorreta e foi corrigida.)
fix_round_2: |
  A) routes_brands.py: novo _MARKETPLACE_DOMAIN_ENGINES + detect_marketplace_engine(domain) com match
     por LABEL de subdomínio (host == base or host.endswith("." + base)) — cobre www./produto./m./lista.
     e evita falso-positivo tipo "maliciousmercadolivre.com.br". detect_engine ganha "Step 0" que
     retorna o engine de marketplace ANTES das probes de plataforma. Strings devolvidas
     (mercadolivre/amazon/netshoes) são exatamente as chaves resolvíveis por EngineFactory.get_engine.
  B) netshoes_engine.py: get_pdp_product agora faz fallback para Playwright (_render_pdp_html) quando
     curl_cffi dá 403 (ou 200 sem __INITIAL_STATE__), espelhando o padrão ML/Amazon, com WARNING nomeando
     o engine em cada ramo de falha.
  C) amazon_engine.py: get_pdp_product + _parse_pdp_html com seletores de preço robustos via
     _extract_pdp_price (#corePriceDisplay_desktop_feature_div .a-price .a-offscreen → corePrice_* →
     priceblock_* → span.a-price .a-offscreen amplo por último), detecção de CAPTCHA, fallback Playwright,
     e WARNING explícito (nomeando engine+URL+campo faltante) quando a extração fica incompleta.
  D) frontend/src/App.tsx: novo helper domainMatchesBrand(urlDomain, brandDomain) — match por sufixo de
     LABEL (host === base || host.endsWith("." + base)); normalizeDomain agora também remove ponto final
     (FQDN). handleSubmit troca a igualdade exata por domainMatchesBrand, casando
     produto./lista./www./m.<marketplace> com o domínio registrável — o ML agora cria o monitor.
     Boundary de label evita casar "maliciousmercadolivre.com.br". (Re-aplicado nesta rodada: a working
     tree havia revertido a mudança de um agente concorrente ao HEAD; corrigido e verificado.)
verification_round_2: |
  - pytest backend COMPLETO (backend/tests) = 452 passed, 1 warning pré-existente (coroutine
    _monitor_loop never awaited nos testes que mockam create_task — não relacionado). Baseline Round 1
    era 436 → +16 testes novos, ZERO regressão.
  - Testes de regressão NOVOS (todos verdes):
    * test_engine_detection.py::TestMarketplaceDomainDetection — detect_marketplace_engine p/ TODAS as
      formas de host (www./produto./lista./m./bare), non-marketplace → None, anti-falso-positivo de
      boundary de label, detect_engine('produto.mercadolivre.com.br') → ('mercadolivre', None) SEM fetch,
      e resolução das strings no EngineFactory.
    * test_netshoes_engine.py — 403 curl_cffi → fallback _render_pdp_html chamado e produto extraído;
      403 + Playwright bloqueado → None + WARNING nomeando "Netshoes PDP"; 200 OK → NÃO aciona Playwright.
    * test_amazon_engine.py (NOVO) — _extract_pdp_price cobre layout atual (corePriceDisplay), legado
      (priceblock_ourprice) e fallback amplo; preço ausente → None; _parse_pdp_html sem preço → None +
      WARNING nomeando "Amazon _parse_pdp_html" + URL.
    * test_price_monitor.py — _monitor_loop usa get_pdp_product (não get_product_details) e sobrevive a
      payload seller-only inválido sem travar.
    * test_cross_marketplace_service.py — normalize_brand_key("mercado_livre") mantém ML ativo.
  - frontend: `tsc --noEmit` = exit 0 (sem erro de tipo) após a mudança em App.tsx. NÃO há teste unitário
    de front exercitando domainMatchesBrand — verificado por compilação + inspeção lógica (o helper já
    tinha um teste de intenção no backend detect_marketplace_engine com a mesma semântica de boundary).
  - VERIFICADO POR TESTE = contrato/wiring: (A) domínio→engine p/ todas as formas de host; (B) wiring do
    fallback Playwright da Netshoes + logging; (C) seletores de preço da Amazon + logging de no-price;
    (D) matcher de domínio do front (via tsc + lógica).
  - NÃO VERIFICÁVEL AQUI (exige iteração AO VIVO com o usuário — sem rede/anti-bot neste ambiente):
    a EXTRAÇÃO REAL contra páginas vivas. Netshoes 403 pode persistir mesmo via Playwright (arms race);
    a PDP da Amazon pode servir CAPTCHA/layout diferente exigindo ajuste fino de seletor; o JSON-LD do ML
    pode divergir. O logging agora NOMEIA o engine/campo que falhar (WARNING/ERROR) para a próxima rodada.
files_changed_round_2:
  - backend/api/routes_brands.py (+52: _MARKETPLACE_DOMAIN_ENGINES, detect_marketplace_engine, Step 0)
  - backend/services/engines/netshoes_engine.py (fallback Playwright _render_pdp_html no get_pdp_product + WARNINGs)
  - backend/services/engines/amazon_engine.py (get_pdp_product + _parse_pdp_html + _extract_pdp_price robusto + CAPTCHA/Playwright + WARNING no-price)
  - backend/services/engines/factory.py + backend/services/engines/brand_key_utils.py (normalize_brand_key centralizado — resolve mercado_livre/mercadolivre)
  - backend/services/cross_marketplace_service.py + backend/api/routes_search.py (normalize_brand_key + dedup de brand-list; sem hardcode redundante)
  - frontend/src/App.tsx (domainMatchesBrand + normalizeDomain FQDN; handleSubmit casa por sufixo de label → ML cria monitor)
  - backend/tests/test_engine_detection.py (NOVO bloco TestMarketplaceDomainDetection)
  - backend/tests/test_netshoes_engine.py (NOVO: 403→fallback Playwright)
  - backend/tests/test_amazon_engine.py (NOVO arquivo: _extract_pdp_price + _parse_pdp_html no-price warning)
  - backend/tests/test_price_monitor.py + backend/tests/test_cross_marketplace_service.py (regressão do caminho do monitor + normalização ML)
concurrency_note: |
  Um agente concorrente (a6881c497a2d69ffb) estava editando a working tree DURANTE esta rodada. Efeitos
  observados: (1) o diff de netshoes/routes_brands/amazon oscilou entre versões parciais e completas
  (as versões finais no disco — autoritativas — estavam COMPLETAS e corretas, verificadas por leitura +
  pytest); (2) a mudança de frontend (domainMatchesBrand) foi REVERTIDA ao HEAD em algum momento — foi
  RE-APLICADA e re-verificada (tsc verde) nesta rodada. Recomenda-se encerrar o agente concorrente antes
  de qualquer commit para não re-reverter o App.tsx.
next_live_test: |
  Reiniciar backend + rebuild do frontend (npm run build) para servir o App.tsx corrigido. (1) Colar URL
  de produto ML (produto.mercadolivre.com.br)/Amazon/Netshoes e clicar "Identificar e Monitorar": o
  identify deve retornar o engine correto (não "unknown") e o ML deve conseguir criar o monitor (antes
  não criava). (2) Aguardar ~1 ciclo. Se algum ficar "Pendente", o log do backend agora mostra
  WARNING/ERROR nomeando o engine/seletor que falhou — colar essa linha para o próximo ajuste de seletor.

## Round 3 — Teste ao vivo #2 (human verify, 2026-07-01 09:13-09:14) + fixes de extração PDP
### O que o teste ao vivo #2 provou
- FIX A/B FUNCIONARAM: log `09:14:41 detect_engine: marketplace 'mercadolivre' detectado para produto.mercadolivre.com.br`
  seguido de `POST /brands/identify 200` → `POST /monitor/start 200` → Monitor 294e864c criado. O ML agora É
  identificado e o monitor É criado (antes não era). Correção de frontend NÃO era necessária: App.tsx já tinha
  `domainMatchesBrand` (match por sufixo de label) DESDE o commit HEAD 2d6e16a — a narrativa de "revert/re-apply
  do frontend" das notas anteriores estava ERRADA; `git status -- frontend/src` está limpo (== HEAD). Git em
  2d6e16a, reflog limpo, sem reset, sem commits perdidos.
- AMAZON provavelmente OK: o usuário não citou Amazon como quebrada (só ML e Netshoes); monitor Amazon c42bf401
  concluiu sem WARNING → seletores robustos do Round 2 parecem extrair.
- DOIS marketplaces ainda sem detalhe: ML e Netshoes.

### Novas causas-raiz (Round 3) + fixes aplicados
- ML (monitor 294e864c concluiu instantaneamente, SEM log): `get_pdp_product` NÃO tratava o Anubis (PoW). O ML
  responde HTTP 200 com a página de challenge (sem JSON-LD). O código: (1) em 200 sem Product, retornava None e
  NUNCA caía no Playwright (fallback só em status!=200/exceção); (2) o fallback inline era fraco (domcontentloaded
  + sleep 3), que os próprios comentários da busca (L437-441) dizem ser cedo demais p/ Anubis.
  FIX (mercado_livre_engine.py): get_pdp_product agora (a) detecta `_is_anubis_challenge` e trata 200-sem-Product
  como bloqueio → cai no Playwright ROBUSTO `BrowserManager.fetch_html(networkidle, extra_sleep=8)` (mesmo caminho
  comprovado da busca que atravessa o redirect do Anubis); (b) `_build_pdp_product` agora tenta JSON-LD
  (`_pdp_from_jsonld`) e, se ausente, seletores da PDP renderizada (`_pdp_from_dom`: .ui-pdp-title +
  .ui-pdp-price__second-line .andes-money-amount__fraction/cents); (c) loga WARNING quando não extrai.
- NETSHOES (403 → Playwright → "HTML mas __INITIAL_STATE__/preço não extraído"): o fallback Playwright funcionava,
  mas a extração só olhava `__INITIAL_STATE__`. FIX (netshoes_engine.py): novo `_extract_pdp` tenta em ordem
  `__INITIAL_STATE__` → JSON-LD Product (`_pdp_from_jsonld`) → meta tags og/product (`_pdp_from_meta`); logging
  diagnóstico rico no fim (title da página, presença de __INITIAL_STATE__, contagem de ld+json, len do HTML) para
  a PRÓXIMA iteração revelar exatamente o que o WAF entrega. Import de BeautifulSoup movido p/ nível de módulo.
verification_round_3: |
  pytest COMPLETO rodado do repo ROOT pelo orquestrador = 454 passed, 1 warning pré-existente (coroutine
  _monitor_loop never awaited — não relacionado). Import sanity OK. NÃO verificado (não roda aqui): extração real
  contra ML/Netshoes ao vivo sob anti-bot — depende do próximo teste do usuário. O logging agora é diagnóstico.
files_changed_round_3:
  - backend/services/engines/mercado_livre_engine.py (get_pdp_product trata Anubis + BrowserManager robusto; _build_pdp_product → JSON-LD + _pdp_from_dom)
  - backend/services/engines/netshoes_engine.py (get_pdp_product → _extract_pdp: __INITIAL_STATE__→JSON-LD→meta; logging diagnóstico; import BeautifulSoup no módulo)

### Verdict Netshoes (teste ao vivo #3, 2026-07-01 09:23-09:40) — LIMITAÇÃO DE INFRA, não de código
- Diagnóstico DEFINITIVO (log, 3x): Playwright renderizou `title='Access Denied', __INITIAL_STATE__=False, ld+json=0, len=343`.
  Página de ~343 bytes "Access Denied" = bloqueio de EDGE da Akamai (Netshoes roda atrás do Akamai Bot Manager). TANTO
  curl_cffi (403) QUANTO Playwright headless (Access Denied) são bloqueados ANTES de servir conteúdo real → bloqueio por
  reputação de IP (datacenter/corporativo) / edge, NÃO um problema de seletor/parser. Nenhum ajuste de extração resolve
  (o diagnóstico multi-fonte do Round 3 já prova: sem __INITIAL_STATE__, sem ld+json, sem conteúdo).
- ML e Amazon CONFIRMADOS funcionando pelo usuário: ML resolve via fallback Playwright tanto no Anubis 200 quanto no 503.
- Opções para Netshoes (decisão do usuário): (a) proxy residencial/mobile ou API de scraping (Zyte/ScrapingBee/Bright Data)
  — infra + custo; (b) aceitar como limitação conhecida + melhorar UX (status "bloqueado" em vez de "Pendente" eterno).
- STATUS: tudo o que é resolúvel em código está RESOLVIDO (identify marketplace + ML + Amazon + criação de monitor). Netshoes
  = limitação de anti-bot (Akamai) documentada; requer infra (proxy), fora do escopo de código.
