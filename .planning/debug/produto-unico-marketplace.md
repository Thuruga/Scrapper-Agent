---
status: resolved
trigger: "Por que o monitoramento de um produto unico nos marketplaces nao funciona?"
created: 2026-06-30
updated: 2026-06-30
resolution: resolved (2 bugs corrigidos e verificados via pytest)
---

# Debug Session: produto-unico-marketplace

## Symptoms
- expected: Monitorar um produto único e receber os resultados dele nos marketplaces (mercado_livre, netshoes, amazon, etc.)
- actual: Lista vazia / nada — a busca roda mas não retorna nenhum resultado de marketplace para o produto
- timeline: Nunca funcionou
- errors: React warning repetido no console — "Encountered two children with the same key, `mercado_livre`" (idem `netshoes`, `amazon`). Chaves duplicadas ao renderizar a lista de marketplaces. Ruídos não relacionados: 404 de favicon (buckmanbck.com.br), "Tracking Prevention blocked access to storage".
- reproduction: Acionar o monitoramento de um produto único nos marketplaces no frontend.

## Current Focus
- hypothesis: CONFIRMADA — routes_search.py adiciona ["mercado_livre","netshoes","amazon"] via .extend() a uma lista que JÁ contém essas marcas (agora entradas reais e ativas em brands.json desde Plan 04/D-10). Isso duplica cada marketplace na lista de marcas-alvo quando nenhum filtro de marca é enviado.
- test: Reproduzido em Python — list_brands(active_only=True) já inclui mercado_livre/netshoes/amazon; após .extend(), Counter mostra cada um com contagem 2.
- expecting: Duplicação confirma os DOIS sintomas — chaves React duplicadas (render duas vezes por brand_key) e resultados vazios/instáveis (mesmo engine anti-bot rodado 2x em paralelo dispara bloqueio; e o .find() no front pega o PRIMEIRO BrandSearchResult, que pode ser o vazio/erro).
- next_action: Aplicar fix (continue → find_and_fix) com refinamentos do especialista Python e rodar pytest.
- reasoning_checkpoint:
    hypothesis: "routes_search.py duplica as 3 brand_keys de marketplace porque faz .extend() de uma lista que já as contém (brands.json virou fonte única que já as inclui), causando execução dupla do engine e brand_key repetida no resultado."
    confirming_evidence:
      - "Reproduzido: Counter(all_brands) => {'mercado_livre':2,'netshoes':2,'amazon':2} (saída do script Python)."
      - "brands.json L535-579: mercado_livre/netshoes/amazon são entradas reais com is_active=true."
      - "factory.py L87-92 documenta que list_brands(active_only=True) já inclui os 3 marketplaces (Plan 04/D-10) — o .extend() ficou redundante."
      - "App.tsx L1607-1615: render mapeia brandKeysToShow com key={brandKey}; L1609 usa .find() pegando só o primeiro resultado por brand_key."
    falsification_test: "Se removendo o .extend() (ou deduplicando target_brands) o warning de chave duplicada e os resultados vazios desaparecerem na busca sem filtro de marca, a hipótese se mantém. Se o warning persistir, a causa está em outro lugar."
    fix_rationale: "Remover o .extend() redundante (ou deduplicar target_brands preservando ordem) elimina a execução dupla na raiz — corrige simultaneamente a chave React duplicada e a instabilidade/vazio dos resultados. Fix de front (key composta) só mascararia o sintoma sem parar a busca dupla."
    blind_spots: "Não executei a busca end-to-end nos engines reais (rede/anti-bot) para medir quão frequentemente o resultado fica vazio vs. apenas duplicado. A duplicação de execução é certa; o grau de 'vazio' depende do comportamento anti-bot ao rodar 2x em paralelo."

## Evidence
- timestamp: 2026-06-30
  checked: backend/services/cross_marketplace_service.py (fluxo /search/cross-marketplace, por SKU)
  found: Saída usa display names ("Mercado Livre"/"Netshoes"/"Amazon") como campo marketplace; o render do front desse fluxo (App.tsx L2249/L2259) usa key={marketplace} com display name — chaves ÚNICAS.
  implication: O warning de chave duplicada com a forma 'mercado_livre' (underscore) NÃO vem do fluxo cross-marketplace; vem do fluxo multi-brand /search que usa brand_key.

