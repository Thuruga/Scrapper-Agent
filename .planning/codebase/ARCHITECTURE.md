# Architecture: Intelligence Scraper

## Overview
O sistema utiliza uma arquitetura em camadas, agora desacoplada por uma camada de abstração de motores (Engines), permitindo suporte a múltiplas plataformas de e-commerce (VTEX, Shopify, etc).

## Component Hierarchy

### 1. API Layer (`api/`)
- **FastAPI Router**: Define endpoints REST e WebSocket.
- **Background Tasks**: Gerencia jobs de varredura longa no mesmo event loop da aplicação principal para reaproveitamento de recursos.

### 2. Service Layer (`services/`)
- **Orchestrators**: Coordenam o fluxo de varredura (Paginada -> Extração -> Excel).
  - `orchestrator.py`: Marca única.
  - `orchestrator_multi.py`: Multi-marca paralela usando `asyncio.gather`.
- **Category Intelligence**: Realiza Fuzzy Matching entre categorias da plataforma e slugs canônicos.
- **Price Monitor**: Serviço em background para monitoramento recorrente de preços.

### 3. Engine Layer (`services/engines/`)
- **BaseEngine**: Interface abstrata que define o contrato para qualquer plataforma.
- **VTEXEngine / ShopifyEngine**: Implementações concretas que traduzem comandos genéricos em chamadas de API específicas de cada motor.
- **EngineFactory**: Router dinâmico que instancia o motor correto baseado no metadado da marca.

### 4. Core Layer (`core/`)
- **SessionManager**: Gerencia o ciclo de vida de uma única `aiohttp.ClientSession` compartilhada.
- **Models**: Definições Pydantic para validação rigorosa de dados (Camada Bronze).

## Data Flow
1. **Frontend** solicita varredura.
2. **API** lança `Background Task`.
3. **Orchestrator** solicita ao **Engine** a extração dos dados.
4. **Engine** usa **ApiClient** para buscar JSONs da plataforma.
5. **Orchestrator** consolida dados e salva em Excel via `run_in_executor`.
6. **WebSocket** envia logs de progresso em tempo real.

## Threading & Async Model
- **Single Event Loop**: Tudo roda no loop principal do FastAPI para evitar conflitos de sessão HTTP.
- **CPU Offloading**: Operações pesadas de Pandas/Excel rodam em `ThreadPoolExecutor` para não bloquear o loop de IO.
