---
phase: 39
slug: cobertura-de-marcas-hugo-boss-zara
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-26
---

# Phase 39 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `39-RESEARCH.md` § "Arquitetura de Validação".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (inferido de `backend/tests/test_vtex_brand_onboarding_contract.py`) |
| **Config file** | none — pytest detecta por convenção (sem `pytest.ini`) |
| **Quick run command** | `cd backend && python -m pytest tests/test_vtex_brand_onboarding_contract.py tests/test_hugoboss_category_mapping.py -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds (herméticos; rede ao vivo fica como spike) |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Req ID | Behavior | Wave | Threat Ref | Test Type | Automated Command | File Exists | Status |
|--------|----------|------|------------|-----------|-------------------|-------------|--------|
| COMP-06-a | `hugoboss.mappings` populados com slugs do vocabulário canônico | 1 | T-path-traversal | unit | `pytest tests/test_vtex_brand_onboarding_contract.py -x -q` | ✅ (contrato cobre auto_match + update_mappings + VALID_SLUGS) | ⬜ pending |
| COMP-06-b | `resolve_category_for_brands("camisas", ["hugoboss"])` retorna URL válida | 1 | — | unit | `pytest tests/test_vtex_brand_onboarding_contract.py::TestBrandContract::test_resolve_category_returns_valid_url -x -q` | ✅ (adaptar p/ hugoboss) ❌ W0 | ⬜ pending |
| COMP-06-c | `get_canonical_categories()` inclui `hugoboss` em `available_brands` | 1 | — | unit/integration | `pytest tests/test_hugoboss_category_mapping.py -x -q` | ❌ W0 | ⬜ pending |
| COMP-06-d | scan VTEX da Hugo Boss retorna `SearchProductResult` válido (mock) | 1 | T-product-sanitize | integration (mock) | `pytest tests/test_hugoboss_vtex_scan.py -x -q` | ❌ W0 | ⬜ pending |
| COMP-07-spike | `experiment.py` do spike 010 emite veredito GO/NO-GO com evidência | 1 | — | manual/spike | execução manual; `REPORT.md` é o artefato | ❌ W0 | ⬜ pending |
| COMP-07-engine (só GO) | `EngineFactory.get_engine("zara")` retorna `InditexEngine` | 2 | — | unit | `pytest tests/test_inditex_engine.py::TestInditexFactory -x -q` | ❌ W0 (só GO) | ⬜ pending |
| COMP-07-engine (só GO) | `InditexEngine.search("camiseta")` ≥1 `SearchProductResult` em `zara.com/br`, `price_full>0` (mock) | 2 | T-product-sanitize | unit (mock) | `pytest tests/test_inditex_engine.py::TestInditexEngineSearch -x -q` | ❌ W0 (só GO) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_hugoboss_category_mapping.py` — cobre COMP-06-c (`get_canonical_categories` inclui hugoboss) e COMP-06-b (resolve via `brand.mappings` dinâmicos)
- [ ] `backend/tests/test_hugoboss_vtex_scan.py` — cobre COMP-06-d (scan retorna `SearchProductResult` válido com mock de `VtexApiClient`)
- [ ] `.planning/spikes/010-zara-product-price/experiment.py` — artefato do spike (execução manual, não pytest)
- [ ] `backend/tests/test_inditex_engine.py` — cobre COMP-07 em GO (factory + search mock); criar **somente após veredito GO**

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Veredito de viabilidade pública da Zara (≥3 produtos reais título+URL+preço, reexecução estável) | COMP-07 | Depende de rede ao vivo + anti-bot Inditex; não-determinístico, fora dos herméticos | Rodar `experiment.py` do spike 010 com `camiseta`/`calça` (filtro masculino), 2 execuções; registrar GO/NO-GO + evidência em `REPORT.md` |
| Varredura-amostra real da Hugo Boss por categoria mapeada retorna produtos reais | COMP-06 | Validação dos `vtex_fq_path` exige catálogo VTEX ao vivo antes de persistir | Rodar o script de descoberta-e-persistência; conferir produtos reais (título+URL+preço) por categoria antes do commit dos mappings |
| Scheduler de 10 min inclui Hugo Boss sem falso positivo em re-execução inalterada | COMP-06 | Comportamento temporal do job real | Criar entrada via `POST /monitor/category` (brand=hugoboss); observar 2 ciclos de categoria inalterada sem "produto novo" |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
