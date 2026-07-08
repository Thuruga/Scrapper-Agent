# Intelligence Scraper - Core Evolution & Reliability

## What This Is

Um sistema robusto de web scraping focado em monitoramento de preços e descoberta de catálogos para marcas de moda. O projeto provê um dashboard para gestão de marcas, mapeamento de categorias multi-plataforma e monitoramento de produtos em tempo real com resiliência anti-bot.

## Core Value

Extração automatizada e resiliente de dados de mercado com mínima intervenção humana e alta fidelidade de dados.

## Current Milestone: none (v4.0 shipped 2026-07-08)

**Status:** v4.0 Paridade de Dados, Cobertura Total de Frete & Inteligência Competitiva concluído — 9 phases (37-45), 32 plans. Todos os 24 requisitos comprometidos foram entregues (incluindo COMP-07/Zara, cujo NO-GO inicial foi revertido a GO em 2026-07-01). Ver `.planning/MILESTONES.md` e `.planning/milestones/v4.0-ROADMAP.md`/`v4.0-REQUIREMENTS.md` para o registro completo. Próximo milestone a definir via `/gsd-new-milestone`.

## Requirements

### Active

Nenhum requisito ativo — aguardando definição do próximo milestone via `/gsd-new-milestone`.

### Validated (v4.0)

