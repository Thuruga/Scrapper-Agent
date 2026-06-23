# Milestone v1.2 — Project Summary

**Generated:** 2026-06-02
**Purpose:** Team onboarding and project review

---

## 1. Project Overview

Um sistema robusto de web scraping focado em monitoramento de preços e descoberta de catálogos para marcas de moda. O projeto provê um dashboard para gestão de marcas, mapeamento de categorias multi-plataforma e monitoramento de produtos em tempo real com resiliência anti-bot.

**Current Focus:** Melhorar o algoritmo de match criando uma validação de OCR para comparar imagens do site da Aramis com as de outros marketplaces.

*Note: Milestone v1.2 is currently in the planning stage. No phases have been executed yet.*

## 2. Architecture & Technical Decisions

- **Decision:** Abstração de Scrapers
  - **Why:** Permitir suporte plugável a novos motores.
  - **Phase:** v1.0
- **Decision:** Extração em Streaming
  - **Why:** Evitar saturação de RAM em jobs massivos.
  - **Phase:** v1.0
- **Decision:** Fallback para Playwright
  - **Why:** Garantir coleta mesmo em sites com WAF agressivo.
  - **Phase:** v1.0
- **Decision:** JWT Authentication
  - **Why:** Proteger dados sensíveis e gerenciar sessões.
  - **Phase:** v1.0

## 3. Phases Delivered

No phases have been executed yet for this milestone.

*(Previous completed phases from v1.0/v1.1 include: Stabilization & Core Intelligence, Architectural Refactoring, Price History & Monitoring, Expansion Spike, Data Quality Gates, Resilience, Optimization & Security)*

## 4. Requirements Coverage

- ❌ **CAT-01**: Todas as requisições de varredura, pesquisa e mapeamento devem aplicar o filtro de categoria "masculino" ou "infantil masculino". (Pending)
- ❌ **LOG-01**: Implementar logs detalhados de falha de extração. (Pending)
- ❌ **LOG-02**: Sistema de retry automático para falhas transientes de rede. (Pending)
- ❌ **MON-02**: Alertas de mudança de preço (Webhook/Telegram). (Pending)

*(All 6 core requirements from v1.0 were verified as successfully implemented)*

## 5. Key Decisions Log

No new decisions logged for v1.2 yet.

## 6. Tech Debt & Deferred Items

- **Incremental Excel Writing**: Atualmente acumulamos produtos na memória antes de salvar. Recomendado para volumes >50k SKUs.
- **Brute-force Protection**: O endpoint de login não possui rate limit.
- **Job Persistence**: O estado visual do Job é perdido no reload do frontend.

## 7. Getting Started

- **Run the project:** `python -m uvicorn app:app --reload` (backend) and `npm run dev` (frontend)
- **Key directories:** `.planning/` for documentation, `app/` (or equivalent) for backend, `frontend/` for UI.
- **Where to look first:** `BaseEngine` and the scraper implementations for understanding the core engine.

---

## Stats

- **Timeline:** 2026-06-02
- **Phases:** 0 / 0
- **Commits:** 1 (since v1.2 start)
