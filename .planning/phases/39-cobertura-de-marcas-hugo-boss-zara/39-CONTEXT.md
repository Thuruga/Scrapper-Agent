# Phase 39: Cobertura de Marcas — Hugo Boss & Zara - Context

**Gathered:** 2026-06-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Esta phase tem duas frentes independentes:

1. **Hugo Boss (COMP-06):** fazer a varredura e o monitoramento por categoria da Hugo Boss funcionarem ponta-a-ponta. A Hugo Boss já está cadastrada e ativa como `engine="vtex"` (`www.hugoboss.com.br`), mas hoje tem `mappings: []` em `brands.json` — ou seja, **nenhum de/para de categoria**. Por isso selecionar uma categoria não aponta para nenhuma URL da Hugo Boss. O trabalho é descobrir e preencher esse de/para de categorias VTEX (slug canônico → path + `fq`), sem criar novo engine.

2. **Zara (COMP-07):** um spike de viabilidade GO/NO-GO sobre extração **pública** de produto + preço (Inditex), registrado em `.planning/spikes/010-zara-product-price/REPORT.md`. O engine Zara só é construído em caso de GO; em NO-GO, COMP-07 é formalmente deferido ao backlog com evidência, sem commitar engine incompleto.

**Fronteiras travadas:**
- Hugo Boss: catálogo VTEX existente, sem novo engine; reusa o `VtexEngine`/`VtexApiClient` atuais.
- Zara: catálogo + preço **públicos** apenas. Sem proxy residencial/pago, CAPTCHA solving, browser headed, login, credenciais privadas ou endpoint interno/mobile privado sem aprovação explícita posterior (envelope do v3.0, D-02/D-03 da Phase 36).
- Regra de gate: nenhum código de engine Zara antes do veredito GO.

</domain>

<decisions>
## Implementation Decisions

### Hugo Boss — de/para de categorias
- **D-01 [fonte do de/para]:** O de/para da Hugo Boss vive nos **mappings dinâmicos** do `DynamicBrand` (campo `mappings` em `backend/data/brands.json`: `canonical_slug` + `vtex_fq_path` + `label`), **não** no bloco hardcoded `_RAW_CATEGORIES` de `category_mapping.py`. Motivo: é o mecanismo já usado para marcas adicionadas; `category_mapping.py` já faz fallback nos mappings dinâmicos (`resolve_category_for_brands` / `get_category_preview`). Mantém o hardcoded focado nas marcas da casa (aramis/reserva/tommy).
- **D-02 [escopo de categorias]:** Mapear, **dentre os slugs canônicos já existentes** (`camisas`, `polos`, `camisetas`, `calcas`, `bermudas`, `jaquetas`, `infantil`), os que a Hugo Boss realmente possui no catálogo. Objetivo: a Hugo Boss entra na comparação "banana com banana" por categoria junto das demais marcas VTEX, sem fragmentar o vocabulário canônico criando slugs novos.
- **D-03 [descoberta dos paths]:** Os paths/`fq` reais devem ser **auto-descobertos** a partir da árvore de categorias VTEX da Hugo Boss (`VtexApiClient.fetch_categories("www.hugoboss.com.br")` → `_flatten_vtex_tree`, padrão "VALID_SLUGS-from-RAW" citado no roadmap), e **validados** com uma varredura-amostra que retorne produtos reais (título + URL + preço) antes de gravar. Não mapear caminhos à mão sem conferência contra a árvore real.
- **D-04 [persistência]:** O de/para descoberto é **curado e persistido estaticamente** em `brands.json` (descoberta única via script/spike). Não redescobrir a árvore VTEX a cada varredura — evita chamada extra por scan, latência e drift que poderia gerar falso positivo de "produto novo". Re-executar a descoberta só quando o catálogo da Hugo Boss mudar.

