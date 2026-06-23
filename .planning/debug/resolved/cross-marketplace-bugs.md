---
status: resolved
trigger: "O SKU PO.10.0278010 nao esta trazendo produtos da amazon e a ordenação dos score nao estao do maior para o menor; ao pesquisar \"camisa\" na busca comparativa nao esta sendo possivel trazer os produtos da hering. Investigar tambem os logs do terminal do antigravity."
created: 2026-06-13
updated: 2026-06-13
---

# Debug Session: cross-marketplace-bugs

## Symptoms
- **S1 — Amazon sem produtos (busca cruzada por SKU):** SKU `PO.10.0278010` não traz produtos da Amazon.
- **S2 — Ordenação de score:** scores não saem do maior para o menor.
- **S3 — Hering ausente (busca comparativa):** pesquisar "camisa" não traz produtos da Hering.
- **Antigravity logs:** sem erro/traceback de busca no terminal — só reloads do uvicorn (WatchFiles)
  e o `category_monitor_job` rodando a cada 10 min. Confirma que os bugs estão na lógica do request-path,
  não em crash de servidor.

## Reprodução
- Endpoint: POST `/search/cross-marketplace` (S1, S2) e POST `/search` (S3).
- Scripts de repro: `scratch_debug_repro.py`, `scratch_debug_repro2.py` (descartáveis).

## Current Focus
hypothesis: 3 causas independentes confirmadas e corrigidas (ver Resolution).
next_action: DONE — fixes aplicados e verificados; suíte de testes 78/78 verde.

## Evidence

### S1 — Amazon: motor funciona, gate+corte descartam 100%
- `AmazonEngine.search("Polo Manga Curta Basica Aramis")` → **30 produtos** (via Playwright fallback; curl_cffi
  retorna 200 com página de ~2KB / anti-bot). Motor OK.
- SKU resolve corretamente na Aramis VTEX → "Polo Manga Curta Básica Piquet Marinho" (cat "Polo Manga Curta").
  Hipótese inicial "SKU vira string literal" → **REFUTADA**.
- `passes_brand_gate(titulo, official_title="...aramis", enabled=True)` exige "aramis" no título do marketplace.
  **Nenhum** dos 30 resultados Amazon contém "aramis" (Amazon BR não tem listings da marca Aramis) → gate=False em 100%.
- Text score NLP dos resultados ~15–23, muito abaixo do corte `CROSS_MIN_SCORE_WITHOUT_VISION=55`
  (e `CROSS_MIN_SCORE_WITH_VISION=60`) → reprovam também no corte.
- Resultado: `0/30` sobrevivem → "Amazon traz 0 produtos".
- Risco secundário: no fluxo real `ENGINE_DEFAULT_TIMEOUT_SECONDS=30s` (cross) < timeout interno do Playwright
  Amazon (35s); sob concorrência (ML também usa Playwright) Amazon pode estourar timeout → 0. Causa dominante
  reproduzida é gate+corte.
- Arquivos: services/cross_marketplace_service.py:355-361 (filtro), :16-38 (passes_brand_gate),
  services/relevance_gates.py:60-72 (cutoff), api/routes_search.py:344-368 (construção de query).

### S2 — apply_visual_tiebreak ordena por imagem, não por score final
- `VISUAL_TIEBREAK_ENABLED=True`, `VISUAL_TIEBREAK_TEXT_WINDOW=10.0` (defaults, config.py:227-246).
- Repro determinístico (4 candidatos "aramis", visão ativa): ordem final de `final_match_score` = **[82, 85, 88, 70]** → NÃO decrescente.
- Causa: coorte in-window da mesma marca usa chave `(0, -top_da_marca, -image_match_score, preco)` → desempata
  por imagem, embaralhando a coluna de score final exibida. `known_brands_for_detection=["aramis","reserva","tommy"]`
  → no fluxo por SKU todos os itens viram a MESMA marca (aramis) → 1 só coorte → ordenado por imagem.
- Inversão adicional entre faixas/marcas: faixa 0 (qualquer item in-window) sempre precede faixa 1, então um
  item final=70 (band0 de marca com top baixo) pode aparecer acima de um final=75 (band1).
- Arquivo: services/cross_marketplace_service.py:69-149 (apply_visual_tiebreak), :367-371 (chamada).

### S3 — Hering: mapping de categoria stale força path VTEX vazio
- Hering ESTÁ registrada (data/brands.json:38-80), engine=vtex, vtex_account=null, e ESTÁ na VTEX
  (category/tree/3 → 117 nós).
- `resolve_query_to_vtex_category_path("camisa","hering")` → `'/bodies/camisa'` (mapping em brands.json).
- Probe direto:
  - `/api/catalog_system/pub/products/search/camisa` → **206, JSON, 10 itens** ✅ (full-text funciona)
  - `/api/catalog_system/pub/products/search/bodies/camisa` → **200, len=2, 0 itens** ❌ (path mapeado quebrado)
