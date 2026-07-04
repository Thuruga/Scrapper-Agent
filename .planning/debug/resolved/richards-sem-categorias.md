---
status: resolved
trigger: "Richards nao esta trazendo as categorias na Varredura por Categoria"
created: 2026-06-25
updated: 2026-06-25
---

# Debug Session: richards-sem-categorias

## Symptoms

- **Expected behavior:** Ao selecionar a marca Richards na "Varredura por Categoria" (Categorias por Marca), o dropdown deve listar as categorias disponíveis da marca.
- **Actual behavior:** O dropdown da Richards fica vazio — só mostra a opção placeholder "Selecione a categoria...". (Ver screenshot anexado pelo usuário.)
- **Error messages:** Nenhum erro visível (sem toast na UI, sem erro de console/rede reportado, sem stacktrace no backend reportado).
- **Timeline:** Desde o onboarding da Richards — nunca trouxe categorias. Richards usa engine `wake` (cadastrada ao vivo em 2026-06-25, commit adb9635).
- **Scope:** Apenas a Richards está vazia. Marcas VTEX (Levi's, Calvin Klein, etc.) listam categorias normalmente no mesmo dropdown.
- **Reproduction:** Abrir "Categorias por Marca" → "Varredura por Categoria" → selecionar Richards → dropdown sem opções.

## Investigation Context (from project STATE)

- Richards = engine `wake`, domínio `www.richards.com.br`, ativa, busca por SKU OK (3 produtos).
- STATE Operator Next Steps contém pista: "(opcional) Hugo Boss: rodar de/para de categorias VTEX (onboard_vtex_brands-style) para habilitar scans por categoria além da busca por SKU." → sugere que o source de categorias do dropdown pode ser específico de VTEX / depende de um mapeamento de/para que marcas não-VTEX (Wake) não possuem.
- Hipótese inicial: a fonte de categorias do dropdown é populada apenas para marcas VTEX (via category mapping / onboard_vtex_brands), e o engine Wake não tem categorias mapeadas — por isso o dropdown vem vazio sem erro.

## Current Focus

- hypothesis: CONFIRMADO — o dropdown da "Varredura por Categoria" é populado por `GET /brands/{brand}/categories`, que chama `engine.get_catalog()`. Para o engine `wake` (Richards), `get_catalog()` é um stub que retorna `[]` por design (D-08, Phase 32). Logo o dropdown vem vazio sem erro. O mecanismo de/para (`brand.mappings`) é a fonte pretendida para engines não-árvore (padrão Shopify), mas (a) o WakeEngine não lê `mappings` em `get_catalog()` e (b) Richards tem `mappings: []`.
- test: leitura do data flow completo: routes_category.py → engine.get_catalog() → wake_engine stub; comparação com shopify_engine.get_catalog() (padrão correto); brands.json (Richards mappings vazio).
- expecting: confirmado.
- next_action: AGUARDANDO VERIFICAÇÃO HUMANA — confirmar na UI que (1) o dropdown da Richards popula com as 6 categorias e (2) a varredura por categoria traz produtos reais. Se confirmado: arquivar sessão. Se algum path da Richards (ex: /bermudas) não corresponder a uma categoria real do site, ajustar o vtex_fq_path/label em brands.json (o termo de busca derivado já cobre o caso comum).
- reasoning_checkpoint:
    hypothesis: "O dropdown vazio da Richards é causado por WakeEngine.get_catalog() retornar [] (stub D-08). O endpoint GET /brands/{brand}/categories chama get_catalog(), então marcas Wake nunca surfacem categorias. VTEX/Shopify funcionam porque seus get_catalog() retornam dados reais."
    confirming_evidence:
      - "routes_category.py:103 — get_categories() chama `engine.get_catalog()` e retorna {categories}."
      - "wake_engine.py:399-401 — get_catalog() retorna [] (stub explícito, comentário D-08)."
      - "frontend App.tsx:404 — fetchBrandCategories() chama GET /brands/{brandKey}/categories e achata group.items[].path/label; se vazio, dropdown só mostra placeholder."
      - "shopify_engine.py:64-70 — get_catalog() retorna [{group, items:[{label, path}]}] real (padrão correto para engine não-árvore)."
      - "brands.json:352-364 — richards engine=wake, mappings=[] (vazio)."
    falsification_test: "Se eu popular brand.mappings da Richards E fizer WakeEngine.get_catalog() retorná-las, mas o dropdown continuar vazio, a hipótese está errada."
    fix_rationale: "Endereça a causa raiz (get_catalog stub) no nível certo: faz o Wake usar o mesmo mecanismo de/para (brand.mappings) que resolve_category_for_brands e o padrão Shopify já usam. Não é workaround de sintoma."
    blind_spots: "Wake run_bulk_scrape também é stub — habilitar o dropdown sem habilitar o scrape resultaria em 0 produtos na varredura. Preciso verificar se a varredura por categoria do Wake é viável via GraphQL (o spike 007 só validou search por termo, não listing por categoria)."
- tdd_checkpoint:

## Evidence

- timestamp: 2026-06-25
  checked: backend/api/routes_category.py — endpoint GET /brands/{brand}/categories
  found: Linha 95-104 — `get_categories()` resolve a marca, chama `engine = engine_factory.get_engine(brand_key)` e retorna `{"brand": brand, "categories": await engine.get_catalog()}`. A fonte do dropdown é exclusivamente `engine.get_catalog()`.
  implication: O dropdown depende inteiramente da implementação de get_catalog() do engine da marca. Não há fallback para o de/para canônico (`/canonical-categories`) neste endpoint.

- timestamp: 2026-06-25
  checked: backend/services/engines/wake_engine.py — get_catalog/discover_categories/run_bulk_scrape
  found: Linhas 395-412 — `get_catalog()` retorna `[]`, `discover_categories()` retorna `[]`, `run_bulk_scrape()` retorna (yields nothing). Todos são stubs explícitos com comentário "(D-08)". Decisão de design da Phase 32: Wake foi escopado só para busca por termo.
  implication: Causa raiz do sintoma reportado. Richards (wake) sempre retorna dropdown vazio. ADEMAIS: mesmo habilitando o dropdown, run_bulk_scrape também é stub → a varredura em si não traria produtos sem trabalho adicional.

- timestamp: 2026-06-25
  checked: frontend/src/App.tsx:401-415 (fetchBrandCategories) + api/client.ts
  found: O componente de "Varredura por Categoria" chama `GET /brands/${brandKey}/categories` e achata `data.categories[].items[]` em `{slug: i.path, label: "group - label"}`. Se a lista vem vazia, o `<select>` só mostra a opção placeholder "Selecione a categoria..." (App.tsx:572). Nenhum tratamento de erro/aviso para lista vazia.
  implication: Confirma o sintoma exato (dropdown só com placeholder, sem erro visível). O valor selecionado (`i.path`) volta como `category_path` no /scrape-category.

- timestamp: 2026-06-25
  checked: backend/services/engines/shopify_engine.py:59-70 (get_catalog) — padrão de referência para engine não-VTEX
  found: Shopify get_catalog() retorna `[{"group": "Coleções / Categorias", "items": [{"label": c["name"], "path": c["path"]} for c in flat_cats]}]`, derivado de discover_categories(). É o padrão correto de shape para o frontend.
  implication: Define o contrato de retorno que o WakeEngine.get_catalog() deve seguir: lista de {group, items:[{label, path}]}.

- timestamp: 2026-06-25
  checked: backend/data/brands.json — Richards + comparação com marcas que funcionam
  found: richards (linha 352-364): engine=wake, mappings=[] (VAZIO). Marcas que listam categorias têm mappings populados (ex: levis, calvinklein, zapalla, austral, trackfield) OU são VTEX com vtex_catalog dinâmico. bck (Shopify/Buckman) tem mappings populado e usa o padrão de/para.
  implication: Há DUAS lacunas: (1) WakeEngine.get_catalog() não lê brand.mappings; (2) Richards.mappings está vazio. Ambas precisam ser corrigidas para o dropdown funcionar.

- timestamp: 2026-06-25
  checked: backend/services/category_mapping.py (resolve_category_for_brands, get_category_preview) + category_resolver.py
  found: Ambos já leem `brand_data.mappings` (canonical_slug, vtex_fq_path, label) como fonte de/para para marcas dinâmicas. resolve_category_for_brands constrói `https://{domain}{path}` a partir de mapping.vtex_fq_path. ScrapeCategoryRequest.resolved_url() usa resolve_category_for_brands.
  implication: O mecanismo de/para via brand.mappings JÁ EXISTE e é o caminho pretendido (confirma a pista do STATE). A correção alinha o WakeEngine.get_catalog() a esse mecanismo já estabelecido — sem inventar nova infraestrutura.

- timestamp: 2026-06-25
  checked: backend/services/orchestrator.py:40-54
  found: run_orchestrator() despacha a varredura via `engine.run_bulk_scrape(category_url=...)`. Para Wake, run_bulk_scrape é stub (yields nothing) → "Nenhum produto válido extraído." (orchestrator.py:100).
  implication: BLIND SPOT confirmado. Habilitar só o dropdown deixaria a varredura por categoria do Wake retornando 0 produtos. O fix end-to-end precisa também de um run_bulk_scrape Wake funcional, OU o escopo do fix é apenas o dropdown (sintoma reportado) e a varredura real fica como follow-up. Decisão: implementar run_bulk_scrape via GraphQL search por termo derivado da categoria (Wake não tem listing por path confirmado; spike 007 só validou search por query).

## Eliminated

## Resolution

root_cause: "O dropdown da 'Varredura por Categoria' é populado exclusivamente por `GET /brands/{brand}/categories` → `engine.get_catalog()`. O WakeEngine.get_catalog() era um stub que retorna [] (design D-08 da Phase 32, quando o Wake foi escopado só para busca por termo). Por isso Richards (engine=wake) sempre mostrava o dropdown vazio, sem erro. Marcas VTEX/Shopify funcionam porque seus get_catalog() retornam categorias reais. Causa secundária: run_bulk_scrape do Wake também era stub (yields nothing) → mesmo com dropdown habilitado a varredura traria 0 produtos."
fix: "(1) WakeEngine.get_catalog()/discover_categories() agora derivam categorias de `brand.mappings` (mesmo mecanismo de/para que resolve_category_for_brands e o padrão Shopify já usam), retornando o shape {group, items:[{label, path}]} que o frontend espera. Sem mappings → [] (preserva graça do D-08). (2) brands.json: Richards ganhou 6 mappings (camisas, polos, camisetas, calcas, bermudas, jaquetas). (3) WakeEngine.run_bulk_scrape() deixou de ser stub: deriva um termo de busca do último segmento do path da categoria (_category_url_to_search_term) e pagina via search() — caminho GraphQL já validado em produção — yieldando dicts de produto no contrato do orchestrator."
verification: "Testes hermeticos (24 passam em test_wake_engine.py, incluindo 6 novos: catalog/discover de mappings, shape do frontend, derivação de termo, run_bulk_scrape via search). Exercício end-to-end do route handler GET /brands/richards/categories retorna as 6 categorias no shape correto. brand_service carrega os 6 CategoryMapping. ScrapeCategoryRequest('/camisas').resolved_url() = https://www.richards.com.br/camisas. Suites relacionadas (engine_detection, brand_active, brand_gate, vtex_onboarding) sem regressão (31 passam). FALTA verificação humana ao vivo: dropdown popula na UI e a varredura traz produtos reais da Richards (depende do token Wake/storefront ao vivo — search validado no onboarding)."
files_changed:
  - "backend/services/engines/wake_engine.py: get_catalog/discover_categories derivam de brand.mappings; run_bulk_scrape via search; helper _category_url_to_search_term"
  - "backend/data/brands.json: Richards mappings populados (6 categorias)"
  - "backend/tests/test_wake_engine.py: TestWakeStubs → TestWakeCatalog (testa de/para + run_bulk_scrape; stubs antigos substituídos)"

## Cycle 2 — Verificação ao vivo FALHOU, nova causa raiz (token) + categorias incompletas

A verificação humana do Cycle 1 expôs dois defeitos NÃO cobertos pelos testes herméticos:

- timestamp: 2026-06-25
  symptom: 'Console: "Erro crítico: Token Wake nao resolvido para richards..." — a varredura aborta antes de qualquer produto.'
  checked: live GET https://www.richards.com.br + WakeEngine._resolve_token / requirements.txt
  found: "A loja Richards (Wake/Kestrel + CDN fbits) responde SEMPRE com Content-Encoding: br (Brotli), ignorando o Accept-Encoding. O aiohttp do backend só descomprime Brotli se a lib `brotli` estiver instalada — e ela NÃO estava em requirements.txt (só aiohttp>=3.9.0). Logo _resolve_token rodava o regex storefrontAccessToken em cima de bytes comprimidos, não achava nada, retornava None → ValueError. Prova: decodificando o Brotli (220KB) o token aparece mascarado como storefrontAccessToken: 'tcs_richa_35...'. Sem descomprimir vem 20KB de lixo binário."
  implication: "ROOT CAUSE real do erro de token. Os testes herméticos do Cycle 1 mockavam o token, então nunca exercitaram a auto-extração ao vivo — por isso passaram com o caminho quebrado."

- timestamp: 2026-06-25
  symptom: "Só 6 categorias aparecem no dropdown, mas o menu real da Richards tem ~15 (Masculino)."
  checked: brand.mappings da Richards vs menu real do site
  found: "O Cycle 1 semeou apenas 6 categorias de exemplo à mão em brand.mappings. O menu real é renderizado por JS (a home estática tem só 24 hrefs, todos de CSS/asset — fbitsstatic.net), então a árvore não é raspável estaticamente; a lista é necessariamente um de/para curado."
  implication: "O dropdown reflete exatamente o de/para. Faltavam 9 categorias do menu Masculino."

cycle2_fix: "(1) brotli>=1.1.0 adicionado a backend/requirements.txt e instalado no interpretador do backend (Python 3.14) → aiohttp passa a descomprimir Brotli → _resolve_token volta a auto-extrair o token (escolha do usuário: brotli+auto, durável para qualquer loja Wake). (2) brands.json: Richards expandida de 6 → 15 mappings (menu Masculino completo: Acessórios, Bermudas, Blazers, Calçados, Calças, Camisas, Íntimo, Jaquetas, Moletom, Polos, Praia, Shorts, T-Shirts→/camisetas, Tricos e Blusas→/tricot, Outlet)."
cycle2_verification: "VERIFICADO AO VIVO pelo próprio WakeEngine (não mockado): _resolve_token(brand, domain) → tcs_richa_3567...; get_catalog() → 15 items; run_bulk_scrape('/camisas') → produtos reais ('Camisa Linho Hortencia | R$ 479.0'). test_wake_engine.py 24/24 verde. Token extraction end-to-end confirmada via brotli 1.2.0."
cycle2_files_changed:
  - "backend/requirements.txt: + brotli>=1.1.0 (Wake storefronts forçam Content-Encoding: br)"
  - "backend/data/brands.json: Richards mappings 6 → 15 (menu Masculino completo)"
notes: "Limitações conhecidas: (a) a 'varredura por categoria' do Wake é busca-por-termo derivado do path (spike 007 só validou search), não navegação real por árvore — categorias do tipo seção (Íntimo, Praia, Outlet) podem retornar resultados fracos/ruidosos; ajustar o vtex_fq_path para um termo melhor se necessário. (b) Escopo Masculino apenas, por decisão do usuário; Feminino/Selaria/Linhos podem ser adicionados ao mappings depois."

## Cycle 3 — token ainda falhava ao vivo (ambiente sem brotli) → token override

- timestamp: 2026-06-25
  symptom: "Após reiniciar (11:12), categorias carregam (GET /brands/richards/categories 200, 15 itens) mas a varredura ainda erra: aiohttp 'Can not decode content-encoding: brotli (br). Please install Brotli' → 'Token Wake nao resolvido'."
  checked: "Interpretador do backend vs onde brotli foi instalado; Content-Encoding do endpoint GraphQL."
  found: "O backend rodando usa um interpretador Python ONDE brotli NÃO está instalado (sem venv detectável; o reinstall do requirements foi para outro env). PORÉM o endpoint GraphQL (storefront-api.fbits.net/graphql) responde em GZIP (respeita Accept-Encoding), que o aiohttp decodifica nativamente — só a HOME força Brotli. Logo, gravar o token manual no brands.json faz _resolve_token retornar na etapa 1 (override > cache > auto) SEM buscar a home Brotli, e a busca GraphQL gzip funciona sem brotli."
  implication: "Fix decisivo e independente de ambiente."
cycle3_fix: "brands.json: richards.wake_access_token = 'tcs_richa_35...' (override mascarado; valor real deve ficar fora do repo). brotli>=1.1.0 mantido no requirements como caminho durável de auto-extração quando estiver presente no env do backend."
cycle3_verification: "PROVADO sem brotli: rodei o WakeEngine com o import de `brotli` bloqueado (HAS_BROTLI=False, = ambiente do backend) → _resolve_token retorna o token sem HTTP, search('camisas') → 3 produtos reais. test_wake_engine.py 24/24 verde. brands.json: token set + 15 mappings + active."
cycle3_files_changed:
  - "backend/data/brands.json: richards.wake_access_token override (desbloqueio independente de brotli no env do backend)"
risk: "Tokens de storefront Wake são públicos e longevos mas podem rotacionar. Se rotacionar E o env do backend não tiver brotli, a auto-extração não cobre (override tem precedência sobre auto) — re-extrair o token da home (decodificando Brotli) e atualizar o override. O ideal de longo prazo é garantir `brotli` no interpretador que roda o uvicorn (sem venv detectado; instalar nele) e então remover o override para voltar à auto-extração."
