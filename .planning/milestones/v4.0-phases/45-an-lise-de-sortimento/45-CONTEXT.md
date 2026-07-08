# Phase 45: Análise de Sortimento - Context

**Gathered:** 2026-07-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Entregar um fluxo próprio de análise de sortimento que varre categorias selecionadas em batch/cron, gera snapshots JSON por categoria e expõe uma página dedicada na UI para mostrar a distribuição atual e os deltas entre execuções.

Esta phase não é uma extensão do monitor de preço em tempo real. Ela pode reaproveitar categorias monitoradas como insumo inicial, mas mantém cadastro, snapshots, comparação e superfície de consumo próprios. Também não reabre o escopo da Phase 37 para persistência analítica em SQLite: para esta phase, a fonte de verdade será JSON local.

O cron de sortimento deve ser independente do scheduler atual de 10 minutos do monitor de categoria e nunca pode bloquear buscas ao vivo.

</domain>

<decisions>
## Implementation Decisions

### Persistência analítica
- **D-01:** A fonte de verdade da análise de sortimento será **JSON local**, não SQLite. Esta decisão sobrescreve a redação antiga do roadmap da Phase 45 e segue o veto explícito da Phase 37.
- **D-02:** Cada execução gera **um arquivo por categoria por execução**, em vez de um arquivo único agregando todas as categorias do cron.
- **D-03:** A localização do snapshot anterior usa **nome canônico de arquivo + manifesto/índice leve**, para manter auditabilidade e leitura rápida.
- **D-04:** Cada snapshot guarda **agregados + evidência mínima**. Não persistir a lista completa do catálogo normalizado; manter apenas informação suficiente para explicar os buckets e comparar execuções.

### Fonte das categorias
- **D-05:** O sortimento mantém **lista própria de categorias**, separada da lista de monitoramento de preço.
- **D-06:** Essa lista própria é alimentada por **sincronização automática one-way** a partir de `backend/data/monitored_categories.json`, servindo como ponto de partida para o cadastro do sortimento.
- **D-07:** Categorias sincronizadas entram no cadastro de sortimento **desativadas por padrão**. O operador decide quando cada uma passa a rodar no cron de sortimento.

### Recorte inicial do relatório
- **D-08:** A v1 do sortimento analisa apenas um conjunto enxuto e padronizado de dimensões: **cor, tamanho e composição**.
- **D-09:** Valores ausentes, vazios ou muito sujos devem ser agrupados como **`não informado`**, em vez de serem descartados da contagem.
- **D-10:** As análises e deltas da v1 são calculados **por dimensão separada** (`available_colors`, `available_sizes`, `composition`), e não por combinações cartesianas entre dimensões.

### Superfície de consumo
- **D-11:** A primeira versão já nasce com **tela na UI**, não apenas com endpoint/export backend.
- **D-12:** Essa tela será uma **nova aba/página própria de sortimento**, separada da área de monitoramento de categoria.
- **D-13:** A experiência principal da página será um **dashboard visual com cards e gráficos**, reaproveitando a linguagem visual já existente no frontend.
- **D-14:** O dashboard deve mostrar **ambos**: no topo, os deltas entre snapshots; abaixo, a distribuição atual da categoria pelos atributos selecionados.

### Comparação entre snapshots
- **D-15:** A comparação padrão ao abrir a página será **último snapshot vs snapshot anterior**.
- **D-16:** Quando ainda não existir snapshot anterior, a UI mostra o retrato atual com estado explícito de **`baseline inicial`**, sem tentar fabricar delta.
- **D-17:** Os deltas devem ser exibidos em **valor absoluto + percentual**, não apenas um dos dois.

