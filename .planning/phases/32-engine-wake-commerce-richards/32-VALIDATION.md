---
phase: 32
slug: engine-wake-commerce-richards
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-24
---

# Phase 32 — Validation Strategy

> Contrato de validação por phase para amostragem de feedback durante a execução.
> Derivado de `32-RESEARCH.md` §"Arquitetura de Validação" + §"Domínio de Segurança".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + pytest-asyncio 1.3.0 (já instalados) |
| **Config file** | `pytest.ini` / `pyproject.toml` (existente no repo — verificar antes de adicionar) |
| **Quick run command** | `python -m pytest backend/tests/test_wake_engine.py -q --tb=short` |
| **Full suite command** | `python -m pytest backend/tests/ -q` |
| **Estimated runtime** | ~20–40s (suite completa; 225 testes existentes verdes + novos Wake) |

---

## Sampling Rate

- **After every task commit:** `python -m pytest backend/tests/test_wake_engine.py -q --tb=short`
- **After every plan wave:** `python -m pytest backend/tests/ -q`
- **Before `/gsd-verify-work`:** Suite completa deve estar verde
- **Max feedback latency:** ~40s

---

## Per-Task Verification Map

> Mapa Requisitos → Testes (de `32-RESEARCH.md`). Task IDs definitivos são atribuídos pelo planner;
> abaixo a cobertura esperada por wave. SC-1 (spike) é gate manual da Wave 0.

| Item | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| Spike GO/NO-GO | 0 | COMP-04 SC-1 | — | Veredito registrado antes de qualquer código de engine | manual (spike) | `python .planning/spikes/007-wake-graphql-token-confirmation/experiment.py` | ❌ W0 | ⬜ pending |
| `search()` retorna ≥1 produto real | 1 | COMP-04 SC-2 | — | title+url+price via GraphQL Wake (não VTEX), SessionManager mockado | unit | `pytest backend/tests/test_wake_engine.py::TestWakeEngineSearch::test_search_returns_products -x` | ❌ W0 | ⬜ pending |
| Factory seleciona `WakeEngine` | 1 | COMP-04 SC-3 | — | `engine="wake"` retorna `WakeEngine` (não `NotImplementedError`); token por loja em cada request | unit | `pytest backend/tests/test_wake_engine.py::TestWakeFactory::test_factory_returns_wake_engine -x` | ❌ W0 | ⬜ pending |
| Token ausente → erro claro | 1 | COMP-04 SC-4 | T-32 token | `BrandSearchResult.error` com mensagem diagnosticável (nunca 0 produtos silenciosos) | unit | `pytest backend/tests/test_wake_engine.py::TestWakeTokenFailure::test_missing_token_returns_error -x` | ❌ W0 | ⬜ pending |
| `calculate_shipping` → None | 1 | COMP-04 / D-08 | — | Sem badge "Frete Grátis" indevido | unit | `pytest backend/tests/test_wake_engine.py::TestWakeEngineSearch::test_calculate_shipping_returns_none -x` | ❌ W0 | ⬜ pending |
| Campo `wake_access_token` opcional | 1 | D-06 | — | Opcional em `DynamicBrandCreate`/`DynamicBrand` sem quebrar marcas existentes | unit | `pytest backend/tests/test_wake_engine.py::TestWakeModels::test_model_wake_token_optional -x` | ❌ W0 | ⬜ pending |
| Stubs graciosos | 1 | D-08 | — | `discover_categories()`/`get_catalog()` retornam `[]` sem crash | unit | `pytest backend/tests/test_wake_engine.py::TestWakeStubs::test_discover_categories_stub -x` | ❌ W0 | ⬜ pending |
| Regressão suite completa | 1 | — | — | 225 testes existentes + novos Wake verdes | regression | `python -m pytest backend/tests/ -q` | ✅ (225) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `.planning/spikes/007-wake-graphql-token-confirmation/experiment.py` — spike isolado (fora de `backend/` até GO)
- [ ] `.planning/spikes/007-wake-graphql-token-confirmation/REPORT.md` — veredito GO/NO-GO gerado pelo spike
- [ ] `backend/tests/test_wake_engine.py` — cobre SC-2, SC-3, SC-4, D-06, D-08 (criado só após GO)

*Infraestrutura de testes existente (pytest, pytest-asyncio, conftest) cobre todos os requisitos — apenas os novos arquivos de teste precisam ser criados.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Spike confirma GraphQL+token retorna produtos reais da Richards (fallback Shop2gether) | COMP-04 SC-1 | Confirmação empírica contra API externa viva da Wake (não mockável — é o ponto do gate) | Rodar `experiment.py`; inspecionar `REPORT.md`: veredito GO exige ≥1 produto com título+URL+preço + token usado + endpoint |

---

## Validation Sign-Off

- [ ] Todas as tarefas têm verify `<automated>` ou dependência da Wave 0
- [ ] Continuidade de amostragem: nunca 3 tarefas consecutivas sem verify automatizado
- [ ] Wave 0 cobre todas as referências MISSING (spike + test_wake_engine.py)
- [ ] Sem flags de watch-mode
- [ ] Latência de feedback < 40s
- [ ] `nyquist_compliant: true` setado no frontmatter (após sign-off na execução)

**Approval:** pending
