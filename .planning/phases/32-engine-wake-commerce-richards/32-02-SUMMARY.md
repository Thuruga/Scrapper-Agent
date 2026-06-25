---
phase: 32-engine-wake-commerce-richards
plan: "02"
subsystem: backend/services/engines
tags: [wake, graphql, engine, factory, models, richards]
dependency_graph:
  requires:
    - "32-01 (spike GO — graphql+token confirmado empiricamente)"
  provides:
    - "backend/services/engines/wake_engine.py"
    - "WakeEngine(BaseEngine) — busca GraphQL Wake com token por loja"
    - "EngineFactory.get_engine('wake') -> WakeEngine (sem NotImplementedError)"
    - "DynamicBrandCreate.wake_access_token Optional[str]"
  affects:
    - "backend/services/engines/factory.py"
    - "backend/core/models.py"
    - "backend/tests/test_sfcc_engine.py"
    - "32-03 (testes herméticos do WakeEngine)"
tech_stack:
  added: []
  patterns:
    - "POST GraphQL com variaveis $q/$first — sem interpolacao de string (T-32-02)"
    - "GET com allow_redirects=False para extracao de token publico de storefront (T-32-01)"
    - "Cache de token por instancia (self._token_cache, nunca de classe) (T-32-06)"
    - "Import lazy dentro de get_engine — mesmo padrao SFCCEngine (anti-circular)"
    - "ValueError claro no token ausente capturado por _search_one como BrandSearchResult.error (D-07)"
    - "Quality Gates: filter_mens_fashion -> validate_single -> SearchProductResult (CAT-01)"
key_files:
  created:
    - "backend/services/engines/wake_engine.py"
  modified:
    - "backend/core/models.py"
    - "backend/services/engines/factory.py"
    - "backend/tests/test_sfcc_engine.py"
decisions:
  - "[32-02/D-06]: wake_access_token Optional[str] = None adicionado em DynamicBrandCreate apos logo_url — herda automaticamente em DynamicBrand"
  - "[32-02/D-09]: Import lazy WakeEngine dentro de get_engine espelha exatamente o padrao SFCCEngine (factory.py L48-50)"
  - "[32-02/D-07]: ValueError claro (nao 0 produtos silenciosos) capturado por _search_one como BrandSearchResult.error"
  - "[32-02/SC-3]: NotImplementedError removido do branch wake — EngineFactory agora instancia WakeEngine"
  - "[32-02/Armadilha 2]: aliasComplete relativo prefixado com dominio: f'https://{domain}/{alias.lstrip('//')}'"
  - "[32-02/Armadilha 4]: prices.price passthrough como float em reais — spike confirmou 479 = R$479, sem divisao por 100"
  - "[32-02/test_sfcc]: test_factory_wake_still_raises removido de test_sfcc_engine.py — era marcador de Phase 32 pendente; substituido por test_factory_returns_wake_engine em test_wake_engine.py (plano 32-03)"
metrics:
  duration: "~5 min"
  completed: "2026-06-25"
  tasks_completed: 3
  tasks_total: 3
  files_created: 1
  files_modified: 3
---

# Phase 32 Plan 02: WakeEngine Build — Summary

## One-liner

WakeEngine(BaseEngine) implementado com busca GraphQL Wake (POST storefront-api.fbits.net/graphql, variaveis $q/$first, TCS-Access-Token por loja), resolucao de token em 3 etapas (override->cache->auto-extract com allow_redirects=False), Quality Gates CAT-01+Pydantic, stubs graciosos para shipping/categorias e wiring lazy na EngineFactory substituindo o NotImplementedError.

## Gate Pre-condition

Veredito do spike 32-01: **GO** — todas as suposicoes A1-A6 confirmadas empiricamente.
Plano executado conforme a precondição D-01/D-03.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Adicionar campo opcional wake_access_token ao modelo de marca (D-06) | `1e63376` | `backend/core/models.py` |
| 2 | Implementar WakeEngine — busca GraphQL + resolucao de token + stubs (D-05/D-07/D-08/D-10/D-11) | `0c6951d` | `backend/services/engines/wake_engine.py` |
| 3 | Plugar WakeEngine na EngineFactory — substituir NotImplementedError (D-09, SC-3) | `6c02290` | `backend/services/engines/factory.py`, `backend/tests/test_sfcc_engine.py` |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Remocao da string "BrowserManager" de docstring do wake_engine.py**

- **Found during:** Task 2 (verificacao dos acceptance criteria)
- **Issue:** O script de verificacao do plano filtra apenas linhas que comecam com `#` (comentarios Python). A docstring do modulo continha a palavra "BrowserManager" em uma linha de docstring (`- D-11: aiohttp via SessionManager; NO BrowserManager (API, no render).`), que nao comeca com `#`, causando falha na verificacao `assert sum('BrowserManager' in l for l in code) == 0`.
- **Fix:** Linha alterada para `- D-11: aiohttp via SessionManager only; no browser rendering.` — semanticamente equivalente, sem a palavra proibida fora de comentarios.
- **Files modified:** `backend/services/engines/wake_engine.py`
- **Commit:** incluido no commit `0c6951d`

