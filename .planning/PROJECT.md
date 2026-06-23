# Intelligence Scraper - Core Evolution & Reliability

## What This Is

Um sistema robusto de web scraping focado em monitoramento de preços e descoberta de catálogos para marcas de moda. O projeto provê um dashboard para gestão de marcas, mapeamento de categorias multi-plataforma e monitoramento de produtos em tempo real com resiliência anti-bot.

## Core Value

Extração automatizada e resiliente de dados de mercado com mínima intervenção humana e alta fidelidade de dados.

## Current Milestone: v3.0 Expansão Multi-Plataforma de Concorrentes & Frete VTEX

**Goal:** Onboardar marcas concorrentes que rodam fora do VTEX (construindo 2 engines novos — SFCC e Wake Commerce) e entregar o cálculo de frete VTEX que ficou pendente do v2.0.

**Target features:**
- **Engine SFCC (browser público):** onboard de **Lacoste** e **HugoBoss** via extração browser-rendered (JSON-LD/OpenGraph) — catálogo + preço apenas.
- **Engine Wake Commerce:** onboard de **Richards** via API GraphQL (`TCS-Access-Token` por loja), precedido de um spike de confirmação do token.
- **Detecção de engine:** `detect_engine` reconhece e rotula `sfcc` e `wake` (hoje retornam `unknown`), liberando o cadastro com o engine certo.
- **Frete VTEX (carregado do v2.0):** preço + prazo de frete via checkout nos sites de marca VTEX.

**Key context:** O caminho SFCC validado por spike é **público via browser** — sem frete/checkout, estoque por CEP, OCAPI/SCAPI (exige credenciais) ou bypass de anti-bot. **Zara / Inditex IOP** (COMP-FUT-03) permanece deferido (sem caminho público validado). Auth segue API key compartilhada; perfis de acesso e banners→SharePoint seguem adiados.

## Requirements

### Active

<!-- REQ-IDs canônicos e escopo detalhado vivem em .planning/REQUIREMENTS.md; o roadmap mapeia cada um a uma phase. -->

- [ ] **COMP-03**: Operador onboarda e busca produtos das marcas SFCC **Lacoste** e **HugoBoss** (catálogo + preço) via extração pública browser-rendered. (cumpre COMP-FUT-02)
- [ ] **COMP-04**: Operador onboarda e busca produtos da **Richards** (Wake Commerce) via GraphQL com `TCS-Access-Token` por loja. (cumpre COMP-FUT-01; bloqueado por spike de confirmação)
- [ ] **COMP-05**: `detect_engine` reconhece e rotula `sfcc` e `wake`, permitindo cadastrar essas marcas com o engine correto.
- [ ] **FRET-05**: Preço e prazo de frete via checkout nos sites de marca VTEX (carregado do v2.0).

### Validated (v2.0)

- ✓ **COMP-02**: Plataforma não suportada é detectada (`detect_engine` retorna `"unknown"` + probe Wake `fbitsstatic.net`) em vez de cair em VTEX; marca incompatível não entra silenciosamente na busca. (Phase 25)
- ✓ **MGMT-01**: Marca pode ser ativada/desativada via `PATCH /brands/{key}/active`; inativas excluídas de busca/monitoramento/exportação/scheduler pelo chokepoint único `list_brands(active_only=True)`; `GET /brands/` mantém inativas (opt-in). (Phase 25)
- ✓ **MGMT-02**: Campo unificado de gestão de marcas (adicionar / remover / ativar-desativar) na aba "Marcas" — toggle por linha via `PATCH /brands/{key}/active`, distinção visual de inativas, toggle escondido para marketplaces virtuais. (Phase 27)
- ✓ **HIST-01**: Buscas comparativas também são salvas no histórico (`type="search"`, lista interna) e reexibidas sem nova raspagem. (Phase 27)
- ✓ **HIST-02**: Qualquer busca salva (comparativa ou por SKU) reabre a partir do histórico por aba; `preloadedJobId` é dono e propagado por `App.tsx`. (Phase 27)

### Validated (v1.12)

- ✓ **EXPORT-01**: Seleção/desseleção de produtos nos resultados da busca por SKU. (Phase 24)
- ✓ **EXPORT-02**: Marcar/desmarcar todos os produtos de uma vez. (Phase 24)
- ✓ **EXPORT-03**: Diálogo de exportar com "Todos" / "Apenas selecionados". (Phase 24)
- ✓ **EXPORT-04**: Geração de `.xlsx` com as colunas exibidas no card. (Phase 24)
- ✓ **EXPORT-05**: Exportação reflete os resultados exibidos, sem re-raspagem. (Phase 24)
- ✓ **EXPORT-06**: Download com nome significativo (SKU/query + timestamp). (Phase 24)

### Validated (v1.11)