- timestamp: 2026-06-30
  checked: backend/api/routes_search.py L185-186 (POST /search), L279-280 (GET /search), L317-318 (POST /search/export)
  found: Os três handlers fazem all_brands = [b.brand_key for b in list_brands(active_only=True)] e em seguida all_brands.extend(["mercado_livre","netshoes","amazon"]).
  implication: Quando request.brands é None (usuário não filtra marca → "Buscando em todas as marcas ativas"), target_brands = all_brands, que contém marketplaces duplicados.

- timestamp: 2026-06-30
  checked: backend/data/brands.json L535-579
  found: mercado_livre, netshoes e amazon são entradas REAIS com is_active=true.
  implication: list_brands(active_only=True) já retorna os 3 marketplaces — o .extend() é redundante e gera duplicata.

- timestamp: 2026-06-30
  checked: backend/services/engines/factory.py L65-113 (search_all_brands) e L87-92 (comentário)
  found: search_all_brands roda um _search_one por entrada de target_brands em paralelo (asyncio.gather). O comentário L87-92 documenta que list_brands já inclui os 3 marketplaces (Plan 04/D-10).
  implication: Com target_brands duplicado, cada engine de marketplace roda DUAS vezes em paralelo → dois BrandSearchResult com o mesmo brand_key.

- timestamp: 2026-06-30
  checked: backend/services/engines/{mercado_livre,netshoes,amazon}_engine.py
  found: get_engine (factory L22-28) normaliza 'mercado_livre' → 'mercadolivre' e retorna MercadoLivreEngine() com brand_key default = "mercado_livre". O BrandSearchResult retornado carrega brand_key="mercado_livre" (idem netshoes/amazon).
  implication: Os dois resultados duplicados têm brand_key idêntico "mercado_livre" — origem direta do warning React.

- timestamp: 2026-06-30
  checked: frontend/src/App.tsx L1577-1620
  found: brandKeysToShow = results.results.map(r => r.brand_key) quando não há filtro; render .map(brandKey => <div key={brandKey}>); L1609 brandRes = results.results.find(r => r.brand_key === brandKey).
  implication: (1) brand_key repetido → key React duplicada (warning). (2) .find() pega só o PRIMEIRO BrandSearchResult do brand_key — se a primeira das duas execuções vier vazia/erro (provável sob anti-bot ao rodar 2x), a coluna renderiza vazia mesmo que a outra tenha resultados.

- timestamp: 2026-06-30
  checked: frontend/src/App.tsx L1260, L1286
  found: brands: selectedBrands.length > 0 ? selectedBrands : undefined.
  implication: No caminho default (sem seleção, "todas as marcas ativas") o front envia brands=undefined → backend entra no ramo all_brands duplicado. Confirma que o sintoma aparece justamente na busca de produto sem filtro de marca.

- timestamp: 2026-06-30
  checked: Reprodução Python (script ad-hoc)
  found: "active brand_keys" inclui mercado_livre/netshoes/amazon; após .extend(), Counter => {'mercado_livre':2,'netshoes':2,'amazon':2}.
  implication: Duplicação PROVADA empiricamente, não inferida.

- timestamp: 2026-06-30 (BUG 2 — fluxo por SKU "produto único")
  checked: backend/services/cross_marketplace_service.py L21-25 (_ENGINE_MAP) e L177-189 (_active_engines)
  found: _ENGINE_MAP usa a chave "mercadolivre" (SEM underscore), mas _active_engines faz `engine_key in active_keys` SEM normalização, e active_keys = {b.brand_key} contém "mercado_livre" (COM underscore, conforme brands.json). "mercadolivre" não está em {"mercado_livre",...}.
  implication: No fluxo POST /search/cross-marketplace (compare_product → _fetch_all_engines → _active_engines), o Mercado Livre é SILENCIOSAMENTE excluído de TODA busca por SKU. Só Netshoes e Amazon rodam. Esse é o fluxo "monitorar um produto único nos marketplaces".

