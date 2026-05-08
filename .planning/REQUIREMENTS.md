# Requirements: Intelligence Scraper

**Defined:** 2026-05-07
**Core Value:** Extração automatizada e resiliente de dados de mercado com mínima intervenção humana.

## v1 Requirements (Estabilização e Refatoração)

### Frontend Fixes
- [x] **UI-01**: Corrigir reload da página ao submeter o formulário de monitoramento de produto.
- [x] **UI-02**: Garantir que o feedback de "sucesso" ou "erro" seja exibido sem resetar o estado do formulário.

### Automated Intelligence
- [x] **AI-01**: Identificar automaticamente a estrutura de categorias de uma marca VTEX a partir da sua URL ou identificador.
- [x] **AI-02**: Relacionar categorias encontradas com o catálogo interno sem necessidade de mapeamento manual pelo usuário.
- [/] **AI-03**: Fallback resiliente para marcas que não seguem o padrão VTEX padrão.

### Backend Architecture (Extensibilidade)
- [x] **ARCH-01**: Criar interface abstrata `BaseEngine` para suportar diferentes motores de e-commerce (VTEX, Shopify, etc.).
- [x] **ARCH-02**: Implementar `VTEXEngine` herdando da interface abstrata, isolando a lógica específica de VTEX.
- [x] **ARCH-03**: Refatorar `scraper_factory.py` para instanciar engines e scrapers de forma dinâmica e desacoplada.

### Reliability & Logging
- [ ] **LOG-01**: Implementar logs detalhados de falha de extração (ex: mudança de seletor, timeout de proxy).
- [ ] **LOG-02**: Sistema de retry automático para falhas transientes de rede.

## v2 Requirements (Expansão)

### Multi-Engine Support
- **ENG-01**: Adicionar suporte nativo para Shopify.
- **ENG-02**: Adicionar suporte para sites customizados (non-standard).

### Advanced Monitoring
- **MON-01**: Histórico de preços com visualização em gráfico.
- **MON-02**: Alertas de mudança de preço (Webhook/Telegram).

## Out of Scope

| Feature | Reason |
|---------|--------|
| Migração para Banco de Dados SQL | Mantido em JSON para agilidade nesta fase de estabilização. |
| Autenticação de Usuários | O sistema continua sendo de uso único/local nesta fase. |
| Dashboards de BI Complexos | Foco na integridade dos dados, não na visualização analítica avançada. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| UI-01 | Phase 1 | Completed |
| UI-02 | Phase 1 | Completed |
| ARCH-01 | Phase 2 | Completed |
| ARCH-02 | Phase 2 | Completed |
| AI-01 | Phase 1 | Completed |
| AI-02 | Phase 1 | Completed |
| AI-03 | Phase 1 | In Progress |
| ARCH-03 | Phase 2 | Completed |
| LOG-01 | Phase 3 | Pending |
| LOG-02 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-07*
*Last updated: 2026-05-07 after initial definition*
