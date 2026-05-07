# Technology Stack

**Analysis Date:** 2026-05-07

## Languages

**Primary:**
- Python 3.10+ - All backend application code (`api/`, `services/`, `scrapers/`, `core/`)

**Secondary:**
- JavaScript/TypeScript (React) - Frontend dashboard code (`frontend/`)
- HTML/CSS - Static assets and template files (`index.html`, `static/`)

## Runtime

**Environment:**
- Python 3.10+
- Node.js (for frontend build process)

**Package Manager:**
- pip - Using `requirements.txt`
- npm - Used for the frontend project in `frontend/`

## Frameworks

**Core:**
- FastAPI >=0.110.0 - Main web framework for the backend API
- React - UI framework for the dashboard (served as static files)

**Testing:**
- None detected (no `tests/` directory)

**Build/Dev:**
- Uvicorn[standard] - ASGI server for running the FastAPI application
- Playwright - Used for browser-based web scraping

## Key Dependencies

**Critical:**
- Pydantic >=2.0 - Data validation and settings management
- playwright >=1.40.0 - Headless browser automation for scraping
- aiohttp >=3.9.0 - Asynchronous HTTP client for API-based scraping
- curl_cffi >=0.6.0 - High-performance HTTP client for evasion
- pandas >=2.0 - Data manipulation and export (Excel/CSV)

**Infrastructure:**
- python-dotenv - Environment variable management
- pydantic-settings - Settings management from env files

## Configuration

**Environment:**
- `.env` files - Managed via `python-dotenv` and `Pydantic Settings`
- `config.py` - Centralized configuration singleton

**Build:**
- `requirements.txt` - Backend dependencies
- Frontend has its own build pipeline in `frontend/` (Vite inferred)

## Platform Requirements

**Development:**
- Windows (ProactorEventLoopPolicy detected in `app.py`)
- Any platform with Python 3.10+ and Node.js

**Production:**
- Any ASGI-compatible environment (Docker, Cloud Run, etc.)
- Headless browser support required for Playwright

---

*Stack analysis: 2026-05-07*
*Update after major dependency changes*
