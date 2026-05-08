# Roadmap: Intelligence Scraper

## Overview

Este roadmap foca na estabilização do frontend, automação da inteligência de catálogos e na criação de uma base arquitetural extensível para suportar novas marcas e motores de e-commerce além do VTEX.

## Phases

- [x] **Phase 1: Stabilization & Core Intelligence** - Fix frontend and automate category mapping.
- [x] **Phase 2: Architectural Refactoring** - Engine Abstraction Layer for multi-platform support.
- [ ] **Phase 3: Reliability & Logging** - Advanced logging and network resilience.
- [x] **Phase 4: Expansion Spike** - Adding a non-VTEX pilot brand.

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

### Phase 3: Reliability & Logging
**Goal**: Garantir que o sistema seja resiliente a falhas de rede.
**Depends on**: Phase 2
**Requirements**: LOG-01, LOG-02
**Success Criteria**:
  1. Logs detalhados e retry automático funcionando.
**Plans**: 1 plan

### Phase 4: Expansion Spike
**Goal**: Provar a arquitetura adicionando um motor não-VTEX.
**Depends on**: Phase 3
**Success Criteria**:
  1. Uma marca de outro motor (ex: Shopify) é varrida com sucesso.
**Plans**: 1 plan

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Stabilization & Core Intelligence | 2/2 | Completed | 2026-05-08 |
| 2. Architectural Refactoring | 1/1 | Completed | 2026-05-08 |
| 3. Reliability & Logging | 0/1 | Not started | - |
| 4. Expansion Spike | 1/1 | Completed | 2026-05-08 |
