# Architecture: Intelligence Scraper

## Overview
O sistema utiliza uma arquitetura em camadas, totalmente desacoplada por uma camada de abstração de motores (Engines). Isso permite que a lógica de negócio (orquestração, monitoramento, precificação) seja idêntica independentemente da plataforma de e-commerce (VTEX, Shopify, etc).

## Component Hierarchy

### 1. API Layer (`api/`)
- **FastAPI Router**: Define endpoints REST e WebSocket.
- **Background Tasks**: Gerencia jobs de varredura longa no mesmo event loop da aplicação principal, garantindo reuso de conexões HTTP.

### 2. Service Layer (`services/`)
- **Orchestrators**: Coordenam o pipeline de extração (Varredura -> Extração Paralela -> Consolidação Excel).
  - `orchestrator.py`: Fluxo para marca única.
  - `orchestrator_multi.py`: Fluxo multi-marca usando `asyncio.gather`.
- **Category Intelligence**: Serviço agnóstico que utiliza o motor da marca para descobrir coleções/categorias e mapeá-las via Fuzzy Matching.
- **Price Monitor**: Serviço recorrente que verifica mudanças de preço e disponibilidade.

### 3. Engine Layer (`services/engines/`)
- **BaseEngine**: Contrato abstrato que unifica o comportamento de qualquer motor.
- **VTEXEngine / ShopifyEngine**: Implementações que consomem APIs específicas.
- **EngineFactory**: Ponto central de resolução de motores.

### 4. Core Layer (`core/`)
- **SessionManager**: Singleton que mantém a `aiohttp.ClientSession` ativa durante todo o ciclo de vida do servidor.
- **Models**: Esquemas Pydantic que garantem a integridade da "Camada Bronze" dos dados.

## Threading & Async Model
- **Async-First**: Toda a IO é não-bloqueante no loop principal.
- **Worker Offloading**: Tarefas de CPU intensiva (Pandas/Excel) são delegadas para threads via `run_in_executor` para evitar lag na API.
