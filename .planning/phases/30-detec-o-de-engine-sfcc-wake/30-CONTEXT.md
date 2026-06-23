# Phase 30: Detecção de Engine SFCC & Wake - Context

**Gathered:** 2026-06-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Ensinar `detect_engine` (em `backend/api/routes_brands.py`) a **reconhecer e rotular** `sfcc` (Lacoste, HugoBoss) e `wake` (Richards) em vez de retornar `unknown`, de modo que `create_brand` persista essas marcas **ativas** com o engine correto — sem cair na regra D-04 (engine desconhecido → auto-desativa). Atende COMP-05.

**Apenas detecção/rotulagem.** Os engines de extração SFCC e Wake (catálogo/busca/preço) são as Phases 31 e 32 — fora do escopo aqui. Esta phase não extrai produtos, não faz checkout/frete, não confirma o GraphQL da Wake.

</domain>

<decisions>
## Implementation Decisions

### Detecção SFCC
- **D-01:** O sinal SFCC é obtido via **render da home no browser (Playwright)**, não por HTTP direto. Os spikes 003-006 provaram que HTTP direto retorna **403** para sites SFCC (Lacoste, HugoBoss) e que só o DOM renderizado expõe os sinais `demandware` (508/1729 ocorrências). Isso fica consistente com o engine browser-rendered da Phase 31.
- **D-02:** O veredito `"sfcc"` é cravado pela presença de **host de assets exclusivo** — `demandware.static` e/ou `demandware.edgesuite.net` — no HTML renderizado. Espelha o padrão já usado para VTEX (`vtexassets.com`) e Shopify (`cdn.shopify.com`) e respeita T-25-01 (somente marcador exclusivo). Escolhido sobre o path `/on/demandware.store/` (mais frágil) e sobre o substring amplo `demandware` (menos preciso).
- **D-03:** O probe SFCC deve **reaproveitar o `BrowserManager` existente** (`backend/core/browser_manager.py`), não criar infraestrutura de browser nova.
- **D-04:** Robustez: se a render falhar ou der timeout, `detect_engine` retorna `"unknown"` — **nunca crash** (espelha o padrão try/except → unknown já existente nas probes atuais).

### Detecção Wake
- **D-05:** O marcador `fbitsstatic.net` (CDN exclusivo da Wake Commerce) **basta** para rotular `"wake"`. Hoje esse ramo retorna `"unknown"` (`routes_brands.py:51-53`); a Phase 30 vira o retorno para `"wake"`. Mantém o probe HTML **antes** do VTEX HTML (D-02 / Pitfall 1 do v2.0).
- **D-06:** A confirmação empírica do fluxo GraphQL + `TCS-Access-Token` da Wake **NÃO** entra aqui — é o spike gating (Wave 0) da Phase 32. Detecção apenas rotula a plataforma; não prova que o engine funciona.

### Ordem das probes & falsos positivos (SC-4)
- **D-07:** O probe SFCC (browser) é a **última etapa** da cadeia: só dispara depois que Shopify (collections.json) → VTEX (category/tree) → HTML (Wake/VTEX/Shopify) **todas** falharem, imediatamente antes de retornar `"unknown"`. Cadastro de marca é evento raro (não hot path), então o custo de subir um browser uma vez por site realmente-unknown é aceitável.
- **D-08:** SC-4 fica protegido pela combinação **marcador exclusivo (D-02) + last-resort (D-07)**: Zara/Inditex (COMP-FUT-03, deferido) também responde 403, mas o DOM renderizado **não** tem `demandware.static` → continua `"unknown"`. A detecção nova não introduz falso positivo em VTEX/Shopify/Wake nem em plataformas proprietárias.