### the agent's Discretion
- Esquema exato dos arquivos JSON e do manifesto/índice, desde que preserve: um arquivo por categoria por execução, nome canônico e lookup rápido do snapshot anterior.
- Local do código backend que será dono do cadastro de sortimento, da sincronização one-way com o monitor e da geração dos snapshots.
- Nomes finais dos endpoints, tipos TypeScript e modelos de resposta para a página de sortimento.
- Tipos de gráfico, layout visual e composição dos cards do dashboard, desde que a página mantenha o contrato de produto discutido: deltas no topo e distribuição atual abaixo.
- Formato da evidência mínima persistida por bucket, desde que permaneça leve e auditável.
- Frequência exata do cron de sortimento e a presença ou não de gatilho manual complementar, desde que o fluxo continue batch e separado do monitor de 10 minutos.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Escopo e conflitos que precisam ser respeitados
- `.planning/ROADMAP.md` § `Phase 45: Análise de Sortimento` — objetivo original da phase, critérios de sucesso e a redação legada que ainda menciona SQLite.
- `.planning/REQUIREMENTS.md` § `SORT-01` — requisito formal da análise de sortimento; cruzar com a decisão desta discussão de manter JSON como fonte de verdade.
- `.planning/PROJECT.md` — objetivo do milestone v4.0 e a posição da análise de sortimento dentro do eixo de inteligência competitiva.
- `.planning/STATE.md` — contém a decisão acumulada `[v4.0 ARCH/SQLite]` que presume SQLite para dados analíticos; quando houver conflito, seguir este `45-CONTEXT.md`.

### Decisões herdadas de phases anteriores
- `.planning/phases/37-paridade-de-atributos-funda-o-sqlite/37-CONTEXT.md` — contrato canônico de produto, semântica aditiva e veto explícito ao SQLite no projeto.
- `.planning/phases/39-cobertura-de-marcas-hugo-boss-zara/39-CONTEXT.md` — cobertura por categoria da Hugo Boss e importância dos mappings corretos para qualquer leitura confiável de sortimento.
- `.planning/phases/44-ruptura-de-estoque-avalia-es-refor-adas/44-CONTEXT.md` — precedente recente de artefatos JSON por varredura, analytics operacionais desacoplados da busca ao vivo e risco herdado de categoria Hugo Boss.
- `.planning/todos/pending/hugoboss-vtex-io-category-scan.md` — dependência/risk note para confiabilidade de scans Hugo Boss; não é escopo novo da Phase 45, mas impacta a confiança dos snapshots dessa marca.

