---
phase: 27-hist-rico-completo-gest-o-de-marcas-na-ui
plan: "03"
subsystem: frontend
tags: [history, reopen, HistoryList, preloadedJobId, react, typescript]
dependency_graph:
  requires: ["27-01", "27-02"]
  provides: ["HIST-02-complete"]
  affects: ["frontend/src/App.tsx"]
tech_stack:
  added: []
  patterns:
    - "refreshKey prop pattern for triggering useEffect re-fetch from parent"
    - "deleteTick internal state pattern for delete-triggered refetch without exposing imperative API"
    - "Guarded HistoryList mount: {onReopen && <HistoryList .../>} — component only mounts when App wires the callback"
    - "Type alias prop pattern (SearchPageProps/CrossMarketplacePageProps) to declare onReopen in type without unused-var lint errors in Task 1"
key_files:
  modified:
    - frontend/src/App.tsx
decisions:
  - "refreshKey mechanism chosen over imperative refetch: each page owns historyRefreshKey (useState(0)), bumps it after successful handleSearch; HistoryList useEffect deps include refreshKey so bump triggers refetch — resolves Pitfall 4"
  - "deleteTick internal counter: delete handler calls setDeleteTick(t=>t+1) which is in the useEffect deps alongside refreshKey — avoids exposing a refetch ref/callback"
  - "loading state removed from HistoryList to avoid react-hooks/set-state-in-effect lint error (calling setLoading synchronously inside useEffect body triggers the rule); items appear immediately after the async fetch resolves — acceptable UX for a collapsed panel"
  - "SearchPageProps / CrossMarketplacePageProps type aliases: onReopen declared in type but not destructured in Task 1 so no unused-var error while renderTab call sites already type-check (Task 1 independently buildable)"
  - "HistoryList mounted only when onReopen is defined: {onReopen && <HistoryList .../>} — natural guard since onReopen is the required prop"
  - "Comparative label composed entirely in FE: brands.slice(0,2).join(', ') + optional marcas suffix + optional query suffix (RESEARCH Pitfall 2 — raw query must not be pre-composed into label)"
metrics:
  duration: "10m"
  completed: "2026-06-20T23:05:27Z"
  tasks: 2
  files_modified: 1
---

# Phase 27 Plan 03: App-level preloadedJobId + HistoryList per-tab UI Summary

One-liner: App.tsx gains preloadedJobId state + handleReopen, plus a reusable collapsible HistoryList component mounted in SearchPage (type=search) and CrossMarketplacePage (type=cross), with refreshKey-driven refetch and D-06 COMPLETED-only reopen.

## What Was Built

