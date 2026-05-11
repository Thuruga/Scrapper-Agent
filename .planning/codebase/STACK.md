# Technology Stack

## Core
- **Language**: Python 3.10+
- **Backend Framework**: FastAPI (Async)
- **Frontend Framework**: React 18+ (Vite)
- **Styling**: Vanilla CSS (Premium Glassmorphism)

## Data & Extraction
- **HTTP Clients**: 
  - `curl_cffi` (Impersonate mode) for high-speed scraping and WAF bypass.
  - `aiohttp` for standard REST API integrations (VTEX, Shopify).
- **Fallback Engine**: `Playwright` (Headless Chromium) for anti-bot bypass and JavaScript rendering.
- **Data Processing**: `Pandas` for Excel generation and complex data manipulation.
- **Validation**: `Pydantic v2` for strict data quality gates and type safety.

## Security
- **Authentication**: JWT (JSON Web Tokens).
- **Libraries**: `python-jose` (signing), `passlib[bcrypt]` (hashing).
- **Storage**: Browser LocalStorage for persistent sessions.

## Infrastructure
- **Web Server**: Uvicorn (ASGI).
- **Persistence**: File-based (Excel/JSON) for data layers.
- **Concurrency**: `asyncio` for non-blocking I/O and task management.
- **Real-time**: WebSockets for live logging and progress monitoring.
