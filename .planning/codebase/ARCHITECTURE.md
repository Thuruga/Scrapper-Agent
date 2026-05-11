# Architecture

## System Overview
O Intelligence Scraper utiliza uma arquitetura orquestrada e assíncrona, projetada para alta performance e desacoplamento entre a coleta e o processamento de dados.

## Core Patterns

### 1. Engine Abstraction Layer
- `BaseEngine` define o contrato (bulk scrape, search, discovery).
- Implementações específicas (`ShopifyEngine`, `VTEXEngine`) abstraem a complexidade das APIs de e-commerce.

### 2. Anti-Bot Fallback System
- **Nível 1 (Rápido)**: Requisições diretas via `curl_cffi` ou `aiohttp`.
- **Nível 2 (Resiliente)**: Fallback automático para `Playwright` em caso de erro 403 ou desafios WAF detectados pelos clientes.

### 3. Streaming & Async Task Management
- **AsyncGenerators**: Toda a extração flui em streaming para evitar saturação de memória.
- **asyncio.Event**: Gerenciamento de cancelamento de jobs de forma idiomática e instantânea.
- **Task Offloading**: Operações pesadas de I/O (como geração de Excel com Pandas) são movidas para threads separadas via `asyncio.to_thread` para não travar a interface.

### 4. Layered Data Storage (Medallion)
- **Bronze**: Dados crus validados via Pydantic salvos em Excel.
- **Silver**: Dados consolidados e enriquecidos (ex: monitoramento de preços).

## Authentication & Authorization
- Fluxo centralizado de JWT com suporte a persistência no frontend e validação manual em WebSockets.
- Rotas protegidas por escopos de usuário.