- `VtexApiClient.search` prioriza `category_path` quando presente e **não faz fallback** para full-text quando
  vazio → retorna 0, error=None (silencioso).
- Arquivos: services/vtex_api_scraper.py:762-785 (escolha de URL por category_path), data/brands.json:47-52 (mapping).

## Eliminated
- hypothesis: "SKU PO.10.0278010 não é encontrado na Aramis e a query vira o SKU literal" — REFUTADA: resolve para
  o produto correto; broad_q = "Polo Manga Curta Básica Aramis".
- hypothesis: "Hering não está cadastrada / não é VTEX" — REFUTADA: cadastrada, VTEX ativa, full-text retorna 10.
- hypothesis: "Amazon bloqueada por CAPTCHA retorna 0 no motor" — PARCIAL/REFUTADA como causa dominante: curl_cffi
  é bloqueado mas o Playwright fallback retorna 30–57 produtos; o 0 final vem do gate+corte.

## Root Causes (confirmadas)
1. **S1:** Para produto de marca própria (Aramis) o brand gate exige "aramis" no título do marketplace e o corte
   de score exige alta similaridade textual; Amazon não tem listings "aramis" e os polos genéricos têm score baixo
   → 100% filtrados.
2. **S2:** `apply_visual_tiebreak` reordena a coorte da mesma marca por `image_match_score` (não por
   `final_match_score`), quebrando a expectativa de ordem decrescente por score.
3. **S3:** O mapping de categoria da Hering (`/bodies/camisa`) está stale/inválido e retorna 0; a busca VTEX não
   tem fallback para o endpoint full-text (`/search/camisa`, que retorna 10).

## Resolution
root_cause: (ver seção "Root Causes" acima)

fix (decisões do usuário):
- **S1 (Amazon):** "mostrar similares/concorrentes". Fallback two-pass em `compare_product`: quando o filtro
  estrito (brand gate + corte) zera TUDO, refaz sem o brand gate com corte `CROSS_SIMILAR_MIN_SCORE` (default 15).
  Novos knobs em config: `CROSS_SIMILAR_FALLBACK_ENABLED` (True), `CROSS_SIMILAR_MIN_SCORE` (15.0). Campo
  `similar_fallback` adicionado ao payload de resposta. Preserva precisão quando há match exato.
- **S2 (ordem):** "retirar a % de match no frontend". Removido o `• Match: X%` em App.tsx (a ordenação interna
  por visual-tiebreak permanece, mas não é mais exibida como número que parecia fora de ordem).
- **S3 (Hering):** "fallback full-text + limpar mapping". `VtexApiClient.search` agora cai para o endpoint
  full-text (`/search/{query}`) quando o `category_path` mapeado retorna 0. Mappings stale da Hering removidos
  em data/brands.json E no Supabase (6 → 0).

verification:
- S3: `VTEXEngine("hering").search("camisa")` → 7 produtos (antes 0). ✅
- S1: filtro estrito = 0 (reproduz o bug), fallback = 28 similares da Amazon exibidos. ✅
- Suíte: `pytest tests/` → 78 passed. ✅

files_changed:
- config.py (S1: 2 knobs)
- services/cross_marketplace_service.py (S1: fallback + campo similar_fallback)
- services/vtex_api_scraper.py (S3: fallback full-text em search())
- frontend/src/App.tsx (S2: remove Match %)
- data/brands.json (S3: mappings da Hering → []; gitignored)
- Supabase tabela `brands` (S3: mappings da Hering → []; dado vivo)

notas:
- Frontend `dist/` está stale — rebuild (`npm run build`) ou rodar `vite dev` para ver a mudança de S2.

## Follow-up round 2 (2026-06-14): "ML e Amazon não trouxeram produtos" (SKU PO.10.0278010, vision ATIVA)

### Sintomas (run real 11:40, vision ativa)
- ML: 0 produtos. Amazon: 0 no resultado final. Netshoes: ok. Resultado final = 10 (só Netshoes).

### Root causes (confirmadas empiricamente)
- **S1-bis (Amazon flaky):** Com vision ativa, Amazon TEM produtos Aramis (passam o brand gate — 27/30), mas o
  `final_match_score` depende do download da IMAGEM do produto. Quando a imagem da Amazon é bloqueada por anti-bot
  → `image_match_score=0` → blend texto-only cai abaixo do corte de visão (60) → Amazon zera no filtro estrito.
  O fallback da rodada 1 era GLOBAL (só dispara se TODAS as plataformas zeram); como Netshoes tinha match estrito,
  o fallback não disparava e a Amazon sumia. (Quando as imagens da Amazon baixam, ela passa no estrito — daí o
  comportamento intermitente.)
