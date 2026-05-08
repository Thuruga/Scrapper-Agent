# Structure: Intelligence Scraper

## Directory Tree
```text
/
├── api/                # FastAPI routers (category, brand, monitors, search)
├── core/               # Shared logic (models, session, websocket, identity)
├── data/               # Persistent JSON storage (brands, price_monitors)
├── frontend/           # Modern React application (Vite, TS, Tailwind, Framer)
│   └── src/            # Application source code
├── services/           # Business logic and cross-platform orchestration
│   ├── engines/        # Engine abstraction layer (Factory, BaseEngine)
├── static/             # Legacy static assets (deprecated JS/CSS)
├── scratch/            # Diagnostic, validation, and spike scripts
└── app.py              # Main application entry point and service loader
```

## Key Components
- **`app.py`**: Entry point that initializes the API and schedules background monitors.
- **`services/engines/factory.py`**: Dynamic resolver that maps brands to their respective e-commerce engine.
- **`services/vtex_api_scraper.py`**: Robust client for VTEX private and public APIs.
- **`services/shopify_api_client.py`**: High-performance client for Shopify JSON endpoints.
- **`core/session_manager.py`**: Manages the global HTTP session pool.
- **`services/orchestrator_multi.py`**: Core logic for multi-brand competitive analysis.

## Evolutionary Notes
The project has successfully transitioned from brand-specific scripts in `scrapers/` to a unified Engine architecture. 
- **Legacy Removal**: Individual files in `scrapers/` and the old `scraper_factory.py` have been purged.
- **Modernization**: The frontend has been migrated to a React/Vite stack for a superior monitoring experience.
