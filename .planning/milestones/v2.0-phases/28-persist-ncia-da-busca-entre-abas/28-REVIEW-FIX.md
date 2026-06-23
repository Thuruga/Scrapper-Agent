---
phase: 28-persist-ncia-da-busca-entre-abas
fixed_at: 2026-06-22
review_source: 28-REVIEW.md
fix_scope: all
iteration: 2
findings_in_scope: 5
fixed: 4
skipped: 1
status: partial
fix_commits: [9ff516e, 8e93905, 3eaf048, 6e31098]
---

# Phase 28 — Code Review Fix Report (cumulative)

Two fix passes. All Critical and Warning findings across both reviews are resolved; 3 of 4 Info fixed; IN-01 (codebase-wide typing) intentionally deferred. Build (`tsc -b && vite build`) green after every pass. Every fix independently verified (gsd-verifier + 4 adversarial lenses in pass 1; a focused adversarial verifier in pass 2).

## Pass 1 — `--fix` (Critical + Warning) — commits 9ff516e, 8e93905

| Finding | Status | Fix |
|---|---|---|
| CR-01 (Critical) — cancelled cross-search re-wrapped another search's results | ✅ Fixed | `withDisplayOrder` moved into `startCrossSearch` (single exported source); caller no longer reads/re-wraps the store after `await`; AbortController identity guard; discriminated `SearchOutcome` return |
| WR-01/WR-02 — AbortController lifecycle / stale clobber | ✅ Fixed | Identity guard (`abortController !== controller`) on success + error paths of both actions; controller cleared on terminal states |
| WR-03 — reopen-from-history silently dropped while a search loads | ✅ Fixed | `loadingPreloadId` distinguishes in-flight preload (skip on remount) from a normal search (reopen aborts it and wins); preload callbacks identity-guarded; `onClearPreloadedJob` kept in `.finally` |
| WR-04 — partial WS handler cleanup | ✅ Fixed | Cleanup nulls `onopen`/`onerror`/`onclose`/`onmessage` |
| WR-05 — unguarded `JSON.parse` in `ws.onmessage` | ✅ Fixed | Wrapped in try/catch; malformed frame ignored |
| WR-06 — `historyRefreshKey` bumped on failed/aborted search | ✅ Fixed | Both `handleSearch` gate the bump on `outcome.status === 'success'` |

**Pass-1 verification:** gsd-verifier (Gap 1 CR-01 CLOSED, line-cited) + 4 adversarial lenses (all `sound`, 0 blocking / 0 concerns).

## Pass 2 — `--all --fix` — commits 3eaf048, 6e31098

Re-review of the fixed code surfaced one NEW Warning (a path the first review missed) and re-confirmed the 4 Info findings. Current review state: 0 Critical / 1 Warning / 4 Info.

| Finding | Status | Fix |
|---|---|---|
| WR-01 (new) — `handleCalculateShipping` post-await race (same class as CR-01) | ✅ Fixed | Snapshot `cross.results` reference before the `calculateSingleShipping` await; skip the write if the result set was replaced during the await (commit 3eaf048) |
| IN-02 — duplicated export/blob logic | ✅ Fixed | `exportSearch`/`exportCrossMarketplace` delegate to a shared private `downloadExport(endpoint, payload, defaultFilename, context)` helper (6e31098) |
| IN-03 — magic `100`ms blob-revoke timeout | ✅ Fixed | Extracted to `BLOB_REVOKE_DELAY_MS` (6e31098) |
| IN-04 — legacy `getToken()` leaking the API key under a token-shaped name | ✅ Fixed | Removed dead `getToken`/`setToken`/`clearToken` (zero callers in `src`) (6e31098) |
| IN-01 — pervasive `any` at the store/API boundary | ⏭️ Deferred | See rationale below |

**Pass-2 verification:** focused adversarial verifier — both changes `SOUND` (high confidence). WR-01 guard correct on all axes (every store write creates a new object reference, so reference-equality reliably detects replacement; no false stale-skip; `loadingShipping` always cleared in `finally`). Export refactor is a faithful, behavior-preserving extraction; removed auth helpers confirmed callerless.

## Skipped — IN-01 (deferred, not a defect)

**IN-01 — pervasive `any` at the store/API boundary.** Deferred deliberately. This is a codebase-wide typing posture: `frontend/src/api/client.ts` and `frontend/src/App.tsx` both open with `/* eslint-disable @typescript-eslint/no-explicit-any */`, and `ApiClient.request<T>` resolves `any` at the network boundary. Tightening only the search-store slices would just relocate `any` (the API responses remain untyped upstream) for high churn and little real safety gain. A proper fix requires defining the backend response contracts (ComparisonResult / CrossMarketplaceResult / ShippingInfo) as a dedicated, cross-cutting typing effort — out of proportion to a phase-28 review fix. Tracked as a future improvement.

Re-run `/gsd-code-review 28 --all --fix` after introducing shared response types if IN-01 is prioritized.