- timestamp: 2026-06-30 (repro empírica BUG 2)
  checked: Script Python sobre brands.json
  found: engine_key 'mercadolivre' in active brand_keys? False | 'netshoes'? True | 'amazon'? True → engines ativados no cross-marketplace = ['netshoes','amazon'].
  implication: Mercado Livre nunca é consultado na busca por SKU. PROVADO empiricamente.

- timestamp: 2026-06-30 (por que o BUG 2 nunca foi pego)
  checked: backend/tests/test_cross_marketplace_service.py L377 vs backend/tests/test_brand_active.py L178-182
  found: O teste de _active_engines cria o fake do ML com brand_key="mercadolivre" (SEM underscore = nome do engine), enquanto test_brand_active documenta corretamente o brand_key real como "mercado_livre" (COM underscore). O teste é auto-consistente mas não reflete os dados de produção.
  implication: _active_engines passa no teste (mercadolivre==mercadolivre) e falha em produção (mercadolivre != mercado_livre). Gap de fixture mascarou o bug.

## Eliminated
- hypothesis: O warning de chave duplicada vem do fluxo cross-marketplace por SKU (POST /search/cross-marketplace).
  evidence: Esse fluxo usa display names ("Mercado Livre") como campo marketplace e key={marketplace} no render (App.tsx L2249/L2259) — chaves únicas. O warning cita a forma 'mercado_livre' (underscore = brand_key), que só aparece no render multi-brand /search (key={brandKey}).
  timestamp: 2026-06-30
- hypothesis: Há uma única causa raiz para os dois sintomas.
  evidence: São DOIS bugs independentes em DOIS fluxos distintos. BUG 1 (.extend duplicado em routes_search) → warning de chave React no fluxo multi-brand /search. BUG 2 (_ENGINE_MAP "mercadolivre" vs brand_key "mercado_livre") → ML ausente no fluxo por SKU /search/cross-marketplace ("produto único"). Compartilham o mesmo TEMA (migração dos marketplaces para brands.json em Plan 04/D-10 deixou dois caminhos legados), mas a correção exige dois ajustes distintos.
  timestamp: 2026-06-30

## Specialist Review
- reviewer: python (best-practices code review)
- timestamp: 2026-06-30
- verdict: AMBOS root causes corretos; AMBAS as direções de fix corretas, com 3 refinamentos:
  - BUG 1: aplicar como REMOÇÃO do .extend() **mais** dedupe ordenado (dict.fromkeys), NÃO dedupe sozinho.
    Dedupe sozinho deixaria a lista hardcoded como 2ª fonte de verdade que re-quebra ao desativar um
    marketplace (D-11/T-40-06). Idiomático: `target_brands = list(dict.fromkeys(b.lower() for b in target_brands))`
    (preserva ordem das colunas no front; set embaralharia). No handler GET (L279-280), o brands_searched
    é montado de list_brands+extend enquanto search_all_brands roda com brands=None → metadata mais longa
    que o resultado; remover o .extend() lá também realinha a metadata.
  - BUG 2: NÃO inline `.replace("_","")`. Reusar a convenção canônica do factory.py L22
    (`.lower().replace(" ", "").replace("_", "")` — também tira espaços). Extrair helper único
    `normalize_brand_key(key)` importado por ambos os módulos (util ou staticmethod em EngineFactory),
    refatorar factory.py L22 para usá-lo, e usar em _active_engines:
    `active_keys = {normalize_brand_key(b.brand_key) for b in active_brands}`. Mata a divergência entre
    os ~3 call sites (factory L22, chaves de _ENGINE_MAP, _active_engines).
  - TESTES: corrigir AMBAS as fixtures. test_inactive_marketplace_excluded L376 → brand_key="mercado_livre".
    test_active_marketplace_included L449-457 gera fixtures de _ENGINE_MAP.items() (brand_key="mercadolivre")
    → deve usar o brand_key real "mercado_livre" e ter `assert "Mercado Livre" in active` para fixar a regressão.
    O campo engine=key é incidental (_active_engines chaveia por brand_key, não engine).

