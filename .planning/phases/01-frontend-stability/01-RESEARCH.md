# Phase 1: Frontend Stability & Category Intelligence - Research

## Overview

Esta fase foca em resolver instabilidades na interface do usuário (reload indesejado) e em automatizar a descoberta de categorias no backend VTEX, eliminando a dependência de mapeamentos hardcoded.

## Frontend Bug Analysis

### Page Reload on Submission
- **Localização**: `frontend/src/App.tsx`, especificamente no componente `MonitorPage`.
- **Causa Provável**: Embora `e.preventDefault()` esteja presente, o uso de `alert()` síncrono pode interromper o fluxo de renderização do React em alguns browsers se houver um erro silencioso antes. Além disso, botões no dashboard não têm `type="button"`, o que pode causar submissões acidentais em outras abas.
- **Solução**: 
  - Substituir `alert()` por uma implementação de "Toast" ou feedback embutido no `GlassCard`.
  - Garantir que todos os botões que não são de submit tenham `type="button"`.
  - Adicionar estados de `success` e `error` visíveis no formulário.

## Category Mapping Automation

### Current State
- `services/category_mapping.py` contém uma lista fixa `_RAW_CATEGORIES` para Aramis, Reserva e Tommy.
- Novas marcas exigem edição manual de código ou mapeamento via DynamicBrand (que é complexo para o usuário final).

### Proposed Automation (Intelligence)
1. **Discovery**: Utilizar `VtexApiClient.fetch_categories(domain)` para obter a árvore real da VTEX.
2. **Matching**: Implementar um algoritmo de "Fuzzy Matching" para relacionar categorias encontradas (ex: "Camisas Sociais") com o catálogo canônico (ex: "camisas") automaticamente.
3. **Persistência Dinâmica**: Ao detectar uma nova marca, o sistema deve sugerir ou aplicar o mapeamento sem exigir que o usuário conheça os IDs internos (vtex_fq).

## Engine Abstraction Layer

### Refactoring Strategy
- **BaseEngine**: Introduzir uma classe que orquestra a lógica de "Discovery -> Scrape -> Save" independente do motor.
- **VTEXEngine**: Mover a lógica específica de VTEX (descoberta de conta, catalog system) do `VtexApiClient` para esta engine.
- **Scraper Factory**: Otimizar a fábrica para que ela não apenas instancie o cliente HTTP, mas selecione a estratégia de extração baseada na marca.

## Verification Plan

### Automated Tests
- Criar script de teste para validar o algoritmo de auto-matching de categorias.
- Validar se a `VTEXEngine` consegue resolver a conta de um novo domínio sem configuração prévia.

### Manual Verification
- Testar a submissão do formulário de monitoramento no dashboard e verificar se o reload parou.
- Adicionar uma marca VTEX nova e verificar se o sistema "puxa" as categorias sozinho na aba de Varredura.

---
*Research completed: 2026-05-07*