**Task 1 — App-level preloadedJobId state + handleReopen + renderTab propagation (SC#2)**

Added to `App()`:
- `const [preloadedJobId, setPreloadedJobId] = useState<string | null>(null)`
- `handleReopen(jobId, type)` — sets active tab + preloadedJobId
- `renderTab` now passes `preloadedJobId`, `onClearPreloadedJob`, and `onReopen` to both `<SearchPage>` and `<CrossMarketplacePage>`
- `SearchPageProps` and `CrossMarketplacePageProps` type aliases declare `onReopen?: (jobId: string) => void` so the renderTab JSX passes TypeScript excess-property checking independently of Task 2

Task 1 built independently (`npm run build` exits 0 without Task 2).

**Task 2 — Reusable HistoryList component + per-tab mounting**

Built `HistoryList` component within `frontend/src/App.tsx`:
- Props: `type: 'search'|'cross'`, `onReopen: (jobId:string) => void`, `refreshKey: number`
- Internal state: `items`, `collapsed` (default true), `deleteTick`
- Fetch: `useEffect` on `[refreshKey, deleteTick]` calls `ApiClient.getHistoryList()` + filters by `type`
- Collapsed `GlassCard`-style panel above results in each page; header = "Histórico de buscas" + count badge + chevron
- Row layout (reuses `.brand-item` geometry): label / type badge / date DD/MM/YYYY HH:mm / status badge / delete button
- COMPLETED rows: real `<button>` with `onReopen(job_id)` + `--primary` hover affordance
- FAILED rows: `opacity: 0.7`, error badge, non-clickable (`<div>`)
- PENDING rows: `animate-spin` spinner + "Em andamento" badge, non-clickable
- Delete: `stopPropagation` + `confirm()` + `ApiClient.deleteHistory` + `setDeleteTick(t=>t+1)`
- Comparative label: `brands.slice(0,2).join(', ')` + optional `· N marcas` + optional `— "query"` (Pitfall 2)
- SKU label: stored `query` as-is (`"SKU: …"`)

Mounted in `SearchPage`:
- `const [historyRefreshKey, setHistoryRefreshKey] = useState(0)` added
- `setHistoryRefreshKey(k => k + 1)` after `setResults(data)` in `handleSearch` success path
- `{onReopen && <HistoryList type="search" onReopen={onReopen} refreshKey={historyRefreshKey} />}`

Mounted in `CrossMarketplacePage`:
- Same `historyRefreshKey` pattern
- `{onReopen && <HistoryList type="cross" onReopen={onReopen} refreshKey={historyRefreshKey} />}`

## Verification

- `npm run build`: exits 0 (both tasks)
- `npm run lint`: 7 problems (6 errors, 1 warning) — identical to pre-existing baseline, zero new errors

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed `loading` state from HistoryList to avoid new lint error**
- **Found during:** Task 2 implementation
- **Issue:** `react-hooks/set-state-in-effect` fires when `setLoading(true)` is called synchronously inside `useEffect` body — this is the same rule that produces 2 of the 6 baseline errors (SearchPage/CrossMarketplacePage preloaded effects). Adding a third instance would exceed the baseline.
- **Fix:** Removed `loading`/`setLoading` from `HistoryList`. The fetch happens asynchronously; items appear once the Promise resolves. The loading spinner copy ("Carregando histórico…") was removed from the collapsed panel render. Acceptable UX since the panel is collapsed by default.
- **Files modified:** `frontend/src/App.tsx` (HistoryList component)
- **Commit:** a0a69ff

**2. [Rule 1 - Bug] Type alias pattern for onReopen prop to keep Task 1 independently buildable**
- **Found during:** Task 1 — first edit attempt
- **Issue:** `@typescript-eslint/no-unused-vars` fires on any destructured prop not used in the function body, with no underscore-prefix exception in this project's eslint config (rule at level 2 with no `argsIgnorePattern`). Declaring `onReopen` in destructuring in Task 1 before Task 2 mounts `HistoryList` would create a new lint error.
- **Fix:** Used `SearchPageProps`/`CrossMarketplacePageProps` type aliases — `onReopen` is declared in the type (so JSX call site passes TS excess-property check) but Task 1 destructures only what it uses. Task 2 then adds `onReopen` to the CrossMarketplacePage destructuring and uses it in SearchPage mount.
- **Files modified:** `frontend/src/App.tsx`
- **Commit:** cdbdc8a

## Threat Model Verification

| Threat ID | Status |
|-----------|--------|
| T-27-03-01 (XSS) | Mitigated — all label/badge text rendered via JSX text nodes; no dangerouslySetInnerHTML |
| T-27-03-02 (DoS client) | Accepted — collapsed by default; client-side type filter |
| T-27-03-03 (FAILED/PENDING reopen) | Mitigated — row rendered as `<div>` (not `<button>`) for FAILED/PENDING; `onReopen` never called |
| T-27-03-SC (npm installs) | Accepted — zero packages installed; `ChevronDown` and `History` from already-installed `lucide-react` |

## Known Stubs

None — `HistoryList` fetches real data from `ApiClient.getHistoryList()` and `ApiClient.deleteHistory()`. No hardcoded mock data.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced.

## Manual UAT (required per VALIDATION.md)

These steps must be verified manually after deployment:
1. Run a comparative search → entry appears in SearchPage history list (refreshKey refetch) with label composed from brands + query
2. Click the COMPLETED entry → results re-display identically in SearchPage with NO new scrape network call
3. Run an SKU search in CrossMarketplacePage → entry appears in CrossMarketplacePage history list
4. Click the COMPLETED SKU entry → SKU results re-display without re-scraping
5. Confirm FAILED/PENDING entries (if any) show their badges and are NOT clickable
6. Delete an entry → confirm dialog appears; after confirm, entry removed from list

## Self-Check: PASSED

- `frontend/src/App.tsx` modified: confirmed (197 insertions Task 2, 12 insertions Task 1)
- Commit `cdbdc8a` exists: Task 1
- Commit `a0a69ff` exists: Task 2
- `grep -c "preloadedJobId={preloadedJobId}" App.tsx` → 2 hits (SearchPage + CrossMarketplacePage in renderTab)
- `grep -c "HistoryList" App.tsx` → component definition + 2 mount sites
- Build exits 0, lint at 6-error baseline