## Resolution
root_cause: |
  DOIS bugs independentes, ambos resíduos da migração dos marketplaces para brands.json (Plan 04/D-10).

  BUG 1 (fluxo multi-brand POST /search — causa o WARNING de chave React no console):
  routes_search.py faz .extend(["mercado_livre","netshoes","amazon"]) sobre uma lista que JÁ contém
  essas marcas (list_brands(active_only=True) as inclui agora). Resultado: cada marketplace duplicado
  na lista de marcas-alvo quando brands=None → search_all_brands roda o engine 2x → dois
  BrandSearchResult com brand_key idêntico → React "two children with the same key,
  mercado_livre/netshoes/amazon" (render keyed por brand_key) + coluna possivelmente vazia (.find pega
  o primeiro dos dois, que sob anti-bot pode vir vazio).

  BUG 2 (fluxo por SKU POST /search/cross-marketplace — é o "monitoramento de PRODUTO ÚNICO"):
  _ENGINE_MAP usa a chave "mercadolivre" (sem underscore) e _active_engines compara
  `engine_key in active_keys` SEM normalizar, enquanto o brand_key real em brands.json é
  "mercado_livre" (com underscore). Logo o Mercado Livre é SILENCIOSAMENTE excluído de TODA busca por
  SKU — só Netshoes e Amazon rodam. Se o produto procurado está no ML (ou NS/AMZ não retornam), o
  resultado parece vazio. Nunca foi pego porque o teste usa brand_key="mercadolivre" (sem underscore).
fix: |
  BUG 1 (backend): remover o .extend(["mercado_livre","netshoes","amazon"]) das três rotas em
  routes_search.py (L185-186, L279-280, L317-318) — list_brands(active_only=True) já as inclui. Adicionar
  dedupe ordenado como salvaguarda: target_brands = list(dict.fromkeys(b.lower() for b in target_brands)).
  No GET handler realinhar brands_searched (remover o .extend lá também).
  BUG 2 (backend): extrair helper normalize_brand_key reutilizado por factory.py (L22) e por
  _active_engines (cross_marketplace_service.py L177-189): active_keys = {normalize_brand_key(b.brand_key)
  for b in active_brands} para que "mercado_livre" → "mercadolivre" case com a chave do _ENGINE_MAP.
  Corrigir AMBAS as fixtures de teste (test_cross_marketplace_service.py L376 e L449-457) para
  brand_key="mercado_livre" (dado de produção), de modo que o teste reflita a realidade e pegue a regressão.
verification: |
  Fix aplicado e verificado via pytest (repo backend/).
  - tests/test_cross_marketplace_service.py: 9 passed (inclui test_inactive_marketplace_excluded
    e test_active_marketplace_included com fixtures corrigidas para brand_key="mercado_livre" +
    assert "Mercado Livre" in active fixando a regressão do BUG 2).
  - Suítes relacionadas (test_brand_active, test_search_history_comparative,
    test_search_shipping_contract, test_export_cross_marketplace): 47 passed no total.
  - Sanity empírico contra brands.json real:
    * BUG 2: cross_marketplace_service._active_engines() agora retorna
      ['Amazon', 'Mercado Livre', 'Netshoes'] — ML deixou de ser silenciosamente excluído.
    * BUG 1: target_brands após dedupe (dict.fromkeys) não tem duplicatas e preserva ordem.
    * normalize_brand_key('mercado_livre') == 'mercadolivre'; factory.get_engine('mercado_livre')
      e get_engine('Mercado Livre') resolvem MercadoLivreEngine.
  - Nota: test_phase44_routes.py::test_stock_depth_route_does_not_involve_search_routes falha SOMENTE
    quando o pytest roda de dentro de backend/ (usa Path relativo "backend/api/routes_search.py");
    passa a partir da raiz do repo. Falha pré-existente de cwd, NÃO causada por este fix.
files_changed:
  - backend/services/engines/brand_key_utils.py (NOVO — helper normalize_brand_key, fonte única)
  - backend/services/engines/factory.py (get_engine L22 reutiliza normalize_brand_key)
  - backend/services/cross_marketplace_service.py (_active_engines normaliza active_keys; BUG 2)
  - backend/api/routes_search.py (remove .extend redundante nos 3 handlers; dedupe ordenado em POST/export; realinha brands_searched no GET; BUG 1)
  - backend/tests/test_cross_marketplace_service.py (fixtures com brand_key de produção "mercado_livre" + assert de regressão)
