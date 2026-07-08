# Phase 44: Ruptura de Estoque & Avaliações Reforçadas - Context

**Gathered:** 2026-06-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Entregar inteligência operacional de estoque e avaliações sobre produtos de categoria/marca:

1. **Ruptura de estoque (STOCK-01):** após uma varredura por categoria, registrar por marca a porcentagem de produtos esgotados, distinguindo explicitamente `em_estoque`, `esgotado` e `não verificado`.
2. **Profundidade de estoque (STOCK-02):** permitir que o operador solicite, sob demanda, a profundidade de estoque de um produto específico de uma varredura controlada via cart-probe de 999 unidades, sempre rotulado como estimativa/máximo observado.
3. **Avaliações reforçadas (REVW-01):** manter `rating` e `review_count` como resumo leve quando disponível, e adicionar comentários estruturados sob demanda por produto, com paginação limitada e dedup.

**Fronteiras travadas:**
- Cart-probe nunca roda em busca ao vivo e nunca roda automaticamente para todos os produtos.
- Cart-probe usa sessões Playwright efêmeras e isoladas, cleanup garantido, throttle e limites conservadores.
- Ruptura não deve fingir precisão: produtos sem sinal de estoque entram como `unknown_stock` e não contaminam o denominador.
- Comentários completos de avaliações não devem ser buscados inline em cada busca normal; o caminho pesado é sob demanda.
- Marcas sem provider conhecido de reviews ficam com estado explícito `unsupported`, sem falhar a busca.
- Hugo Boss é o test bed natural de ruptura por categoria, mas há um todo pendente da Phase 39 para corrigir a estratégia de scan VTEX-IO/GraphQL antes de confiar no monitor de categoria da HB.

</domain>

<decisions>
## Implementation Decisions

### Métrica de ruptura por marca
- **D-01 [denominador verificado]:** `rupture_pct` deve usar apenas produtos com estoque verificado: `out_of_stock / (in_stock + out_of_stock)`. Produtos com `stock_availability is None` entram em `unknown_stock` e não afetam o percentual.
- **D-02 [fonte da verdade]:** Persistir um resumo por execução/varredura, reutilizável por varredura manual e scheduler, com pelo menos: `total_products`, `in_stock_count`, `out_of_stock_count`, `unknown_stock_count`, `verified_stock_count`, `rupture_pct`, `brand`, `scan_id/monitor_id` e timestamp.
- **D-03 [lacuna não é erro]:** Engines/marcas que não conseguem verificar estoque naquela varredura aparecem no relatório com `unknown_stock`; `rupture_pct` fica `null` se não houver nenhum produto verificado. Isso é diferente de falha técnica da varredura.
- **D-04 [produto com variações]:** No nível agregado do produto, `stock_availability=True` se qualquer variação/tamanho tiver estoque. Produto só conta como esgotado quando nenhuma variação disponível for encontrada.

### Operação do cart-probe
- **D-05 [sob demanda por produto]:** O operador dispara profundidade de estoque sob demanda para um produto específico de uma varredura controlada. Não executar probe em massa por padrão.
- **D-06 [persistência no produto do scan]:** O resultado do probe deve ser salvo no registro do produto daquela execução de varredura, com campos aditivos como `stock_depth_estimate`, `stock_depth_state`, `stock_depth_checked_at`, `stock_depth_source` e rótulo de "máximo observado/estimativa via cart-probe".
- **D-07 [limites conservadores]:** Começar com limite conservador: 1 produto por ação, throttle fixo, timeout curto, cleanup sempre, e máximo configurável pequeno por marca/execução. O número exato fica para o planner, mas deve ser baixo por padrão.
- **D-08 [estados explícitos]:** Se o cart-probe não medir profundidade, salvar estado explícito sem inventar quantidade. Estados mínimos: `estimated`, `unavailable`, `unsupported`, `blocked`, `temporary_failure`.
- **D-09 [sem false data]:** `0` só pode significar indisponibilidade/estoque zero quando o provider realmente retornar isso de forma confiável. Falha, bloqueio, unsupported ou timeout nunca viram quantidade zero.

### Comentários de avaliações
- **D-10 [comentários sob demanda]:** Busca normal e varredura devem continuar leves, trazendo `rating` e `review_count` quando disponível. Comentários completos são carregados sob demanda por produto.
- **D-11 [schema compacto]:** Cada comentário retornado/salvo deve ser estruturado e compacto: `review_id`, `rating`, `title`, `text`, `author`, `created_at`, `source_provider`, e `source_ref`/`raw_url` quando existir.
- **D-12 [paginação limitada]:** Paginação de comentários é configurável com default pequeno, provavelmente 1 ou 2 páginas por produto. Dedup obrigatório por `review_id`; se provider não expõe ID estável, derivar hash estável de campos estruturados.
- **D-13 [provider coverage]:** A fase deve auditar/configurar providers conhecidos. Marcas sem caminho identificado ficam com `reviews_state="unsupported"` e não quebram busca/varredura.
- **D-14 [sem payload bruto pesado]:** Não persistir payload bruto completo de reviews por padrão. Payload bruto pode ser log/debug temporário em spike/teste, mas o contrato de produto deve ser o schema compacto.