### EngineFactory — janela ativa-sem-engine (30→31/32)
- **D-09:** Adicionar um **guard explícito** para `sfcc`/`wake` em `EngineFactory.get_engine` (`backend/services/engines/factory.py`): falhar de forma **clara e diagnosticável** ("engine sfcc/wake ainda não disponível") em vez de cair silenciosamente no `return VTEXEngine(brand_key)` (linha 45). Motivação dupla: (a) fecha a janela em que uma marca sfcc/wake fica ativa (SC-3) mas sem engine até as Phases 31/32, evitando rodar VTEX contra domínio não-VTEX (0 produtos/erro silencioso a cada varredura); (b) corrige o fallback-pra-VTEX latente que hoje engole qualquer string de engine desconhecida.
- **D-10:** O guard cobre `sfcc` **E** `wake` e **não** pode quebrar os engines já existentes (`vtex`, `shopify`, marketplaces virtuais `mercado_livre`/`netshoes`/`amazon`). A forma exata da falha (exceção vs. resultado-vazio diagnosticável) é detalhe do planner; deve ser capturada pelo try/except de `_search_one` (`factory.py:86-88`) sem derrubar o gather.

### Testes
- **D-11:** O teste atual `backend/tests/test_engine_detection.py` mocka `SessionManager.get_session` com respostas aiohttp falsas. O caminho SFCC (browser) exige um **seam de mock novo** — mockar o `BrowserManager` / injetar um HTML-fixture renderizado contendo o marcador `demandware.static`. Os 4 cenários existentes (shopify/vtex/wake→unknown/all-fail) viram a base de regressão; acrescentar: SFCC→`sfcc`, Wake→`wake` (era `unknown`), e um caso 403-sem-`demandware`→`unknown` (anti-falso-positivo, ex.: Zara).

### Claude's Discretion
- Gatilho fino do probe SFCC: ficou decidido "sempre como última probe" (D-07). Se durante a implementação o custo de browser se mostrar relevante, o planner pode otimizar para "só quando a home der 403" — desde que preserve SC-1 (todo domínio SFCC detectado) e SC-4.
- Forma exata do guard da factory (exceção custom vs. engine sentinela que retorna erro) fica a critério do planner, respeitando D-10.
- Nomes de constantes/markers e estrutura dos novos testes seguem as convenções do repo.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requisito & Roadmap
- `.planning/ROADMAP.md` §"Phase 30: Detecção de Engine SFCC & Wake" — Goal, Depends on, 4 Success Criteria (SC-1..SC-4).
- `.planning/REQUIREMENTS.md` — COMP-05 (rotular sfcc/wake no cadastro) e COMP-02 validado (detecção `unknown` + probe Wake `fbitsstatic.net`).
- `.planning/PROJECT.md` §"Current Milestone v3.0" — escopo SFCC público e fronteiras (sem OCAPI/SCAPI, sem anti-bot bypass).

### Código a ser alterado
- `backend/api/routes_brands.py` L14-69 — `detect_engine` (cadeia de probes atual); L51-53 ramo Wake que hoje retorna `"unknown"`; L72-94 `create_brand` + regra D-04 (L85-90).
- `backend/services/engines/factory.py` L17-45 — `EngineFactory.get_engine`; L45 é o fallback-pra-VTEX a ser guardado (D-09).
- `backend/core/browser_manager.py` — infra de browser a reaproveitar no probe SFCC (D-03).
- `backend/tests/test_engine_detection.py` — testes RED de detecção; base de regressão e seam de mock (D-11).

### Spikes SFCC (evidência do caminho browser-público)
- `.planning/spikes/MANIFEST.md` — índice e veredictos dos spikes 003-006.
- `.planning/spikes/003-sfcc-inditex-storefront-mvp/REPORT.md` — HTTP direto = 403 (BLOCKED_BY_DIRECT_HTTP_403); Zara também 403 (Inditex, não SFCC).
- `.planning/spikes/004-sfcc-browser-public-probe/REPORT.md` — browser carrega Lacoste/HugoBoss e expõe sinais Demandware/SFCC (VALIDATED_FOR_SFCC_PUBLIC_BROWSER).
- `.planning/spikes/006-sfcc-live-browser-e2e-prototype/REPORT.md` — `demandware`=508 (HugoBoss) / 1729 (Lacoste) na render.

### Decisões herdadas (v2.0)
- `.planning/milestones/v2.0-ROADMAP.md` — D-01/D-02/D-03 (probe Wake antes do VTEX HTML; não assumir VTEX), D-04 (unknown → inativo), T-25-01 (marcador exclusivo + allow_redirects=False).

