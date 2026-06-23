---
phase: quick-260615-dkc
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - services/engines/seller_extraction.py
  - services/engines/mercado_livre_engine.py
  - services/engines/amazon_engine.py
  - services/engines/netshoes_engine.py
  - services/cross_marketplace_service.py
  - tests/test_seller_extraction.py
autonomous: true
requirements: [SELLER-ROBUST-01]

must_haves:
  truths:
    - "Quando a PDP expõe uma lojista terceira, o card mostra o nome dela (não o do marketplace)"
    - "Quando a PDP NÃO expõe lojista terceira / falha / dá timeout, o card mostra o nome do marketplace como fallback"
    - "Um seller real obtido na listagem não é sobrescrito por um default de marketplace vindo da PDP"
    - "Nenhum produto sem lojista é descartado; nenhum rótulo neutro ('Vendedor não identificado') é introduzido"
    - "tests/test_netshoes_engine.py continua verde sem alteração de asserções"
  artifacts:
    - path: "services/engines/seller_extraction.py"
      provides: "Constantes de seller-default por marketplace + helper is_marketplace_default + extratores puros de seller (HTML/soup) para ML e Amazon"
    - path: "tests/test_seller_extraction.py"
      provides: "Cobertura offline (fixtures HTML/state) da extração robusta de seller para ML, Amazon e do helper de precedência"
  key_links:
    - from: "services/cross_marketplace_service.py::_enrich_pdp_and_shipping"
      to: "services/engines/seller_extraction.py::is_marketplace_default"
      via: "precedência seller listagem vs PDP"
      pattern: "is_marketplace_default"
    - from: "services/engines/mercado_livre_engine.py"
      to: "services/engines/seller_extraction.py"
      via: "import + chamada do extrator puro de seller"
      pattern: "from services.engines.seller_extraction import"
    - from: "services/engines/amazon_engine.py"
      to: "services/engines/seller_extraction.py"
      via: "import + chamada do extrator puro de seller"
      pattern: "from services.engines.seller_extraction import"
---

<objective>
Tornar a extração do vendedor (lojista terceira) mais robusta nos três marketplaces (Mercado Livre, Amazon, Netshoes), de modo que TODO card de produto exiba o nome da lojista real sempre que ela existir na PDP, mantendo o nome do marketplace apenas como fallback quando a lojista não é exposta (venda 1P, extração falha ou timeout).

Purpose: Hoje seletores frágeis e desatualizados (ML/Amazon mudam CSS com frequência) fazem a PDP cair no default do marketplace com frequência; além disso o enriquecimento via PDP pode sobrescrever um seller real já obtido na listagem com o default do marketplace. O resultado é cards mostrando "Amazon"/"Mercado Livre" mesmo quando há lojista terceira.

Output:
- Novo módulo `services/engines/seller_extraction.py` com: constantes de default por marketplace, helper `is_marketplace_default`, e extratores PUROS de seller (recebem HTML/soup, retornam string ou None) para ML e Amazon.
- Engines ML e Amazon passam a usar os extratores puros com mais seletores/fallbacks (incluindo estado JSON embutido).
- `_enrich_pdp_and_shipping` com regra de precedência correta (PDP só sobrescreve quando traz seller real) e logging mais visível das falhas, sem quebrar o contrato.
- Testes offline cobrindo a extração robusta e a precedência.

Decisão TRAVADA respeitada: fallback = nome do marketplace; NÃO introduzir rótulo neutro; NÃO descartar produtos sem lojista.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/STATE.md

