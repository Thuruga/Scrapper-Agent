---
phase: 33-frete-via-checkout-nos-sites-vtex
plan: 01
subsystem: api
tags: [vtex, shipping, pydantic, pytest, pure-functions, tdd]

requires:
  - phase: 32-engine-wake-commerce-richards
    provides: "Modelos SearchProductResult/ShippingInfo e VtexApiClient existentes"

provides:
  - "vtex_shipping.py: parse_estimate, filter_and_sort_slas, select_candidate, classify_result (puros, sem HTTP)"
  - "ShippingInfo estendida com service_name, service_id, estimate_display, estimate_unit, is_free_shipping"
  - "SearchProductResult com shipping_options: List[ShippingInfo] = [] (aditivo)"
  - "37 testes unitários puros (test_vtex_shipping.py) cobrindo todos os comportamentos do contrato FRET-05"

affects:
  - 33-02 (wave 2: wiring dos helpers no _fetch_shipping HTTP real)
  - 33-03 (wave 3: renderizacao no frontend)

tech-stack:
  added: []
  patterns:
    - "Módulo puro stateless (sem self, sem I/O, sem async) espelhando vtex_parsing.py"
    - "TDD RED→GREEN: test commit antes do feat commit; 37 testes determinísticos sem rede"
    - "Evolução aditiva de Pydantic: campos novos com defaults seguros preservam registros antigos"
    - "Contrato explícito is None vs 0.0 (D-02): nunca tratar grátis como ausência de valor"

key-files:
  created:
    - backend/services/vtex_shipping.py
    - backend/tests/test_vtex_shipping.py
  modified:
    - backend/core/models.py

key-decisions:
  - "Backstage path: exception approved by operator — in-repo conventions of record (MCP not configured this session). Convenções seguidas: stateless helper style de vtex_parsing.py, Pydantic field style de models.py, test style de test_vtex_api_client.py + Clean Code / refactoring.guru."
  - "VTEX-only boundary (D-03) re-afirmada: vtex_shipping.py não toca SFCC/Wake/Shopify/marketplaces."
  - "parse_estimate retorna (value, unit, sort_seconds, display_text) ou None — nunca lança exceção em dado malformado."
  - "filter_and_sort_slas inclui is_free_shipping e price_reais no dict normalizado para consumo direto pelo caller Wave 2."
  - "ShippingInfo ganhou is_free_shipping como campo próprio (além do field em SearchProductResult) para que cada opção em shipping_options carregue seu flag individualmente."

requirements-completed: [FRET-05]

duration: 3 min
completed: 2026-06-25
---

# Phase 33 Plan 01: Frete VTEX — Parser Puro e Contrato de Modelo Summary

**Módulo puro `vtex_shipping.py` com quatro helpers (parse_estimate, filter_and_sort_slas, select_candidate, classify_result), ShippingInfo estendida com metadados de modalidade, e `shipping_options: List[ShippingInfo]` adicionado aditivamente ao SearchProductResult — 37 testes puros verdes (RED→GREEN TDD), 5 baseline client tests intactos.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-06-25T18:38:07Z
- **Completed:** 2026-06-25T18:41:45Z
- **Tasks:** 3 (Task 1 operator-resolved checkpoint; Task 2 TDD RED+GREEN; Task 3 model evolution)
- **Files modified:** 3

## Accomplishments

- Módulo puro `vtex_shipping.py` criado sem `self`, `async def`, ou `aiohttp` — quatro helpers determinísticos cobrindo parse de prazo, filtro/ordenação de SLAs, seleção de candidato, e classificação de resultado.
- 37 testes unitários puros em `test_vtex_shipping.py` cobrindo: filtro de pickup (channel + defensivos), centavos→reais com guarda R$1.000, quatro unidades VTEX (bd/d/h/m) com textos PT exatos, ordenação price-then-duration, coexistência grátis+pago, entradas malformadas, contrato None≠0.0.
- `ShippingInfo` estendida com `service_name`, `service_id`, `estimate_display`, `estimate_unit`, `is_free_shipping` (defaults seguros — registros antigos válidos sem migração).
- `SearchProductResult` com `shipping_options: List[ShippingInfo] = Field(default_factory=list)` adicionado aditivamente; `shipping`/`shipping_price`/`is_free_shipping`/`landed_price`/`calculate_landed_price` integralmente preservados (D-08).
- TDD gate compliance: `test(33-01)` → `feat(33-01)` → `feat(33-01)` confirmados em git log.

## Task Commits

1. **Task 1: Backstage coding-standards prerequisite** — operador resolveu; nenhum commit (gate-only task)
2. **Task 2 RED: test_vtex_shipping.py failing tests** — `8832c28` (test)
3. **Task 2 GREEN: vtex_shipping.py implementation** — `1c70535` (feat)
4. **Task 3: ShippingInfo + shipping_options** — `ce9818f` (feat)

