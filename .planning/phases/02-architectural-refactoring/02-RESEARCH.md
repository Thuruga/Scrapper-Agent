# Phase 2: Architectural Refactoring - Research

## Overview

Esta fase foca em desacoplar o sistema do ecossistema VTEX, criando uma camada de abstração que permita a inclusão de novos motores (Shopify, Magento, etc) e novas marcas sem redundância de código.

## Current Coupling Issues

### 1. Orchestrators & Services
- `services/orchestrator.py` e `services/orchestrator_multi.py` importam `VtexApiClient` diretamente.
- A lógica de fluxo (Paging -> Extraction -> Save) está amarrada às capacidades da API VTEX.

### 2. Brand Scrapers
- Arquivos em `scrapers/` (ex: `aramis.py`, `reserva.py`) são apenas wrappers repetitivos do `VtexApiClient`.
- Não há separação entre "O QUE extrair" (dados do produto) e "COMO extrair" (chamada de API vs Playwright).

### 3. Factory
- `scrapers/__init__.py` retorna módulos em vez de objetos de engine padronizados.

## Proposed Abstraction: Engine Layer

### BaseEngine (Interface)
Definirá o contrato para qualquer motor de e-commerce:
- `discover_categories()`: Retorna a árvore de categorias.
- `scrape_category(url)`: Retorna lista de produtos.
- `get_product(url)`: Retorna detalhes de um produto.
- `search(query)`: Realiza busca full-text.

### VTEXEngine (Implementation)
Consolidará toda a lógica atual do `VtexApiClient`, incluindo:
- Auto-discovery de conta.
- Fallback para `.vtexcommercestable`.
- Paginamento via Search API.

### EngineFactory
Substituirá o registro atual. Ao receber uma marca, a factory identificará qual motor ela usa e retornará a instância da Engine correta.

## Impacts & Benefits
- **Extensibilidade**: Adicionar um motor Shopify exigirá apenas criar uma `ShopifyEngine` que herda de `BaseEngine`.
- **Manutenibilidade**: Correções no fluxo de extração serão feitas em um único lugar (`BaseEngine` ou engine específica) e refletirão em todas as marcas.
- **Redução de Código**: Eliminação dos arquivos repetitivos em `scrapers/`.

## Verification Plan

### Automated Tests
- Validar se a `EngineFactory` retorna a engine correta para marcas VTEX.
- Garantir que a `VTEXEngine` produz o mesmo output (RawProductBronze) que o cliente atual.

### Manual Verification
- Executar uma varredura via dashboard e validar que o fluxo continua funcionando de ponta a ponta.

---
*Research completed: 2026-05-07*