- ✓ **BRAND-01**: Produto sem a marca da query no título é descartado quando a query especifica marca conhecida (independente do visual). (Phase 22)
- ✓ **BRAND-02**: Resgate visual não promove marca ausente/divergente acima da régua. (Phase 22)
- ✓ **BRAND-03**: Gate de marca configurável via config, sem hardcode. (Phase 22)
- ✓ **MODEL-01**: Topo do resultado é o modelo buscado, não um modelo adjacente da mesma marca. (Phase 23)
- ✓ **MODEL-02**: Visual atua como desempate entre candidatos da mesma marca quando o texto é ambíguo. (Phase 23)

### Validated (v1.10)

- ✓ **NLP-01 / NLP-02**: NLP redundante removido do cross_marketplace_service; texto e cores centralizados no nlp_service.
- ✓ **REL-01..04**: Motor de relevância por Decision Gates (árvore condicional substituindo média linear).
- ✓ **VIS-01..03**: Download concorrente + inferência CLIP em batch + cegueira de cor (grayscale).

### Validated (v1.9)

- ✓ Persistência de buscas em segundo plano (evita cancelamento ao iniciar nova busca)
- ✓ Notificação na interface quando a busca finalizar
- ✓ Histórico das pesquisas salvas no sistema
- ✓ Re-exibição rápida dos resultados ao clicar num item do histórico

### Validated (v1.8)

- ✓ Endpoint/Ação no dashboard para iniciar o monitoramento de uma categoria inteira (por URL ou identificador).
- ✓ Job agendado (scheduler) que executa a cada 10 minutos varrendo as categorias monitoradas.
- ✓ Armazenamento e comparação do estado da categoria para alertar/listar atualizações (novos produtos, etc.).

### Validated (v1.7)

- ✓ **FRET-01**: O sistema deve extrair o valor nominal do frete e identificar opções de "Frete Grátis".
- ✓ **FRET-02**: O sistema deve suportar a configuração de um CEP padrão.
- ✓ **FRET-03**: O sistema deve extrair o prazo estimado de entrega.
- ✓ **FRET-04**: O modelo Pydantic atualizado para incluir `shipping_cost` e `shipping_time`.
- ✓ **UI-01**: Os cards de produto exibem o valor do frete e o prazo de entrega.
- ✓ **UI-02**: O dashboard calcula e exibe o "Preço Total" (Preço do Produto + Valor do Frete).
- ✓ **UI-03**: O dashboard permite a ordenação dos resultados pelo "Preço Total".

### Validated (v1.6)

- ✓ **PREC-01**: O sistema deve gerar variantes de busca (sinônimos, abreviações) a partir da query original para ampliar o recall.
- ✓ **PREC-02**: O score NLP deve penalizar ausência de termos essenciais (categoria, marca) mas não rejeitar produtos apenas por palavras extras.
- ✓ **PREC-03**: Títulos extraídos dos marketplaces devem ser normalizados (remover HTML, caracteres especiais, abreviações) antes do scoring.
- ✓ **PREC-04**: Produtos idênticos ou variantes (cor/tamanho) de um mesmo SKU devem ser agrupados na resposta da API.

### Validated (v1.4)

- ✓ **VISUAL-01**: Suporte a GPU (CUDA/MPS) no modelo CLIP
- ✓ **VISUAL-02**: Recorte automático de bordas brancas (Crop to Content)
- ✓ **VISUAL-03**: Cache do embedding da imagem de referência

### Validated (v1.3)

- ✓ **SEARCH-01**: Atualizar a lógica de busca com filtros masculinos.
- ✓ **SEARCH-02**: Implementar filtro pós-extração (fallback).

### Validated (v1.1)

- ✓ **CAT-01**: Todas as requisições de varredura devem aplicar o filtro de categoria masculino/infantil.

### Validated (v1.0)

- ✓ Integração com API de Busca VTEX e Shopify JSON.
- ✓ Motor de Scrapping híbrido (Playwright/curl_cffi/aiohttp).
- ✓ Dashboard React com autenticação JWT.
- ✓ Validação de dados via Pydantic (Quality Gates).
- ✓ Extração via Streaming (AsyncGenerators) para escalabilidade.
- ✓ Mapeamento de categorias multi-marca consolidado.

### Upcoming / Backlog

- [ ] **Incremental Storage**: Migrar para escrita incremental no disco para grandes volumes.
- [ ] **Price Trends**: Visualização avançada de tendências de 30/60/90 dias.
- [ ] **API Rate Limiting**: Proteção contra brute-force e abuso de endpoints.
- [ ] **Cloud Deployment**: Preparação para deploy via Docker/Kubernetes.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Abstração de Scrapers | Permitir suporte plugável a novos motores. | ✓ Implementado |
| Extração em Streaming | Evitar saturação de RAM em jobs massivos. | ✓ Implementado |
| Fallback para Playwright | Garantir coleta mesmo em sites com WAF agressivo. | ✓ Implementado |
| JWT Authentication | Proteger dados sensíveis e gerenciar sessões. | ✓ Implementado |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-23 — Milestone v3.0 iniciado (Expansão Multi-Plataforma: SFCC, Wake & Frete VTEX).*