- ✓ **PARID-01**: Vocabulário canônico único de atributos de produto, compartilhado por todas as marcas/engines, aditivo sobre o bag `specifications` bruto. (Phase 37)
- ✓ **PARID-02**: Todos os engines (VTEX/Wake/SFCC/marketplace) populam o conjunto canônico de atributos para as marcas antes deficientes (Levi's, Calvin Klein, Zapalla, Austral, Track & Field, Richards, Hugo Boss). (Phase 37)
- ✓ **PARID-03**: Nomes de atributos das fontes normalizados/aliasados para chaves canônicas de forma aditiva (sem sobrescrever o bag bruto). (Phase 37)
- ✓ **PARID-04**: Reinterpretado — o relatório de cobertura por marca foi substituído por paridade de contrato de export (colunas canônicas fixas no Excel comparativo/categoria); nenhum relatório/endpoint novo foi construído (decisão registrada em `37-CONTEXT.md`). (Phase 37)
- ✓ **COMP-06**: Varredura e monitoramento por categoria da **Hugo Boss** funcionam (de/para de categorias VTEX; storefront VTEX-IO exigiu estratégia de scan via DOM-tile). (Phase 39)
- ✓ **COMP-07**: Spike 010 (Phase 39) inicialmente retornou NO-GO (bloqueio anti-bot), mas foi **revertido em 2026-07-01** por reteste ao vivo do operador: `ZaraEngine`/`zara_parser.py` construídos e ativos (`is_active: true`, 7 mappings de categoria), varredura de categoria real confirmada (export `dados_zara_categoria.xlsx`); `proxy_url` segue vazio — mesmo risco de reputação de IP da Lacoste se rodado de datacenter. (Phase 39, revisado)
- ✓ **UX-01**: Monitor de categoria e varredura por categoria são responsivos em viewports menores (768px), sem overflow horizontal ou sobreposição de elementos. (Phase 38)
- ✓ **UX-02**: Lista de monitoramento exibe o valor da promoção (`last_price_discount`, preço efetivo via D-01) além do preço cheio, sem chamada de rede adicional. (Phase 38)
- ✓ **UX-03**: Operador cadastra/monitora uma marca colando apenas a URL do produto — `POST /brands/identify` detecta marca+engine com fallback manual; fluxo reworkado para "identify-first" dentro do Monitor (rework re-verificado ao vivo pelo operador no fechamento do v4.0). (Phase 40)
- ✓ **UX-04**: Adição de produto ao monitoramento direto da busca comparativa, busca por SKU e monitor de categoria, com dedup idempotente por url+marca. (Phase 40)
- ✓ **UX-05**: Toggles de ativar/desativar para marketplaces virtuais (Mercado Livre, Netshoes, Amazon), respeitados pelo `cross_marketplace_service`. (Phase 40)
- ✓ **UX-06**: Histórico de busca acessível por ícone no canto superior direito, com badge type-scoped, em ambas as abas (comparativa e SKU). (Phase 38)
- ✓ **UX-07**: Busca por SKU valida o padrão `ML.05.XXXXXXX` no frontend; CEP inline na mesma linha do SKU. (Phase 38)
- ✓ **UX-08**: Selecionar uma categoria no monitor dispara a primeira varredura automaticamente (reaproveitando o trigger de background já existente) e abre a lista de produtos ao concluir. (Phase 38)
- ✓ **COMP-08**: Lacoste não aparece como opção selecionável em nenhuma superfície de busca; garantido pelo chokepoint `list_brands(active_only=True)` + teste de regressão. (Phase 38)
- ✓ **FRET-07**: Frete não-VTEX entregue por abstração `BaseShipping` com providers Shopify/Buckman e Wake/Richards, endpoint sob demanda para marcas não-VTEX, busca inline com CEP, estados unsupported/temporary sem falso grátis, e VTEX preservado no `VtexApiClient`. (Phase 41)
- ✓ **FRET-08**: Frete calculado sob demanda para os três marketplaces (Mercado Livre, Netshoes, Amazon) via providers `BaseShipping` dedicados; Netshoes retorna estado `blocked` explícito (nunca frete falso), Amazon retorna `temporary_failure` em bloqueio real; prazo de entrega extraído quando a API expõe o campo; validado ao vivo contra os três marketplaces reais. (Phase 42)
- ✓ **FRET-09**: Matriz de Frete Multi-Regional sob demanda para os 5 CEPs-chave (`cep_matrix.json`), com throttle, cache TTL por `(produto, CEP)` (cache hit confirmado ao vivo: ~21s frio vs ~1s em cache) e guard testado contra execução inline em varredura/busca ao vivo. (Phase 42)
- ✓ **MAP-01**: Preço mínimo permitido (MAP) por produto/marca/categoria com sinalização de produtos abaixo do MAP e identificação do vendedor infrator. (Phase 43)
- ✓ **PROMO-01**: Extração estruturada de selos de oferta e condições de pagamento ("Leve 3 pague 2", "15% OFF no Pix"), com texto bruto preservado quando não parseável. (Phase 43)
- ✓ **STOCK-01**: Percentual de produtos esgotados por marca registrado na varredura por categoria. (Phase 44)
- ✓ **STOCK-02**: Profundidade de estoque via cart-probe de 999 unidades, rotulada como estimativa; sessões Playwright efêmeras isoladas, throttle, só em varreduras controladas (nunca em busca ao vivo). (Phase 44)
- ✓ **REVW-01**: Avaliações reforçadas (notas + comentários) por provider (Trustvox/VTEX native), com paginação limitada e dedup. (Phase 44)
- ✓ **SORT-01**: Cron de análise de sortimento conta produtos por atributo canônico por categoria, gerando snapshots JSON comparáveis entre execuções, com dashboard dedicado. (Phase 45)

**Nota:** o code review da Phase 38 (`38-REVIEW.md`) encontrou 1 bug crítico pré-existente fora de escopo (`CR-01`, comparação `available_colors`/`available_sizes` em `price_monitor_service.py` pode lançar `TypeError` em dados mistos/`None`) — registrado como dívida técnica, não bloqueou a phase. Manual UAT (`38-HUMAN-UAT.md`) permanece `partial`/pendente de confirmação humana em browser para UX-01/UX-06/UX-07/UX-08 — todos os checks automatizados (473 testes backend + build frontend) passaram.

**Nota:** o code review da Phase 42 (`42-REVIEW.md`) encontrou 1 bug crítico pré-existente fora de escopo (`CR-01`, `MercadoLivreEngine._fetch_shipping_options` reporta o preço mais alto — não o mais barato — quando nenhuma opção é gratuita; decisão anterior documentada em comentário no código desde 2026-06-23, não introduzida por esta phase) — registrado como dívida técnica, não bloqueou a phase. Dois achados adicionais foram corrigidos dentro da própria phase: escrita não-atômica do cache da matriz (`CR-02`, commit `98cc9c7`) e um gap real de goal-backward verification em que itens Amazon na busca cruzada automática eram rotulados incorretamente como "Bloqueado (anti-bot)" quando na verdade o Tier-2 apenas não está implementado (commit `2311c7c`, achado + corrigido + re-verificado nesta mesma execução). Manual UAT (`42-HUMAN-UAT.md`) permanece `partial`/pendente de confirmação visual humana em browser do botão/modal "Matriz Regional" — todos os checks automatizados (513 testes backend + build frontend) e a verificação ao vivo contra Mercado Livre/Amazon/Netshoes reais (incluindo a matriz regional e o cache) passaram; o operador aprovou avançar sem o passo visual pendente.

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

- [ ] **BANNER-05 / BANNER-06** (do v3.0): Publicação idempotente dos banners desktop no SharePoint (extração/BANNER-01..04 já entregue na Phase 34/v3.0). Ainda bloqueado por destino/credenciais/permissões do SharePoint.
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
| Abstração de Frete por Engine | Permitir frete real em Shopify/Wake sem mover VTEX para o novo resolver. | ✓ Implementado na Phase 41 |
| Vocabulário canônico aditivo (PARID) | Nivelar atributos entre marcas sem quebrar o bag `specifications` bruto nem consumidores existentes. | ✓ Implementado na Phase 37 |
| SQLite (stdlib) para dados analíticos | Suficiente para volumes single-node (sortimento/estoque/reviews); JSON permanece só para config. | ✓ Implementado na Phase 37, consumido na Phase 45 |
| Cart-probe de 999 unidades com sessões efêmeras | Capturar profundidade de estoque sem contaminar buscas ao vivo nem deixar sessões presas. | ✓ Implementado na Phase 44, guard-railed |
| Matriz de Frete Multi-Regional on-demand (nunca inline) | Evitar custo/latência de calcular 5 CEPs a cada busca; throttle + cache por (sku, cep). | ✓ Implementado na Phase 42 |
| Onboarding "identify-first" reworked no Monitor (UX-03) | Feedback do operador: fluxo original (form separado) foi substituído por identificar-e-monitorar direto no card de "Monitorar Novo Produto". | ✓ Implementado na Phase 40, re-verificado ao vivo no fechamento do v4.0 |
| Zara (COMP-07): spike-gated GO/NO-GO antes do engine | NO-GO inicial (anti-bot, ambiente de teste) foi revertido a GO por reteste ao vivo do operador — engine só foi commitado após confirmação real. | ✓ GO revertido 2026-07-01; engine ativo |

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
*Last updated: 2026-07-08 — Milestone v4.0 concluído e arquivado (9 phases, 32 plans, 24/24 requisitos). Todos os requisitos Active movidos para Validated (v4.0); COMP-07/Zara corrigido de "deferido" para entregue (NO-GO revertido a GO em 2026-07-01); Key Decisions atualizado com as decisões arquiteturais do milestone. Aguardando definição do v5.0 via `/gsd-new-milestone`.*
