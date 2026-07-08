---
phase: 38-ux-de-busca-monitoramento-quick-wins
verified: 2026-07-01T00:00:00Z
status: passed
score: 6/6 must-haves verified (codebase); 4/4 manual UAT checks recorded
overrides_applied: 0
human_verification_confirmed: "All 4 items below were confirmed via 38-HUMAN-UAT.md (4/4 passed, operator confirmed live 2026-07-06)."
human_verification:
  - test: "UX-01 — Responsive .grid-category at 768px (both screens)"
    expected: "At exactly 768px viewport, both MonitoredCategoriesPage and CategoryPage show the sidebar/tree column stacked above the content column, no horizontal scrollbar, no overlap; products modal grid does not overflow."
    why_human: "No frontend test runner/DOM viewport harness exists in this project (confirmed in 38-RESEARCH.md); this is a rendered-layout check."
  - test: "UX-06 — Search-history top-right icon + type-scoped badge (both tabs)"
    expected: "History icon visible top-right without scrolling on load on both comparativa and SKU tabs; clicking toggles the panel; badge count is type-filtered and may differ between tabs; tooltip reads 'Ver histórico de buscas'."
    why_human: "Visual placement/scroll-position and interactive toggle behavior cannot be verified via static analysis alone."
  - test: "UX-07 — SKU pattern validation + CEP inline on same row"
    expected: "Invalid SKU + blur shows red inline error with exact copy and disables submit; valid SKU clears error and enables submit; CEP renders on same row as SKU above 980px collapse."
    why_human: "Blur-triggered validation timing and visual row layout require interactive browser confirmation."
  - test: "UX-08 — Auto-start first sweep sequence (D-05/D-06)"
    expected: "After Salvar: modal closes immediately, success toast appears, new row shows spinner, no manual 'Iniciar' needed, spinner clears and products modal auto-opens when scan completes, failure toast on scan failure."
    why_human: "End-to-end sequence spanning frontend polling state + real backend async completion; requires a live run."
---

# Phase 38: UX de Busca/Monitoramento — Quick Wins Verification Report

**Phase Goal:** As telas de monitor de categoria e varredura funcionam corretamente em viewports menores; a lista de monitoramento exibe o valor da promoção; o histórico de buscas fica acessível no canto superior direito em todas as abas; o campo de SKU valida o padrão e o CEP fica inline; o monitor de categoria inicia a varredura automaticamente ao selecionar uma categoria; e a Lacoste deixa de aparecer em qualquer superfície de busca.

