---
phase: 28-persist-ncia-da-busca-entre-abas
reviewed: 2026-06-22T01:50:16Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - frontend/src/App.tsx
  - frontend/src/api/client.ts
  - frontend/src/stores/searchStore.ts
findings:
  critical: 0
  warning: 1
  info: 4
  total: 5
status: issues_found
---

# Phase 28: Code Review Report

**Reviewed:** 2026-06-22T01:50:16Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

This is a re-review after the prior round's 1 Critical + 6 Warnings were addressed in commits `9ff516e` + `8e93905`. All seven of those findings are genuinely resolved in the current code:

- **CR-01 (re-wrap race):** `withDisplayOrder` is now the single exported source in `searchStore.ts:55-64`; `startCrossSearch` applies it *inside* the action (`searchStore.ts:160`) and `handleSearch` no longer reads/rewrites the store after the await (`App.tsx:1311-1322`). Resolved.
- **WR-01 / WR-02 (AbortController identity guards):** Both `startSearch` and `startCrossSearch` guard `get().X.abortController !== controller` on the success path (`searchStore.ts:120,156`) and the error path (`searchStore.ts:129,166`), plus an `AbortError` early-return (`searchStore.ts:127,165`). A late-resolving stale request can no longer clobber the vigent one. Resolved.
- **WR-03 (reopen-vs-search race):** `loadingPreloadId` was added to both slices; the reopen effects abort any in-flight search, set `loadingPreloadId`, and identity-guard the `.then`/`.catch`/`.finally` against it (`App.tsx:878-901`, `1220-1245`). I traced both orderings (search→reopen and reopen→search) and the `loading` flag is owned by exactly one operation in each case. Resolved.
- **WR-04 (WS handler nulling):** `App.tsx:389-394` now nulls `onmessage`, `onopen`, `onerror`, and `onclose` before `close()`. Resolved.
- **WR-05 (unguarded JSON.parse):** `App.tsx:489-493` wraps `JSON.parse` in try/catch and returns on malformed frames. Resolved.
- **WR-06 (history refresh on non-success):** Both handlers gate `setHistoryRefreshKey` on `outcome.status === 'success'` (`App.tsx:934-936`, `1319-1321`). Resolved.

What remains is **one new WARNING** — a post-await write in `handleCalculateShipping` that lacks the same staleness guard the fixes added everywhere else — plus the **four pre-existing Info items** (IN-01..04), none of which were addressed and all of which still apply to the current code. No new Critical issues were introduced by the fixes.

## Warnings

### WR-01: `handleCalculateShipping` writes shipping results back to the store without a staleness guard — post-await race can splice freight into a different search's results

**File:** `frontend/src/App.tsx:1272-1294`

The shipping calculation reads `cross.results` *after* awaiting the network call and writes the mutated array straight back:

```ts
const data = await ApiClient.calculateSingleShipping({ marketplace, url: item.url, zipcode: currentZip });
if (data.status === 'success' && data.shipping_info) {
  const prev = useSearchStore.getState().cross.results;   // read AFTER await
  if (!prev) return;
  const newResults = prev.results.map((r: any) => { /* splice shipping into matching row */ });
  // ...recompute is_buybox_winner...
  setCross({ results: { ...prev, results: newResults } });  // unconditional write-back
}
```

