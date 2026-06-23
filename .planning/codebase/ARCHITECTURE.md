---
last_mapped_commit: unknown
---

# 🏗️ Architecture

**Date:** 2026-06-08

## System Design
The application follows a Service-Oriented Architecture (SOA) pattern, centralized around a FastAPI backend and a React frontend, augmented with an asynchronous background worker layer using Celery.

## Layers & Components
- **API Layer**: Located in `api/`, handling routing for brands, categories, jobs, monitors, products, and search.
- **Service Layer**: Located in `services/`, handling core business logic, including NLP (`nlp_service.py`), Image AI (`image_ai_service.py`), OCR (`ocr_service.py`), platform-specific logic (`vtex_api_scraper.py`, `shopify_api_client.py`), and historical data management (`search_history_service.py`).
- **Background Worker Layer**: Managed by `Celery` (`core/worker.py`), offloads long-running multi-brand scrape tasks and streams updates via Redis Pub/Sub.
- **Core Layer**: Located in `core/`, providing foundational capabilities like Browser Management (`browser_manager.py`), Session Management (`session_manager.py`), data models (`models.py`), and WebSocket orchestration (`websocket.py`).

## Data Flow
- Incoming synchronous requests hit the **API Layer** and are resolved quickly.
- Long-running requests (e.g. `POST /search`) dispatch tasks to the **Worker Layer** (Celery) and return a `job_id` immediately.
- The worker executes scraping tasks either via HTTP (`curl_cffi`) or Headless Browser (`playwright`).
- Results are saved to persistent files (via `SearchHistoryService`) or Supabase DB.
- Worker publishes `COMPLETED` events to **Redis Pub/Sub**.
- The `SSE` endpoint (`/notifications/stream`) relays these events to the **React Frontend**.
- Frontend updates state and fetches the final JSON/CSV payload when the `job_completed` event fires.
