# Intelligence Scraper - Core Evolution & Reliability

## What This Is

Um sistema robusto de web scraping focado em monitoramento de preços e descoberta de catálogos para marcas de moda. O projeto provê um dashboard para gestão de marcas, mapeamento de categorias multi-plataforma e monitoramento de produtos em tempo real com resiliência anti-bot.

## Core Value

Extração automatizada e resiliente de dados de mercado com mínima intervenção humana e alta fidelidade de dados.

## Current Milestone: v4.0 Paridade de Dados, Cobertura Total de Frete & Inteligência Competitiva

**Goal:** Nivelar a extração de atributos entre todas as marcas, fechar lacunas de cobertura (Hugo Boss por categoria, Zara, frete universal) e adicionar camadas de inteligência competitiva (MAP, promoções, ruptura de estoque, sortimento, avaliações).

**Target features (5 categorias):**

- **A — Paridade de Dados de Marca:** marcas que hoje trazem atributos incompletos (Levi's, Calvin Klein, Zapalla, Austral, Track & Field, Richards, Hugo Boss) devem extrair o mesmo conjunto de atributos das demais; normalização/enriquecimento do schema de produto.
- **B — Cobertura de Marcas:** corrigir varredura e monitoramento por categoria da Hugo Boss; adicionar **Zara**; remover **Lacoste** das buscas.
- **C — UX de Monitoramento & Busca:** responsividade no monitor e na varredura por categoria; lista de monitoramento exibindo valor de promoção; onboarding só-por-URL (scraper detecta a marca); ação "adicionar a monitoramento" em busca comparativa / por SKU / monitor de categoria; toggles ativar/desativar para marketplaces; histórico no canto superior direito (comparativa + SKU); busca por SKU aceitando só o padrão (`ML.05.0326046`) com CEP na mesma linha; auto-trigger do monitor de categoria ao selecionar a categoria.
- **D — Frete (cobertura total):** cálculo de frete para as marcas restantes (não-VTEX + Buckman faltante) e para os marketplaces (Mercado Livre, Netshoes, Amazon); **Matriz de Frete Multi-Regional** com CEPs-chave por região do Brasil.
- **E — Inteligência Competitiva (novas features):** Violação de MAP (preço mínimo permitido + vendedor infrator); condições de pagamento + selos de oferta ("Leve 3 pague 2", "15% OFF no Pix"); ruptura de estoque (% esgotado na varredura + profundidade via requisição de 999 unidades no carrinho); avaliações reforçadas (notas + comentários, todas as marcas); análise de sortimento (cron que contabiliza atributos do catálogo/categoria para identificar buracos).

**Key context:** Carregado do v3.0 como cobertura de frete: VTEX já entrega frete via checkout (FRET-05, Phase 33). Banners desktop (BANNER-01..06) e publicação no SharePoint foram movidos para o backlog (fora do ciclo ativo). Lacoste permanece dormente (anti-bot Akamai por reputação de IP) e sai das buscas neste milestone. Zara/Inditex (COMP-FUT-03) entra no escopo de cobertura de marcas. Auth segue API key compartilhada.

## Requirements

### Active

<!-- REQ-IDs canônicos e escopo detalhado do v4.0 vivem em .planning/REQUIREMENTS.md (definidos após a pesquisa de domínio); o roadmap mapeia cada um a uma phase. As 5 categorias do v4.0 estão resumidas em "Current Milestone" acima. -->

_Requisitos v4.0 a serem definidos em REQUIREMENTS.md após a pesquisa de domínio._

### Validated (v4.0)

- ✓ **UX-01**: Monitor de categoria e varredura por categoria são responsivos em viewports menores (768px), sem overflow horizontal ou sobreposição de elementos. (Phase 38)
- ✓ **UX-02**: Lista de monitoramento exibe o valor da promoção (`last_price_discount`, preço efetivo via D-01) além do preço cheio, sem chamada de rede adicional. (Phase 38)
- ✓ **UX-06**: Histórico de busca acessível por ícone no canto superior direito, com badge type-scoped, em ambas as abas (comparativa e SKU). (Phase 38)
- ✓ **UX-07**: Busca por SKU valida o padrão `ML.05.XXXXXXX` no frontend; CEP inline na mesma linha do SKU. (Phase 38)
- ✓ **UX-08**: Selecionar uma categoria no monitor dispara a primeira varredura automaticamente (reaproveitando o trigger de background já existente) e abre a lista de produtos ao concluir. (Phase 38)
- ✓ **COMP-08**: Lacoste não aparece como opção selecionável em nenhuma superfície de busca; garantido pelo chokepoint `list_brands(active_only=True)` + teste de regressão. (Phase 38)

**Nota:** o code review da Phase 38 (`38-REVIEW.md`) encontrou 1 bug crítico pré-existente fora de escopo (`CR-01`, comparação `available_colors`/`available_sizes` em `price_monitor_service.py` pode lançar `TypeError` em dados mistos/`None`) — registrado como dívida técnica, não bloqueou a phase. Manual UAT (`38-HUMAN-UAT.md`) permanece `partial`/pendente de confirmação humana em browser para UX-01/UX-06/UX-07/UX-08 — todos os checks automatizados (473 testes backend + build frontend) passaram.

### Validated (v3.0)

- ✓ **COMP-04**: Operador onboarda e busca produtos da **Richards** (Wake Commerce) via GraphQL com `TCS-Access-Token` por loja; spike de confirmação retornou GO contra a Richards (5 produtos reais via GraphQL + token auto-extraído), `WakeEngine` plugado na `EngineFactory`. (Phase 32)
- ✓ **COMP-05**: `detect_engine` reconhece e rotula `sfcc` e `wake` (probe Wake `fbitsstatic.net` + probe SFCC `demandware.static`/`edgesuite.net` last-resort), permitindo cadastrar essas marcas com o engine correto. (Phase 30)
- ✓ **FRET-05**: Preço e prazo de frete via checkout nos sites de marca VTEX (frete sob demanda — CEP opcional, cálculo por produto), HUMAN-UAT confirmado pelo operador. (Phase 33)

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

- [ ] **BANNER-01..06** (do v3.0): Extração de banners desktop do hero + publicação idempotente no SharePoint. Movido para backlog ao iniciar o v4.0; SharePoint ainda bloqueado por destino/credenciais/permissões.
- [ ] **COMP-03 / Lacoste (SFCC)**: Engine SFCC corrigida e testada offline; ativação dormente — depende só de egress de IP limpo (anti-bot Akamai por reputação de IP). Lacoste sai das buscas no v4.0; reativar quando houver proxy residencial/móvel.
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
*Last updated: 2026-07-02 — Phase 38 completa (UX de Busca & Monitoramento — Quick Wins): UX-01, UX-02, UX-06, UX-07, UX-08, COMP-08 validados.*
