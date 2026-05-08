# Architecture: Intelligence Scraper

## Overview
The system employs a layered architecture, decoupled by an Engine Abstraction Layer. This ensures that business logic (orchestration, monitoring, pricing) remains platform-agnostic, allowing seamless support for VTEX, Shopify, and future e-commerce platforms.

## Component Hierarchy

### 1. API Layer (`api/`)
- **FastAPI Router**: Defines RESTful endpoints and WebSocket handlers for real-time communication.
- **Background Tasks**: Manages long-running extraction jobs within the primary event loop, optimizing resource usage and connection pooling.

### 2. Service Layer (`services/`)
- **Orchestrators**: Coordinates the extraction pipeline (Discovery -> Parallel Extraction -> Excel Consolidation).
  - `orchestrator.py`: Handles single-brand workflows.
  - `orchestrator_multi.py`: Manages multi-brand comparative searches using `asyncio.gather`.
- **Intelligence Services**: 
  - `CategoryIntelligence`: Platform-agnostic service for discovering collections/categories using Fuzzy Matching.
  - `ReviewService`: Multi-provider review aggregator (Trustvox, VTEX Native).
- **Price Monitor**: Recurrent service for tracking price fluctuations and availability changes.

### 3. Engine Layer (`services/engines/`)
- **BaseEngine**: Abstract contract defining the required behavior for any e-commerce engine.
- **VTEXEngine / ShopifyEngine**: Concrete implementations that interface with platform-specific APIs.
- **EngineFactory**: Central resolver for instantiating the correct engine based on brand configuration.

### 4. Core Layer (`core/`)
- **SessionManager**: Global singleton maintaining an active `aiohttp.ClientSession` for the application lifecycle.
- **Models**: Pydantic schemas ensuring data integrity across the "Bronze" (raw) and "Silver" (processed) layers.
- **WebsocketManager**: Manages real-time log broadcasting to the frontend.

## Threading & Async Model
- **Async-First IO**: All network operations are non-blocking, utilizing Python's `asyncio`.
- **CPU-Bound Offloading**: Intensive tasks (Pandas processing, Excel generation) are delegated to thread pools via `run_in_executor` to prevent event loop lag and maintain API responsiveness.