**Verified:** 2026-07-01
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `.grid-category` collapses to 1 column at ≤768px on both category-monitor and category-sweep screens, no new CSS methodology (UX-01) | VERIFIED (code) | `frontend/src/App.css:181` opens `@media (max-width: 768px)`; `.grid-category { grid-template-columns: 1fr; }` at line 207-209, inside that block. Base rule (350px 1fr) unaffected above 768px (line 370-374). `grep -c "@container"` = 0. `npm run build` succeeds. Visual confirmation still pending (see Human Verification). |
| 2 | Monitor list shows promo (strikethrough pre-discount + current) price from the polled payload, no new network call (UX-02) | VERIFIED | `frontend/src/App.tsx:422-431` — `.monitor-pricing` renders `price-original` strikethrough span using `m.last_price + m.last_price_discount` guarded by `m.last_price_discount > 0 && m.last_price_discount < m.last_price * 5` (CR-02 sanity-bound fix, commit `8ef9af2`, present in working tree). No new `ApiClient`/fetch call added for this render (reuses existing polled `GET /monitors` payload). Backend: `last_price_discount` field added to both `PriceMonitorConfig`/`PriceHistoryEntry` (`backend/core/models.py:288,306`); discount-aware `has_change` + WS payload in `price_monitor_service.py:178-237`. Test `test_price_monitor_promo_only_change_triggers_history` passes. |
| 3 | Top-right History icon visible without scrolling on both search tabs, toggles the existing HistoryList panel, badge is type-scoped (UX-06) | VERIFIED (code) | `frontend/src/App.tsx:1503-1537` (SearchPage) and `2212-2246` (CrossMarketplacePage) each render an identical `.btn-icon` History button as the first element in `.page-content`, wired to `HistoryList` via `collapsed`/`onToggleCollapsed`/`onCountChange` controlled props. `HistoryList` (line 791-823) filters `items` by `type` BEFORE reporting `onCountChange?.(items.length)` — badge is type-scoped, not raw total. `getHistoryList` call count unchanged (1 call site, no duplication). Visual "no scrolling on load" still pending (see Human Verification). |
| 4 | SKU field validates `^ML\.05\.\d{7}$` on blur/submit with reused CEP-style inline error, disabled submit while invalid, SKU/CEP row on shared `.search-main-row`/`.search-field` layout (UX-07) | VERIFIED | `frontend/src/App.tsx:63-64` defines `SKU_PATTERN`/`SKU_ERROR_MSG` (D-09 copy verbatim). Lines 2249-2280: SKU field uses `.search-main-row`/`.search-field`, reuses `.cep-input-error`/`.cep-helper`/`.cep-helper-error` classes, validates on blur (line 2267-2270) and clears on edit (line 2265). Submit button `disabled={loading || !isTargetSkuValid}` (line 2307). `handleSearch` (line 2189-2195) also blocks submit-time on invalid SKU. No `sku-input-error` class invented (0 hits). |
| 5 | Selecting/creating a monitored category triggers the scan automatically: modal closes immediately, row spinner shows, products modal auto-opens on completion, no manual "Iniciar" trigger, bounded poll (UX-08) | VERIFIED | `frontend/src/App.tsx:2903-2928` (`handleSubmit`): creates category, closes modal immediately, `toast.success('Categoria adicionada. Iniciando primeira varredura…')` (D-08 verbatim), calls `startAutoSweepPoll`. `startAutoSweepPoll` (2862-2901): polls `GET /monitor/categories` every `AUTO_SWEEP_POLL_MS` (5000ms) up to `AUTO_SWEEP_MAX_ATTEMPTS` (20), calls existing `handleViewProducts` (not reimplemented) when `last_scraped_at` becomes non-null, clears on completion/error/max-attempts. Unmount cleanup effect at line 2784-2789 clears all intervals. No new backend endpoint referenced (uses existing `getMonitoredCategories`). No `alert(` left in `handleSubmit`. |
| 6 | Lacoste (inactive) never appears in any search-surface brand selector — comparativa, SKU, category, scheduler, export (COMP-08) | VERIFIED | `backend/data/brands.json`: `lacoste.is_active = false`. `list_brands(active_only=True)` (`brand_service.py:95-98`) filters on `is_active`, and is the sole chokepoint used by `routes_search.py` (3 call sites), `routes_category.py:187`, `cross_marketplace_service.py:184`, `engines/factory.py:93`, `banner_job_service.py` (2 call sites). New regression test `TestLacosteExcludedFromActiveOnly::test_lacoste_absent_from_active_only` passes against the real `brand_service` singleton. No dedicated scheduler/export module exists beyond these chokepoints (verified via repo-wide `list_brands(` grep) — coverage matches the plan's documented scope. |

