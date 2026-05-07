# Codebase Structure

**Analysis Date:** 2026-05-07

## Directory Layout

```
scrapper/
├── api/                # FastAPI route controllers and models
├── core/               # Shared domain models and utilities
├── data/               # Persistent data storage (JSON)
├── frontend/           # React frontend source code
├── scrapers/           # Site-specific scraper implementations
├── services/           # Business logic and storage orchestration
├── static/             # Static assets (images, CSS)
├── .planning/          # GSD planning and documentation
├── app.py              # Backend entry point
├── config.py           # Application configuration
└── requirements.txt    # Python dependencies
```

## Directory Purposes

**api/**
- Purpose: Handle HTTP/WebSocket requests and response mapping.
- Contains: `routes_*.py` files, `auth.py`.
- Key files: `routes_category.py` (scan logic), `routes_search.py` (search logic).

**core/**
- Purpose: Infrastructure and shared base classes.
- Contains: `base_scraper.py`, `models.py` (shared Pydantic models), `websocket.py`.
- Key files: `models.py` - Single source of truth for domain objects.

**data/**
- Purpose: File-based persistence layer.
- Contains: `*.json` files for brands, monitors, and mappings.
- Key files: `brands.json` - Active brand registry.

**frontend/**
- Purpose: React dashboard for user interaction.
- Contains: `src/`, `public/`, `package.json`, `vite.config.ts`.
- Subdirectories: `dist/` contains the production build served by FastAPI.

**scrapers/**
- Purpose: Specialized extraction logic for specific targets.
- Contains: `aramis.py`, `reserva.py`, `tommy.py`.
- Key files: `__init__.py` - Scraper registry.

**services/**
- Purpose: Implementation of business rules and coordination.
- Contains: `brand_service.py`, `price_monitor_service.py`, `category_intelligence.py`.
- Subdirectories: `engines/` contains high-level engine abstractions.
- Key files: `orchestrator.py` - Core coordination logic.


## Key File Locations

**Entry Points:**
- `app.py`: Main FastAPI server and application bootstrap.
- `frontend/src/main.tsx`: Frontend React entry point.

**Configuration:**
- `config.py`: Centralized settings singleton.
- `.env`: Environment-specific variables (local-only).

**Core Logic:**
- `services/orchestrator.py`: Coordination of scraping tasks.
- `services/vtex_catalog.py`: VTEX category tree management.

## Naming Conventions

**Files:**
- `snake_case.py`: All Python source files.
- `camelCase.ts/tsx`: Frontend React components and logic.

**Directories:**
- `snake_case`: Most directories.
- `kebab-case`: Frontend specific directories (if any).

## Where to Add New Code

**New Scraper:**
- Implementation: `scrapers/{brand}.py` (inherit from `BaseScraper`).
- Registration: Update `scrapers/__init__.py`.

**New API Endpoint:**
- Definition: Add to existing `api/routes_*.py` or create new `api/routes_{feature}.py`.
- Registration: Add to `api_router` in `api/__init__.py`.

**New Business Logic:**
- Implementation: `services/{feature}_service.py`.

**New Domain Model:**
- Definition: `core/models.py` (for shared models) or local to `api/` (for request/response specific).

## Special Directories

**frontend/dist/**
- Purpose: Compiled frontend assets.
- Source: Built from `frontend/` source.
- Committed: No (in `.gitignore`).

---

*Structure analysis: 2026-05-07*
*Update when directory structure changes*
