# Integrations

## External Services
- **E-commerce APIs**: 
  - **VTEX**: Integração profunda via Catalog e Search API. Inclui módulo de **Auto-Discovery** de nomes de conta via inspeção de HTML.
  - **Shopify**: Integração via endpoints JSON de coleções e produtos.
- **Proxies**: Gestão de IPs rotativos via `IdentityManager` integrada aos clientes HTTP.

## Browser Automation
- **Playwright**: Mecanismo de bypass de última instância para sites protegidos por Cloudflare ou que exigem renderização JS pesada.
  - Driver: Chromium (Headless).
  - Persistência: `SessionManager` compartilha sessões entre clientes quando possível.

## Security & Auth
- **JWT Standard**: Implementação customizada de proteção de rotas via FastAPI dependencies.
- **WebSocket Auth**: Validação manual de tokens para conexões em tempo real.

## Data Formats
- **Input**: JSON (Respostas nativas de e-commerce).
- **Output**: XLSX (Excel) gerado de forma não-bloqueante via `asyncio.to_thread`.
