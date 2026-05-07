# External Integrations

**Analysis Date:** 2026-05-07

## APIs & External Services

**Scraping Services:**
- BrightData Proxy - High-quality residential proxies for evasion
  - Integration method: HTTP Proxy URL
  - Auth: `BRIGHTDATA_PROXY_URL` env var
- ScraperAPI - Alternative scraping infrastructure
  - Integration method: API Key via request parameters
  - Auth: `SCRAPERAPI_KEY` env var

**Target Platforms:**
- VTEX - Primary target for catalog and search scraping
  - Integration method: Direct API calls to VTEX search and catalog endpoints
  - SDK/Client: `aiohttp`, `curl_cffi`, `playwright`
  - Authentication: Session-based or public API access

## Data Storage

**Databases:**
- JSON Files - Local persistence for project metadata
  - Location: `data/` directory
  - Files: `brands.json`, `price_monitors.json`, `category_mappings.json`
  - Management: `services/brand_service.py`, `services/price_monitor_service.py`

**File Storage:**
- Excel (.xlsx) - Data export and reporting
  - Location: Root directory or user-specified paths
  - Management: `pandas` with `openpyxl`

## Authentication & Identity

**API Access:**
- Custom API Key - Secures internal endpoints
  - Implementation: Header-based check (`X-API-Key` or similar)
  - Auth: `SCRAPER_API_KEY` env var (default: `dev-key-123`)

## Monitoring & Observability

**Logs:**
- Python Logging - Structured logs to stdout
  - Implementation: `logging` module in `app.py`
  - Format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`

## CI/CD & Deployment

**Hosting:**
- Local/Custom Server - Currently runs as a standalone Python application
  - Deployment: Manual or script-based
  - Port: 8000 (default)

## Environment Configuration

**Development:**
- Required env vars: `SCRAPER_API_KEY`, `BRIGHTDATA_PROXY_URL` (optional)
- Secrets location: `.env` file (gitignored)

## Webhooks & Callbacks

**Outgoing:**
- WebSocket - Real-time progress updates for scans
  - Implementation: `core/websocket.py` and `api/routes_category.py`
  - Purpose: UI progress bars and status updates during category scans

---

*Integration audit: 2026-05-07*
*Update when adding/removing external services*