@services/cross_marketplace_service.py
@services/engines/mercado_livre_engine.py
@services/engines/amazon_engine.py
@services/engines/netshoes_engine.py
@tests/test_netshoes_engine.py
@tests/test_cross_marketplace_service.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Criar módulo seller_extraction com defaults, helper de precedência e extratores puros (ML + Amazon)</name>
  <files>services/engines/seller_extraction.py, tests/test_seller_extraction.py</files>
  <behavior>
    Helper `is_marketplace_default(seller, marketplace)`:
    - Retorna True quando seller é None, vazio, ou igual (case/acento-insensitive, trim) ao default do marketplace.
    - Retorna True também para os defaults conhecidos de QUALQUER marketplace (ex.: "Amazon", "Mercado Livre", "Netshoes") — para que um default acidental nunca seja tratado como lojista real.
    - Retorna False para uma lojista terceira real (ex.: "Shoestime", "Loja XPTO").

    Constantes: `MARKETPLACE_DEFAULT_SELLER` = mapa { "Mercado Livre": "Mercado Livre", "Amazon": "Amazon", "Netshoes": "Netshoes" } e `ALL_DEFAULT_SELLERS` derivado (set normalizado).

    Extrator ML `parse_ml_seller_from_html(html) -> Optional[str]`:
    - Usa BeautifulSoup. Tenta, em ordem, múltiplos seletores: `.ui-pdp-seller__link-trigger span`, `.ui-pdp-seller__link-trigger-button span`, `.ui-pdp-seller__header__title`, `.ui-pdp-action-modal__link span`, e o link de loja oficial `a[href*="/loja/"]` / `a[href*="tienda"]`.
    - Para o título de seller, remove (regex, case-insensitive) os prefixos "Vendido por", "por", "Loja oficial".
    - Fallback de estado JSON embutido: procura no HTML, via regex, chaves `"official_store_name"`, `"seller":{...,"nickname"|"name"...}` ou `"store_name"` e usa o primeiro valor não-vazio.
    - Retorna None quando nenhum sinal de seller real é encontrado (NÃO retorna o default aqui — quem decide o fallback é o chamador).
    - Nunca retorna string que seja `is_marketplace_default`.

    Extrator Amazon `parse_amazon_seller_from_html(html) -> Optional[str]`:
    - Usa BeautifulSoup. Tenta, em ordem: `#sellerProfileTriggerId`, `#merchant-info a`, texto após "Vendido por" dentro de `#merchant-info`, `#tabular-buybox` (string "Vendido por" → irmão), e o bloco moderno `#offer-display-features`/`[data-csa-c-content-id*="desktop-fakeQuickView"]` ou `.offer-display-feature-text-message`.
    - Limpa prefixos "Vendido por"/"Ships from"/"Enviado por" e espaços.
    - Retorna None quando nada encontrado; nunca retorna string `is_marketplace_default`.

    Casos de teste (offline, fixtures HTML inline — sem rede):
    - ML: HTML com `.ui-pdp-seller__link-trigger span` → retorna o nome da loja.
    - ML: HTML só com `.ui-pdp-seller__header__title` contendo "Vendido por Loja X" → "Loja X".
    - ML: HTML sem qualquer seletor mas com `"official_store_name":"Loja Y"` no JSON → "Loja Y".
    - ML: HTML de venda direta (sem seller terceiro) → None.
    - Amazon: `#sellerProfileTriggerId` → nome da loja.
    - Amazon: só `#merchant-info` com "Vendido por Loja Z" → "Loja Z".
    - Amazon: HTML sem seller terceiro → None.
    - `is_marketplace_default`: "Amazon"/"amazon"/" Mercado Livre "/None/"" → True; "Shoestime" → False.
  </behavior>
  <action>
    Criar `services/engines/seller_extraction.py` como módulo puro (sem I/O de rede, sem Playwright): apenas BeautifulSoup + regex sobre strings já obtidas. Definir `MARKETPLACE_DEFAULT_SELLER`, `ALL_DEFAULT_SELLERS` (normalizado via unicodedata NFD + lower + strip), `is_marketplace_default(seller, marketplace=None)`, `parse_ml_seller_from_html(html)` e `parse_amazon_seller_from_html(html)`. Reaproveitar a normalização de acentos no mesmo estilo de `_slugify` em mercado_livre_engine.py (NFD + ascii ignore + lower). Os extratores DEVEM filtrar qualquer resultado que seja `is_marketplace_default` antes de retornar (retornando None nesse caso). NÃO inlinar HTML real de produção; usar fragmentos sintéticos mínimos nos testes. Criar `tests/test_seller_extraction.py` seguindo o estilo de tests/test_netshoes_engine.py (funções `test_*`, asserções diretas, sem pytest-asyncio, sem rede). Escrever os testes ANTES da implementação (RED → GREEN).
  </action>
  <verify>
    <automated>python -m pytest tests/test_seller_extraction.py -q</automated>
  </verify>
  <done>tests/test_seller_extraction.py passa; o módulo expõe is_marketplace_default, parse_ml_seller_from_html, parse_amazon_seller_from_html e as constantes de default, todos sem dependência de rede.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Ligar extratores robustos nas engines ML e Amazon (curl_cffi + Playwright), preservando fallback do marketplace</name>
  <files>services/engines/mercado_livre_engine.py, services/engines/amazon_engine.py, tests/test_seller_extraction.py</files>
  <behavior>
    Mercado Livre:
    - `get_product_details` (curl_cffi, ~L118-141): após obter `response.text`, chama `parse_ml_seller_from_html(response.text)`. Se retornar um nome real → `seller = nome`; senão `seller = "Mercado Livre"` (default). Mantém o gate atual `"ui-pdp-seller" in response.text` apenas como sinal de PDP carregada, mas NÃO impede o fallback de estado JSON.
    - `_run_playwright_pdp` (~L99-113): substitui os dois seletores inline pela chamada a `parse_ml_seller_from_html(html)`; fallback "Mercado Livre".
    - A extração da LISTAGEM (`_extract_product_array` ~L216-217, JSON-LD ~L260-261, HTML ~L322-328) permanece como está (já lê seller real quando disponível); default continua "Mercado Livre".

    Amazon:
    - `get_product_details` (~L61-90): substitui o bloco de seletores inline pela chamada a `parse_amazon_seller_from_html(response.text)`. Se nome real → usa; senão `seller = "Amazon"`.
    - Listagem (`_parse_html` ~L132): permanece "Amazon" (Amazon não expõe seller na SERP) — sem mudança.

    Comportamento observável preservado:
    - PDP com lojista terceira → seller = lojista.
    - PDP sem lojista / parse vazio → seller = nome do marketplace (fallback travado).
    - Nenhuma exceção nova propagada; erro de rede continua capturado nos try/except existentes.

    Testes adicionais (offline) em tests/test_seller_extraction.py: chamar diretamente os extratores com fragmentos que exercitem os seletores novos de cada engine (já coberto na Task 1; aqui apenas reforçar os seletores Playwright/curl compartilhados se algum caso novo surgir). Não criar testes que façam rede.
  </action>
  <action>
    Importar `from services.engines.seller_extraction import parse_ml_seller_from_html, parse_amazon_seller_from_html, MARKETPLACE_DEFAULT_SELLER` no topo de cada engine. Em ML, trocar os dois blocos duplicados de seletores (em `get_product_details` e `_run_playwright_pdp`) por: `seller = parse_ml_seller_from_html(html) or MARKETPLACE_DEFAULT_SELLER["Mercado Livre"]`. Em Amazon, trocar o bloco de seletores de `get_product_details` por `seller = parse_amazon_seller_from_html(response.text) or MARKETPLACE_DEFAULT_SELLER["Amazon"]`. NÃO remover o gate `"ui-pdp-seller" in response.text` do ML, mas garantir que, quando ausente, o método ainda tente o Playwright (comportamento atual) — não introduzir regressão no fluxo de fallback Playwright. Remover imports locais de `re`/`BeautifulSoup` que ficarem órfãos dentro desses métodos. Netshoes não muda (já robusto e coberto).
  </action>
  <verify>
    <automated>python -m pytest tests/test_seller_extraction.py tests/test_netshoes_engine.py -q</automated>
  </verify>
  <done>ML e Amazon usam os extratores puros; o módulo importa sem erro (`python -c "import services.engines.mercado_livre_engine, services.engines.amazon_engine"`); test_netshoes_engine.py continua verde; extração de seller cai no default do marketplace apenas quando não há lojista real.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Corrigir precedência seller listagem vs PDP no enriquecimento + logging visível das falhas</name>
  <files>services/cross_marketplace_service.py, tests/test_cross_marketplace_service.py</files>
  <behavior>
    Em `_enrich_pdp_and_shipping` (~L444-479), substituir a sobrescrita incondicional `if details.get("seller"): p["seller"] = details["seller"]` por regra de precedência:
    - Seja `pdp_seller = details.get("seller")` e `current = p.get("seller")`.
    - Sobrescreve `p["seller"] = pdp_seller` SOMENTE quando `pdp_seller` é um seller REAL (não `is_marketplace_default(pdp_seller, plat)`).
    - Caso a PDP retorne o default do marketplace MAS a listagem já tinha um seller real (não-default), MANTÉM o da listagem.
    - Caso ambos sejam default, mantém o default (fallback travado — card mostra o marketplace).
    - NUNCA grava rótulo neutro; NUNCA descarta o produto.

    O `except` da PDP (~L464-465) passa de `logger.debug` para `logger.warning` (mais visível), mantendo a captura (não propaga, não quebra o pipeline). O `except` do frete permanece como está.

    Casos de teste (offline, estilo FakeEngine de tests/test_cross_marketplace_service.py — sem rede/IA):
    - PDP retorna lojista real "Shoestime" e listagem tinha "Amazon" → resultado final `seller == "Shoestime"`.
    - PDP retorna "Amazon" (default) e listagem tinha lojista real "Loja Real" → resultado final `seller == "Loja Real"` (não regride para o default).
    - PDP lança exceção → seller permanece o da listagem; pipeline não quebra (já coberto pelo caso 3 existente — estender asserção de seller).
    - PDP retorna lojista real e listagem tinha default → seller final = o da PDP (caso comum, garante que a melhoria funciona).
  </behavior>
  <action>
    Importar `from services.engines.seller_extraction import is_marketplace_default` em cross_marketplace_service.py. Em `_enrich_pdp_and_shipping`, dentro do `try`, aplicar a regra de precedência descrita usando `plat` (já disponível como `p["plataforma"]`). Trocar o `logger.debug` do `except` da PDP por `logger.warning`. Adicionar/estender casos em tests/test_cross_marketplace_service.py usando o `FakeEngine` e `_prod` já existentes (passar `details_by_url` com seller real e/ou default; verificar `seller` em `result["results"]`). Reaproveitar `_pin_settings` e os monkeypatches de nlp/brand já existentes no arquivo. NÃO alterar asserções dos casos existentes além de, se necessário, adicionar a verificação de `seller` no caso de exceção de motor. Escrever as asserções dos novos casos ANTES da mudança em _enrich_pdp_and_shipping (RED → GREEN).
  </action>
  <verify>
    <automated>python -m pytest tests/test_cross_marketplace_service.py tests/test_seller_extraction.py tests/test_netshoes_engine.py -q</automated>
  </verify>
  <done>PDP só sobrescreve o seller da listagem quando traz lojista real; seller real da listagem nunca regride para o default do marketplace; falhas de PDP logam em warning; todos os testes citados verdes.</done>
