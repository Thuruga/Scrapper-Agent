---
phase: 27
slug: hist-rico-completo-gest-o-de-marcas-na-ui
status: passed
verified: 2026-06-20
method: adversarial (dimensional review → refute → dual-lens goal-backward verification → fix → re-verify)
must_haves_met: 6/6
requirements: [HIST-01, HIST-02, MGMT-02]
---

# Phase 27 — Verification

**Goal:** Todas as buscas ficam registradas no histórico (comparativa e por SKU), qualquer busca salva pode ser reaberta para reexibição, e o usuário tem um campo único na interface para adicionar, remover e ativar/desativar marcas.

**Verdict:** **PASSED** — all three success criteria and all three landmines met; 2 blockers found during verification were fixed (commit `98995f0`) and re-verified closed.

## How this was verified

A multi-agent adversarial workflow (29 agents) reviewed the merged code across correctness/security/integration, refuted each finding, and verified each success criterion with two independent lenses (code-trace + adversarial). Initial verdict was `gaps_found` (2 blockers). Both were fixed and a focused adversarial re-check confirmed closure with no regression. Deterministic gates: backend `pytest` 167 passed (1 pre-existing cv2/OCR failure, unrelated), HIST-01 + brand tests 11/11, frontend `npm run build` exits 0, lint unchanged at pre-existing baseline.

## Must-haves (goal-backward)

| # | Must-have | Met | Evidence |
|---|-----------|-----|----------|
| SC1 | HIST-01: comparative `POST /search` persists (`type="search"`, COMPLETED with INNER `List[BrandSearchResult]`, FAILED on exception) and reopens without re-scrape | ✅ | `api/routes_search.py` (`search_products`: `create_job(type="search")` → `update_job(COMPLETED, results=result.model_dump(mode="json")["results"])`, except→FAILED+raise); SearchPage reopen `useEffect` via `getHistoryDetail`; tests assert inner-list shape |
| SC2 | HIST-02: `preloadedJobId` owned and propagated by `App.tsx` to BOTH pages; history row click reopens in the correct tab | ✅ | `App.tsx`: App-level `preloadedJobId` state, `handleReopen`, `renderTab` passes `preloadedJobId`/`onClearPreloadedJob`/`onReopen` to both pages; reusable `HistoryList` per tab |
| SC3 | MGMT-02: unified brand management — add + remove + activate/deactivate in one place | ✅ | `SettingsPage`: add form + confirm-gated delete + per-row active toggle (`ApiClient.setBrandActive` → `PATCH /brands/{key}/active`) + inactive visual distinction |
| L1 | Stored result is the inner list, not the `ComparisonResult` wrapper | ✅ | `routes_search.py` `model_dump(mode="json")["results"]`; `test_persisted_results_shape_is_inner_list` (negative assertion) |
| L2 | Only COMPLETED history rows are clickable-to-reopen; FAILED/PENDING non-clickable | ✅ | `HistoryList`: COMPLETED rows are `<button onClick=onReopen>`, FAILED/PENDING are non-clickable |
| L3 | Active toggle hidden for virtual marketplaces (mercado_livre/netshoes/amazon) to avoid 404 | ✅ | `App.tsx` `VIRTUAL` guard, `canToggle` gate |

## Blockers found and FIXED (commit 98995f0)

1. **preloadedJobId never cleared after reopen** — `renderTab` fully remounts pages on tab switch, so returning to a tab silently re-fetched the old history entry and overwrote current results. **Fixed:** both reopen `useEffect`s now clear `preloadedJobId` in `.finally()`. Re-verified: clean settle (no loop), reopened results stay on screen, same-row re-click now re-triggers.
2. **Sidebar nav kept a stale preloadedJobId** — a cross/SKU job could be handed to the comparative page and rendered through the wrong template. **Fixed:** new `navigateTab()` helper clears `preloadedJobId` before switching; all 6 sidebar buttons route through it. Re-verified closed.

Also hardened (warnings): `encodeURIComponent` on brand path segments (`deleteBrand`, `setBrandActive`); `update_job` annotation `Optional[list]` → `Optional[Any]`.

## Non-blocking follow-ups (not gating; tracked)

- **History list has no server-side cap / client pagination** (`list_jobs()` returns all; 30-day cleanup only at startup). Low impact (single-user tool; panel collapsed by default), but a `top-N` cap + "show older" is a worthwhile follow-up. Recorded as a backlog todo.
- **Narrow async race:** reopen a job then click a sidebar tab before `getHistoryDetail` resolves → the stale result simply does not render (no data corruption). Inherent to the async lifecycle; acceptable.
- **Nits:** `import uuid` kept inline in `routes_search.py`; `brands_searched` field stored on reopen but unread by the renderer. Cosmetic.

## Human UAT (recommended, non-gating — no frontend test framework)

1. Run a comparative search → open the Histórico panel → click a COMPLETED row → confirm results re-display identically with NO `/search` scrape call (DevTools Network shows only `GET /history/{id}`).
2. Repeat for a SKU search in the SKU tab.
3. Toggle a brand inactive in Marcas → reload → confirm `is_active=false` persists (dimmed + "Inativa") and it's excluded from active-only comparative searches.
4. Confirm mercado_livre / netshoes / amazon rows show no Power toggle.
5. Confirm FAILED/PENDING history rows are non-clickable.
