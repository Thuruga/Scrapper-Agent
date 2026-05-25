# Roadmap: Intelligence Scraper

## Overview

Este roadmap foca na estabilização do frontend, automação da inteligência de catálogos e na criação de uma base arquitetural extensível para suportar novas marcas e motores de e-commerce além do VTEX.

## Phases

- [x] **Phase 1: Stabilization & Core Intelligence** - Fix frontend and automate category mapping.
- [x] **Phase 2: Architectural Refactoring** - Engine Abstraction Layer for multi-platform support.
- [x] **Phase 3: Price History & Monitoring** - Histórico de preços e visualização (MON-01).
- [x] **Phase 4: Expansion Spike** - Adding a non-VTEX pilot brand.
- [x] **Phase 5: Data Quality Gates** - Pydantic-based validation layer in BaseEngine.
- [x] **Phase 6: Resilience, Optimization & Security** - Anti-bot fallback, streaming and JWT Auth.

## Phase Details

### Phase 1: Stabilization & Core Intelligence
**Goal**: Resolver o bug de reload no frontend e automatizar a descoberta de categorias VTEX.
**Depends on**: Nothing
**Requirements**: UI-01, UI-02, AI-01, AI-02
**Success Criteria**:
  1. O usuário adiciona um link de monitoramento sem que a página resete.
  2. O sistema identifica categorias de uma nova marca VTEX automaticamente.
**Plans**: 2 plans

Plans:
- [x] 01-01: Frontend event handling fix and UI feedback improvement.
- [x] 01-02: Backend category auto-discovery and intelligent matching.

### Phase 2: Architectural Refactoring
**Goal**: Desacoplar a lógica VTEX e preparar para novos motores.
**Status**: Completed
**Depends on**: Phase 1
**Requirements**: ARCH-01, ARCH-02, ARCH-03
**Success Criteria**:
  1. Existe uma classe abstrata `BaseEngine` definindo o contrato.
  2. `VTEXEngine` contém toda a lógica específica da VTEX.
**Plans**: 1 plan

Plans:
- [x] 02-01: Implement Engine Abstraction Layer.

### Phase 3: Price History & Monitoring
**Goal**: Implementar persistência de preços para visualização de histórico.
**Depends on**: Phase 2
**Requirements**: MON-01
**Success Criteria**:
  1. O sistema armazena variações de preço no tempo.
  2. O frontend exibe o histórico de preços.
**Plans**: 1 plan

### Phase 4: Expansion Spike
**Goal**: Provar a arquitetura adicionando um motor não-VTEX.
**Depends on**: Phase 3
**Success Criteria**:
  1. Uma marca de outro motor (ex: Shopify) é varrida com sucesso.
**Plans**: 1 plan

### Phase 5: Data Quality Gates
**Goal**: Validar dados na saída dos engines usando Pydantic.
**Success Criteria**:
  1. Produtos com preço zero ou sem imagem são descartados automaticamente.
**Plans**: 1 plan

### Phase 6: Resilience, Optimization & Security
**Goal**: Melhorar a estabilidade do sistema contra bloqueios e otimizar o uso de recursos.
**Success Criteria**:
  1. Fallback automático para Playwright em caso de bloqueio.
  2. Extração via streaming (AsyncGenerator) para economia de memória.
  3. Dashboard protegido por autenticação JWT.

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Stabilization & Core Intelligence | 2/2 | Completed | 2026-05-08 |
| 2. Architectural Refactoring | 1/1 | Completed | 2026-05-08 |
| 3. Price History & Monitoring | 1/1 | Completed | 2026-05-11 |
| 4. Expansion Spike | 1/1 | Completed | 2026-05-08 |
| 5. Data Quality Gates | 1/1 | Completed | 2026-05-08 |
| 6. Resilience, Optimization & Security | 1/1 | Completed | 2026-05-11 |

### Phase 7: Marketplace and Web Search Integration
**Goal**: Expand comparative search to include Netshoes and Mercado Livre, extracting prices, sizes, and colors.
**Depends on**: Phase 6
**Success Criteria**:
  1. The /search route returns Mercado Livre and Netshoes results alongside VTEX brands.
  2. Search results include available sizes and colors.
**Plans**: 1 plan

