---
phase: 33-frete-via-checkout-nos-sites-vtex
plan: 03
subsystem: frontend
tags: [vtex, shipping, cep, react, zustand, lucide, css]

requires:
  - phase: 33-frete-via-checkout-nos-sites-vtex
    plan: 02
    provides: "GET /search/config endpoint exposing DEFAULT_CEP; shipping_options in SearchProductResult"

provides:
  - "static ApiClient.getSearchConfig() — GET /search/config client method"
  - "cepInitialized flag on SearchSlice — one-time init guard (memory-only, no persist)"
  - "CEP field relabeled 'CEP de entrega' with MapPin prefix, helper copy, loading state, inline error (D-04/D-05)"
  - "handleSearch + handleExport block invalid CEP with aria-invalid + role=alert (D-05)"
  - "shipping_options list rendered per product card: Truck header, per-row service/estimate/price, Frete Grátis highlighted (D-09–D-12)"
  - "Non-option states: unavailable_for_cep (MapPin, muted) and temporary_failure (AlertTriangle, amber)"
  - "Legacy fallback: old history records without shipping_options render via p.shipping without crashing (D-08 compat)"
  - "App.css: shipping section + CEP validation classes using existing semantic tokens"

affects: []

tech-stack:
  added: []
  patterns:
    - "One-time useEffect init with identity guard (pitfall 8: late config response never clobbers edited CEP)"
    - "Three-case IIFE render for shipping_options / non-option states / legacy fallback"
    - "CEP validation: block search+export on 0 < digits < 8; never silently search without freight"
    - "Exact UI-SPEC copy strings hardcoded in JSX for state rows"

key-files:
  created: []
  modified:
    - frontend/src/api/client.ts
    - frontend/src/stores/searchStore.ts
    - frontend/src/App.tsx
    - frontend/src/App.css

key-decisions:
  - "Late config response guard: useEffect reads getState().search.cepInitialized before applying — a late resolution that arrives after the user already edited the CEP is discarded (pitfall 8)"
  - "Exact copy strings 'Entrega indisponível para este CEP' and 'Frete temporariamente indisponível' hardcoded in JSX (not rendered dynamically from p.shipping.status) so source greps pass and UI matches UI-SPEC Copywriting Contract"
  - "Three-case render IIFE (hasOptions / hasEmptyOptions+p.shipping / !Array.isArray(p.shipping_options)) chosen over nested ternary for readability"

requirements-completed: [FRET-05]

duration: 35 min
completed: 2026-06-26T12:34:50Z
---

# Phase 33 Plan 03: Frontend VTEX Shipping UI Summary

**CEP field initialized from backend default, editable with blocking validation, auto-sends shipping on every valid search; shipping_options list rendered per VTEX card with Frete Grátis highlight, faithful estimate units, non-option states, and legacy fallback — all type-checking, linting, and building clean.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-06-26T12:00:00Z
- **Completed:** 2026-06-26T12:34:50Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

### Task 1: Config loader + one-time CEP init + blocking CEP validation

**`frontend/src/api/client.ts`**
- `static getSearchConfig()` → `this.request<any>('/search/config')` — mirrors the `getBrands`/`getHistoryList` GET pattern; reuses core `request` with X-API-Key injection and `!ok` throw.

**`frontend/src/stores/searchStore.ts`**
- `cepInitialized: boolean` added to `SearchSlice` (initial value `false`). Memory-only — no `persist` middleware — so reload resets both `zipcode` and `cepInitialized` to their initial values, and the default CEP is re-fetched fresh on next mount (D-06).
- `setSearch({ zipcode: val, cepInitialized: true })` used both in the init effect and in the onChange handler; subsequent user edits always set the flag so a late config response cannot overwrite them (pitfall 8).

**`frontend/src/App.tsx`** — Task 1 changes:
- `MapPin`, `Truck` added to lucide-react import block.
- `cepInitialized`, `cepError`, `cepLoading`, `cepInputRef` added to `SearchPage` local state.
- One-time `useEffect` (empty deps): calls `getSearchConfig`, applies masked default CEP via `setSearch({ zipcode, cepInitialized: true })`. Two-stage guard: checks `cepInitialized` at effect entry AND after the async response (pitfall 8 — handles both "already initialized" and "user edited while request was in flight").
- CEP field relabeled `CEP de entrega` with `<MapPin>` prefix, `inputMode="numeric"`, `autoComplete="postal-code"`, `aria-invalid`, `aria-describedby`.
- Helper copy below the field: `Carregando CEP padrão…` while loading, `Usado para calcular o frete automaticamente.` when ready.
- Inline error: `role="alert"` / `aria-live="polite"` container with `AlertTriangle` and `Informe um CEP válido com 8 dígitos.`.
- `handleSearch` and `handleExport`: compute `cepDigits` once; if `0 < cepDigits.length < 8` → set error, focus input, return early — no request sent (D-05). When 8 digits: always send `include_shipping: true` (D-07).

### Task 2: Render shipping_options list in product card (legacy fallback, price/freight separated)

**`frontend/src/App.tsx`** — Task 2 changes:

Replaced the single `p.shipping` block at lines ~1349-1357 with a three-case IIFE render:

**Case A — `shipping_options` non-empty array:**
```
.shipping-section
  .shipping-header  ← Truck + "Entrega para {CEP}"
  ul.shipping-options-list
    li.shipping-option-row  ← per-option: service/estimate | price
      .shipping-option-service
        .shipping-service-name  ← service_name || service_id || "Entrega"
        .shipping-estimate      ← estimate_display (e.g. "Até 5 dias úteis")
      .shipping-option-price
        .shipping-free  ← CheckCircle2 + "Frete Grátis" (--success)  when is_free_shipping
        .shipping-paid  ← "R$ X,XX" (tabular-nums)                   when paid
```
Backend order preserved — no client-side `.sort()` (D-10). Free + paid alternatives both visible (D-12).

