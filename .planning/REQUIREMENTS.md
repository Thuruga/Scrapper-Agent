# Requirements: Intelligence Scraper

**Defined:** 2026-06-26
**Milestone:** v4.0 Paridade de Dados, Cobertura Total de Frete & Inteligência Competitiva
**Core Value:** Extração automatizada e resiliente de dados de mercado com mínima intervenção humana e alta fidelidade de dados.

## v4.0 Requirements

Requisitos comprometidos para este milestone. Cada um mapeia para uma phase no ROADMAP.

### A — Paridade de Dados de Marca

- [ ] **PARID-01**: Existe um vocabulário canônico único de atributos de produto, compartilhado por todas as marcas/engines (sobre o bag `RawProductBronze.specifications` + campos tipados).
- [ ] **PARID-02**: Cada engine (VTEX/Wake/SFCC/marketplace) popula o conjunto canônico de atributos para as marcas hoje deficientes (Levi's, Calvin Klein, Zapalla, Austral, Track & Field, Richards, Hugo Boss), atingindo paridade com as marcas de referência.
- [ ] **PARID-03**: Nomes de atributos das fontes são normalizados/aliasados para as chaves canônicas (ex.: `Cor2`→`color`, `Corte`/`Fit`→`fit`), de forma aditiva — sem sobrescrever o `specifications` bruto.
- [ ] **PARID-04**: Operador vê um relatório de cobertura de atributos por marca (% de campos canônicos preenchidos), distinguindo "não extraído" de "ausente na fonte".

### B — Cobertura de Marcas

- [x] **COMP-06**: Varredura por categoria e monitoramento por categoria da **Hugo Boss** funcionam (de/para de categorias VTEX, mirando o padrão VALID_SLUGS-from-RAW; sem novo engine).
- [ ] **COMP-07**: Operador onboarda e busca produtos da **Zara** (catálogo + preço). _Gated por um spike de viabilidade GO/NO-GO sobre extração pública de produto+preço (Inditex); se NO-GO, vira backlog sem construir o engine._ (cumpre COMP-FUT-03) — **DEFERIDO ao backlog** (Phase 39 spike 010 = NO-GO, anti-bot; ver `.planning/todos/pending/zara-comp07-deferred.md`). Não entregue; gate cumprido.
- [ ] **COMP-08**: **Lacoste** não aparece como alvo selecionável em nenhuma superfície de busca (comparativa, SKU, categoria, scheduler, export); garantido no chokepoint `list_brands(active_only=True)` + teste de regressão.

### C — UX de Monitoramento & Busca

- [ ] **UX-01**: Monitor de categoria e varredura por categoria são responsivos em viewports menores.
- [ ] **UX-02**: Lista de monitoramento exibe o valor da promoção (`price_discount`) além do preço cheio.
- [ ] **UX-03**: Operador cadastra uma marca colando **apenas a URL**; o sistema detecta marca + engine (`detect_engine` + inferência de nome) e apresenta para confirmação antes de salvar, com override manual disponível.
- [ ] **UX-04**: Operador adiciona um produto ao monitoramento direto da busca comparativa, da busca por SKU e do monitor de categoria; criação idempotente (dedup por url+marca).
- [ ] **UX-05**: Toggles de ativar/desativar disponíveis também para os marketplaces virtuais (Mercado Livre, Netshoes, Amazon), respeitados pelo `cross_marketplace_service`.
- [ ] **UX-06**: Histórico de busca fica no canto superior direito, tanto na busca comparativa quanto na busca por SKU.
- [ ] **UX-07**: Busca por SKU aceita somente o padrão de SKU (ex.: `ML.05.0326046`, validado) e o campo de CEP fica na mesma linha do input do SKU (igual à comparativa).
- [ ] **UX-08**: Selecionar uma categoria no monitor dispara automaticamente a primeira varredura e exibe a lista de produtos, sem trigger manual.

### D — Frete (Cobertura Total)

- [ ] **FRET-07**: O sistema calcula frete para marcas não-VTEX (Wake/Shopify/SFCC) via uma abstração de frete por engine, e fecha o gap de frete do **Buckman** (VTEX). VTEX permanece no `VtexApiClient` (D-03).
- [ ] **FRET-08**: O sistema calcula frete para os marketplaces (Mercado Livre, Netshoes, Amazon).
- [ ] **FRET-09**: **Matriz de Frete Multi-Regional** — o sistema calcula frete para CEPs-chave das 5 regiões do Brasil. _Guard-rails: on-demand/batched (nunca inline na varredura), throttle, cache por (sku, cep), lista de CEPs curada._

### E — Inteligência Competitiva

- [ ] **MAP-01**: Operador define um preço mínimo permitido (MAP) por produto/marca/categoria e o sistema sinaliza produtos anunciados abaixo dele, identificando o vendedor infrator (compara o campo de preço anunciado correto).
- [ ] **PROMO-01**: O sistema extrai selos de oferta e condições de pagamento ("Leve 3 pague 2", "15% OFF no Pix", parcelamento) em um campo estruturado de promoções, preservando o texto bruto quando não parseável.
- [ ] **STOCK-01**: Na varredura por categoria, o sistema registra a porcentagem de produtos esgotados por marca.
- [ ] **STOCK-02**: O sistema captura a profundidade de estoque via requisição de 999 unidades no carrinho, rotulada como "máximo observado/estimativa". _Guard-rails: só em varreduras controladas (nunca em busca), sessões efêmeras isoladas + cleanup, throttle._
- [ ] **REVW-01**: Extração de notas e comentários reforçada para todas as marcas registradas (por provider — Trustvox/VTEX native/etc.), com paginação limitada e dedup.
- [ ] **SORT-01**: Um cron de análise de sortimento varre a categoria/site e contabiliza produtos por atributo canônico (ex.: polos por cor/tecido), gerando snapshots por execução para identificar buracos no catálogo (depende de PARID).

## Future Requirements

Reconhecidos, porém adiados — não entram no roadmap deste milestone.

### Carryover do v3.0

- [ ] **BANNER-05 / BANNER-06**: Configuração e publicação idempotente dos banners no SharePoint. Movido ao backlog ao iniciar o v4.0; ainda bloqueado por destino/credenciais/permissões do SharePoint.
- [ ] **COMP-03 (Lacoste SFCC)**: Engine SFCC corrigida e testada offline; ativação dormente — depende de egress de IP limpo (anti-bot Akamai por reputação de IP). Reabrir quando houver proxy residencial/móvel.
- [ ] **FRET-06**: Frete via checkout para sites de marca Shopify — pode requerer Playwright (AJAX Cart com cookie de sessão); validar com spike. _Nota: pode ser absorvido/antecipado por FRET-07 (abstração inclui Shopify)._

### Perfis de acesso

- [ ] **PROFILE-FUT-01**: Perfis de acesso por equipe com login por usuário e papéis. Exige reforma da auth (hoje API key compartilhada). Provável milestone próprio.

### Outros carryovers

- [ ] **EXPORT-HIST-01**: Exportar para Excel a partir de uma busca por SKU salva no histórico.
- [ ] **EXPORT-UNIFY-01**: Levar a seleção de produtos ao export da busca comparativa por marca.
- [ ] **IDENT-01**: Investigar sinal de identidade de produto além do EAN.

## Out of Scope

Explicitamente excluído deste milestone, com motivo.

| Feature | Reason |
|---------|--------|
| Bypass anti-bot / proxy pago / CAPTCHA para Lacoste | Sem verba de egress de IP limpo; Lacoste segue dormente (COMP-03 Future). |
| Frete/checkout/estoque por CEP para SFCC | Caminho SFCC é só catálogo+preço via browser público. |
| Reforma de autenticação / perfis por usuário | Disruptivo; permanece Future (PROFILE-FUT-01). |
| Publicação no SharePoint (banners) | Bloqueado por credenciais/permissões; movido ao backlog. |
| Servidor de banco externo (Postgres etc.) | SQLite (stdlib) é suficiente para os dados analíticos deste tool single-node. |
| Análise de sortimento em tempo real | SORT-01 é cron/batch; não é tempo real. |
| Profundidade de estoque em busca ao vivo | Cart-probe (STOCK-02) só roda em varreduras controladas, nunca em busca. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PARID-01 | Phase 37 | Pending |
| PARID-02 | Phase 37 | Pending |
| PARID-03 | Phase 37 | Pending |
| PARID-04 | Phase 37 | Pending |
| COMP-08 | Phase 38 | Pending |
| UX-01 | Phase 38 | Pending |
| UX-02 | Phase 38 | Pending |
| UX-06 | Phase 38 | Pending |
| UX-07 | Phase 38 | Pending |
| UX-08 | Phase 38 | Pending |
| COMP-06 | Phase 39 | Complete |
| COMP-07 | Phase 39 | Deferred (NO-GO → backlog) |
| UX-03 | Phase 40 | Pending |
| UX-04 | Phase 40 | Pending |
| UX-05 | Phase 40 | Pending |
| FRET-07 | Phase 41 | Pending |
| FRET-08 | Phase 42 | Pending |
| FRET-09 | Phase 42 | Pending |
| MAP-01 | Phase 43 | Pending |
| PROMO-01 | Phase 43 | Pending |
| STOCK-01 | Phase 44 | Pending |
| STOCK-02 | Phase 44 | Pending |
| REVW-01 | Phase 44 | Pending |
| SORT-01 | Phase 45 | Pending |

**Coverage:**

- v4.0 requirements: 24 total (PARID×4, COMP-06..08, UX-01..08, FRET-07..09, MAP-01, PROMO-01, STOCK-01..02, REVW-01, SORT-01)
- Mapped to phases: 24/24
- Unmapped: 0

---
*Requirements defined: 2026-06-26 for milestone v4.0*
*Last updated: 2026-06-26 — traceability preenchida após criação do ROADMAP (Phases 37-45, cobertura 24/24).*
