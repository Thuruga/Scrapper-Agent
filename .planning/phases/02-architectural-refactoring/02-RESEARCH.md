# Phase 2: Architectural Refactoring / BaseEngine - Research

## Overview

Esta fase foca em criar uma abstração de alto nível (`Engine`) para separar a lógica de orquestração da implementação técnica do scraping (VTEX, etc). Também foca em tornar o `CategoryIntelligenceService` autônomo.

## Architecture Refactoring

### Current State
- `orchestrator.py` está acoplado ao `VtexApiClient` (importado localmente na função).
- A lógica de salvamento e consolidação está dentro do orquestrador.
- Existe um `scrapers/` registry que mapeia marcas para módulos, mas é redundante com o `VtexApiClient` que já lida com múltiplas marcas VTEX.

### Proposed Abstraction: Engine Layer
1. **BaseEngine (ABC)**:
   - `discover_categories()`: Aciona a inteligência para mapear categorias.
   - `run_bulk_scrape()`: Orquestra o ciclo completo (Scan -> Parse -> Save).
   - `resolve_engine(brand_key)`: Factory para retornar a engine correta.

2. **VTEXEngine**:
   - Encapsula chamadas ao `VtexApiClient`.
   - Gerencia o fallback de domínios estáveis.
   - Implementa a descoberta automática de categorias específica da VTEX.

## Autonomous Category Intelligence

### Goal
O `CategoryIntelligenceService` deve rodar em background sem intervenção do usuário.

### Strategy
1. **Background Discovery**: Quando uma nova marca é cadastrada, a `BaseEngine` deve disparar uma tarefa em background para rodar a descoberta.
2. **Persistence**: Os resultados devem ser salvos diretamente nos `mappings` da marca via `brand_service`.
3. **Trigger**: Adicionar um hook no `brand_service.save_brand` para disparar a descoberta se a marca for nova.

## Refactoring Roadmap

1. **Step 1**: Criar `services/engines/base_engine.py` e `services/engines/vtex_engine.py`.
2. **Step 2**: Mover a lógica do `orchestrator.py` para as Engines.
3. **Step 3**: Atualizar `api/routes_category.py` e `api/routes_brands.py` para usar a nova camada de Engine.
4. **Step 4**: Implementar o trigger autônomo de descoberta em background.

## Verification Plan

### Automated Tests
- Validar se a `VTEXEngine` consegue realizar uma varredura completa usando a nova abstração.
- Validar o trigger automático de categorias ao cadastrar uma marca via script.

### Manual Verification
- Cadastrar uma marca "vazia" no dashboard e observar os logs em background descobrindo as categorias.
- Verificar se a aba de "Varredura" já exibe categorias mapeadas sem ação do usuário.

---
*Research completed: 2026-05-07*
