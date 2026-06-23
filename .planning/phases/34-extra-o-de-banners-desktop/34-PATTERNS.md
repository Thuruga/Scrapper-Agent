---
phase: 34
slug: extra-o-de-banners-desktop
created: 2026-06-23
---

# Phase 34 — Codebase Patterns

## Backend integration points

- Register `routes_banners.router` in `backend/api/__init__.py`; the aggregator already applies `verify_api_key` to every HTTP route.
- Use `JOB_CANCEL_FLAGS` from `backend/core/job_manager.py` for cooperative cancellation and `manager.send_message()` from `backend/core/websocket.py` for per-job events.
- Resolve targets exclusively with `brand_service.list_brands(active_only=True)` as established by multi-brand category scraping.
- Follow the 30-day newest-first behavior of `search_history_service.py`, but use a dedicated repository because banner runs own binary assets and approval states.
- Keep long-running Playwright work outside the request coroutine with `asyncio.to_thread`; return `job_id` immediately and reconcile state through a GET endpoint.

## Frontend integration points

- Add a module-scoped Zustand store beside `searchStore.ts`; it must survive tab unmounts and guard late events with the active `job_id`.
- Extend `ApiClient` with start/status/stop/approve/history/assets methods and use the existing API-key request helper.
- Reuse the comparative-search brand chip markup in `SearchPage` and the reopen/delete interaction in `HistoryList`.
- Add the `banners` switch branch, `Images` sidebar item, and page title in `App.tsx`; style only through existing tokens/classes plus banner-specific selectors in `App.css`.

## Prototype promotion boundary

- `testes/extrair_banners.py` is the behavioral reference, not the production import target.
- Move normalized candidate discovery, carousel advance, download, MIME/extension detection, SHA-256, and filename logic into `backend/services/banner_extraction_service.py`.
- Automated browser tests use a local HTML fixture. The 13 live sites remain manual UAT because campaigns and WAF behavior are nondeterministic.

## Storage pattern

- Physical blob path is `{sha256}.{allowlisted_extension}` under a fixed data root.
- Friendly `01-descricao-marca.ext` names are metadata/download names only and never participate in a filesystem join.
- Metadata writes use a lock plus temporary-file replacement. Garbage collection derives live digests from persisted runs/drafts.

