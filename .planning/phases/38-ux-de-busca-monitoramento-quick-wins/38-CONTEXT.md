# Phase 38: UX de Busca & Monitoramento — Quick Wins - Context

**Gathered:** 2026-07-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Seis correções pontuais de UX/dados nas telas de busca e monitoramento, sem novas capacidades:

1. **UX-01** — Responsividade do monitor de categoria e da varredura por categoria em viewports menores (768px).
2. **UX-02** — Lista de monitoramento de preços passa a exibir o valor da promoção (`price_discount`) além do preço cheio.
3. **UX-06** — Histórico de busca acessível por ícone no canto superior direito, nas duas abas de busca (comparativa e SKU).
4. **UX-07** — Campo de SKU valida o padrão `ML.05.XXXXXXX` no frontend; CEP fica na mesma linha do SKU, igual à busca comparativa.
5. **UX-08** — Selecionar uma categoria no monitor dispara a primeira varredura automaticamente, sem clique em "iniciar".
6. **COMP-08** — Lacoste não aparece como opção selecionável em nenhuma superfície de busca (garantia de não-regressão sobre o chokepoint já existente).

Um **UI-SPEC.md já aprovado** (`38-UI-SPEC.md`) trava a maior parte das decisões visuais/de copy/layout dos itens 1, 3, 4 e 6. Esta discussão focou nas lacunas que o UI-SPEC deixou explicitamente como "assumption — confirm" ou como decisão de comportamento/dado que o design contract não cobre (cálculo de preço no backend, comportamento pós-varredura automática).

**Fora de escopo:** qualquer capacidade nova (paginação de histórico, filtros adicionais, novas superfícies de busca), engine da Zara/Hugo Boss (Phase 39), onboarding por URL (Phase 40), frete (Phase 41), estoque/reviews (Phase 44).

</domain>

<decisions>
## Implementation Decisions

### Cálculo do preço de promoção no monitor (UX-02)

**Achado de código (não é opinião, é fato confirmado durante a discussão):** hoje `backend/services/price_monitor_service.py:178` grava `current_price = product.price_full` como `last_price` — `price_discount` nunca é lido do produto raspado nem persistido em `PriceMonitorConfig`/`PriceHistoryEntry` (`backend/core/models.py:281-313`). A detecção de mudança (`has_change`, linha 193) só compara `price_full`. Implementar UX-02 corretamente exige mudança de dado/lógica no backend, não só um ajuste visual no frontend.

