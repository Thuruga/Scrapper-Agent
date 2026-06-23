---
phase: 28-persist-ncia-da-busca-entre-abas
plan: "02"
subsystem: frontend-state
tags: [zustand, abortcontroller, state-management, search-store]
dependency_graph:
  requires: [28-01]
  provides: [useSearchStore, ApiClient.signal, zustand-dep]
  affects: [frontend/src/stores/searchStore.ts, frontend/src/api/client.ts, frontend/package.json]
tech_stack:
  added: [zustand@5.0.14]
  patterns: [zustand-module-scoped-store, abortcontroller-in-action, toast-from-store]
key_files:
  created:
    - frontend/src/stores/searchStore.ts
  modified:
    - frontend/src/api/client.ts
    - frontend/package.json
    - frontend/package-lock.json
decisions:
  - "[28-02/D-05]: No persist middleware — selectedItems is Set<string> (non-serializable); store is memory-only"
  - "[28-02/D-06]: Single useSearchStore with two slices (search + cross) — no separate stores"
  - "[28-02/Padrão 2]: signal spread as ...(signal ? { signal } : {}) — undefined signal never passed to fetch"
metrics:
  duration: "3m"
  completed: "2026-06-21"
  tasks: 2
  files: 4
---

# Phase 28 Plan 02: Install zustand + Create searchStore Summary

zustand@5.0.14 installed, ApiClient gains optional AbortSignal support, and unified module-scoped searchStore created with search+cross slices, AbortController-based cancellation, and global toast notifications.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Install zustand and add signal?: AbortSignal to ApiClient | 7d7ddb9 | frontend/package.json, frontend/package-lock.json, frontend/src/api/client.ts |
| 2 | Create searchStore.ts (zustand store with slices search + cross) | c4ec553 | frontend/src/stores/searchStore.ts |

## What Was Built

**Task 1 — zustand install + ApiClient signal support:**
- `npm install zustand@5.0.14` in `frontend/` — package added to dependencies
- `ApiClient.request<T>` gains third optional parameter `signal?: AbortSignal`, forwarded to `fetch` conditionally via `...(signal ? { signal } : {})` to avoid passing `undefined` to fetch
- `ApiClient.search(payload, signal?)` and `ApiClient.crossMarketplaceSearch(payload, signal?)` each gain optional second `signal?: AbortSignal` parameter, forwarded as third arg to `this.request()`
- All existing callers unaffected (parameter is optional)

**Task 2 — searchStore.ts:**
- New file `frontend/src/stores/searchStore.ts` with `/* eslint-disable @typescript-eslint/no-explicit-any */` header
- `useSearchStore` exported via `create<SearchStoreState>()(...)` using named import `import { create } from 'zustand'` (v5 API — no default export)
- `search` slice: `query`, `sort`, `inStock`, `zipcode`, `selectedBrands`, `results`, `loading`, `abortController`
- `cross` slice: `targetSku`, `zipcode`, `results`, `selectedItems: Set<string>`, `selectionMode`, `loading`, `abortController`
- `setSearch(patch)` / `setCross(patch)`: shallow merge actions
- `startSearch(payload)`: aborts previous `AbortController` → creates new → sets `loading=true/results=null` → `await ApiClient.search(payload, controller.signal)` → sets results + `toast.success('Busca Comparativa concluída')` → catches AbortError silently, real errors via `toast.error`
- `startCrossSearch(payload)`: analogous via `ApiClient.crossMarketplaceSearch`, additionally resets `selectedItems` and `selectionMode` at start of new search
- No `persist` middleware import (D-05)
- `selectedItems: Set<string>` documented as non-serializable (comment in store)

## Verification

- `cd frontend && npm run build` passed after Task 1 (tsc -b + vite build, exit 0)
- `cd frontend && npm run build` passed after Task 2 (tsc -b + vite build, exit 0)
- Build warning about chunk size >500kB is pre-existing (App.tsx monolith) — not introduced by this plan

## Deviations from Plan

None — plan executed exactly as written. The `signal` spreading uses `...(signal ? { signal } : {})` as specified in PATTERNS.md (excludes `undefined` from fetch options object).

## Known Stubs

None — the store is fully functional. Plan 03 (Wave 2) will wire the components (`SearchPage` / `CrossMarketplacePage`) to consume this store.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes introduced. Store is memory-only (no localStorage/sessionStorage). AbortController only cancels in-flight network requests. Consistent with T-28-02 and T-28-03 dispositions in the threat model.

## Self-Check: PASSED

- FOUND: frontend/src/stores/searchStore.ts
- FOUND: frontend/src/api/client.ts (modified)
- FOUND: frontend/package.json (contains "zustand": "^5.0.14")
- FOUND commit 7d7ddb9 (Task 1)
- FOUND commit c4ec553 (Task 2)
- signal?: AbortSignal appears 3 times in client.ts (request, search, crossMarketplaceSearch)
- export const useSearchStore present
- toast.success calls present (both actions)
- AbortError guard present (both actions)
- No persist import in searchStore.ts
