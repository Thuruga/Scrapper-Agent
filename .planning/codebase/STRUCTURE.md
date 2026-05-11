# Project Structure

```text
scrapper/
├── api/                    # Camada de Endpoints FastAPI
│   ├── auth.py             # Lógica JWT e hashing
│   ├── routes_auth.py      # Endpoints de login [NEW]
│   ├── routes_category.py  # Varredura massiva + WebSockets
│   └── routes_monitor.py   # Dashboards e histórico
├── core/                   # Núcleo do Sistema
│   ├── base_scraper.py     # Classe base para scrapers paged
│   └── browser_manager.py  # Singleton Playwright [NEW]
├── services/               # Lógica de Negócio
│   ├── engines/            # Implementações de motores (Shopify, VTEX)
│   ├── orchestrator.py     # Pipeline de extração única
│   └── orchestrator_multi.py # Pipeline multi-marca
├── frontend/               # Interface React
│   └── src/
│       ├── api/client.ts   # Cliente com gestão de JWT
│       └── App.tsx         # Dashboard + Login View
├── data/                   # Armazenamento (JSON/Excel)
├── .planning/              # Documentação GSD
└── app.py                  # Entrypoint da Aplicação
```

## Key Files
- `app.py`: Bootstrap da aplicação e registro de rotas protegidas.
- `config.py`: Gestão de variáveis de ambiente e segredos.
- `requirements.txt`: Dependências do sistema.