</task>

</tasks>

<verification>
- Suite alvo verde: `python -m pytest tests/test_seller_extraction.py tests/test_cross_marketplace_service.py tests/test_netshoes_engine.py -q`
- Suite completa sem regressão: `python -m pytest -q`
- Imports sãos: `python -c "import services.engines.mercado_livre_engine, services.engines.amazon_engine, services.engines.netshoes_engine, services.cross_marketplace_service"`
- Sem rótulo neutro introduzido: grep não encontra "Vendedor não identificado" / "não identificado" nos arquivos modificados.
</verification>

<success_criteria>
- Cards exibem a lojista terceira real sempre que a PDP a expõe (ML, Amazon, Netshoes).
- Quando a PDP não expõe lojista (1P), falha ou dá timeout, o card exibe o nome do marketplace como fallback (decisão travada).
- Seller real obtido na listagem nunca é sobrescrito por um default vindo da PDP.
- Nenhum produto sem lojista é descartado; nenhum rótulo neutro foi introduzido.
- tests/test_netshoes_engine.py permanece verde sem alteração de asserções; nova cobertura offline para ML/Amazon e para a precedência.
</success_criteria>

<output>
Create `.planning/quick/260615-dkc-no-caso-todos-devem-mostrar-o-nome-da-lo/260615-dkc-SUMMARY.md` when done
</output>