### Código e pontos de integração
- `backend/core/models.py` — campos canônicos já disponíveis em `RawProductBronze` / `SearchProductResult`, especialmente `category`, `composition`, `available_colors` e `available_sizes`.
- `backend/app.py` — scheduler atual do monitor de categoria (`AsyncIOScheduler` + job a cada 10 min); o cron de sortimento deve nascer como fluxo separado.
- `backend/services/category_monitor_service.py` — padrão atual de varredura por categoria, persistência de artefatos JSON por unidade de trabalho e boundary de execução não-live.
- `backend/services/stock_summary_service.py` — helpers seguros de artefato JSON, convenção de nomes e persistência por scan; forte precedente para a infraestrutura de snapshot do sortimento.
- `backend/api/routes_monitor.py` — CRUD atual de categorias monitoradas, leitura de snapshots por monitor e padrão de rotas locais para analytics de categoria.
- `backend/data/monitored_categories.json` — fonte de entrada para a sincronização one-way do cadastro de sortimento.
- `frontend/src/App.tsx` — shell principal de tabs/páginas e padrões existentes de gráficos/tabelas para a nova superfície de sortimento.
- `frontend/src/api/client.ts` — padrão centralizado de tipagem e chamadas HTTP que deve ser estendido para os endpoints do sortimento.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app.py` já inicializa jobs periódicos com `AsyncIOScheduler`, oferecendo um seam claro para um cron adicional de sortimento separado do monitor atual.
- `backend/services/category_monitor_service.py` já executa scrape bulk por categoria e persiste artefatos JSON por monitor (`monitored_products_{monitor_id}.json`), o que serve como referência direta para o modelo de snapshots do sortimento.
- `backend/services/stock_summary_service.py` já encapsula helpers de persistência JSON, IDs estáveis de produtos de scan e convenções de artefato que podem ser reaproveitadas/adaptadas.
- `backend/core/models.py` já expõe os campos canônicos necessários para a primeira versão analítica (`available_colors`, `available_sizes`, `composition`, `category`) sem exigir expansão do contrato.
- `frontend/src/App.tsx` já contém padrões de dashboard com cards, tabela responsiva e gráficos (`PriceChart`/Recharts), úteis para uma nova página visual de sortimento.
- `frontend/src/api/client.ts` já centraliza tipos e chamadas HTTP para features analíticas recentes, reduzindo o custo de plugar novas rotas.

### Established Patterns
- Features analíticas recentes persistem artefatos locais em JSON em `backend/data`, sem introduzir nova infraestrutura externa.
- Fluxos batch/operacionais são mantidos fora das buscas ao vivo e fora das rotas críticas síncronas.
- Novos campos e artefatos são aditivos; o sistema prefere enriquecer superfícies existentes sem quebrar contratos de busca/export.
- O projeto já usa arquivos por unidade de trabalho + metadados leves ao redor, em vez de um banco analítico pesado.
- O frontend continua concentrado em `App.tsx` + `ApiClient`; a forma mais consistente de entregar a UI de sortimento é estender essa shell, não criar uma aplicação paralela.

### Integration Points
- Novo cadastro de sortimento em arquivo/serviço próprio, com sincronização one-way a partir de `backend/data/monitored_categories.json`.
- Novo cron de sortimento inicializado no backend em paralelo ao job atual, com frequência própria e isolamento do monitor de categoria.
- Nova camada de snapshot/manifests por categoria, reaproveitando o resultado canônico das engines e padrões de persistência JSON já existentes.
- Novas rotas backend + métodos no `ApiClient` para: listar categorias de sortimento, habilitar/desabilitar, consultar snapshots e obter payload consolidado do dashboard.
- Nova aba/página em `frontend/src/App.tsx` para renderizar cards/gráficos de delta e distribuição atual.

</code_context>

<specifics>
## Specific Ideas

- A v1 da página de sortimento deve mostrar, no topo, os deltas do **último snapshot vs anterior**; abaixo, a distribuição atual por **cor**, **tamanho** e **composição**.
- Buckets ausentes entram explicitamente como **`não informado`** para expor buraco de catálogo e/ou de extração.
- O cadastro de sortimento nasce separado do monitor, mas é semeado automaticamente pelas categorias já monitoradas.
- A evidência mínima do snapshot pode usar referências leves como URLs, `scan_product_id`s ou pequenas amostras por bucket; não persistir o catálogo completo.
- Não há exigência de drill-down por combinações `cor+tamanho+composição` na v1; a visão principal é por dimensão separada.

</specifics>

<deferred>
## Deferred Ideas

- Drill-down por combinações de dimensões (`cor + tamanho + composição`) — deixado para evolução futura; a v1 calcula tudo por dimensão separada.
- Comparação arbitrária entre quaisquer dois snapshots do histórico — a v1 abre em `último vs anterior`.
- Primeira entrega backend-only/export-only — rejeitada nesta discussão em favor de página dedicada na UI desde a v1.

### Reviewed Todos (not folded)
- `.planning/todos/pending/hugoboss-vtex-io-category-scan.md` — permanece como dependência/risk note para confiabilidade de scans Hugo Boss; não foi dobrado como feature nova da Phase 45.
- `.planning/todos/pending/audit-category-mappings-all-brands.md` — auditoria ampla de mappings/categorias fica fora do escopo da phase; Phase 45 consome categorias confiáveis, não vira projeto de saneamento global.
- `.planning/todos/pending/zara-comp07-deferred.md` — trata de cobertura/anti-bot da Zara, não de analytics de sortimento.
- `.planning/todos/pending/reforcar-discriminacao-modelo.md` — trata de relevância/discriminação de modelo em busca SKU, fora do domínio desta phase.

</deferred>

---

*Phase: 45-Análise de Sortimento*
*Context gathered: 2026-07-05*
