---
phase: 34
slug: extra-o-de-banners-desktop
status: complete
researched: 2026-06-23
---

# Phase 34 — Technical Research

## Research Question

What must be understood to plan a production-grade, user-facing desktop banner extraction workflow from the validated prototype without losing cancellation, history, deduplication, review, and UI decisions?

## Executive Summary

The extraction algorithm is already empirically validated in `testes/extrair_banners.py`: 13/13 active sites completed, 37 images were downloaded, 3 video slides were identified, and no downloads failed in the reference run. Phase 34 should therefore **promote and separate** the prototype rather than redesign the detector.

The recommended production shape is a long-running banner job with five boundaries:

1. a browser collector that reuses the proven DOM/carousel logic;
2. a content-addressed asset store keyed by SHA-256;
3. a run repository for drafts, approvals, 30-day history, and references to assets;
4. API/job orchestration with cancellation and progress events;
5. a dedicated React page/store for selection, live progress, review, approval, and history.

No new runtime dependency is required. Installed versions at research time are Playwright 1.58.0, FastAPI 0.132.0, and Pydantic 2.12.5. An attempted official-documentation lookup was blocked by the session's web gateway, so recommendations below are grounded in the installed APIs, the live prototype, and existing project patterns.

## Existing Assets to Promote

### Extraction logic

`testes/extrair_banners.py` already provides:

- fixed desktop viewport `1366×768` and realistic browser context;
- large-first-viewport filtering that excludes logos, products, and lower sections;
- `img`, `srcset`, lazy attributes, `picture`, and CSS background extraction;
- generic next-control discovery and traversal of declared carousel slides;
- handling for videos interleaved between later image slides;
- original-byte download, content type/extension detection, SHA-256, screenshots, JSON, CSV, and HTML gallery;
- per-brand isolation and a sequential browser strategy appropriate for the project's memory warning.

The prototype is synchronous and CLI-oriented. Production code should extract its pure helpers and browser workflow into a service callable from an async job, using `asyncio.to_thread` where sync Playwright remains necessary on Windows.

### Existing application patterns

- `backend/services/brand_service.py`: obtain brands through `list_brands(active_only=True)`; do not filter inactivity independently in routes or UI payload processing.
- `backend/core/job_manager.py`: `JOB_CANCEL_FLAGS[job_id]` is the established cooperative-cancel primitive.
- `backend/core/websocket.py`: `ConnectionManager.send_message()` is the existing per-job progress stream.
- `frontend/src/stores/searchStore.ts`: Zustand slices own `AbortController`, result identity guards, global toast completion, and state across tab unmounts.
- `frontend/src/App.tsx`: `SearchPage` has the exact brand-chip selection requested; `HistoryList` has the requested reopen/delete interaction.
- `backend/services/search_history_service.py`: establishes 30-day retention, newest-first ordering, and manual deletion, but must not be reused directly for binary banner payloads.

## Recommended Architecture

### 1. Banner collector

Create a production service that accepts one registered brand, a cancellation signal, and a progress callback. Keep one Chromium process per job and one context/page per brand, processed sequentially by default. Check cancellation:

- before starting each brand;
- after navigation/settle;
- between carousel advances;
- before each asset download;
- immediately after blocking browser operations return.

The browser collector returns normalized candidates and video metadata. It does not own history, approval, or SharePoint behavior.

### 2. Asset store

Use content-addressed local storage:

- physical path derived from SHA-256, never from external URLs or alt text;
- original extension derived from response content type with a safe allowlist;
- one blob per digest;
- a logical banner reference contains the friendly display filename (`01-descricao-marca.ext`) and points to the digest;
- reference counting is computed from run metadata during cleanup rather than trusted from mutable counters.

This satisfies deduplication across runs while allowing each run to present its own order, name, source URL, rendered URL, click target, alt, dimensions, and capture time.

### 3. Run repository and lifecycle

Recommended statuses:

- `RUNNING`: brands are being collected;
- `REVIEW`: all selected brands succeeded and await user approval;
- `COMPLETED`: immutable approved run in 30-day history;
- `PARTIAL`: one or more brands failed; visible only in the current session/draft surface;
- `CANCELLED`: user stopped the job; not added to history;
- `FAILED`: no usable result; not added to history.

Persist run metadata atomically. `REVIEW` drafts should survive a normal page navigation; only `COMPLETED` records appear in history. Approval removes deselected logical references, deletes newly orphaned blobs when safe, marks the run immutable, and makes it history-visible. Cleanup removes completed runs older than 30 days and then garbage-collects unreferenced blobs.

### 4. Job/API boundary

The API needs contracts for:

