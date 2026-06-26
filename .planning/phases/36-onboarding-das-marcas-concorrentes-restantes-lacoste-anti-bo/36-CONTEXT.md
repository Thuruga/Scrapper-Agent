# Phase 36: Onboarding das Marcas Concorrentes Restantes - Lacoste (anti-bot) & Zara - Context

**Gathered:** 2026-06-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Habilitar a busca ao vivo da **Lacoste** (engine `sfcc`) se, e somente se, um gate de viabilidade anti-bot provar um caminho publico e reprodutivel para extrair catalogo + preco. A Lacoste ja esta cadastrada em `backend/data/brands.json` como `engine="sfcc"`, mas permanece `is_active=false` porque HTTP direto retorna 403 e o `BrowserManager` atual tambem recebe "Access Denied" em Playwright headless.

Esta phase tambem **reavalia a Zara/Inditex** como spike de viabilidade. Zara nao vira engine comprometido nesta phase; se houver caminho publico viavel, o resultado e promover um requisito/fase propria.

**Fronteiras travadas:** catalogo + preco apenas. Sem frete, checkout, estoque por CEP, OCAPI/SCAPI, conta/login, credenciais privadas, APIs internas/mobile privadas, CAPTCHA solving ou escalada de proxy/gateway sem aprovacao explicita do usuario. Acesso restrito a dados publicos de catalogo.

**Regra de gate:** nao investir em fetcher completo antes do veredito GO/NO-GO da Lacoste. Se o gate der NO-GO, documentar evidencia e manter a Lacoste inativa.

</domain>

<decisions>
## Implementation Decisions

### Gate de viabilidade Lacoste
- **D-01:** A phase comeca com um spike isolado e reproduzivel em `.planning/spikes/` (sugestao: `008-lacoste-antibot-zara-recheck`) com `experiment.py` + `REPORT.md`. O report deve ter veredito explicito **GO** ou **NO-GO**, evidencia de respostas do anti-bot e tecnicas testadas.
- **D-02 [allowed anti-bot envelope]:** O primeiro e unico caminho permitido sem nova aprovacao e **browser publico mais realista**: `playwright-stealth` (ja presente em `backend/requirements.txt`), contexto/headers/locale/timezone/viewport coerentes, mascaramento de fingerprint, baixa frequencia e logging de evidencia. Isto pode estender ou envolver o `BrowserManager`, mas deve ficar isolado do caminho global ate o GO.
- **D-03 [explicit escalation required]:** Proxy residencial, BrightData, ScraperAPI, CAPTCHA solving, browser headed/manual, perfil persistente de usuario real ou qualquer tecnica que aumente custo/risco operacional so entra com aprovacao explicita posterior do usuario. O planner nao deve assumir que essas opcoes estao autorizadas.
- **D-04 [NO-GO behavior]:** Se o caminho permitido em D-02 nao retorna produto real, a phase para no gate: registrar NO-GO, tecnicas testadas, assinatura do bloqueio, e manter `lacoste.is_active=false`. Nao construir engine degradado nem mascarar como "0 produtos".

### Criterio de GO e ativacao da Lacoste
- **D-05 [technical GO]:** O gate tecnico da Lacoste e **>=1 produto real** com titulo + URL no dominio Lacoste + preco extraido por caminho publico. Este e o minimo para provar a rota fim-a-fim.
- **D-06 [activation GO]:** Ativar a Lacoste (`is_active=True`) exige sinal mais forte: pelo menos **3 produtos reais** com titulo + URL Lacoste + preco para uma query padrao (`polo` primeiro; `camisa` como fallback) e uma repeticao bem-sucedida do mesmo fluxo. Se atingir D-05 mas nao D-06, documentar "GO tecnico / nao ativar ainda" e deixar follow-up claro.
- **D-07 [data contract]:** O produto aceito deve passar pelo contrato atual de busca: `SearchProductResult` com `brand`, `product_name`, `url`, `price_full` e, quando disponivel, `image_url`. Continuar usando Quality Gates (`validate_single`/`validate_and_filter`) e filtro masculino (`filter_mens_fashion`) como no `SFCCEngine`.
- **D-08 [shipping]:** `calculate_shipping` continua retornando `None` para SFCC/Lacoste. Nao exibir frete gratis falso nem tentar checkout.

