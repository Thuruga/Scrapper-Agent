# Structure: Intelligence Scraper

## Directory Tree
```text
/
├── api/                # Rotas FastAPI (category, brand, monitors, search)
├── core/               # Lógica base (models, session, websocket, identity)
├── data/               # Persistência JSON (brands, price_monitors)
├── frontend/           # Aplicação React (Vite, TS, Tailwind)
├── scrapers/           # API Clients de baixo nível (VTEX, Shopify)
├── services/           # Lógica de negócio e orquestração
│   ├── engines/        # Abstração de motores (Factory, BaseEngine)
├── static/             # Assets estáticos (JS/CSS legados)
├── scratch/            # Scripts de teste e verificação
└── app.py              # Ponto de entrada da aplicação
```

## Key Files
- `app.py`: Inicialização do FastAPI e serviços de monitoramento.
- `services/engines/factory.py`: Ponto central para obtenção de motores.
- `core/session_manager.py`: Garantia de performance e reuso de conexões.
- `api/routes_category.py`: Orquestração de varreduras via Background Tasks.

## Modularity
O sistema é altamente modular. Adicionar um novo motor (ex: Magento) requer apenas:
1. Criar `magento_engine.py` em `services/engines/`.
2. Registrar no `factory.py`.
3. Configurar a marca com `"engine": "magento"` no `brands.json`.
