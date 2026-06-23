---
phase: 27
slug: hist-rico-completo-gest-o-de-marcas-na-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-20
---

# Phase 27 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `27-RESEARCH.md` → Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (backend)** | pytest (in-repo `tests/` dir; pattern: in-memory service + direct async route-fn call via `asyncio.run`, singletons monkeypatched — see `tests/test_brand_active.py`) |
| **Config file** | none (no `pytest.ini`/`pyproject.toml`; discovery by convention `tests/test_*.py`) |
| **Framework (frontend)** | NONE installed (no vitest/jest, no `test` script). FE validation = `tsc -b` (type-check via build) + `eslint` + scripted manual UAT |
| **Quick run command** | backend: `python -m pytest tests/test_search_history_comparative.py -x` · frontend: `cd frontend && npm run build && npm run lint` |
| **Full suite command** | backend: `python -m pytest tests/ -x` · frontend: `cd frontend && npm run build` |
| **Estimated runtime** | backend ~5–15s; frontend build ~15–30s |

---

## Sampling Rate

- **After every task commit:** backend `python -m pytest tests/test_search_history_comparative.py -x`; frontend `npm run build` (type gate) + `npm run lint`
- **After every plan wave:** backend full suite `python -m pytest tests/ -x`; frontend `npm run build`
- **Before `/gsd-verify-work`:** backend suite green + frontend builds clean + manual UAT of the 3 success criteria
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

> Task IDs are assigned by the planner; rows below are keyed by requirement and become task `<automated>` blocks during planning.

| Req | Behavior | Threat Ref | Test Type | Automated Command | File Exists | Status |
|-----|----------|------------|-----------|-------------------|-------------|--------|
| HIST-01 | `POST /search` creates a `type="search"` history record | — | integration | `pytest tests/test_search_history_comparative.py::test_post_search_persists_history -x` | ❌ W0 | ⬜ pending |
| HIST-01 | Persisted record COMPLETED; `results` = inner `List[BrandSearchResult]` (**shape contract**) | — | integration | `pytest tests/test_search_history_comparative.py::test_persisted_results_shape_is_inner_list -x` | ❌ W0 | ⬜ pending |
| HIST-01 | On search exception, record marked FAILED with `error` set | T-Tampering | integration | `pytest tests/test_search_history_comparative.py::test_search_failure_marks_failed -x` | ❌ W0 | ⬜ pending |
| HIST-01 | `create_job(type="search")` + `update_job` round-trip via service | — | unit | `pytest tests/test_search_history_comparative.py::test_history_service_search_type -x` | ❌ W0 | ⬜ pending |
| HIST-02 | Reopen re-displays without re-scraping (`getHistoryDetail` → render shape) | — | manual UAT + type-check | `cd frontend && npm run build` + manual | n/a | ⬜ pending |
| HIST-02 | `App.tsx` declares `preloadedJobId` and `renderTab` passes it to both pages | — | static / type-check | `cd frontend && npm run build` + code review | n/a | ⬜ pending |
| MGMT-02 | `PATCH /brands/{key}/active` toggles `is_active` | T-Tampering (404 on unknown key) | integration (existing) | `pytest tests/test_brand_active.py -x` | ✅ exists | ⬜ pending |
| MGMT-02 | `ApiClient.setBrandActive` issues PATCH with correct body | — | manual + type-check | `cd frontend && npm run build` + manual | n/a | ⬜ pending |
| MGMT-02 | Inactive brands render with visual distinction; virtual marketplaces (ML/NS/AMZ) have no toggle | — | manual UAT | manual | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_search_history_comparative.py` — covers HIST-01 (persistence, **shape contract**, FAILED path, service round-trip). Follow the in-memory + monkeypatch-singleton pattern from `tests/test_brand_active.py` (patch `routes_search.search_history_service` and the engine/orchestrator singleton).
- [ ] No frontend test framework — **do not install one in this phase** (scope creep; would trigger package-legitimacy gate). FE behavior validated by `tsc -b` build + `eslint` + scripted manual UAT.
- [ ] Framework install: none needed (pytest already in use).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Reabrir busca comparativa do histórico reexibe resultados idênticos sem nova raspagem | HIST-02 | No FE test framework | Rodar uma busca comparativa; abrir a seção de histórico da aba; clicar na entrada; confirmar colunas/resultados idênticos e ausência de chamada de scrape (Network) |
| Reabrir busca por SKU do histórico reexibe resultados | HIST-02 | No FE test framework | Idem na aba SKU |
| Toggle ativar/desativar marca persiste após refresh; inativas distinguidas; virtuais sem toggle | MGMT-02 | No FE test framework | Desativar uma marca → confirmar dimmed/badge; refresh → estado mantido; confirmar ML/NS/AMZ sem toggle |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify (FE tasks rely on build+lint+manual — flagged)
- [ ] Wave 0 covers all MISSING references (`tests/test_search_history_comparative.py`)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
