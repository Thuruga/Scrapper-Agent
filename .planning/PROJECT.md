# Intelligence Scraper - Core Evolution & Reliability

## What This Is

Um sistema robusto de web scraping focado em monitoramento de preços e descoberta de catálogos para marcas de moda. Atualmente focado no ecossistema VTEX, o projeto provê um dashboard para gestão de marcas, mapeamento de categorias e monitoramento de produtos em tempo real.

## Core Value

Extração automatizada e resiliente de dados de mercado com mínima intervenção humana.

## Requirements

### Validated

- ✓ Integração com API de Busca VTEX — v1.0
- ✓ Motor de Scrapping baseado em Playwright/curl_cffi — v1.0
- ✓ Dashboard React para gestão de marcas — v1.0
- ✓ Persistência baseada em arquivos JSON — v1.0

### Active

- [ ] **Fix Frontend Event Loop**: Corrigir reload indesejado ao submeter formulários de monitoramento.
- [ ] **Intelligent Category Mapping**: Automatizar a descoberta e relacionamento de categorias VTEX sem seleção manual.
- [ ] **Engine Abstraction Layer**: Refatorar o backend para permitir a adição plugável de novos motores (além do VTEX) e novas marcas.
- [ ] **Reliability Boost**: Implementar tratamento de erros mais granulado e logging de recuperação.

### Out of Scope

- Migração para Banco de Dados SQL/NoSQL (nesta fase) — Manteremos JSON para velocidade de entrega.
- Notificações (E-mail/Slack) — Foco total no motor de extração.

## Context

O projeto nasceu como uma ferramenta de extração para marcas específicas da VTEX (Aramis, Reserva, Tommy). Atualmente, o sistema de mapeamento de categorias exige muito esforço manual e o frontend apresenta instabilidades de UX (reset de página). A estrutura atual é muito acoplada à lógica VTEX, dificultando a expansão para outros e-commerces.

## Constraints

- **Tech Stack**: Manter Python/FastAPI e React.
- **Environment**: Otimizado para execução em ambiente Windows (Proactor loop).
- **Anti-Bot**: Deve respeitar delays e rotação de User-Agents definidos em `config.py`.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Abstração de Scrapers | Facilitar a entrada de motores não-VTEX no futuro. | — Pending |
| Mapeamento Automático | Reduzir o churn de configuração de novas marcas. | — Pending |

---
*Last updated: 2026-05-07 after project initialization*