This is the exact post-await race class the round-1 fixes hardened against in `startSearch`/`startCrossSearch` and the reopen effects — but this path was left unguarded. If, while a shipping request is in flight, the user (a) starts a new SKU search, (b) reopens a different history entry, or (c) calculates shipping for another item, then `useSearchStore.getState().cross.results` may already point at a *different* search's result set by the time this `.then` runs. The `.map` matches on `r.url === item.url && r.marketplace === marketplace`; if no row matches it's a no-op, but if the new result set happens to contain a row with the same URL+marketplace (common when reopening the same SKU's history), it silently writes a stale `landed_price`/`shipping_price` and recomputes `is_buybox_winner` against the wrong data. There is no `AbortController` on `calculateSingleShipping` (`client.ts:85-90` takes no signal), so the request cannot be cancelled either.

**Fix:** Capture an identity token before the await and re-check it before writing, mirroring the store actions. Simplest robust option — snapshot the array reference:

```ts
const before = useSearchStore.getState().cross.results;
const data = await ApiClient.calculateSingleShipping({ marketplace, url: item.url, zipcode: currentZip });
const prev = useSearchStore.getState().cross.results;
if (prev !== before) return;            // a newer search/reopen replaced results — drop this update
if (data.status === 'success' && data.shipping_info) {
  // ...existing map / buybox recompute / setCross...
}
```

Alternatively thread the slice's `abortController`/`loadingPreloadId` into the guard. Either way, do not write `results` back if the underlying search changed during the await.

## Info

### IN-01: Pervasive `any` typing defeats the type safety the store migration could have provided

**File:** `frontend/src/stores/searchStore.ts:21,30,48-49` (and broadly across `App.tsx`, `client.ts`)

`results: any | null`, `startSearch: (payload: any) => Promise<SearchOutcome>`, and `setSearch/setCross` patches are untyped beyond `Partial<Slice>` where the slice itself holds `any`. Both files lead with `/* eslint-disable @typescript-eslint/no-explicit-any */`. The phase introduced a clean `SearchOutcome` discriminated union — the same rigor applied to `results` (a `SearchResults` / `CrossResults` interface) would catch shape drift between the API, the store, the reopen path (`App.tsx:887` constructs `{ results, query, brands_searched }` by hand), and the render code that reads `results.results`, `results.reference_product`, `results.search_query`, etc.

**Fix:** Define result interfaces for the search and cross slices and replace the `any` payload/result types. Fully typing the legacy render code is out of scope, but the store boundary is the highest-leverage place to start.

### IN-02: Duplicated export/blob-download logic across `exportSearch` and `exportCrossMarketplace`

**File:** `frontend/src/api/client.ts:113-197`

`exportSearch` (113-154) and `exportCrossMarketplace` (156-197) are near-identical: same header construction, same `response.ok` + JSON-error-parse block, same `content-disposition` filename extraction, same blob → object-URL → anchor-click → deferred-revoke dance. Only the endpoint, default filename, and payload type differ. This was flagged in round 1 and remains unchanged.

**Fix:** Extract a private helper, e.g. `downloadBlob(endpoint, payload, defaultFilename)`, and have both methods delegate to it. Reduces the surface where the blob-lifecycle logic (and the IN-03 timeout) can drift between the two.

### IN-03: Magic `100` ms timeout before revoking the blob URL

**File:** `frontend/src/api/client.ts:150-153, 193-196`

```ts
setTimeout(() => {
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}, 100);
```

The `100` is an unexplained magic delay duplicated in both export methods. The comment says "allow the browser to initiate the download," but the value is arbitrary and the revoke is not tied to any actual download event. On a slow machine 100 ms could still race the download start; conversely the cleanup could often be done synchronously after `a.click()` in modern browsers for blob URLs.

**Fix:** Hoist to a named constant (e.g. `const BLOB_REVOKE_DELAY_MS = 100;`) — ideally in the shared helper from IN-02 — and add a brief comment justifying the value.

### IN-04: Legacy `getToken()` returns the raw API key; `setToken`/`clearToken` are silent no-ops

**File:** `frontend/src/api/client.ts:10-16`

```ts
public static getToken(): string | null {
  return API_KEY;   // returns the API key for "compatibility"
}
public static setToken(_token: string) { /* no-op */ }
public static clearToken() { /* no-op */ }
```

`getToken()` exposes the API key under a JWT-flavored name, and `setToken`/`clearToken` accept calls that do nothing. Any caller that believes it is managing a session token is silently misled, and the API key leaks to any code path that calls `getToken()` expecting a session credential. Not phase-28 logic, but it lives in a reviewed file and is dead/misleading legacy surface. (Note: the API key is also embedded client-side via `VITE_API_KEY` and passed as a `?api_key=` query param on the WS URL at `App.tsx:478,482` — query-param secrets tend to land in logs/proxies. Both are inherent to this build-time-key design and out of scope to fix in this phase, but worth recording.)

**Fix:** If no JWT flow exists, delete the three legacy auth helpers and update any callers; do not surface the API key through a token-shaped accessor.

---

_Reviewed: 2026-06-22T01:50:16Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
