---
phase: 32-engine-wake-commerce-richards
plan: "03"
subsystem: backend/tests
tags: [wake, graphql, tests, hermetic, session-manager, tdd]
dependency_graph:
  requires:
    - "32-02 (WakeEngine implementado e factory wired)"
  provides:
    - "backend/tests/test_wake_engine.py"
    - "Testes herméticos do WakeEngine: SC-2/SC-3/SC-4/D-06/D-08"
    - "Suite completa verde: 235 testes (224 baseline + 11 novos Wake)"
  affects:
    - "backend/tests/ (suite completa — regressao verificada)"
tech_stack:
  added: []
  patterns:
    - "Mock seam SessionManager.get_session (aiohttp) — _SESSION_GET_TARGET = 'core.session_manager.SessionManager.get_session'"
    - "Async context manager mock para session.post(_GRAPHQL_RESPONSE) via __aenter__/__aexit__"
    - "MagicMock para brand com atributos brand_name/domain/wake_access_token/engine"
    - "asyncio.run() para executar coroutines em testes sync (mesmo padrao test_sfcc_engine.py)"
key_files:
  created:
    - "backend/tests/test_wake_engine.py"
  modified: []
decisions:
  - "[32-03/SC-3]: TestWakeFactory::test_factory_returns_wake_engine confirma EngineFactory.get_engine('wake') retorna WakeEngine (nao NotImplementedError)"
  - "[32-03/SC-2]: URL do produto verificada como https://www.richards.com.br/ (nao fbits.net) — Armadilha 2 coberta por teste explicito"
  - "[32-03/D-07]: TestWakeTokenFailure::test_missing_token_returns_error usa search_all_brands() para testar via _search_one() — captura ValueError como BrandSearchResult.error"
  - "[32-03/guard-deviated]: test_factory_wake_still_raises ja removido em 32-02 (Deviation 1 abaixo); Task 2 executada como verificacao + regressao apenas"
metrics:
  duration: "~5 min"
  completed: "2026-06-25"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 0
---

# Phase 32 Plan 03: WakeEngine Test Suite — Summary

## One-liner

Testes herméticos do WakeEngine criados em `test_wake_engine.py` (11 testes, 5 classes: TestWakeFactory/TestWakeEngineSearch/TestWakeTokenFailure/TestWakeModels/TestWakeStubs) cobrindo SC-2/SC-3/SC-4/D-06/D-08 com SessionManager mockado — suite completa verde: 235 testes passando.

## Gate Pre-condition

Veredito do spike 32-01: **GO** — fluxo GraphQL+TCS-Access-Token confirmado contra Richards (A1-A6 verificados).
WakeEngine implementado em 32-02 — pré-condição atendida.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Criar test_wake_engine.py — SC-2/SC-3/SC-4/D-06/D-08 com SessionManager mockado | `4e976e9` | `backend/tests/test_wake_engine.py` |
| 2 | Verificar remoção do guard + regressão da suite completa | (nenhum commit necessário — guard já removido em 32-02) | N/A |

## Deviations from Plan

### Task Done Early (in 32-02)

**1. [Done in 32-02] Remoção de test_factory_wake_still_raises**

- **Context:** O plano 32-03 especificava remover `test_factory_wake_still_raises` de `test_sfcc_engine.py` como Task 2. No entanto, o executor de 32-02 já realizou essa remoção durante o wiring da factory (documentado no 32-02-SUMMARY.md como "Deviation 2: Rule 2 - Missing Critical").
- **Verification:** `grep -n "test_factory_wake_still_raises" backend/tests/test_sfcc_engine.py` retorna somente a linha 235, que é um comentário explicativo (não um método de teste ativo):
  ```
  235:# test_factory_wake_still_raises removed in Phase 32 plan 02 — WakeEngine is now live.
  ```
- **Status:** Task 2 tratada como verificação + regressão only. Nenhuma edição adicional em `test_sfcc_engine.py` foi necessária.
- **Note:** O grep literal `grep -c "test_factory_wake_still_raises"` retorna 1 (não 0) porque o comentário contém o nome do teste removido. Isso é intencional — o comentário serve como rastreabilidade histórica. O teste ativo foi removido; a verificação funcional passa.

## Test Coverage Delivered