**Score:** 6/6 truths verified at the codebase level. All 6 have a corresponding pending manual UAT confirmation (except truth 5/UX-08 has no completed browser run either) — see Human Verification section. `HUMAN-UAT.md` for this phase records **0 of 4 passed, 4 pending**, unchanged since plan creation (commit `b598449`), despite `.planning/REQUIREMENTS.md` marking UX-01/02/06/07/08/COMP-08 as `[x]` Complete. That REQUIREMENTS.md status is premature relative to the phase's own `38-VALIDATION.md` gate ("Before /gsd-verify-work: Full suite must be green + manual UAT complete").

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/core/models.py` | `last_price_discount` field on both models | VERIFIED | 2 hits, both `Optional[float] = None` (lines 288, 306) |
| `backend/services/price_monitor_service.py` | Discount-aware change detection + WS payload | VERIFIED | `price_discount`/`price_full` in `has_change`, `PriceHistoryEntry` ctor, and WS dict (lines 178-237) |
| `backend/tests/test_price_monitor.py` | D-01/D-03 regression test | VERIFIED | `test_price_monitor_promo_only_change_triggers_history` present and passing |
| `backend/tests/test_brand_active.py` | COMP-08 regression class | VERIFIED | `TestLacosteExcludedFromActiveOnly` present and passing |
| `backend/tests/test_category_monitor.py` | UX-08 backend contract test | VERIFIED | File exists, asserts `last_scraped_at` write, passing |
| `frontend/src/App.css` | `@media (max-width: 768px)` `.grid-category` rule | VERIFIED | Present at line 207, inside `@media` block opened line 181 |
| `frontend/src/App.tsx` | History icon, SKU validation, auto-sweep, promo render | VERIFIED | All four sub-features present and wired (see truths 2-5 evidence) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `price_monitor_service.py` `_monitor_loop` | `models.py` `PriceHistoryEntry`/`PriceMonitorConfig` | `last_price_discount=...` constructor arg + `config.last_price_discount` assignment | WIRED | Confirmed at lines 223, 230 |
| `test_brand_active.py` | `brand_service.list_brands` | `active_only=True` chokepoint assertion | WIRED | Real singleton, no mocking, test passes |
| `App.tsx` content-header (SearchPage/CrossMarketplacePage) | `HistoryList` collapsed state | Controlled props (`collapsed`/`onToggleCollapsed`/`onCountChange`) | WIRED | Identical wiring on both tabs, verified lines 1503-1537, 2212-2246 |
| `App.css` `@media 768px` | `.grid-category` | `grid-template-columns: 1fr` override | WIRED | Confirmed inside the correct media block |
| `MonitoredCategoriesPage.handleSubmit` | `GET /monitor/categories` (poll) + `handleViewProducts` | `last_scraped_at` non-null → stop poll → call `handleViewProducts` | WIRED | Confirmed lines 2862-2901, 2903-2928; reuses existing fetch, no duplication |
| `.monitor-pricing` render | `PriceMonitorConfig.last_price_discount` (from Plan 01) | Polled `GET /monitors` payload | WIRED | Confirmed lines 422-431; CR-02 sanity bound present |
| SKU input | `.cep-input-error`/`.cep-helper`/`.cep-helper-error` | Reused validation classes | WIRED | Confirmed lines 2252, 2274-2278; no new `sku-input-error` class |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `.monitor-pricing` (MonitorPage) | `m.last_price_discount`, `m.last_price` | Polled `GET /monitors` → `PriceMonitorConfig` serialized by `_monitor_loop`'s persisted state | Yes — backend `_monitor_loop` populates `last_price_discount` from real scraped `product.price_discount`, persisted via `_save_monitors()` | FLOWING |
| `MonitoredCategoriesPage` row spinner / auto-open | `latest.find(...).last_scraped_at` | Polled `GET /monitor/categories` ← `run_category_scan` writes `last_scraped_at` on real scan completion | Yes — confirmed by `test_category_monitor.py` backend contract test | FLOWING |
| `HistoryList` badge count | `items.length` (type-filtered) | `ApiClient.getHistoryList()` real fetch, filtered client-side by `type` | Yes — same fetch already used for the panel body, no static/empty stub | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend phase-38 test subset | `cd backend && python -m pytest tests/test_price_monitor.py tests/test_brand_active.py tests/test_category_monitor.py -q` | `19 passed` | PASS |
| Full backend suite (regression check) | `cd backend && python -m pytest -q` | `473 passed, 1 warning` (pre-existing unawaited-coroutine warning, unrelated) | PASS |
| Frontend build | `cd frontend && npm run build` | `tsc -b && vite build` succeeded, `built in 1.06s` | PASS |
| Lacoste `is_active` flag | `python -c` reading `brands.json` | `lacoste False` | PASS |
| No container-query methodology introduced | `grep -c "@container" frontend/src/App.css` | `0` | PASS |

### Probe Execution

Step 7c: SKIPPED — no `scripts/*/tests/probe-*.sh` files exist in this repository and no PLAN/SUMMARY/VALIDATION artifact for this phase declares probe-based verification (confirmed via `find`/grep — this phase uses pytest + `npm run build` + manual UAT, not shell probes).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| UX-01 | 38-02 Task 1 | Responsive category monitor/sweep screens | SATISFIED (code) / NEEDS HUMAN (visual) | CSS media query verified; visual confirmation pending in HUMAN-UAT.md §1 |
| UX-02 | 38-01 + 38-03 Task 3 | Promo value in monitoring list | SATISFIED | Backend + frontend both verified with passing tests and CR-02 fix present |
| UX-06 | 38-02 Task 2 | Search history top-right, both tabs | SATISFIED (code) / NEEDS HUMAN (visual/interaction) | Wiring verified; visual confirmation pending in HUMAN-UAT.md §2 |
| UX-07 | 38-03 Task 1 | SKU pattern validation + inline CEP | SATISFIED (code) / NEEDS HUMAN (interaction) | Validation logic verified; interaction confirmation pending in HUMAN-UAT.md §3 |
| UX-08 | 38-03 Task 2 | Auto-start category scan | SATISFIED (code) / NEEDS HUMAN (end-to-end) | Poll/spinner/auto-open logic verified; live-run confirmation pending in HUMAN-UAT.md §4 |
| COMP-08 | 38-01 Task 1 | Lacoste excluded everywhere | SATISFIED | Chokepoint + regression test verified; no human check required (fully automatable, confirmed) |

No orphaned requirements: all 6 IDs declared across the three plans' frontmatter are accounted for above, and match the REQUIREMENTS.md entries under sections B/C exactly.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/services/price_monitor_service.py` | 211, 215 | `sorted(config.available_colors)` / `sorted(current_sizes)` can raise `TypeError` on mixed/None entries (CR-01, pre-existing) | INFO (out of scope) | Predates phase 38; not touched by this phase's diff (only the discount-check lines 204-208 were added nearby); per task instructions, not counted as a phase-38 regression or blocker |
| `frontend/src/App.tsx` | — | None found specific to phase-38-modified regions (no `TBD`/`FIXME`/`XXX`, no placeholder returns, no empty handlers in the reviewed sections) | — | — |

No blocker-level anti-patterns introduced by this phase. CR-02 (the one critical finding attributable to this phase's new code) was fixed post-review in commit `8ef9af2` and is confirmed present in the working tree.

### Human Verification Required

### 1. UX-01 — Responsive `.grid-category` at 768px (both screens)

**Test:** At exactly 768px viewport (devtools responsive mode), open the category-monitor screen and the category-sweep screen; also open a category's products modal at 768px.
**Expected:** Sidebar/tree column stacks above the content column on both screens, no horizontal scrollbar, no element overlap; products modal grid does not overflow.
**Why human:** No frontend DOM/viewport test runner exists in this project (confirmed in 38-RESEARCH.md); this is purely a rendered-layout check.

### 2. UX-06 — Search-history top-right icon + type-scoped badge (both tabs)

**Test:** Open the comparativa tab, confirm the History icon is visible top-right without scrolling and shows tooltip "Ver histórico de buscas"; click to toggle; note badge count. Repeat on the SKU tab; compare badge counts.
**Expected:** Icon visible without scroll on load on both tabs; toggle works; badge counts are type-scoped and may differ between tabs.
**Why human:** Visual placement/scroll-position and click-driven toggle behavior require interactive browser confirmation.

### 3. UX-07 — SKU pattern validation + CEP inline on same row

**Test:** On the SKU tab, type an invalid SKU and blur; then type a valid SKU (`ML.05.0326046`); confirm CEP renders on the same row as SKU above the 980px breakpoint.
**Expected:** Invalid SKU shows the exact red inline error and disables submit; valid SKU clears the error and enables submit; CEP is inline with SKU at desktop width.
**Why human:** Blur-timing behavior and visual row layout require interactive browser confirmation (build only catches type errors, not runtime DOM layout).

### 4. UX-08 — Auto-start first sweep sequence (D-05/D-06)

**Test:** Create a new monitored category and click "Salvar"; observe the full sequence through scan completion (or failure).
**Expected:** Modal closes immediately; success toast appears; new row shows spinner with no manual "Iniciar" click; spinner clears and products modal auto-opens when the background scan finishes; failure toast appears on scan failure.
**Why human:** This is an end-to-end sequence spanning frontend polling state and a real backend async scan; it requires a live run against the actual backend, not just static code inspection.

### Gaps Summary

No code-level gaps were found — all 6 must-haves (UX-01, UX-02, UX-06, UX-07, UX-08, COMP-08) have their implementation verified in the codebase: correct artifacts exist, are substantive (not stubs), are wired to real data sources, and (where applicable) are covered by passing automated tests. The full backend suite (473 tests) and frontend build both pass with no regressions. The previously-identified critical review finding CR-02 (monitor card derived-price sanity bound) is confirmed fixed in the current working tree; CR-01 is confirmed pre-existing and outside this phase's diff, per the verification note.

The phase is NOT ready to be marked `passed` because its own `38-VALIDATionN.md` gate explicitly requires manual UAT completion for UX-01/UX-06/UX-07/UX-08 before verification, and `38-HUMAN-UAT.md` still shows all 4 tests as `pending` (0 passed) — unchanged since the plan was created, i.e., no human has yet run the browser checks described above. `.planning/REQUIREMENTS.md` currently marks these requirements `[x]` Complete, which is inconsistent with the phase's own unclosed UAT file; that inconsistency should be resolved by actually performing the 4 UAT checks (or by formally overriding the UAT requirement) before the phase is considered done.

---

_Verified: 2026-07-01_
_Verifier: Claude (gsd-verifier)_
