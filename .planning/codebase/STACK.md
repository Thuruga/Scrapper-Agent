---
last_mapped_commit: unknown
---

# 🥞 Tech Stack

**Date:** 2026-06-08

## Overview
This project is the "Intelligence Scraper" application consisting of a Python backend and a React/TypeScript frontend. It performs comparative multi-brand product searching and price monitoring.

## Backend
- **Language:** Python 3.8+
- **Runtime:** CPython
- **Framework:** FastAPI with Uvicorn server
- **Background Tasks:** Celery with Redis broker/backend
- **Dependencies:** 
  - `pydantic`, `pydantic-settings` for validation and config
  - `celery`, `redis`, `sse-starlette` for async background tasks and SSE streaming
  - `playwright`, `curl_cffi`, `beautifulsoup4` for scraping and bypassing anti-bot systems
  - `httpx` for async HTTP requests
  - `pandas`, `openpyxl` for data processing and Excel export
  - `transformers`, `easyocr`, `opencv-python-headless` for computer vision / NLP tasks
  - `supabase` for persistence of brand mapping/categories
  - `APScheduler` for lightweight cron-like background jobs

## Frontend
- **Language:** TypeScript
- **Runtime:** Node.js (build), Browser (runtime)
- **Framework:** React 18/19, Vite
- **Dependencies:** 
  - `framer-motion` for complex UI animations
  - `recharts` for charts
  - `lucide-react` for icons
  - `react-hot-toast` for notifications
  - `tailwindcss`, `clsx`, `tailwind-merge` for styling
  - Native `EventSource` for Server-Sent Events

## Configuration
- `config.py` manages application state and hyperparameters, loading from `.env` via `pydantic-settings`.
- Redis running on `localhost:6379`.