### Dependências e guardrails
- **D-15 [Hugo Boss dependency]:** O todo `.planning/todos/pending/hugoboss-vtex-io-category-scan.md` deve ser tratado como dependência/risco para usar Hugo Boss como prova de ruptura por categoria. Phase 44 não deve mascarar o problema com `0 produtos`; planner deve resolver ou declarar dependência antes de UAT com Hugo Boss.
- **D-16 [Phase 37 dependency]:** Phase 44 depende do schema canônico/SQLite previsto para Phase 37, mas nenhum `37-CONTEXT.md` existe nesta workspace no momento da captura. Planner deve verificar o estado real da Phase 37 antes de escolher onde persistir summaries e comentários.

### Claude's Discretion
- Nome exato dos campos e modelos internos, desde que preservem as semânticas acima e sejam aditivos.
- Se o summary de ruptura fica em JSON local existente, SQLite introduzido pela Phase 37, ou ambos em migração, dependendo do estado real da Phase 37 no momento do planejamento.
- Valor inicial exato de `max_review_pages`, timeout e throttle, desde que defaults sejam conservadores.
- Nome/forma exata do endpoint sob demanda para stock-depth e comentários.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requisito e roadmap
- `.planning/ROADMAP.md` - Phase 44: "Ruptura de Estoque & Avaliações Reforçadas"; goal, depends on Phase 37/39, success criteria #1-4.
- `.planning/REQUIREMENTS.md` - `STOCK-01`, `STOCK-02`, `REVW-01`, além dos guardrails de STOCK-02 e out-of-scope para profundidade de estoque em busca ao vivo.
- `.planning/PROJECT.md` - milestone v4.0, eixo "Inteligência Competitiva" e fronteiras gerais do sistema.
- `.planning/STATE.md` - decisões acumuladas `[v4.0 STOCK-02/guard-rails]`, Hugo Boss ativa como VTEX, Lacoste dormente/inativa, e arquitetura SQLite prevista para dados analíticos.

### Fases e todos que condicionam esta fase
- `.planning/phases/39-cobertura-de-marcas-hugo-boss-zara/39-CONTEXT.md` - Hugo Boss como VTEX ativa, categoria por mappings dinâmicos, Zara NO-GO se refletido nos artefatos posteriores, e padrão de gate/spike.
- `.planning/todos/pending/hugoboss-vtex-io-category-scan.md` - pendência crítica: monitor de categoria da Hugo Boss retorna 0 produtos no fluxo legado; precisa estratégia VTEX-IO GraphQL/DOM antes de UAT de ruptura com HB.
- `.planning/phases/41-abstracao-de-frete-marcas-nao-vtex/41-CONTEXT.md` - padrão recente de providers, estados explícitos, não representar falha como valor válido, e resolver centralizado por engine.
- `.planning/phases/33-frete-via-checkout-nos-sites-vtex/33-CONTEXT.md` - precedente de chamada controlada a checkout público, estados distintos para falha/indisponibilidade e regra de não transformar falha em `0.0`.
- `.planning/phases/31-engine-sfcc-browser-p-blico-lacoste-hugoboss/31-CONTEXT.md` - limite SFCC público, `calculate_shipping -> None`, anti-bot e cuidado para ausência explícita sem falso sucesso.

