# Structure: Intelligence Scraper

## Directory Tree
```text
/
├── api/                # Rotas FastAPI (category, brand, monitors, search)
├── core/               # Lógica base (models, session, websocket, identity)
├── data/               # Persistência JSON (brands, price_monitors)
├── frontend/           # Aplicação React (Vite, TS, Tailwind)
├── services/           # Lógica de negócio e orquestração
│   ├── engines/        # Abstração de motores (Factory, BaseEngine)
├── static/             # Assets estáticos (JS/CSS legados)
├── scratch/            # Scripts de diagnóstico e validação
└── app.py              # Ponto de entrada da aplicação
```

## Key Files
- `app.py`: Ponto de entrada que carrega a API e o Price Monitor.
- `services/engines/factory.py`: Resolve qual motor usar baseado no `brands.json`.
- `services/vtex_api_scraper.py`: Cliente robusto para APIs VTEX.
- `services/shopify_api_client.py`: Cliente robusto para APIs Shopify.
- `core/session_manager.py`: Gerenciador de conexão global.

## Removed Legacy
O projeto passou por uma faxina técnica onde os arquivos individuais em `scrapers/` (como `aramis.py`) e o `scraper_factory.py` legado foram removidos em favor da arquitetura de Engines unificada.
```text
/scrapers/              # Pasta esvaziada (legado removido)
```
