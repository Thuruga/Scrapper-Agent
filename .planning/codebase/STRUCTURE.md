# Project Structure

```text
scrapper/
├── api/                    # Camada de Endpoints FastAPI
│   ├── auth.py             # Lógica central JWT
│   ├── routes_auth.py      # Login/Logout
│   ├── routes_brands.py    # Gestão de marcas e domínios
│   ├── routes_category.py  # Varredura em lote e multi-marca
│   ├── routes_jobs.py      # Gestão de cancelamento (asyncio.Event)
│   └── routes_monitor.py   # Dashboards de monitoramento
├── core/                   # Núcleo e Infraestrutura
│   ├── base_scraper.py     # Lógica base de paginação e retries
│   ├── browser_manager.py  # Singleton Playwright
│   ├── job_manager.py      # Registro global de cancelamento (asyncio.Event)
│   ├── models.py           # Modelos Pydantic (Bronze/Silver)
│   └── websocket.py        # Gestão de conexões em tempo real
├── services/               # Lógica de Negócio
│   ├── engines/            # Implementações VTEX/Shopify
│   ├── orchestrator.py     # Pipeline marca única
│   └── orchestrator_multi.py # Pipeline multi-marca paralelo
├── frontend/               # Interface React (Vite)
│   └── src/
│       ├── api/client.ts   # Cliente centralizado
│       └── App.tsx         # Dashboard Principal
├── data/                   # Armazenamento persistente (JSON/XLSX)
└── app.py                  # Entrypoint e registro de middlewares
```

## Key Modules
- `services.engines`: Ponto de extensão para novos e-commerces.
- `core.job_manager`: Onde reside a inteligência de cancelamento assíncrono.
- `api.routes_category`: Orquestração complexa de varredura.