### Código a alterar/reusar
- `backend/core/models.py` - `RawProductBronze.stock_availability`, `SearchProductResult.available`, `rating`, `review_count`, `DynamicBrand.review_provider`, `review_store_id`; campos novos devem ser aditivos.
- `backend/services/category_monitor_service.py` - scheduler de categoria, persistência `monitored_products_{monitor_id}.json` e ponto natural para summary de ruptura por scan.
- `backend/api/routes_category.py` - endpoints de varredura manual/multi e possível superfície para retornar summaries.
- `backend/services/vtex_api_scraper.py` - fonte atual de disponibilidade VTEX (`AvailableQuantity > 0`), seleção de SKU/seller e chamadas existentes de reviews em lote.
- `backend/services/review_service.py` - provider atual de resumo Trustvox/VTEX Native; deve evoluir para comentários sob demanda e states.
- `backend/services/engines/sfcc_parser.py`, `backend/services/engines/wake_engine.py`, `backend/services/shopify_api_client.py`, `backend/services/engines/zara_parser.py` - fontes atuais/parciais de `stock_availability` por engine.
- `backend/data/brands.json` - configuração de `review_provider`/`review_store_id`; base para auditoria de coverage.
- `frontend/src/App.tsx` e `frontend/src/api/client.ts` - superfícies de monitor/categoria caso o planner inclua exibição mínima ou ações sob demanda.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RawProductBronze` e `SearchProductResult` já possuem `stock_availability`/`available`, `rating` e `review_count`, então Phase 44 deve evoluir o contrato de forma aditiva.
- `category_monitor_service.run_category_scan` já persiste os produtos de cada monitor em JSON local e atualiza `last_scraped_at`; é o ponto mais direto para anexar `scan_summary` e campos de stock-depth por produto se Phase 37/SQLite ainda não estiver pronto.
- `review_service.py` já roteia por `DynamicBrand.review_provider` e suporta resumo Trustvox e VTEX Native; faltam comentários, paginação, states e dedup.
- `VtexApiClient.search`/`scrape_category_paged` já calculam disponibilidade por `AvailableQuantity > 0` e fazem bulk reviews, um bom molde para manter busca leve.
- Parsers/engines não-VTEX já expõem algum sinal de disponibilidade (`SFCC`, `Wake`, `Shopify`, `Zara`) com maturidade variável; `None` precisa permanecer distinguível de `False`.

### Established Patterns
- Campos novos em Pydantic devem ter defaults seguros e não quebrar históricos/exports antigos.
- Falha por marca/produto não deve derrubar lote; retornar estado explícito por produto/marca.
- Testes unitários devem ser herméticos com sessões/fetchers fake; chamadas reais a checkout/reviews/cart-probe pertencem a spike ou UAT controlado.
- Provider resolver centralizado e estados explícitos evitam espalhar `if engine == ...` pelo sistema.
- Dados sensíveis/operacionais como CEP, payload de checkout e resposta bruta de provider não devem ser logados de forma ampla.

### Integration Points
- Ruptura por marca: `run_category_scan` e endpoints de varredura manual precisam computar summary a partir de `stock_availability`.
- Cart-probe: endpoint/action sob demanda deve receber identidade segura do produto do scan, validar marca/domínio, executar provider controlado, atualizar o registro daquele scan e retornar estado.
- Reviews sob demanda: endpoint/action por produto deve resolver provider por `brand_key`, buscar páginas limitadas, deduplicar e retornar schema compacto com `reviews_state`.
- UI pode inicialmente só expor ações/estado mínimo; a fonte de verdade fica no backend/persistência de scan.

</code_context>

<specifics>
## Specific Ideas

- Summary sugerido por scan:
  - `brand`, `scan_id`/`monitor_id`, `scanned_at`
  - `total_products`, `verified_stock_count`, `in_stock_count`, `out_of_stock_count`, `unknown_stock_count`
  - `rupture_pct` (`null` quando `verified_stock_count == 0`)
- Campos sugeridos por produto com depth:
  - `stock_depth_estimate: Optional[int]`
  - `stock_depth_state: "estimated" | "unavailable" | "unsupported" | "blocked" | "temporary_failure"`
  - `stock_depth_checked_at`
  - `stock_depth_label: "máximo observado/estimativa via cart-probe"`
- Comentário sugerido:
  - `review_id`, `rating`, `title`, `text`, `author`, `created_at`, `source_provider`, `source_ref`
- Configs sugeridas:
  - `MAX_REVIEW_PAGES` default pequeno (1 ou 2)
  - `STOCK_PROBE_THROTTLE_SECONDS`
  - `MAX_STOCK_DEPTH_PROBES_PER_BRAND`
- A fórmula de ruptura deve aparecer em testes com os três casos: `True`, `False`, `None`.

</specifics>

<deferred>
## Deferred Ideas

- UI completa de dashboard/analytics de ruptura, além do necessário para operar/verificar a fase.
- Cart-probe automático para todos os produtos de uma varredura.
- Cart-probe em lote grande por marca.
- Ruptura por SKU/tamanho como métrica principal; Phase 44 consolida no nível produto.
- Persistir payload bruto completo de reviews.
- Heurística genérica agressiva de comentários via HTML/PDP para qualquer marca sem provider identificado.
- Reavaliar Zara/Inditex fora do envelope permitido; segue dependente de outro caminho autorizado.

### Reviewed Todos (not folded)
- `.planning/todos/pending/hugoboss-vtex-io-category-scan.md` - não é dobrado como nova feature de Phase 44; é dependência/risco herdado da Phase 39 para UAT de ruptura com Hugo Boss.
- `.planning/todos/pending/zara-comp07-deferred.md` - Zara segue bloqueada por anti-bot no envelope permitido; não usar como alvo de ruptura/reviews nesta fase.
- `.planning/todos/pending/reforcar-discriminacao-modelo.md` - pertence à precisão de busca por SKU/modelo, não a estoque ou reviews por categoria.
- `.planning/todos/pending/cap-search-history-list.md` - pertence ao histórico de busca/UX, não a Phase 44.

</deferred>

---

*Phase: 44-Ruptura de Estoque & Avaliações Reforçadas*
*Context gathered: 2026-06-29*