- start with selected brand keys;
- get job/run status and current results;
- stop a running job;
- approve selected banner IDs;
- list/get/delete completed history;
- serve an asset and viewport screenshot safely.

Start should return a `job_id` promptly. Progress events should include brand key, brand status, completed/total counts, new banner metadata, and terminal state. The UI must reconcile from the status endpoint after reconnecting; WebSocket events are transport hints, not the sole source of truth.

### 5. Frontend state

Add a dedicated banner slice/store rather than component-only state. It should own selected brands, active job ID, status by brand, incremental candidates, review selection, loaded history run, and cancellation identity. This preserves progress when the user changes tabs and prevents a late response from overwriting a newer run.

## Data Contract

Each logical banner should include at least:

- stable banner ID within the run;
- run ID, brand key/name, slide order;
- friendly filename and SHA-256 asset digest;
- source URL chosen for download and rendered URL observed at `1366×768`;
- click target, alt/aria text, DOM kind;
- rendered and natural dimensions;
- content type, original extension, byte count;
- capture timestamp and approval state.

Each run should include selected brands, timestamps, overall status, per-brand status/error, ordered banner references, video slide URLs/counts, screenshot references, and approval timestamp.

## Security Threat Model

| Threat | Severity | Required mitigation |
|--------|----------|---------------------|
| Path traversal through alt text, brand names, URLs, or MIME extension | High | Physical paths derive only from validated digest/allowlisted extension; friendly names are sanitized and remain metadata/download names. |
| Unbounded file growth/resource exhaustion | High | Sequential brands, size/time limits, 30-day cleanup, content deduplication, and orphan garbage collection. |
| SSRF through arbitrary asset URLs | Medium | Jobs accept only registered active brands; asset URLs must be HTTP(S), discovered from the loaded page, and requests must reject local/file schemes. |
| Cross-job cancellation or data access | Medium | Validate job IDs, keep cancellation flags isolated, and use the existing API-key/auth dependencies on every HTTP/WebSocket contract. |
| Partial metadata writes corrupt history | Medium | Atomic temp-file replacement under a repository lock; terminal status written only after consistent metadata. |
| Stale WebSocket events overwrite a newer job | Medium | Frontend identity guard keyed by active `job_id`; status endpoint remains authoritative. |

Each PLAN.md must include a `<threat_model>` block and tests for the high-severity mitigations.

## Testing Strategy

Avoid making the automated suite depend on live retail sites. Use three layers:

1. **Unit tests:** filename sanitization, extension detection, SHA deduplication, run lifecycle, approval immutability, retention cleanup, orphan collection, and status transitions.
2. **Browser fixture tests:** local/static HTML fixtures for stacked slides, hidden/lazy slides, `srcset`, CSS backgrounds, videos between images, false-positive lower sections, and generic next controls.
3. **API/store tests:** start/progress/stop/approve/history contracts with collector fakes; assert cancelled/partial runs never enter history.

The 13-site live run remains a manual smoke/UAT gate because external content, WAFs, and campaigns change independently of the code.

## Validation Architecture

### Fast feedback

- `python -m pytest backend/tests/test_banner_extraction.py -q`
- `python -m pytest backend/tests/test_banner_history.py -q`
- `python -m pytest backend/tests/test_banner_routes.py -q`
- `cd frontend && npm run lint`
- `cd frontend && npm run build`

### Phase regression

- `python -m pytest backend/tests -q`
- `cd frontend && npm run lint && npm run build`

### Manual UAT

1. Open Banners tab; confirm all active brands selected, then toggle individual brands.
2. Start extraction; observe incremental per-brand progress and results.
3. Stop a run; confirm current work stops, completed cards remain in session, and no history entry is created.
4. Complete a run; review gallery, deselect a false candidate, approve, and confirm only approved banners enter history.
5. Reopen the run without new network scraping; delete it manually.
6. Repeat extraction with an unchanged banner and verify one physical blob is referenced by multiple runs.
7. Run the 13 active sites and visually compare hero slides against viewport screenshots.

## Planning Recommendations

Split the phase into four dependency-ordered plans:

1. domain models, content-addressed storage, lifecycle, and tests;
2. production collector extracted from the spike plus deterministic browser fixtures;
3. API/job orchestration, cancellation, progress, approval, history, and route tests;
4. dedicated frontend tab/store, live progress, review/approval, history, and build/UAT gates.

This structure keeps the reusable core independent, makes API work depend on stable storage/collector contracts, and reserves the final plan for the full user-facing vertical integration.

## Research Complete

The phase is technically feasible with the existing stack. The principal planning risks are state lifecycle correctness, safe content-addressed storage, true backend cancellation (not only aborting the browser request), and keeping live-site behavior out of deterministic automated tests.

