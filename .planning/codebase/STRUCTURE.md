# Project Structure

```text
scrapper/
├── api/                    # FastAPI routes and authentication
│   ├── auth.py             # Basic auth logic
│   ├── routes_brands.py    # Brand management
│   ├── routes_category.py  # Category scanning and mapping
│   ├── routes_jobs.py      # Background job status
│   ├── routes_product.py   # Product monitoring and export
│   └── routes_search.py    # Search and comparative search
├── core/                   # Shared core modules
│   ├── base_scraper.py     # Base class for all scrapers
│   ├── identity.py         # User-Agent and proxy rotation
│   ├── job_manager.py      # Basic job tracking
│   ├── models.py           # Pydantic data models
│   ├── vtex_schemas.py     # VTEX API specific schemas
│   └── websocket.py        # WebSocket connection manager
├── services/               # Business logic and service layer
│   ├── brand_service.py    # CRUD for brands
│   ├── category_mapping.py # Category tree and path resolution
│   ├── orchestrator.py     # Coordination for scraping jobs
│   ├── price_monitor.py    # Price tracking logic
│   ├── vtex_api_scraper.py # Core VTEX API integration
│   └── scraper_factory.py  # Dynamic scraper instantiation
├── scrapers/               # Brand-specific scraper implementations
│   ├── aramis.py
│   ├── reserva.py
│   └── tommy.py
├── frontend/               # React + Vite frontend
│   ├── src/
│   │   ├── components/     # UI components
│   │   └── App.tsx         # Main application entry
├── static/                 # Static assets (legacy or shared)
├── data/                   # JSON/Excel storage for persistence
├── app.py                  # Main entry point (FastAPI)
├── config.py               # Global settings and secrets
└── requirements.txt        # Python dependencies
```
