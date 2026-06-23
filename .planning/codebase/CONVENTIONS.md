---
last_mapped_commit: unknown
---

# 📐 Conventions

**Date:** 2026-06-08

## Code Style
- **Python**: Uses modern Python 3 typing and `pydantic` for strict data validation. `FastAPI` dependency injection is used in route definitions.
- **Frontend**: Follows standard React and TypeScript conventions. Uses Tailwind CSS and `clsx` + `tailwind-merge` for utility class management.

## Configuration Pattern
- All hyperparameters (e.g., ML thresholds, proxy configurations) are centralized in `config.py` to avoid "magic numbers" in the service code. They fall back to robust defaults but can be overridden by `.env`.

## Error Handling & Resiliency
- Includes retry mechanisms with exponential backoff (`RETRY_MAX_ATTEMPTS`, `RETRY_BASE_SECONDS`).
- Employs a Circuit Breaker pattern to protect against continuous failures from specific scraping engines (`CIRCUIT_BREAKER_FAILURE_THRESHOLD`).
- Intelligent fallback strategies (e.g., falling back to Playwright if `curl_cffi` encounters CAPTCHA).
- Silent excepts should be avoided; `logging.warning` or `logging.error` is preferred for background scrape operations to aid debuggability without crashing the batch.
