# Stack: Intelligence Scraper

## Backend
- **Framework**: FastAPI (Python 3.11+)
- **Server**: Uvicorn
- **Async IO**: `aiohttp` para requisições de alta performance.
- **Resilience**: `curl_cffi` para bypass de WAF/Cloudflare.
- **Data Analysis**: Pandas (geração de relatórios Excel).

## Frontend
- **Framework**: React 18+ (Vite)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Real-time**: WebSockets para logs de streaming.

## Infrastructure
- **Storage**: JSON dinâmico (local) para metadados.
- **Excel**: `openpyxl` como engine de escrita.
