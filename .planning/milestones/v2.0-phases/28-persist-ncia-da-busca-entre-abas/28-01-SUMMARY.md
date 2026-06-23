---
phase: 28-persist-ncia-da-busca-entre-abas
plan: "01"
subsystem: frontend
tags: [websocket, cleanup, react, lifecycle, categorypage]
dependency_graph:
  requires: []
  provides: [ws-cleanup-categorypage]
  affects: [frontend/src/App.tsx]
tech_stack:
  added: []
  patterns: [useEffect-cleanup, wsRef-nulling]
key_files:
  created: []
  modified:
    - frontend/src/App.tsx
decisions:
  - "[28-01]: useEffect with [] dep array placed after scroll useEffect and before fetchBrandCategories — within CategoryPage body, not inside startScrape"
  - "[28-01]: onmessage = null set BEFORE close() per Armadilha 5 to prevent in-flight message delivery to setState after unmount"
  - "[28-01]: existing done/error_done branch ws.close() left intact — covers normal completion path"
metrics:
  duration: 5m
  completed: "2026-06-21"
  tasks: 1
  files_modified: 1
---

# Phase 28 Plan 01: WebSocket Cleanup na CategoryPage Summary

**One-liner:** Added 10-line useEffect cleanup to CategoryPage that nulls onmessage before closing wsRef.current on unmount, preventing setState calls in unmounted component when user switches tabs mid-scrape.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | useEffect de cleanup do WebSocket na CategoryPage | 207953b | frontend/src/App.tsx (+10 lines) |

## What Was Built

Added a `useEffect(() => { return () => { ... }; }, [])` cleanup hook inside the `CategoryPage` component body, positioned after the existing scroll `useEffect([logs])` and before `fetchBrandCategories`. The cleanup function guards on `wsRef.current` existence then:

1. Sets `wsRef.current.onmessage = null` — prevents in-flight messages from dispatching `setState` to the unmounted component (Armadilha 5)
2. Calls `wsRef.current.close()` — terminates the WebSocket connection
3. Sets `wsRef.current = null` — releases the reference

The pre-existing `ws.close()` inside the `done`/`error_done` branch of `ws.onmessage` was NOT removed — it continues handling the normal scrape-completion path.

## Verification

- `cd frontend && npm run build` — exit code 0 (tsc -b + vite build green, 3.37s)
- Acceptance criteria source checks all pass:
  - useEffect with `[]` dep array exists in CategoryPage body
  - `wsRef.current.onmessage = null` occurs before `wsRef.current.close()`
  - `msg.type === 'done' || msg.type === 'error_done'` branch with `ws.close()` intact
- UAT manual (Critério #4): requires human verification per 28-VALIDATION.md

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — change is purely a React lifecycle cleanup hook. Reduces risk (orphan WS connection) without introducing new surface.

## Self-Check: PASSED

- File modified: `frontend/src/App.tsx` — EXISTS (confirmed by build passing and Read)
- Commit `207953b` — FOUND (`git rev-parse --short HEAD` = 207953b)
- `done`/`error_done` branch with `ws.close()` — INTACT (verified at App.tsx:486-488)
- `onmessage = null` before `close()` — VERIFIED (App.tsx:385 before App.tsx:386)