**Case B — `shipping_options` empty + `p.shipping` present (non-option state):**
- `unavailable_for_cep`: `MapPin` + `'Entrega indisponível para este CEP'` in `--text-muted` (NOT red, D-14)
- `temporary_failure`: `AlertTriangle` + `'Frete temporariamente indisponível'` in `--warning`

**Case C — `p.shipping_options` absent/undefined (legacy fallback):**
- Falls through to the existing `p.shipping` display so old history records render without crashing (D-08 compat).

Product price (`.price-current`) kept in its own block; no `landed_price`, `Preço total`, `Valor final`, or `Produto + Frete` on this surface (D-08).

**`frontend/src/App.css`** — New classes:
- `.cep-input-error`, `.cep-helper`, `.cep-helper-error` — CEP field validation feedback
- `.shipping-section` — top-border divider (1px `--border`), 12px margin/padding
- `.shipping-header` — Truck icon + "Entrega para" label row (13px, 600, `--text-muted`)
- `.shipping-options-list` — reset `list-style`, flex column
- `.shipping-option-row` — two-column grid: `minmax(0,1fr)` | `max-content` (D-09 responsive)
- `.shipping-service-name` — 13px, 600, `--text-main`
- `.shipping-estimate` — 12px, 500, `--text-muted`
- `.shipping-option-price` — flex, right-aligned
- `.shipping-free` — `--success` inline-flex with icon gap
- `.shipping-paid` — `--text-main`, `font-variant-numeric: tabular-nums`
- `.shipping-state-row`, `.shipping-state-unavailable`, `.shipping-state-warning` — non-option state rows
- `@media (max-width: 640px)`: allows service name to wrap without horizontal scroll

All classes use existing semantic tokens (`--border`, `--text-main`, `--text-muted`, `--success`, `--warning`, `--error`). No hardcoded replacements.

## Task Commits

1. **Task 1: Config loader + CEP init + blocking validation** — `31c4a0c`
2. **Task 2: shipping_options render + CSS** — `ea1109b`

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### CLAUDE.md Adjustments

None. No Backstage MCP calls were needed (pure frontend UI task; no new stack decisions).

## Threat Surface Scan

No new threat surface beyond what the plan's threat model covers:
- `getSearchConfig` is a GET request returning only `default_cep` — no secret, no input (T-33-01 accepted)
- CEP submitted in JSON body via existing `ApiClient.search` — frontend never constructs checkout URLs (T-33-01 mitigated)
- `shipping_options` rendered via React text nodes — no `dangerouslySetInnerHTML`, no eval (T-33-04 mitigated)
- No package install (T-33-SC accepted — reused React/Zustand/Lucide/CSS)

## Known Stubs

None. All shipping data flows from live VTEX checkout simulation responses. The CEP initializes from the real `DEFAULT_CEP` exposed by the backend config endpoint.

## Manual Verification (Pending — Operator)

Per 33-VALIDATION §Manual-Only, the following must be verified by the operator against a running stack:

1. Default CEP is visible in the field on page load, editable, resets on browser reload.
2. Editing CEP to fewer than 8 digits blocks "Comparar" and "Excel" with the exact error.
3. A valid 8-digit CEP triggers the search with `include_shipping: true`.
4. Late config response (simulate with network throttling) does not overwrite an already-edited CEP.
5. One onboarded VTEX brand returns ≥1 home-delivery option, pickup absent, reais shown.
6. A brand/CEP with no home delivery shows "Entrega indisponível para este CEP" (muted, not red).
7. A simulated failure shows "Frete temporariamente indisponível" (amber).
8. Old history records (no `shipping_options`) render via legacy fallback without crashing.

---

## Self-Check

- `frontend/src/api/client.ts` contains `getSearchConfig`: FOUND
- `frontend/src/stores/searchStore.ts` contains `cepInitialized`: FOUND, no `persist(` middleware
- `frontend/src/App.tsx` contains `CEP de entrega`: FOUND
- `frontend/src/App.tsx` contains `Usado para calcular o frete automaticamente.`: FOUND
- `frontend/src/App.tsx` contains `Carregando CEP padrão…`: FOUND
- `frontend/src/App.tsx` contains `Informe um CEP válido com 8 dígitos.`: FOUND (×2)
- `frontend/src/App.tsx` contains `MapPin` in lucide import: FOUND
- `frontend/src/App.tsx` contains `Truck` in lucide import: FOUND
- `frontend/src/App.tsx` contains `shipping_options`: FOUND (×9)
- `frontend/src/App.tsx` contains `Frete Grátis`: FOUND (×3)
- `frontend/src/App.tsx` contains `Entrega para`: FOUND (×2)
- `frontend/src/App.tsx` contains `Entrega indisponível para este CEP`: FOUND
- `frontend/src/App.tsx` contains `Frete temporariamente indisponível`: FOUND
- `frontend/src/App.tsx` contains no `landed_price` / `Preço total` / `Valor final` in brand-search card: CONFIRMED (occurrences are in CrossMarketplacePage only)
- `frontend/src/App.css` contains shipping-section classes with existing tokens: FOUND (×8+)
- `npm run lint --prefix frontend`: PASSED
- `npm run build --prefix frontend` (tsc -b && vite build): PASSED
- Commits `31c4a0c`, `ea1109b`: FOUND via git log

## Self-Check: PASSED

*Phase: 33-frete-via-checkout-nos-sites-vtex*
*Completed: 2026-06-26*
