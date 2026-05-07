# Architecture

**Analysis Date:** 2026-05-07

## Pattern Overview

**Overall:** Layered Service-Oriented Web Application (FastAPI)

**Key Characteristics:**
- RESTful API with distinct route controllers
- Business logic encapsulated in specialized Services
- Asynchronous execution (async/await) throughout
- File-based persistence (JSON/Excel)
- Real-time communication via WebSockets for long-running tasks

## Layers

**API Layer:**
- Purpose: Handle HTTP requests, input validation, and response formatting
- Contains: Route handlers, request/response models (Pydantic)
- Location: `api/`
- Depends on: Service layer
- Used by: External clients (Frontend, API consumers)

**Service Layer:**
- Purpose: Core business logic, data processing, and orchestration
- Contains: `brand_service.py`, `orchestrator.py`, `vtex_api_scraper.py`, etc.
- Location: `services/`
- Depends on: Core/Domain layer, Scraper layer
- Used by: API layer

**Scraper Layer:**
- Purpose: Implement site-specific extraction logic
- Contains: `aramis.py`, `reserva.py`, `tommy.py`
- Location: `scrapers/`
- Depends on: Core/Base scraper logic
- Used by: Service layer (via `scraper_factory.py`)

**Core/Domain Layer:**
- Purpose: Shared models, base classes, and infrastructure utilities
- Contains: `models.py`, `base_scraper.py`, `websocket.py`
- Location: `core/`
- Depends on: Third-party libraries only
- Used by: All layers

## Data Flow

**Product Search Flow:**

1. Frontend sends `GET /search?q=...`
2. `api/routes_search.py` receives request and extracts params
3. Controller calls `services/vtex_search.py` (or similar)
4. Service interacts with VTEX API or spawns a scraper
5. Scraper extracts raw data -> Service transforms to Domain Model
6. Controller returns JSON response

**Category Scanning (WebSocket):**

1. Frontend initiates WebSocket connection to `/ws/scan`
2. `api/routes_category.py` accepts connection
3. Controller triggers `services/vtex_api_scraper.py`
4. Progress updates are sent back through the WebSocket periodically
5. Results are saved to `data/` and confirmation sent to UI

**State Management:**
- Stateless API: State is persisted to local JSON files in `data/`
- In-memory Task Tracking: `core/job_manager.py` manages active background tasks

## Key Abstractions

**Service:**
- Purpose: High-level business logic and storage abstraction
- Examples: `BrandService`, `PriceMonitorService`
- Pattern: Singleton (instantiated once per application)

**Scraper:**
- Purpose: Protocol for extracting data from specific websites
- Examples: `AramisScraper`, `ReservaScraper`
- Pattern: Strategy / Factory (`scraper_factory.py`)

**Model:**
- Purpose: Structured data representation with validation
- Examples: `Product`, `Brand`, `CategoryMapping`
- Pattern: Pydantic BaseModel

## Entry Points

**Web Application:**
- Location: `app.py`
- Triggers: Uvicorn invocation
- Responsibilities: Initialize FastAPI, register middlewares, mount routers, start background loops

**API Controllers:**
- Location: `api/routes_*.py`
- Triggers: HTTP/WebSocket requests
- Responsibilities: Input parsing, service delegation, error handling

## Error Handling

**Strategy:** Exception propagation with HTTP-aware catch blocks in the API layer.

**Patterns:**
- Services throw custom or standard exceptions
- API controllers use `try/except` to catch and raise `HTTPException` with appropriate status codes
- Global logging of exceptions to stdout for debugging

## Cross-Cutting Concerns

**Logging:**
- Standard Python `logging` used throughout. Configured in `app.py`.

**Validation:**
- Pydantic used for strict type checking and validation at API and Service boundaries.

**Evasion (Anti-Bot):**
- Centralized `identity.py` and `config.py` manage User-Agent rotation and proxy settings.

---

*Architecture analysis: 2026-05-07*
*Update when major patterns change*
