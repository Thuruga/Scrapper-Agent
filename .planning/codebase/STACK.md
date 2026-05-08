# Stack: Intelligence Scraper

## Backend
- **Framework**: FastAPI (Python 3.11+)
- **Server**: Uvicorn
- **Async IO**: `aiohttp` for high-performance requests.
- **Resilience**: `curl_cffi` for WAF/Cloudflare bypass.
- **Automation**: `playwright` for complex scraping scenarios.
- **Data Validation**: `pydantic` (v2) for models and settings.
- **Data Analysis**: Pandas for Excel report generation.

## Frontend
- **Framework**: React 19 (Vite)
- **Language**: TypeScript
- **State & Animation**: Framer Motion for premium UI transitions.
- **Icons**: Lucide React.
- **Styling**: Tailwind CSS with `tailwind-merge` and `clsx`.
- **Real-time**: WebSockets for streaming logs and progress.

## Infrastructure
- **Storage**: Dynamic local JSON for metadata and persistence.
- **Excel**: `openpyxl` as the writing engine.