**Plan metadata:** (docs commit abaixo)

_TDD tasks produced 2 commits: test (RED) → feat (GREEN)_

## Files Created/Modified

- `backend/services/vtex_shipping.py` — módulo puro: parse_estimate, filter_and_sort_slas, select_candidate, classify_result (230 linhas)
- `backend/tests/test_vtex_shipping.py` — 37 testes unitários puros (345 linhas)
- `backend/core/models.py` — ShippingInfo estendida (+5 campos); SearchProductResult ganha shipping_options

## Pure-Helper Function Names in vtex_shipping.py

| Função | Assinatura resumida | Propósito |
|--------|---------------------|-----------|
| `parse_estimate(shipping_estimate)` | `-> Optional[Tuple[int, str, int, str]]` | Parseia "5bd"→(5, "bd", sort_s, "Até 5 dias úteis"); None se inválido |
| `filter_and_sort_slas(slas)` | `-> List[Dict]` | Filtra pickup, valida, converte centavos, ordena price+duration |
| `select_candidate(items)` | `-> Optional[Tuple[str, str]]` | Retorna (sku_id, seller_id) da primeira oferta disponível |
| `classify_result(options, transport_error)` | `-> str` | "available" / "unavailable_for_cep" / "temporary_failure" |

## New ShippingInfo Fields Added

| Campo | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| `service_name` | `str \| None` | `None` | Nome da modalidade VTEX (ex: "Normal", "Expressa") |
| `service_id` | `str \| None` | `None` | ID interno da SLA VTEX |
| `estimate_display` | `str \| None` | `None` | Texto PT: "Até 5 dias úteis", "Até 12 horas", etc. |
| `estimate_unit` | `str \| None` | `None` | Unidade: "bd", "d", "h" ou "m" |
| `is_free_shipping` | `bool` | `False` | True quando price == 0.0 |

## Decisions Made

- **Backstage path:** Exceção aprovada pelo operador — in-repo conventions of record (MCP não configurado nesta sessão). Estilo espelhado: `vtex_parsing.py` (stateless helpers), `models.py` (Pydantic fields), `test_vtex_api_client.py` (pure assertions).
- **VTEX-only boundary (D-03) re-afirmada** antes de qualquer código: `vtex_shipping.py` não toca SFCC/Wake/Shopify/marketplaces.
- **is_free_shipping em ShippingInfo** (não só em SearchProductResult): cada opção em `shipping_options` carrega seu próprio flag, evitando que o caller faça `price == 0.0` manualmente.
- **filter_and_sort_slas retorna dict enriquecido** (com `price_reais`, `is_free_shipping`, `estimate_*`) para consumo direto pelo caller Wave 2 que construirá os objetos ShippingInfo.

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED | `8832c28` `test(33-01): add failing tests for vtex_shipping...` | PASS |
| GREEN | `1c70535` `feat(33-01): implement vtex_shipping pure helper module` | PASS |
| REFACTOR | — | Não necessário (código limpo na primeira passagem) |

## Deviations from Plan

None — plano executado exatamente como escrito. O operador pré-aprovou a exceção Backstage (Task 1), que é documentada como resolução de checkpoint, não como desvio.

## Issues Encountered

None.

## User Setup Required

None — sem configuração externa. Módulo puro + Pydantic sem dependências novas.

## Next Phase Readiness

- Wave 2 (33-02): pode importar `parse_estimate`, `filter_and_sort_slas`, `select_candidate`, `classify_result` de `services.vtex_shipping` e `shipping_options` de `core.models.SearchProductResult`. Contrato de unidade e classificação de estado estabelecidos.
- 5 testes baseline `test_vtex_api_client.py` intactos — nenhuma regressão no `_fetch_shipping` atual (que será evoluído no Wave 2).

---

## Self-Check

- `backend/services/vtex_shipping.py` existe: FOUND
- `backend/tests/test_vtex_shipping.py` existe: FOUND
- `backend/core/models.py` contém `shipping_options`: FOUND (1 ocorrência)
- `backend/core/models.py` contém `landed_price`: FOUND (10 ocorrências)
- `backend/core/models.py` contém `calculate_landed_price`: FOUND (2 ocorrências)
- Commits `8832c28`, `1c70535`, `ce9818f`: FOUND via git log
- 37 testes em test_vtex_shipping.py + 5 em test_vtex_api_client.py = 42 passando

## Self-Check: PASSED

*Phase: 33-frete-via-checkout-nos-sites-vtex*
*Completed: 2026-06-25*