- **D-01:** A detecção de mudança de preço (histórico + notificação WebSocket `price_update`) passa a usar o **preço efetivo**: `current_price = price_discount if price_discount > 0 else price_full`. Uma promoção que altera só o desconto (preço cheio inalterado) agora deve gerar entrada de histórico e notificação — hoje isso é silenciosamente ignorado.
- **D-02:** Monitores já ativos não têm `price_discount` histórico. É aceitável que o dado só passe a existir a partir da **próxima checagem agendada** de cada monitor — **sem** re-scraping retroativo e **sem** disparar um recheck forçado de todos os monitores ativos ao subir a mudança.
- **D-03:** A mensagem WebSocket `price_update` passa a incluir `price_discount` (e o preço cheio) no payload ao vivo, seguindo o mesmo padrão dos demais campos já transmitidos (`price`, `available`, `available_colors`, `available_sizes`).
- **D-04 (Claude's discretion, não travado pelo usuário):** nomes exatos dos novos campos em `PriceMonitorConfig`/`PriceHistoryEntry` (ex.: `last_price_full`/`last_price_discount` vs. outra convenção) ficam a critério do planner/executor — desde que `last_price` continue representando o preço efetivo (compatibilidade com o frontend atual que já lê `last_price`).

### Comportamento após a 1ª varredura automática (UX-08)

- **D-05:** Ao terminar a primeira varredura automática (disparada pelo `handleSubmit` de `MonitoredCategoriesPage`, `App.tsx:2673-2686`), o **modal de produtos abre automaticamente** — segue a letra literal do requisito UX-08 ("dispara automaticamente a primeira varredura... e os resultados aparecem na lista"/"exibe a lista de produtos"). Isto substitui a opção mais conservadora que o UI-SPEC havia colocado como mínimo aceitável (só atualizar a linha da tabela).
- **D-06:** O modal de cadastro de categoria **fecha imediatamente** após o `Salvar` (sem esperar a varredura terminar); a varredura roda em background. A linha da categoria na tabela mostra o spinner (`<RefreshCw className="animate-spin" size={14} />`, já usado em `App.tsx:2911`) até a varredura concluir — só então o modal de produtos abre sozinho. O operador não fica bloqueado esperando.

### Textos de toast/tooltip (confirmados sem alteração)

O UI-SPEC.md tinha três strings marcadas "(assumption — confirm)". Todas foram confirmadas como estão — nenhuma mudança de copy:

- **D-07:** Tooltip do ícone de histórico (ambas as abas): `title="Ver histórico de buscas"`.
- **D-08:** Toast de sucesso do auto-sweep: "Categoria adicionada. Iniciando primeira varredura…". Toast de falha: "Categoria salva, mas a primeira varredura falhou. Tente novamente na lista."
- **D-09:** Erro inline do SKU inválido: "Formato inválido. Use o padrão ML.05.XXXXXXX (ex: ML.05.0326046)."

### Claude's Discretion

- Nomes exatos dos novos campos de preço no backend (D-04).
- Estrutura interna de como o `handleSubmit` de `MonitoredCategoriesPage` orquestra fechar o modal + disparar sweep + atualizar spinner + abrir modal de produtos ao final (D-05/D-06) — desde que a sequência observável pelo operador seja a descrita.
- Qual endpoint/serviço de "scan agora" já existente é reaproveitado para disparar a primeira varredura (não criar um novo se já existir um usado por `handleViewProducts`/scan manual).
- Todos os detalhes visuais, de layout e de responsividade já travados em `38-UI-SPEC.md` (UX-01, UX-06, UX-07, COMP-08) — não fizeram parte desta discussão porque já estão decididos e aprovados.

### Reviewed Todos (not folded)

- `cap-search-history-list.md` — sobre paginação do histórico; tangencial ao ícone de histórico (UX-06), mas é uma capacidade nova (paginação), não parte do escopo desta phase.
- `audit-category-mappings-all-brands.md` — auditoria de mapeamento de categorias entre marcas; tema de dados/backend de categorização, não de UX de busca/monitoramento.
- `reforcar-discriminacao-modelo.md` — precisão de match de modelo/NLP na busca; já revisado e descartado como fora de escopo na Phase 36.
- `zara-comp07-deferred.md` — engine Zara, sem relação com esta phase.
- `hugoboss-vtex-io-category-scan.md` — bug de scan VTEX-IO da Hugo Boss, sem relação com esta phase.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design contract (já aprovado — trava UX-01, UX-06, UX-07, COMP-08 e todo o copy/visual)
- `.planning/phases/38-ux-de-busca-monitoramento-quick-wins/38-UI-SPEC.md` — contrato visual completo: spacing, tipografia, cor, copywriting e contrato surface-by-surface para os 6 requisitos desta phase. **Ler antes de planejar** — evita redecidir o que já foi aprovado.

### Requisito & Roadmap
- `.planning/ROADMAP.md` seção "Phase 38: UX de Busca & Monitoramento — Quick Wins" — goal, requirements, 6 success criteria.
- `.planning/REQUIREMENTS.md` — UX-01, UX-02, UX-06, UX-07, UX-08, COMP-08 (seção C — UX de Monitoramento & Busca; e seção sobre COMP-08 em Cobertura de Marcas).
- `.planning/STATE.md` — decisão `[D-07/25-02]`: `list_brands` chokepoint (`active_only`) é a fonte única de verdade para filtrar marcas inativas; relevante para a garantia de não-regressão do COMP-08.

### Fase anterior relacionada (Lacoste/COMP-08)
- `.planning/phases/36-onboarding-das-marcas-concorrentes-restantes-lacoste-anti-bo/36-CONTEXT.md` — confirma que o chokepoint `list_brands(active_only=True)` é o único ponto de controle esperado; nenhuma lógica de filtro client-side por nome deve ser adicionada.

### Código a alterar/reusar — backend (UX-02)
- `backend/services/price_monitor_service.py` (linhas ~150-224) — ciclo de checagem do monitor; ponto onde `current_price`/`has_change`/`PriceHistoryEntry`/mensagem WebSocket `price_update` são construídos.
- `backend/core/models.py` (`PriceMonitorConfig` linha 293, `PriceHistoryEntry` linha 281) — modelos a estender com dado de desconto.
- `backend/data/price_monitors.json` — shape atual persistido (confirmado: só tem `last_price`, sem `price_discount`/`price_full` separados).

### Código a alterar/reusar — frontend (UX-02, UX-08)
- `frontend/src/App.tsx:417-434` (`MonitorPage`, `.monitor-pricing`) — onde o valor de promoção deve ser renderizado, reusando o padrão visual de `App.tsx:3009-3018`.
- `frontend/src/App.tsx:2673-2686` (`MonitoredCategoriesPage.handleSubmit`) — ponto de disparo do auto-sweep (D-05/D-06).
- `frontend/src/App.tsx:2911` — spinner `RefreshCw` já usado para "Carregando árvore de categorias...", reusar mesmo padrão na linha da categoria durante o sweep.
- `frontend/src/App.tsx` (`handleViewProducts`, próximo a `getMonitoredCategoryProducts`) — modal de produtos a ser aberto automaticamente ao final do sweep (D-05).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.monitor-price-value` / `.price-original` (strikethrough) — padrão de exibição de preço com promoção já implementado e funcionando em `App.tsx:3009-3018` (produtos de categoria monitorada) e `App.tsx:1658-1671` (resultados de busca); só falta replicar em `MonitorPage` (`App.tsx:417-434`) com o dado correto vindo do backend.
- `<RefreshCw className="animate-spin" size={14} />` — spinner padrão já usado para estados de carregamento assíncrono na tabela de categorias.
- `toast.success(...)` / `toast.error(...)` (sonner) — padrão de feedback assíncrono já usado em toda a aplicação (ex. `App.tsx:1972`, `2079`).
- `.cep-input-error` / `.cep-helper` / `.cep-helper-error` (`App.css:1281-1305`) — padrão de validação inline já implementado no campo de CEP da busca comparativa; reusar tal e qual para o novo erro de SKU (UX-07).

### Established Patterns
- Broadcast de estado do monitor via WebSocket carrega todos os campos relevantes no mesmo payload (`price`, `available`, `available_colors`, `available_sizes`) — D-03 estende esse padrão, não cria um novo.
- Chokepoint único (`list_brands(active_only=True)`) para filtrar marcas inativas — nenhuma superfície nova deve duplicar esse filtro no client.

### Integration Points
- O auto-sweep (UX-08) deve reaproveitar o endpoint/ação de scan manual já existente (o mesmo que `handleViewProducts`/scan-now usa) — não criar um endpoint novo.
- O valor de promoção no `MonitorPage` vem do mesmo payload de `GET /monitors` já buscado — nenhuma chamada de rede nova (conforme ROADMAP success criterion 2).

</code_context>

<specifics>
## Specific Ideas

- Efeito prático de D-01: uma queda de preço causada só por entrada em promoção (sem mudar o preço cheio) passa a contar como "mudança de preço" para fins de histórico e notificação — isso é uma correção de comportamento, não só uma feature de exibição.
- D-05/D-06 juntos descrevem o fluxo completo: clicar Salvar → modal fecha na hora → linha da categoria mostra spinner → varredura roda em background → ao concluir, spinner some e o modal de produtos abre sozinho.

</specifics>

<deferred>
## Deferred Ideas

- Paginação do histórico de buscas (`cap-search-history-list.md`) — capacidade nova, não parte do escopo desta phase.
- Qualquer melhoria de mapeamento de categorias entre marcas, precisão de modelo/NLP, engine Zara ou bug de scan VTEX-IO Hugo Boss — nada disso pertence à Phase 38 (ver Reviewed Todos acima).

</deferred>

---

*Phase: 38-ux-de-busca-monitoramento-quick-wins*
*Context gathered: 2026-07-01*
