# Architecture

## System Overview
O Intelligence Scraper utiliza uma arquitetura orquestrada e assíncrona, projetada para alta performance e resiliência contra bloqueios.

## Core Patterns

### 1. Engine Abstraction Layer
- `BaseEngine` define o contrato para extração.
- Implementações específicas (`ShopifyEngine`, `VTEXEngine`) lidam com as particularidades de cada plataforma.

### 2. Anti-Bot Fallback System
- **Nível 1 (Rápido)**: `curl_cffi` com impersonate de browser.
- **Nível 2 (Resiliente)**: Fallback automático para `Playwright` quando detectado erro 403 ou desafios de rede.
- Gerenciado via `BrowserManager` (Singleton).

### 3. Streaming Data Pipeline
- Toda a extração é feita via `AsyncGenerators` (`yield`).
- Os dados fluem dos Scrapers -> Engines -> Orchestrators sem acumulação em massa, liberando o event loop do FastAPI.

### 4. Layered Data Storage (Medallion-ish)
- **Bronze**: Dados crus extraídos (Excel/JSON).
- **Silver**: Dados validados via Pydantic e enriquecidos com histórico de preços.

## Authentication Flow
- Login via `/api/auth/login` (Admin credentials).
- JWT emitido para o frontend.
- Todas as rotas de API protegidas via `Depends(get_current_user)`.
- Suporte a token em query param para WebSockets.
