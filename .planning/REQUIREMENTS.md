# Requirements: Intelligence Scraper

**Defined:** 2026-06-23
**Milestone:** v3.0 Expansão Multi-Plataforma de Concorrentes & Frete VTEX
**Core Value:** Extração automatizada e resiliente de dados de mercado com mínima intervenção humana e alta fidelidade de dados.

## v3.0 Requirements

Requisitos comprometidos para este milestone. Cada um mapeia para uma phase no ROADMAP.

### Concorrentes — Novas Plataformas

- [ ] **COMP-03**: Operador consegue onboardar e buscar produtos das marcas SFCC **Lacoste** e **HugoBoss** (catálogo + preço) via extração pública browser-rendered (JSON-LD / OpenGraph). _(cumpre COMP-FUT-02; status 2026-06-25: Hugo Boss entregue como VTEX, Lacoste segue bloqueada/inativa após Phase 36 NO-GO no envelope público stealth permitido)_
- [x] **COMP-04**: Operador consegue onboardar e buscar produtos da **Richards** (Wake Commerce) via API GraphQL com header `TCS-Access-Token` por loja. _(cumpre COMP-FUT-01; gated por um spike de confirmação do fluxo GraphQL + token antes de construir o engine)_
- [x] **COMP-05**: Ao cadastrar uma marca SFCC ou Wake, o sistema detecta e rotula o engine correto (`detect_engine` retorna `sfcc` / `wake` em vez de `unknown`), permitindo o cadastro com o engine certo em vez de desativar a marca.

### Frete (Checkout) — carregado do v2.0

- [x] **FRET-05**: O sistema calcula preço e prazo de frete via checkout para os sites de marca VTEX (que hoje retornam vazio em `calculate_shipping`), com unidade correta (centavos→reais) e detecção de frete grátis.

### Banners Desktop — Extração

- [x] **BANNER-01**: Operador consegue executar uma coleta desktop (`1366×768`) em todas as marcas ativas cadastradas e obter todos os slides de imagem do carrossel principal da primeira tela.
- [x] **BANNER-02**: Para cada banner extraído, o sistema preserva o arquivo original e registra marca, URL de origem, link de destino, texto alternativo, dimensões, tipo de mídia, data da coleta e hash SHA-256.
- [x] **BANNER-03**: O sistema navega o carrossel para descobrir slides ocultos ou carregados sob demanda e contabiliza slides em vídeo sem classificá-los ou baixá-los como imagens.
- [x] **BANNER-04**: Cada execução gera JSON, CSV, galeria visual e screenshot por site, isolando e reportando a falha de uma marca sem interromper as demais.

### Banners Desktop — SharePoint

- [ ] **BANNER-05**: Operador consegue configurar o destino e as credenciais do SharePoint sem armazenar segredos no código ou nos artefatos gerados.
- [ ] **BANNER-06**: Operador consegue publicar os banners originais e seus metadados no SharePoint, organizados por marca e sem duplicar o mesmo arquivo em reexecuções, com resultado de envio por item.

## Future Requirements

Reconhecidos, porém adiados — não entram no roadmap deste milestone.

### Concorrentes em plataformas não suportadas (precisam de engine novo)

- [ ] **COMP-FUT-03**: Engine para **Zara** (Inditex IOP, proprietário — sem API padrão de catálogo). Phase 36 recheck carregou home/search públicos sem bloqueio; promover para fase futura dedicada para validar extração de produto+preço e só então comprometer engine.

### Perfis de acesso (adiado da reunião 17/06)

- [ ] **PROFILE-FUT-01**: Perfis de acesso por equipe (ARAMIS: Janete/Edna/Heitor; URBAN: Aline/Caio; NEXT: Aline/Caio; MARKETPLACE: Cauan), com login por usuário, papéis e seleção de marcas a acompanhar no 1º acesso. Exige reforma da auth (hoje API key compartilhada). Provável milestone próprio.

### Frete (próximas iterações)

- [ ] **FRET-06**: Calcular frete via checkout para sites de marca Shopify. Adiado por incerteza de viabilidade — o fluxo AJAX Cart (`prepare/async_shipping_rates`) exige cookie de sessão e pode demandar Playwright; validar com um spike antes de comprometer.

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
| Escalada anti-bot / proxy pago / CAPTCHA / WAF | Phase 36 testou apenas o envelope público stealth aprovado; qualquer escalada além disso exige aprovação explícita posterior. |
| Engine **Zara / Inditex IOP** | Plataforma proprietária; Phase 36 viu páginas públicas carregarem, mas produto+preço e engine exigem fase futura dedicada (COMP-FUT-03). |
| Reforma de autenticação / perfis de acesso por usuário | Disruptivo (hoje é API key compartilhada); permanece Future (PROFILE-FUT-01). |
| Banners mobile | O milestone cobre somente viewport desktop; imagens responsivas/mobile exigem coleta e validação próprias. |
| Download de slides em vídeo | Vídeos são contabilizados para completar o carrossel, mas a entrega comprometida é somente de imagens. |
| Agendamento recorrente da coleta | A execução será disparada sob demanda; cadência automática não foi definida. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| COMP-05 | Phase 30 | Complete |
| COMP-03 | Phase 31 + Phase 36 | Partial / blocked for Lacoste (NO-GO) |
| COMP-04 | Phase 32 | Complete |
| FRET-05 | Phase 33 | Complete |
| BANNER-01 | Phase 34 | Complete |
| BANNER-02 | Phase 34 | Complete |
| BANNER-03 | Phase 34 | Complete |
| BANNER-04 | Phase 34 | Complete |
| BANNER-05 | Phase 35 | Pending |
| BANNER-06 | Phase 35 | Pending |

**Coverage:**

- v3.0 requirements: 10 total
- Mapped to phases: 10 (COMP-05→30, COMP-03→31+36, COMP-04→32, FRET-05→33, BANNER-01..04→34, BANNER-05..06→35)
- Unmapped: 0 ✓
- Deferred (Future): COMP-FUT-03 (promover para fase Zara/Inditex dedicada), PROFILE-FUT-01, FRET-06, EXPORT-HIST-01, EXPORT-UNIFY-01, IDENT-01

---
*Requirements defined: 2026-06-23 for milestone v3.0*
*Last updated: 2026-06-25 — Phase 36 concluiu Lacoste NO-GO no envelope público stealth permitido; Zara recheck promove COMP-FUT-03 para fase futura dedicada.*