**2. [Rule 2 - Missing Critical] Remocao do teste obsoleto test_factory_wake_still_raises**

- **Found during:** Task 3 (wiring da factory)
- **Issue:** PATTERNS.md §"Remocao obrigatoria" especifica que `test_sfcc_engine.py` L235-249 (`test_factory_wake_still_raises`) deve ser removido apos o WakeEngine ser implementado — esse teste verifica que `NotImplementedError` e lancado, o que agora e incorreto (regressao de correctness).
- **Fix:** Teste removido e substituido por comentario explicativo. O teste equivalente correto (`test_factory_returns_wake_engine`) sera criado no plano 32-03.
- **Files modified:** `backend/tests/test_sfcc_engine.py`
- **Commit:** incluido no commit `6c02290`

## Success Criteria Verification

| Criterio | Status |
|----------|--------|
| COMP-04 SC-3: EngineFactory.get_engine para engine='wake' retorna WakeEngine | ATENDIDO — factory retorna `WakeEngine(brand_key)` via import lazy |
| COMP-04 SC-4: token por loja; ausencia/erro -> BrandSearchResult.error claro | ATENDIDO — ValueError em _resolve_token capturado por _search_one |
| COMP-04 SC-4: calculate_shipping -> None (sem badge "Frete Gratis") | ATENDIDO — `return None` em calculate_shipping |
| D-06: wake_access_token opcional no modelo sem quebrar marcas existentes | ATENDIDO — Optional[str] = None; 224 testes passando |
| D-08: discover_categories/get_catalog retornam [] sem crash | ATENDIDO — stubs graciosos implementados |
| D-10: busca single-query, sem enriquecimento PDP | ATENDIDO — search() usa apenas a query GraphQL WakeSearch |
| D-11: aiohttp via SessionManager, sem BrowserManager | ATENDIDO — nenhuma importacao de BrowserManager |
| Regressao: suite existente verde | ATENDIDO — 224 testes passando (225 - 1 obsoleto removido) |

## Implementation Notes

### GraphQL Query Confirmada pelo Spike

A query `WakeSearch($q: String!, $first: Int!)` usa `search(query: $q) { products(first: $first) { edges { node { productName aliasComplete prices { price } images { url } available } } } }` com variaveis — confirmada pelo spike 007 como funcional contra a Richards.

### Resolucao de Token (3 etapas, D-05/D-06)

1. `brand.wake_access_token` — override manual (getattr/dict.get compativel com Pydantic e dict)
2. `self._token_cache` — cache por instancia (previne re-fetch na mesma busca)
3. GET `https://{domain}` com `allow_redirects=False` + regex `storefrontAccessToken\s*:\s*['"]([^'"]+)['"]`

### Formato do Preco (Armadilha 4 — confirmada GO)

`prices.price` retorna inteiro/float em reais (ex: `479` para R$479). Passthrough direto como float — sem divisao por 100 (contraste com VTEX).

### URL do Produto (Armadilha 2 — confirmada GO)

`aliasComplete` e relativo (ex: `"produto/camisa-linho-hortencia-196863"`). URL montada como `f"https://{domain}/{alias.lstrip('/')}"`.

## Known Stubs

| Stub | Arquivo | Linha | Razao |
|------|---------|-------|-------|
| `discover_categories() -> []` | `wake_engine.py` | ~333 | D-08: implementacao real deferida para phase futura |
| `get_catalog() -> []` | `wake_engine.py` | ~337 | D-08: implementacao real deferida para phase futura |
| `get_product_details() -> None` | `wake_engine.py` | ~352 | D-10: sem enriquecimento PDP nesta phase |
| `run_bulk_scrape() -> None` | `wake_engine.py` | ~343 | D-08: bulk scrape Wake nao planejado nesta phase |

Estes stubs sao intencionais por design (D-08/D-10) e nao impedem o objetivo do plano (busca GraphQL via `search()`).

## Threat Surface Scan

Nenhuma superficie nova alem do que esta no threat_model do plano:

| Flag | Arquivo | Descricao |
|------|---------|-----------|
| — | — | Sem endpoints novos expostos externamente; sem novos caminhos de autenticacao de usuario; sem acesso a arquivos novos. O WakeEngine e chamado internamente pela EngineFactory. |

## Self-Check: PASSED

- [x] `backend/services/engines/wake_engine.py` existe (354 linhas)
- [x] `backend/core/models.py` contem `wake_access_token` em DynamicBrandCreate
- [x] `backend/services/engines/factory.py` contem `from services.engines.wake_engine import WakeEngine` e `return WakeEngine(brand_key)`
- [x] `factory.py` NAO contem mais `raise NotImplementedError` no branch wake
- [x] commit `1e63376` existe (Task 1)
- [x] commit `0c6951d` existe (Task 2)
- [x] commit `6c02290` existe (Task 3)
- [x] 224 testes passando (225 - 1 obsoleto removido intencionalmente)
- [x] `wake_engine.py` NAO contem "BrowserManager" em linhas nao-comentario
- [x] `wake_engine.py` usa `variables` na query GraphQL
