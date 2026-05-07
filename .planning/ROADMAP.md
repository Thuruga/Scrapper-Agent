# Roadmap: Intelligence Scraper

## Overview

Este roadmap foca na estabilização do frontend, automação da inteligência de catálogos e na criação de uma base arquitetural extensível para suportar novas marcas e motores de e-commerce além do VTEX.

## Phases

- [ ] **Phase 1: Frontend Stability** - Correção de instabilidades de UX no dashboard.
- [ ] **Phase 2: Architectural Refactoring** - Criação da Engine Abstraction Layer para suporte multimarcas.
- [ ] **Phase 3: Automated Mapping** - Implementação da descoberta automática de categorias.
- [ ] **Phase 4: Reliability & Polish** - Logging avançado e resiliência de rede.

## Phase Details

### Phase 1: Frontend Stability
**Goal**: Eliminar o reload indesejado da página e melhorar o feedback visual.
**Depends on**: Nothing
**Requirements**: UI-01, UI-02
**Success Criteria**:
  1. O usuário adiciona um link de monitoramento sem que a página resete.
  2. Notificações de sucesso/erro aparecem sem limpar o estado global.
**Plans**: 1 plan

Plans:
- [ ] 01-01: Fix form submission event handling and state preservation.

### Phase 2: Architectural Refactoring
**Goal**: Desacoplar a lógica VTEX e preparar para novos motores.
**Depends on**: Phase 1
**Requirements**: ARCH-01, ARCH-02, ARCH-03
**Success Criteria**:
  1. Existe uma classe abstrata `BaseEngine` definindo o contrato.
  2. `VTEXEngine` contém toda a lógica específica da VTEX.
  3. `scraper_factory.py` instancia scrapers baseados em engine.
**Plans**: 2 plans

Plans:
- [ ] 02-01: Implement BaseEngine and VTEXEngine abstraction.
- [ ] 02-02: Refactor Factory and Scraper registration for dynamic loading.

### Phase 3: Automated Mapping
**Goal**: Eliminar a necessidade de mapeamento manual de categorias.
**Depends on**: Phase 2
**Requirements**: AI-01, AI-02, AI-03
**Success Criteria**:
  1. O sistema identifica categorias de uma nova marca VTEX automaticamente.
  2. O relacionamento entre categorias externas e internas ocorre sem intervenção.
**Plans**: 2 plans

Plans:
- [ ] 03-01: Develop category auto-discovery logic for VTEX.
- [ ] 03-02: Implement auto-relationship engine for internal catalog.

### Phase 4: Reliability & Polish
**Goal**: Garantir que o sistema seja resiliente a falhas de rede e mudanças em sites.
**Depends on**: Phase 3
**Requirements**: LOG-01, LOG-02
**Success Criteria**:
  1. Logs detalhados explicam o motivo exato de uma falha de extração.
  2. Falhas transientes de rede são recuperadas automaticamente via retry.
**Plans**: 1 plan

Plans:
- [ ] 04-01: Implement enhanced logging and retry mechanisms.

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Frontend Stability | 0/1 | Not started | - |
| 2. Architectural Refactoring | 0/2 | Not started | - |
| 3. Automated Mapping | 0/2 | Not started | - |
| 4. Reliability & Polish | 0/1 | Not started | - |
