---
phase: 43
slug: violacao-de-map-selos-de-promocao
status: implemented
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-04
---

# Phase 43 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `43-RESEARCH.md` and `43-CONTEXT.md`.

## Test Infrastructure

| Property | Value |
|----------|-------|
| Backend framework | pytest |
| Frontend framework | Vite / TypeScript |
| Backend quick run | `cd backend && python -m pytest tests/test_map_rules_service.py tests/test_map_evaluator_service.py tests/test_map_rules_routes.py -x -q` |
| Backend integration run | `cd backend && python -m pytest tests/test_phase43_search_contract.py tests/test_export_search_contract.py tests/test_export_cross_marketplace.py -x -q` |
| Frontend run | `cd frontend && npm run build` |
| Full backend suite | `cd backend && python -m pytest -q` |

## Sampling Rate

- After every task: run the task-specific automated command.
- After every wave: run the backend quick run or integration run mapped to that plan.
- Before verify-work: run full backend suite and frontend build.

## Per-Plan Verification Map

| Plan | Behavior | Test Type | Automated Command | Status |
|------|----------|-----------|-------------------|--------|
| 43-01 | Models/rule service/parser/evaluator are additive and deterministic | unit | `cd backend && python -m pytest tests/test_map_rules_service.py tests/test_map_evaluator_service.py -x -q` | passed |
| 43-02 | MAP rules CRUD routes validate payloads and persist JSON safely | route/integration | `cd backend && python -m pytest tests/test_map_rules_routes.py -x -q` | passed |
| 43-03 | Search and export flows surface MAP metadata/promotions without breaking existing contracts | integration/regression | `cd backend && python -m pytest tests/test_phase43_search_contract.py tests/test_export_search_contract.py tests/test_export_cross_marketplace.py -x -q` | passed |
| 43-04 | Settings UI and result badges compile cleanly against the new typed client | build | `cd frontend && npm run build` | passed |

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-map-json | Tampering | `backend/data/map_rules.json` | mitigate | Validate every record through Pydantic/service models; write via temp file + replace only. |
| T-map-price | Integrity | MAP verdict math | mitigate | Reuse `resolve_effective_price`; add tests that prove full/riscado price never drives a violation. |
| T-seller-default | Integrity | Marketplace seller attribution | mitigate | Reuse `seller_extraction.is_marketplace_default` and test first-party/default fallback behavior explicitly. |
| T-backcompat | Regression | Search/history/export contracts | mitigate | New fields must default safely and existing export/search tests must stay green. |
| T-ui-drift | Regression | Settings/result UI | mitigate | Keep UI incremental in `SettingsPage` and result-card branches; verify with `npm run build`. |

## Wave 0 Requirements

- [x] Add unit tests for MAP rule precedence and effective-price violation semantics.
- [x] Add route tests for CRUD over `map_rules.json`.
- [x] Add search/export contract tests that assert additive MAP/promotion fields do not break legacy consumers.
- [x] Frontend has no dedicated test runner; use build verification as the required gate.

## Manual-Only Verifications

| Behavior | Why Manual | Instructions |
|----------|------------|--------------|
| Operator edits a MAP rule from the settings surface and sees it reflected in subsequent search results | CRUD + UI interaction path | Start backend/frontend, create a rule for a product or brand, re-run a search, verify badge/infractor text updates. |
| Promotion badges visually read well across at least one first-party brand and one marketplace result | Visual formatting, mixed data density | Run one comparative search and one cross-marketplace search; confirm badges/rows render without collapsing card layout. |
| Exported Excel still opens cleanly with additive MAP/promotion columns or serialized text | Spreadsheet UX | Export one comparative search and one SKU/cross search after phase implementation; confirm file opens and columns are intelligible. |

## Validation Sign-Off

- [x] All plans have automated verification or an explicit manual gate.
- [x] No new package install is introduced.
- [x] Full backend suite green before close.
- [x] Frontend build green before close.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** code verified; manual UI UAT pending
