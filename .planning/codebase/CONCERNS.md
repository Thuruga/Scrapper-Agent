---
last_mapped_commit: unknown
---

# ⚠️ Concerns

**Date:** 2026-06-08

## Technical Debt & Fragile Areas
- **Anti-Bot Defeat**: Scraping relies heavily on avoiding detection (Playwright Stealth, Proxies, BrightData). If detection mechanisms change (e.g., Amazon, Mercado Livre), scrapers may break.
- **Resource Usage**: Playwright is memory-heavy. Running on low-resource environments (like Render free tier) may cause OOM (Out of Memory) kills if `PLAYWRIGHT_ENABLED` is true.
- **Legacy Configuration**: The `config.py` notes some deprecated/legacy configurations (e.g., `BRAND_REGISTRY` being moved to `data/brands.json`, `SCRAPER_API_KEY` being kept for backwards compatibility).
- **Concurrency on Local Files**: Because `data/search_history.json` and `data/price_monitors.json` are flat files updated by both the FastAPI server and Celery background workers concurrently, there is a risk of race conditions or data corruption under heavy load.
- **Security on Streams**: The SSE endpoint (`/notifications/stream`) is currently public and does not validate the `X-API-Key`. This means any user could potentially listen to job completion events.

## Hardcoded Logic
- Although centralized in `config.py`, complex scoring thresholds require continuous tuning as marketplace layouts or search algorithms shift.