| Classe | Método | SC/Decision | Status |
|--------|--------|-------------|--------|
| TestWakeFactory | test_factory_returns_wake_engine | SC-3 | VERDE |
| TestWakeEngineSearch | test_search_returns_products | SC-2 | VERDE |
| TestWakeEngineSearch | test_search_result_url_not_fbits | SC-2 / Armadilha 2 | VERDE |
| TestWakeEngineSearch | test_calculate_shipping_returns_none | SC-4 / D-08 | VERDE |
| TestWakeTokenFailure | test_missing_token_returns_error | SC-4 / D-07 | VERDE |
| TestWakeModels | test_model_wake_token_optional | D-06 | VERDE |
| TestWakeModels | test_model_wake_token_explicit_value_preserved | D-06 | VERDE |
| TestWakeModels | test_model_existing_brands_unaffected | D-06 backward compat | VERDE |
| TestWakeStubs | test_discover_categories_stub | D-08 | VERDE |
| TestWakeStubs | test_get_catalog_stub | D-08 | VERDE |
| TestWakeStubs | test_get_product_details_stub | D-10 stub | VERDE |

## Success Criteria Verification

| Critério | Status |
|----------|--------|
| COMP-04 SC-2: search retorna produtos com título+url+preço via GraphQL Wake | ATENDIDO — TestWakeEngineSearch::test_search_returns_products |
| COMP-04 SC-3: factory retorna WakeEngine (não NotImplementedError) | ATENDIDO — TestWakeFactory::test_factory_returns_wake_engine |
| COMP-04 SC-4: token ausente → BrandSearchResult.error (nunca 0 produtos silenciosos) | ATENDIDO — TestWakeTokenFailure::test_missing_token_returns_error |
| COMP-04 SC-4: calculate_shipping → None | ATENDIDO — TestWakeEngineSearch::test_calculate_shipping_returns_none |
| D-06: wake_access_token opcional em DynamicBrandCreate | ATENDIDO — TestWakeModels (3 testes) |
| D-08: discover_categories() → [] sem crash | ATENDIDO — TestWakeStubs::test_discover_categories_stub |
| Guard test_factory_wake_still_raises removido | ATENDIDO — realizado em 32-02 (verificado neste plano) |
| Suite completa verde (sem regressão) | ATENDIDO — 235 testes passando (224 + 11 novos Wake) |

## Implementation Notes

### Mock Seam

O seam de mock é `core.session_manager.SessionManager.get_session` (aiohttp), distinto do seam SFCC (`core.browser_manager.BrowserManager.fetch_html` — Playwright). A diferença é crítica: Wake usa API HTTP pura, sem browser rendering (D-11).

### Fixture _GRAPHQL_RESPONSE

Espelha a forma confirmada pelo spike 007:
- `aliasComplete` é relativo (`"produto/camisa-slim-123"`) → URL montada como `https://www.richards.com.br/produto/camisa-slim-123`
- `prices.price` é float em reais (`799.0`) → passthrough direto (sem /100)
- `images` é lista de `{url: ...}` (Armadilha 3)

### TestWakeTokenFailure — Estratégia de mock

O teste usa `EngineFactory().search_all_brands()` → `_search_one()` para verificar que o `ValueError` levantado por `WakeEngine._resolve_token` (token `None` + GET falhou) é capturado como `BrandSearchResult.error`. Dois patches necessários:
1. `services.engines.factory.brand_service.get_brand` — para que `EngineFactory.get_engine` retorne `WakeEngine`
2. `services.brand_service.brand_service.get_brand` — para que `WakeEngine.search()` receba o brand mock com `wake_access_token=None`
3. `_SESSION_GET_TARGET` com `side_effect=Exception` — falha no GET de auto-extração de token

## Known Stubs

Nenhum stub novo introduzido por este plano. Os stubs existentes no `wake_engine.py` (criados em 32-02) estão documentados no 32-02-SUMMARY.md e são cobertos pelos testes `TestWakeStubs`.

## Threat Surface Scan

Nenhuma superfície nova. Este plano cria apenas arquivos de teste (sem endpoints, sem caminhos de autenticação, sem acesso a arquivos externos). A hermeticidade dos testes (SessionManager mockado) é verificada pelo design — nenhuma chamada de rede real ocorre nos testes.

## Self-Check: PASSED

- [x] `backend/tests/test_wake_engine.py` existe (166 linhas, >80 mínimo)
- [x] Contém classes `TestWakeFactory`, `TestWakeEngineSearch`, `TestWakeTokenFailure`, `TestWakeModels`, `TestWakeStubs`
- [x] Usa mock seam `core.session_manager.SessionManager.get_session` (não rede real)
- [x] `pytest backend/tests/test_wake_engine.py -q --tb=short` → 11 passed
- [x] `pytest backend/tests/ -q` → 235 passed (sem regressão)
- [x] `test_factory_wake_still_raises` não existe como método de teste ativo em test_sfcc_engine.py
- [x] commit `4e976e9` existe (Task 1)
- [x] Positive factory test `test_factory_returns_wake_engine` presente em test_wake_engine.py