### Zara — gate de viabilidade (spike 010)
- **D-05 [critério de GO]:** GO = **≥3 produtos reais** com título + URL no domínio Zara (`zara.com/br`) + preço extraído por caminho público, para a query padrão, **com uma reexecução bem-sucedida** do mesmo fluxo. Espelha o gate de ativação do v3.0 (D-06 das fases 32/36) — barra forte antes de investir no engine. Abaixo disso = NO-GO (ou "GO técnico / não construir ainda" se ≥1 mas <3 sem repetição estável, a critério do planner registrar).
- **D-06 [envelope técnico permitido]:** Apenas **browser público + `playwright-stealth`** (já em `requirements.txt`), contexto/headers/locale/timezone/viewport coerentes (pt-BR), baixa frequência e logging de evidência. Somente storefront **público** (JSON-LD/HTML do `zara.com/br` — o spike 008 já obteve 200 + marcador de produto JSON-LD na home). **Sem** proxy residencial/pago, CAPTCHA solving, browser headed/manual, perfil persistente real, login, credenciais privadas, OCAPI/SCAPI ou endpoint interno/mobile privado sem aprovação explícita posterior.
- **D-07 [query padrão]:** Query padrão do spike = **`camiseta` / `calça`** (mais aderentes ao catálogo Zara que `polo`, maior chance de atingir ≥3 produtos reais). Respeitar o filtro masculino do sistema (CAT-01) como nas demais marcas.
- **D-08 [comportamento em GO]:** Em GO, **construir o engine Zara dentro da própria Phase 39** — operador onboarda a Zara e a busca retorna produtos reais (título + URL + preço), conforme o critério #4 do roadmap. O engine é net-new (Inditex, não VTEX/Wake/SFCC); o tamanho real revelado pelo spike informa o plano.
- **D-09 [comportamento em NO-GO]:** Em NO-GO, registrar veredito + técnicas testadas + assinatura do bloqueio no `REPORT.md`, **deferir COMP-07 ao backlog com evidência** e **não commitar engine incompleto** nem mascarar "0 produtos" como sucesso. A Zara não deve ser rotulada como SFCC/Wake/VTEX se a evidência continuar sendo Inditex/proprietária (controle anti-falso-positivo, D-16 da Phase 36).
- **D-10 [produção só pós-GO]:** Todo código experimental do spike fica fora de `backend/` até o GO. Depois do GO, integrar no menor ponto possível (engine + factory), preservando o contrato `SearchProductResult` (`brand`, `product_name`, `url`, `price_full`, `image_url` quando disponível) e os Quality Gates / filtro masculino.

