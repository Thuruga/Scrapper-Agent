---
last_mapped_commit: unknown
---

# 🔌 Integrations

**Date:** 2026-06-08

## External APIs & Services
- **Supabase**: Used for data persistence, managed via the `supabase` Python client (`SUPABASE_URL`, `SUPABASE_KEY`).
- **Redis**: Used heavily for Celery Task Queue brokering and Pub/Sub mechanism for streaming Server-Sent Events (SSE) to the frontend.
- **ScraperAPI / BrightData**: Used as proxy gateways with CAPTCHA solving capabilities (`SCRAPERAPI_KEY`, `BRIGHTDATA_PROXY_URL`).

## Supported Marketplaces / Targets
- **Netshoes**: Queried for products and categories (e.g., via `NETSHOES_GENDER_FILTER`).
- **Mercado Livre**: Supported scraping target, configured with specific timeouts for Playwright and Curl (`ML_TIMEOUT_PLAYWRIGHT_SECONDS`, `ML_CATEGORY_PATH`).
- **Amazon**: Includes fallback mechanisms for Playwright when encountering CAPTCHAs (`PLAYWRIGHT_AMAZON_FALLBACK`).
- **VTEX**: Explicit support for VTEX catalog scraping and category resolution (`vtex_api_scraper.py`, `vtex_catalog.py`). Used for most direct brand scraping.
- **Shopify**: Supported via `shopify_api_client.py`.
- **Trustvox Reviews**: Supported for audited brands with `review_provider="trustvox"` and `review_store_id`; currently Aramis uses store id `78800`. Full comments are fetched on demand through monitor scan-product actions, not inline search.
- **VTEX Reviews & Ratings**: Summary endpoints are supported by `review_service.py`; full-comment support requires explicit per-brand evidence and is not inferred from `engine="vtex"`.

## Webhooks / Events
- **Server-Sent Events (SSE)**: Streams `job_notifications` from Redis to the frontend via `/notifications/stream` for background search job updates.
- **WebSockets**: Supported via `/ws/{job_id}` for granular orchestrator streaming and monitor tracking.
- **Monitor product review action**: `POST /monitor/category/{monitor_id}/products/{scan_product_id}/reviews` fetches compact, page-capped comments for persisted scan products using server-side brand/product identity.
