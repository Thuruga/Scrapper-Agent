# Requirements: Intelligence Scraper

**Defined:** 2026-06-23
**Milestone:** v3.0 Expansão Multi-Plataforma de Concorrentes & Frete VTEX
**Core Value:** Extração automatizada e resiliente de dados de mercado com mínima intervenção humana e alta fidelidade de dados.

## v3.0 Requirements

Requisitos comprometidos para este milestone. Cada um mapeia para uma phase no ROADMAP.

### Concorrentes — Novas Plataformas

- [ ] **COMP-03**: Operador consegue onboardar e buscar produtos das marcas SFCC **Lacoste** e **HugoBoss** (catálogo + preço) via extração pública browser-rendered (JSON-LD / OpenGraph). _(cumpre COMP-FUT-02)_
- [ ] **COMP-04**: Operador consegue onboardar e buscar produtos da **Richards** (Wake Commerce) via API GraphQL com header `TCS-Access-Token` por loja. _(cumpre COMP-FUT-01; gated por um spike de confirmação do fluxo GraphQL + token antes de construir o engine)_
- [ ] **COMP-05**: Ao cadastrar uma marca SFCC ou Wake, o sistema detecta e rotula o engine correto (`detect_engine` retorna `sfcc` / `wake` em vez de `unknown`), permitindo o cadastro com o engine certo em vez de desativar a marca.

### Frete (Checkout) — carregado do v2.0

- [ ] **FRET-05**: O sistema calcula preço e prazo de frete via checkout para os sites de marca VTEX (que hoje retornam vazio em `calculate_shipping`), com unidade correta (centavos→reais) e detecção de frete grátis.

## Future Requirements

Reconhecidos, porém adiados — não entram no roadmap deste milestone.

### Concorrentes em plataformas não suportadas (precisam de engine novo)

- [ ] **COMP-FUT-03**: Engine para **Zara** (Inditex IOP, proprietário — sem API padrão de catálogo). Sem caminho público validado; exige spike de pesquisa de viabilidade antes de comprometer.

### Perfis de acesso (adiado da reunião 17/06)

- [ ] **PROFILE-FUT-01**: Perfis de acesso por equipe (ARAMIS: Janete/Edna/Heitor; URBAN: Aline/Caio; NEXT: Aline/Caio; MARKETPLACE: Cauan), com login por usuário, papéis e seleção de marcas a acompanhar no 1º acesso. Exige reforma da auth (hoje API key compartilhada). Provável milestone próprio.

### Frete (próximas iterações)

- [ ] **FRET-06**: Calcular frete via checkout para sites de marca Shopify. Adiado por incerteza de viabilidade — o fluxo AJAX Cart (`prepare/async_shipping_rates`) exige cookie de sessão e pode demandar Playwright; validar com um spike antes de comprometer.

### Banners → SharePoint (estudo)

- [ ] **BANNER-FUT-01**: Estudar a viabilidade de identificar imagens/informações dos banners da primeira tela dos sites e migrá-las para o SharePoint. Item de estudo/spike, não feature pronta.

### Carryover de milestones anteriores

- [ ] **EXPORT-HIST-01**: Exportar para Excel a partir de uma busca por SKU salva no histórico.
- [ ] **EXPORT-UNIFY-01**: Levar a seleção de produtos (todos/selecionados) ao export da busca comparativa por marca (`/search/export`).
- [ ] **IDENT-01**: Investigar sinal de identidade de produto além do EAN (EAN invalidado por baixa cobertura).

## Out of Scope

Explicitamente excluído deste milestone, com motivo.

| Feature | Reason |
|---------|--------|
| Frete / checkout / estoque por CEP para marcas SFCC | O caminho SFCC validado por spike é só catálogo+preço via browser público; checkout/frete exigiria OCAPI/SCAPI (credenciais) — fora de escopo. |
| OCAPI / SCAPI (APIs autenticadas SFCC) | Exigem credenciais comerciais não disponíveis; a extração SFCC fica na via pública browser-rendered. |
| Bypass de anti-bot / proxy / stealth / CAPTCHA / WAF | Extração SFCC e Wake permanece na superfície pública; sem evasão de bloqueio. |
| Engine **Zara / Inditex IOP** | Plataforma proprietária sem caminho público validado; permanece deferida (COMP-FUT-03). |
| Reforma de autenticação / perfis de acesso por usuário | Disruptivo (hoje é API key compartilhada); permanece Future (PROFILE-FUT-01). |
| Banners → SharePoint | Estudo de viabilidade, não feature comprometida; permanece Future (BANNER-FUT-01). |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| COMP-05 | Phase 30 | Pending |
| COMP-03 | Phase 31 | Pending |
| COMP-04 | Phase 32 | Pending |
| FRET-05 | Phase 33 | Pending |

**Coverage:**

- v3.0 requirements: 4 total
- Mapped to phases: 4 (COMP-05→30, COMP-03→31, COMP-04→32, FRET-05→33)
- Unmapped: 0 ✓
- Deferred (Future): COMP-FUT-03, PROFILE-FUT-01, FRET-06, BANNER-FUT-01, EXPORT-HIST-01, EXPORT-UNIFY-01, IDENT-01

---
*Requirements defined: 2026-06-23 for milestone v3.0*
*Last updated: 2026-06-23 — Milestone v3.0 roadmapeado; COMP-05→Phase 30, COMP-03→Phase 31, COMP-04→Phase 32 (spike-gated), FRET-05→Phase 33; cobertura 4/4.*