### Externo (Wake — para a Phase 32, não bloqueia a 30)
- `https://wakecommerce.readme.io` — fluxo GraphQL + `TCS-Access-Token` (HIGH confidence documental, NÃO testado empiricamente).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/core/browser_manager.py` — infra de browser (Playwright) já existente; o probe SFCC deve reusá-la (D-03).
- `detect_engine` (`routes_brands.py:14`) — cadeia de probes pronta; estende-se com (a) flip do retorno Wake e (b) novo passo SFCC como última probe.
- `create_brand` (`routes_brands.py:72`) — a lógica D-04 (`if saved.engine == "unknown": set_active(False)`) já garante SC-3 automaticamente: ao rotular `sfcc`/`wake`, o ramo `unknown` não dispara e a marca permanece ativa. Nenhuma mudança em `create_brand` é necessária além da detecção retornar o rótulo certo.
- `test_engine_detection.py` — padrão de mock de sessão aiohttp (`_make_mock_session`/`_make_mock_response`) reutilizável para as probes HTTP; SFCC precisa de seam adicional para o browser (D-11).

### Established Patterns
- Marcador exclusivo por plataforma: `vtexassets.com`/`vtexcommercestable.com` (VTEX), `cdn.shopify.com`/`window.shopify` (Shopify), `fbitsstatic.net` (Wake). SFCC segue o mesmo padrão com `demandware.static`/`demandware.edgesuite.net` (D-02).
- Probes em cascata com try/except → fallback `unknown` (nunca crash); `allow_redirects=False` na leitura de HTML (segurança T-25-01).
- `EngineFactory.get_engine` resolve engine por string do campo `engine` da marca; hoje só trata shopify + marketplaces virtuais e cai em VTEX por default (gap endereçado por D-09/D-10).

### Integration Points
- `EngineFactory` (`factory.py`) — novo guard sfcc/wake; ponto onde marcas ativas-sem-engine seriam roteadas hoje.
- `_search_one` (`factory.py:75-88`) — try/except que captura erros por marca sem quebrar o gather; o guard deve falhar de forma capturável aqui.
- `brand_service.list_brands(active_only=True)` — chokepoint que inclui as novas marcas ativas na busca/scheduler (relevante para o impacto do guard D-09).

</code_context>

<specifics>
## Specific Ideas

- Marcas-alvo concretas: SFCC = **Lacoste**, **HugoBoss**; Wake = **Richards** (validar que o domínio da Richards expõe `fbitsstatic.net` — research).
- Sinais SFCC observados nos spikes: hosts `demandware.static`/`demandware.edgesuite.net`, contagem alta de `demandware` no DOM (508/1729), JSON-LD `ProductGroup`/`Product`, OpenGraph de produto.
- Zara/Inditex é o caso de teste anti-falso-positivo por excelência: 403 no HTTP, mas plataforma proprietária (não SFCC) e deferida (COMP-FUT-03) → deve resolver `"unknown"`.

</specifics>

<deferred>
## Deferred Ideas

- **Confirmação GraphQL + `TCS-Access-Token` da Wake** — spike gating (Wave 0) da Phase 32, não desta phase.
- **Engine de extração SFCC** (catálogo + preço browser-rendered) — Phase 31 (COMP-03).
- **Engine de extração Wake** (GraphQL) — Phase 32 (COMP-04).
- **Zara / Inditex IOP** — COMP-FUT-03, deferido (sem caminho público validado).
- **Otimização do gatilho do probe SFCC** ("só em 403") — possível refino futuro se o custo de browser incomodar; não comprometido agora.

### Reviewed Todos (not folded)
- *"Reforçar discriminação de modelo (model-words + visual como desempate)"* — match fraco (score 0.6 por keywords genéricas "phase/marca/falsos/positivos") e **arquivo inexistente** no `.planning/todos/`. É sobre precisão da busca por SKU (discriminação de modelo), **não** sobre detecção de engine. Fora do escopo da Phase 30.

</deferred>

---

*Phase: 30-Detecção de Engine SFCC & Wake*
*Context gathered: 2026-06-23*