### Claude's Discretion
- **Monitoramento HB & falso positivo de "produto novo" (criterion #2 — não selecionado para discussão):** quais categorias da Hugo Boss entram no scheduler de 10 min e a prevenção de falso positivo ficam a critério do planner, reusando o mecanismo de scan/comparação de estado de categoria já existente. Restrição: re-execuções de categoria inalterada **não** podem disparar falso "produto novo".
- Nome/estrutura exata do spike 010, classes, flags e nome do engine Zara (em GO).
- Forma exata do `REPORT.md` do spike, desde que tenha veredito GO/NO-GO explícito e evidência reprodutível.
- Local/forma do script de descoberta-e-persistência do de/para da Hugo Boss (ex.: reusar/estender `backend/scripts/onboard_vtex_brands.py`).
- Número de tentativas no gate da Zara, desde que respeite baixa frequência e produza evidência reprodutível.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requisito & Roadmap
- `.planning/ROADMAP.md` §"Phase 39: Cobertura de Marcas — Hugo Boss & Zara" — Goal, requirements (COMP-06, COMP-07), success criteria e a nota "de/para de categorias VTEX, mirando o padrão VALID_SLUGS-from-RAW".
- `.planning/REQUIREMENTS.md` — COMP-06 (Hugo Boss por categoria), COMP-07 (Zara, spike-gated), COMP-08 (Lacoste fora — contexto), e "Out of Scope".
- `.planning/PROJECT.md` — milestone v4.0, fronteiras públicas de catálogo/preço, envelope anti-bot.

### Fases anteriores (padrões a seguir)
- `.planning/phases/36-onboarding-das-marcas-concorrentes-restantes-lacoste-anti-bo/36-CONTEXT.md` — envelope anti-bot travado (D-02/D-03), padrão de gate GO/NO-GO, contrato de dados (D-07), e confirmação de que Hugo Boss é VTEX ativa e Lacoste segue inativa.
- `.planning/spikes/008-lacoste-antibot-zara-recheck/REPORT.md` — recheck da Zara: veredito `PROMOVER_REQUISITO_FUTURO` (zara.com/br devolveu 200 + marcador JSON-LD de produto via stealth, sem proxy pago). É a evidência-base para o spike 010.
- `.planning/spikes/003-sfcc-inditex-storefront-mvp/REPORT.md` — HTTP direto 403 para SFCC e Zara/Inditex (ponto de partida do que NÃO funciona).
- `.planning/phases/32-engine-wake-commerce-richards/32-CONTEXT.md` — padrão de gate GO/NO-GO antes de engine completo.

### Código a alterar/reusar
- `backend/services/category_mapping.py` — de/para canônico; `resolve_category_for_brands` e `get_category_preview` já fazem fallback nos `brand.mappings` dinâmicos (D-01/D-02).
- `backend/services/engines/vtex_engine.py` — `discover_categories` → `VtexApiClient.fetch_categories(domain)` → `_flatten_vtex_tree` (base da descoberta da árvore RAW, D-03).
- `backend/data/brands.json` — Hugo Boss: `engine="vtex"`, `is_active=true`, `mappings: []` (a popular). Zara não cadastrada (só em GO).
- `backend/scripts/onboard_vtex_brands.py` — possível ponto de reuso para o script de descoberta-e-persistência do de/para (D-04).
- `backend/data/monitored_categories.json` — entradas de categoria monitorada (`{id, url, brand, status, last_scraped_at}`) para o scheduler de 10 min.
- `backend/api/routes_category.py` — endpoints de categoria (preview/scan).
- `backend/core/browser_manager.py` + `playwright-stealth` — base do spike público da Zara (D-06).
- `backend/services/engines/factory.py` — `EngineFactory`/`_search_one`; `BrandSearchResult.error` como canal de falha (em GO da Zara).
- `backend/core/models.py` — `DynamicBrand` (+ `mappings`), `SearchProductResult`, `BrandSearchResult`, `RawProductBronze`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `VtexEngine.discover_categories` já busca e achata a árvore de categorias VTEX da marca (`VtexApiClient.fetch_categories` → `_flatten_vtex_tree`) — é a fonte para auto-descoberta do de/para da Hugo Boss (D-03).
- `category_mapping.py` já resolve `brand.mappings` dinâmicos como fallback do índice hardcoded — popular `mappings` da Hugo Boss já a faz aparecer no select e na varredura, sem mudar o código de mapeamento (D-01).
- `playwright-stealth` já é dependência (usada em `amazon_engine.py` e no spike 008) — reusável no spike 010 sem novo pacote.
- Padrão de spike: `.planning/spikes/NNN-*/` com `experiment.py` + `REPORT.md` e veredito explícito (ex.: 007 Wake, 008 Lacoste/Zara).

### Established Patterns
- Engine completo só após gate GO quando o caminho externo é incerto (fases 32/36).
- Marcas concorrentes adicionadas usam `brand.mappings` dinâmicos; o `_RAW_CATEGORIES` hardcoded é só das marcas da casa (aramis/reserva/tommy).
- `list_brands(active_only=True)` é o chokepoint — a Zara só entra na busca geral após onboard ativo (GO).
- Testes herméticos mockam browser/fetchers; rede ao vivo fica como spike/evidência manual.

### Integration Points
- Hugo Boss: popular `mappings` em `brands.json` → categoria aparece no preview/scan VTEX existente; validar `scan` por categoria retorna produtos reais e o scheduler de 10 min inclui a HB sem falso positivo.
- Zara (só GO): novo engine injetado na `EngineFactory`, contrato `SearchProductResult` preservado, frete `None` (catálogo+preço apenas).

</code_context>

<specifics>
## Specific Ideas

- Hugo Boss: `brand_key="hugoboss"`, `domain="www.hugoboss.com.br"`, `engine="vtex"`, `is_active=true`, `mappings: []` (estado atual — o gap a fechar).
- Slugs canônicos existentes hoje: `camisas`, `polos`, `camisetas`, `calcas`, `bermudas`, `jaquetas`, `infantil`.
- Zara: spike 008 obteve `https://www.zara.com/br/` → 200 (1.7MB) com `jsonld_product_marker` via stealth; busca `?searchTerm=...&section=...` → 200. Caminho HTTP direto = 403 (spike 003).
- Spike alvo: `.planning/spikes/010-zara-product-price/REPORT.md` (caminho citado no roadmap).
- Query padrão do gate Zara: `camiseta` / `calça`.

</specifics>

<deferred>
## Deferred Ideas

- Engine Zara/Inditex em fase própria — **não** é o caminho escolhido (D-08: construir na Phase 39 em GO); manter como alternativa só se o spike revelar escopo grande demais para a fase.
- Frete/checkout/estoque por CEP para Zara/Inditex — fora de escopo (catálogo + preço público apenas).
- Proxy residencial / pago / CAPTCHA solving / browser headed para Zara — requer aprovação explícita posterior (D-06).
- Monitoramento Hugo Boss além das categorias mapeadas (ex.: busca por termo, sortimento) — coberto por outras fases (44/45).

### Reviewed Todos (not folded)
- `reforcar-discriminacao-modelo.md` — sobre precisão de discriminação de modelo (model-words + visual como desempate / NLP); não se relaciona a cobertura de categorias Hugo Boss nem ao spike Zara. (Já revisado e não incorporado na Phase 36.)
- `cap-search-history-list.md` — sobre paginação/limite da lista de histórico de busca; pertence ao eixo de UX (Phase 38/40), não a esta fase. (Já revisado e não incorporado na Phase 36.)

</deferred>

---

*Phase: 39-Cobertura de Marcas — Hugo Boss & Zara*
*Context gathered: 2026-06-26*