- **S4 (ML Anubis):** o Mercado Livre serve o desafio proof-of-work "Anubis". `curl_cffi` é bloqueado e o
  Playwright fallback lia o HTML com `wait_until=domcontentloaded` + 5s — ANTES do JS do Anubis resolver o PoW e
  redirecionar → challenge ainda presente → 0 produtos. API oficial `/sites/MLB/search` → 403 (exige OAuth).

### Fixes
- **S1-bis:** fallback agora é **por plataforma** (cross_marketplace_service.py): para CADA plataforma com 0
  resultados estritos, exibe os similares daquela plataforma (corte `CROSS_SIMILAR_MIN_SCORE`). Plataformas com
  match estrito mantêm a precisão. Cobre o caso "Netshoes ok + Amazon zerada".
- **S4 (ML):** `_search_with_playwright` agora usa `wait_until="networkidle"` + `extra_sleep=10s` + `timeout=60000`
  (mercado_livre_engine.py) — atravessa o redirect do Anubis. `ML_TIMEOUT_PLAYWRIGHT_SECONDS` 60 → 80 (folga no
  cross para o networkidle).

### Verification (E2E real, vision ativa)
- `compare_product(SKU PO.10.0278010)` → **ML=10, Netshoes=10, Amazon=10** (`status=success`, `errors=[]`).
  Amazon entrou via fallback per-plataforma (`similar_fallback=True`, log "Amazon: 0 match estrito; exibindo
  30 similares"). ML resolveu o Anubis ("Mercado Livre: 30 produtos encontrados"). ✅
- Sonda Playwright ML isolada: `anubis=False, parsed=10`. ✅
- `pytest tests/` → 78 passed. ✅

### Notas / riscos remanescentes
- Enriquecimento de seller/frete do ML via PDP falha às vezes ("Page.content ... navigating") e não extrai
  item_id de URLs `/up/MLBU...` (catálogo) → frete não calculado p/ esses. NÃO-fatal (produto aparece). Pré-existente.
- `networkidle` em página pesada do ML pode, em pior caso, estourar timeout → ML degrada a 0 graciosamente
  (sem crash; é capturado). Em Render free (512MB) pode ser mais lento.
- Amazon ainda pode oscilar entre "estrito" (imagens OK) e "similar" (imagens bloqueadas), mas em AMBOS os casos
  agora aparece.

## Code review adversarial (workflow, 2026-06-14): 4 achados MEDIUM corrigidos

Workflow de review (15 agentes, 11 achados levantados, 7 dismissados com razão, 4 confirmados) sobre o diff.
Todos os 4 estavam no gap que o teste E2E (só contagens) não cobria:

1. **Buybox/cheapest incluíam similars** (cross_marketplace_service.py + relevance_gates.py): um similar barato
   (score 15) podia virar `is_buybox_winner`/`cheapest_price`, deslocando o match estrito. **Fix:** produtos do
   fallback marcados com `is_similar`; `mark_buybox_winner` e o cálculo de `cheapest_price` restringem aos
   estritos quando houver (se só houver similares, usa todos; backward-compat p/ chamadores sem a flag).
2. **Orçamento ML 80s estourável** (config.py): curl (15s) roda ANTES do Playwright no MESMO wait_for; pior caso
   ~92s > 80s → ML podia ser cancelado bem quando o Playwright ia ter sucesso. **Fix:** `ML_TIMEOUT_PLAYWRIGHT_SECONDS`
   80 → 100 (cobre curl 15 + goto 60 + sleep 10 + overhead). Como goto tem cap rígido de 60s, a thread sempre
   termina < 100s → o wait_for não dispara → sem Chromium órfão (mitiga o achado 3).
3. **Vazamento de Chromium no timeout + docstring falsa** (browser_manager.py): wait_for não cancela a thread do
   to_thread. **Fix:** docstring corrigida (os flags --single-process/--js-flags NÃO existem em CHROMIUM_ARGS —
   foram removidos por quebrarem redirect JS/Anubis); o orçamento de 100s evita o disparo do wait_for na thread ML.
4. **Similar indistinguível de match exato no front** (App.tsx): backend emitia `similar_fallback` mas o front
   não consumia, e sem a % um similar 15/100 parecia um match 95/100. **Fix:** cada produto do fallback carrega
   `is_similar`; App.tsx renderiza badge "Similar" nesses cards.

### Verification (review fixes)
- Unit: similar barato (100) NÃO rouba buybox de estrito (200); só-similares pega o mais barato; backward-compat OK.
- E2E real: ML=10/Netshoes=10/Amazon=3, buybox=ML estrito R$151.11 (is_similar=False), `is_similar` no payload.
- `pytest tests/` → 78 passed.

files_changed (review round): services/cross_marketplace_service.py, services/relevance_gates.py, config.py,
core/browser_manager.py (docstring), frontend/src/App.tsx (badge).