### Implementacao se Lacoste der GO
- **D-09:** O caminho anti-bot deve ser **especifico/flagado para SFCC-Lacoste**, nao uma mudanca global inicial no `BrowserManager`. Motivo: evitar regressao em banners, deteccao de engine, Amazon, Mercado Livre e outras rotas Playwright ja existentes.
- **D-10:** Preferir um wrapper/fetcher dedicado (ex.: `LacosteBrowserFetcher` ou `SFCCAntiBotFetcher`) chamado pelo `SFCCEngine` apenas quando a marca for Lacoste ou quando uma flag/config por marca estiver ativa. Nomes exatos ficam a criterio do planner.
- **D-11:** A implementacao de producao so acontece depois do GO. Antes do GO, todo codigo experimental fica fora de `backend/`. Depois do GO, integrar no menor ponto possivel: fetch de search/PDP do `SFCCEngine`, preservando parser `sfcc_parser.py` e factory existentes.
- **D-12:** Falhas anti-bot em runtime devem aparecer como `BrandSearchResult.error` diagnosticavel (ou erro capturado por `_search_one`), nunca como sucesso vazio silencioso.
- **D-13:** Manter limites conservadores: `max_results` modesto, baixa concorrencia, sleeps humanos e timeouts claros. A Lacoste ja bloqueou o fluxo atual; volume alto aumenta risco de novo bloqueio.

### Zara / Inditex
- **D-14:** Zara entra nesta phase apenas como **spike de reavaliacao**. O objetivo e decidir se existe um caminho publico permitido para catalogo + preco. Nao construir engine Zara dentro da Phase 36.
- **D-15 [Zara outcomes]:** Se a Zara continuar bloqueada ou depender de endpoint interno/mobile/privado, manter COMP-FUT-03 deferido com evidencia atualizada. Se houver caminho publico viavel, criar/promover requisito ativo e fase propria para engine Inditex/Zara.
- **D-16:** A Zara tambem serve como controle anti-falso-positivo: nao deve ser rotulada como SFCC/Wake/VTEX se a evidencia continuar sendo Inditex/proprietaria.

### Claude's Discretion
- Nome exato do spike 008, classes e flags.
- Forma exata do `REPORT.md`, desde que tenha veredito GO/NO-GO e evidencia suficiente.
- Numero de tentativas no gate, desde que respeite baixa frequencia e produza evidencia reprodutivel.
- Se o fetcher dedicado vive em `backend/core/`, `backend/services/engines/` ou submodulo SFCC, desde que fique isolado e testavel.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requisito & Roadmap
- `.planning/ROADMAP.md` secao "Phase 36: Onboarding das Marcas Concorrentes Restantes - Lacoste (anti-bot) & Zara" - Goal, requirements, success criteria.
- `.planning/REQUIREMENTS.md` - COMP-03 gap (Lacoste ao vivo) e COMP-FUT-03 (Zara/Inditex).
- `.planning/PROJECT.md` - milestone v3.0 e fronteiras publicas de catalogo/preco.
- `.planning/STATE.md` - decisoes de onboarding ao vivo: Richards ativa (`wake`), Hugo Boss ativa (`vtex`), Lacoste inativa (`sfcc`) por anti-bot.

### Fases anteriores
- `.planning/phases/31-engine-sfcc-browser-p-blico-lacoste-hugoboss/31-CONTEXT.md` - contrato do `SFCCEngine`, parser JSON-LD/OpenGraph, search via browser, shipping `None`, categoria com fallback gracioso.
- `.planning/phases/31-engine-sfcc-browser-p-blico-lacoste-hugoboss/31-REVIEW.md` - double-www ja resolvido; bloqueio remanescente da Lacoste e anti-bot, nao URL builder.
- `.planning/phases/32-engine-wake-commerce-richards/32-CONTEXT.md` - padrao de gate GO/NO-GO antes de engine completo.
- `.planning/spikes/003-sfcc-inditex-storefront-mvp/REPORT.md` - HTTP direto 403 para SFCC e Zara/Inditex.
- `.planning/spikes/004-sfcc-browser-public-probe/REPORT.md` e `006-sfcc-live-browser-e2e-prototype/REPORT.md` - caminho browser publico validado em lojas US, mas nao suficiente para Lacoste BR no runtime atual.

