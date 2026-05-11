# Technology Stack

## Core
- **Language**: Python 3.10+
- **Backend Framework**: FastAPI (Async)
- **Frontend Framework**: React 18+ (Vite)
- **Styling**: Vanilla CSS (Premium Glassmorphism)

## Data & Extraction
- **HTTP Client**: `curl_cffi` (Impersonate mode) for high-speed scraping.
- **Fallback Engine**: `Playwright` (Headless Chromium) for anti-bot bypass.
- **Data Processing**: `Pandas` for Excel generation and data manipulation.
- **Validation**: `Pydantic v2` for data quality gates.

## Security
- **Authentication**: JWT (JSON Web Tokens).
- **Libraries**: `python-jose` (signing), `passlib[bcrypt]` (hashing).
- **Storage**: Browser LocalStorage for tokens.

## Infrastructure
- **Web Server**: Uvicorn.
- **Persistence**: File-based (Excel/JSON) for Bronze/Silver layers.
- **Real-time**: WebSockets for live scraping progress.
