# Architecture

## Overview
The project follows a **Monolithic Service-Oriented Architecture (SOA)** approach with a clear separation between the API layer, business logic (services), and data extraction (scrapers). It is designed to be highly resilient to changes in target website structures by utilizing an "API-First" scraping strategy with multiple fallback mechanisms.

## Core Layers
1. **API Layer (`api/`)**: FastAPI routes that handle HTTP requests, input validation (Pydantic), and WebSocket connections.
2. **Service Layer (`services/`)**: The core business logic. Contains orchestrators that coordinate multiple services and scrapers.
3. **Scraper Layer (`scrapers/`, `core/base_scraper.py`)**: Implementation of data extraction logic. Uses a factory pattern to instantiate the correct scraper for each brand.
4. **Core Layer (`core/`)**: Base classes, shared models (Pydantic), and utility modules (WebSocket, Job Manager).
5. **Frontend Layer (`frontend/`)**: A modern React application built with Vite, utilizing a component-based architecture for the dashboard.

## Key Design Patterns
- **Factory Pattern**: Used in `ScraperFactory` to dynamically create scrapers.
- **Repository/Service Pattern**: Business logic is encapsulated in service classes.
- **Async/Await**: Heavily used throughout the backend to handle concurrent I/O operations (API calls, scraping).
- **Identity Rotation**: Managed via `IdentityManager` to prevent blocking by rotating User-Agents and potentially proxies.
- **Layered Data Models**: Uses Pydantic models to define "Bronze" (raw) and more refined data structures.

## Data Flow
1. User interacts with the **Frontend Dashboard**.
2. Frontend calls **FastAPI endpoints**.
3. API routes invoke **Services** (e.g., `Orchestrator`).
4. Services use the **Scraper Factory** to get a brand-specific scraper.
5. Scrapers interact with **VTEX APIs** or perform **Web Scraping**.
6. Data is returned, validated, and potentially saved to **Local Storage** or exported to **Excel**.
7. Real-time updates are sent back via **WebSockets**.
