---
phase: 32-engine-wake-commerce-richards
plan: "01"
subsystem: spike
tags: [wake, graphql, spike, gate, richards]
dependency_graph:
  requires: []
  provides:
    - ".planning/spikes/007-wake-graphql-token-confirmation/experiment.py"
    - ".planning/spikes/007-wake-graphql-token-confirmation/REPORT.md"
  affects:
    - "planos 32-02 e 32-03 (gate GO libera execucao)"
tech_stack:
  added: []
  patterns:
    - "GET com allow_redirects=False para extracao de token publico de storefront (T-32-01)"
    - "POST GraphQL com variaveis $q/$first — sem interpolacao de string (T-32-02)"
    - "Token mascarado em stdout e REPORT (T-32-03)"
    - "Bootstrap ROOT+backend no sys.path (convencao de spikes)"
key_files:
  created:
    - ".planning/spikes/007-wake-graphql-token-confirmation/experiment.py"
    - ".planning/spikes/007-wake-graphql-token-confirmation/REPORT.md"
  modified: []
decisions:
  - "GO — fluxo GraphQL+TCS-Access-Token da Wake validado empiricamente contra Richards; planos 32-02 e 32-03 desbloqueados"
  - "prices.price retorna inteiro/float em reais (479 para produto de R$ 479); sem divisao por 100 necessaria"
  - "aliasComplete e relativo (ex: produto/camisa-linho-hortencia-196863); URL completa montada como https://{domain}/{aliasComplete}"
  - "Fix Rule 3 auto-aplicado: backend/ adicionado ao sys.path (core/ esta em backend/, nao raiz do repo)"
metrics:
  duration: "~10 min"
  completed: "2026-06-25"
  tasks_completed: 2
  tasks_total: 3
  files_created: 2
  files_modified: 1
---

# Phase 32 Plan 01: Spike Wake GraphQL Token Confirmation — Summary

## VEREDITO: GO

> **O gate esta liberado. Os planos 32-02 (engine) e 32-03 (testes) podem executar.**

O fluxo GraphQL + `TCS-Access-Token` da Wake foi validado empiricamente contra a **Richards** (www.richards.com.br). O spike retornou **5 produtos reais** com titulo, URL e preco, atendendo o threshold D-02 (>= 1 produto). Todas as 6 suposicoes A1-A6 do RESEARCH foram **CONFIRMADAS**.

## One-liner

Spike `experiment.py` confirma fluxo Wake GraphQL+TCS-Access-Token contra Richards: 5 produtos retornados, A1-A6 todos confirmados, `prices.price` em reais como inteiro (479), `aliasComplete` relativo necessita prefixo de dominio.

## Evidencia Principal

| Item | Valor |
|------|-------|
| Alvo | Richards (www.richards.com.br) — primario |
| Endpoint | `https://storefront-api.fbits.net/graphql` |
| HTTP home | 200 |
| HTTP GraphQL | 200 |
| Produtos retornados | 5 |
| Token prefixo | `tcs_richa_35...` (mascarado) |
| Estrategia de extracao | regex `storefrontAccessToken` (primaria, padrao SDK Wake) |
| Produto exemplo | "Camisa Linho Hortencia" — R$ 479 |
| URL exemplo | `https://www.richards.com.br/produto/camisa-linho-hortencia-196863` |

## Resolucao das Suposicoes A1-A6

| # | Suposicao | Resultado |
|---|-----------|-----------|
| A1 | `storefrontAccessToken` extraido == `TCS-Access-Token` aceito pelo GraphQL | **CONFIRMADO** |
| A2 | `aliasComplete` disponivel em `search.products.edges.node` | **CONFIRMADO** |
| A3 | `images.url` disponivel em `search.products.edges.node` | **CONFIRMADO** |
| A4 | `prices.price` em reais como float | **CONFIRMADO** (valor `479`, float/int < 10000) |
| A5 | Richards expoe `storefrontAccessToken` no HTML (padrao SDK Wake) | **CONFIRMADO** |
| A6 | Busca nao exige reCAPTCHA/sessao alem do `TCS-Access-Token` | **CONFIRMADO** |

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Criar experiment.py (bootstrap + extracao token + POST GraphQL) | `1e6620d` | `.planning/spikes/007-wake-graphql-token-confirmation/experiment.py` |
| 2 | Rodar spike e gerar REPORT.md com veredito GO/NO-GO | `0f5f613` | `.planning/spikes/007-wake-graphql-token-confirmation/REPORT.md` (+ fix sys.path em experiment.py) |
| 3 | Gate checkpoint (human-verify) | — | Aguardando revisao humana |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fix de sys.path para modulos em backend/**

- **Found during:** Task 2 (execucao do spike)
- **Issue:** `ModuleNotFoundError: No module named 'core'` — os modulos do projeto (core/, services/) ficam em `backend/` e nao na raiz do repo. O bootstrap `sys.path.insert(0, ROOT)` nao era suficiente.
- **Fix:** Adicionado `sys.path.insert(0, os.path.join(ROOT, "backend"))` apos o insert do ROOT. Spike 001 nao precisou disso pois `services/nlp_service.py` tambem resolve via `backend/` path que ja estava no env.
- **Files modified:** `.planning/spikes/007-wake-graphql-token-confirmation/experiment.py`
- **Commit:** `0f5f613`

## Key Findings for Plans 32-02 and 32-03

1. **`prices.price` e inteiro, nao float centavos**: valor retornado foi `479` (tipo `int` na resposta JSON). Parser deve aceitar `int` ou `float`, sem divisao por 100 (contraste com VTEX).
2. **`aliasComplete` e relativo**: `"produto/camisa-linho-hortencia-196863"` — engine deve montar URL completa como `f"https://{domain}/{alias.lstrip('/')}"`.
3. **`images.url` presente em `search`**: A3 confirmada — `images { url }` funciona dentro de `search.products.edges.node`. Quality Gate `validate_single` (obriga `image_url`) passara sem ajuste.
4. **Token via regex primaria**: `storefrontAccessToken\s*:\s*['"]([^'"]+)['"]` encontrou o token na home page da Richards sem necessidade do fallback.
5. **Shop2gether nao foi testado**: GO obtido no primeiro alvo (Richards); fallback nao foi necessario.

## Gate Decision

**VEREDITO: GO**

Os planos **32-02** (implementacao do `WakeEngine`) e **32-03** (testes herméticos) estao **DESBLOQUEADOS**.

Ver `.planning/spikes/007-wake-graphql-token-confirmation/REPORT.md` para evidencia completa.

## Self-Check: PASSED

- [x] `.planning/spikes/007-wake-graphql-token-confirmation/experiment.py` existe
- [x] `.planning/spikes/007-wake-graphql-token-confirmation/REPORT.md` existe
- [x] commit `1e6620d` existe (Task 1)
- [x] commit `0f5f613` existe (Task 2)
- [x] REPORT.md contem secao `## Veredito` com `GO` explicito
- [x] REPORT.md contem `## Evidencia`, `## Campos confirmados`, `## Formato do preco`, `## Token auto-extraido`, `## Alvo testado`
- [x] Token mascarado em todo output (`tcs_richa_35...`)