### Codigo a alterar/reusar
- `backend/services/engines/sfcc_engine.py` - ponto de integracao do fetch de search/PDP; preservar parser/contrato.
- `backend/services/engines/sfcc_parser.py` - parsing JSON-LD/OpenGraph/card/nav ja existente.
- `backend/core/browser_manager.py` - Playwright atual: headless, headers/locale/timezone, fingerprint masking basico.
- `backend/services/engines/factory.py` - `_search_one` captura erros por marca e retorna `BrandSearchResult.error`.
- `backend/core/models.py` - `DynamicBrand`, `BrandSearchResult`, `SearchProductResult`, `RawProductBronze`.
- `backend/data/brands.json` - Lacoste ja cadastrada como `engine="sfcc"`, `is_active=false`.
- `backend/requirements.txt` - `playwright-stealth>=1.0.6` ja disponivel.
- `backend/infrastructure/http/proxy_manager.py` e `session_factory.py` - proxies existem, mas nao autorizados para Phase 36 sem aprovacao explicita (D-03).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SFCCEngine` ja implementa todo o contrato `BaseEngine`, busca via browser, enriquecimento por PDP, `calculate_shipping -> None`, `discover_categories` com fallback `[]`.
- `BrowserManager.fetch_html` cria um browser Chromium headless por chamada, com UA Chrome, `pt-BR`, timezone Sao Paulo, viewport desktop e mascaramento manual de `navigator.webdriver`. Isto e a base a melhorar no spike, nao uma prova de viabilidade.
- `playwright-stealth` ja e dependencia usada em `amazon_engine.py`; pode ser reusado no spike sem adicionar pacote.
- `EngineFactory.search_all_brands` usa `list_brands(active_only=True)`, entao a Lacoste so entra na busca geral depois de D-06.
- `BrandSearchResult.error` ja e o canal padrao para falha por marca.

### Established Patterns
- Spikes vivem em `.planning/spikes/` com `experiment.py` + `REPORT.md` e veredito claro (ver spike 007 Wake).
- Engine completo so deve ser construido depois do gate GO quando o caminho externo e incerto.
- Mudancas de engine devem preservar lazy import/factory wiring e evitar fallback silencioso para VTEX.
- Testes hermeticos devem mockar browser/fetchers; live-network fica como spike/manual evidence.

### Integration Points
- Se GO, o novo fetcher deve ser injetado no menor ponto possivel do `SFCCEngine`: fetch da search page e PDPs da Lacoste.
- Se NO-GO, a unica persistencia esperada e planejamento/evidencia; `brands.json` permanece com Lacoste inativa.
- Se ativar Lacoste, atualizar `backend/data/brands.json` e validar `search_all_brands("polo", brands=["lacoste"])` retorna produto real.

</code_context>

<specifics>
## Specific Ideas

- Lacoste atual: `brand_key="lacoste"`, `domain="lacoste.com.br"`, `engine="sfcc"`, `is_active=false`.
- Query padrao para gate: `polo`; fallback: `camisa`.
- Caminho atual bloqueado: HTTP direto 403; Playwright headless do `BrowserManager` retorna "Access Denied" pequeno (296B) na home e na busca.
- Hugo Boss nao entra nesta phase como SFCC: `www.hugoboss.com.br` foi comprovado VTEX e esta ativo.
- Richards nao entra nesta phase: `wake` ja entregue e ativa.

</specifics>

<deferred>
## Deferred Ideas

- Proxy residencial / BrightData / ScraperAPI / CAPTCHA solving para Lacoste - requer aprovacao explicita posterior.
- Engine Zara/Inditex - fase propria se o spike encontrar caminho publico viavel.
- Frete/checkout/estoque por CEP para SFCC/Lacoste - fora de escopo.
- OCAPI/SCAPI ou qualquer endpoint autenticado/comercial - fora de escopo.
- Categoria/monitoramento Lacoste alem da busca por termo - follow-up se a busca ao vivo estabilizar.

### Reviewed Todos (not folded)
- `reforcar-discriminacao-modelo.md` - sobre precisao de modelo/NLP, nao sobre Lacoste anti-bot ou Zara.
- `cap-search-history-list.md` - sobre paginacao de historico, nao relacionado a Phase 36.

</deferred>

---

*Phase: 36-Onboarding das Marcas Concorrentes Restantes - Lacoste (anti-bot) & Zara*
*Context gathered: 2026-06-25*
