---
last_mapped_commit: unknown
---

# 📁 Structure

**Date:** 2026-06-08

## Directory Layout
- `api/` — FastAPI route controllers.
- `core/` — Foundational classes and managers (browser, session, background worker, basic models).
- `data/` — Local data storage (e.g., `search_history.json`, `price_monitors.json`, and generated `*.xlsx`).
- `db/` — Database migration or configuration scripts.
- `frontend/` — The Vite + React application.
- `infrastructure/` — Infrastructure/deployment configs.
- `scrapers/` — Specialized scraper scripts/modules.
- `scripts/` — Helper scripts.
- `services/` — Core business logic, integrating AI, NLP, historical caching, and orchestrating scraping.
- `tests/` — Unit and integration tests.

## Key Files
- `app.py` — The FastAPI application entry point.
- `config.py` — Centralized configuration using Pydantic Settings.
- `core/models.py` — The primary domain models.
- `core/worker.py` — The Celery worker app definitions and async tasks.
- `services/orchestrator_multi.py` — Handles parallel or multi-target orchestration.
- `frontend/src/App.tsx` — Main React component handling routing, complex layout, and SSE state.
