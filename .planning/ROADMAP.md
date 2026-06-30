# Roadmap: Intelligence Scraper

## Milestones

- ✅ **v1.10 Refatoração do Motor de Relevância & Performance da IA** - Phases 19-21 (shipped)
- ✅ **v1.11 Precisão da Busca por SKU** - Phases 22-23 (shipped)
- ✅ **v1.12 Exportação Excel da Busca por SKU** - Phase 24 (shipped)
- ✅ **v2.0 Cobertura de Concorrentes & Confiabilidade** - Phases 25-29 (shipped — ver `.planning/milestones/v2.0-ROADMAP.md`)
- ✅ **v3.0 Expansão Multi-Plataforma de Concorrentes & Frete VTEX** - Phases 30-36 (shipped)
- 🚧 **v4.0 Paridade de Dados, Cobertura Total de Frete & Inteligência Competitiva** - Phases 37-45 (active)

**Milestone Goal (v4.0):** Nivelar a extração de atributos entre todas as marcas, fechar lacunas de cobertura (Hugo Boss por categoria, Zara, frete universal) e adicionar camadas de inteligência competitiva (MAP, promoções, ruptura de estoque, sortimento, avaliações).

## Overview

Com o motor multi-engine, frete VTEX e os engines Wake/SFCC entregues no v3.0, o v4.0 eleva a qualidade dos dados e expande a cobertura competitiva. A pedra fundamental é a **paridade de atributos** (Phase 37): criar um vocabulário canônico único e garantir que todos os engines o preencham para as marcas hoje deficientes — sem isso, o cron de sortimento (Phase 45) não tem atributos confiáveis para contar. Em paralelo lógico, um lote de **quick wins de UX** e **remoção da Lacoste** das buscas (Phase 38) entrega valor imediato sem dependências pesadas. A Phase 39 fecha a **cobertura de marcas** (Hugo Boss por categoria + Zara, spike-gated). A Phase 40 entrega os fluxos UX mais profundos (onboarding por URL + adicionar ao monitoramento + toggles de marketplace). O eixo de **frete** avança em duas etapas: abstração + marcas não-VTEX (Phase 41), depois marketplaces e a matriz multi-regional CEP (Phase 42, com guard-rails anti-bot). O eixo de **inteligência competitiva** é dividido em MAP+promoções (Phase 43) e ruptura de estoque+avaliações reforçadas (Phase 44 — cart-probe com sessões efêmeras). Por último, o **cron de sortimento** (Phase 45) que depende dos atributos canônicos e da persistência SQLite introduzida na Phase 37.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Phases 19-36 pertencem a milestones CONCLUÍDOS (v1.10-v3.0). As phases ativas do v4.0 são **37-45**.

- [ ] **Phase 37: Paridade de Atributos & Fundação SQLite** - Vocabulário canônico único, normalização/aliasing de atributos em todos os engines, relatório de cobertura por marca e introdução do SQLite para dados analíticos (PARID-01, PARID-02, PARID-03, PARID-04)
- [ ] **Phase 38: UX de Busca & Monitoramento — Quick Wins** - Responsividade do monitor/varredura, promoção na lista de monitoramento, histórico no canto superior direito, padrão de SKU + CEP inline, auto-trigger do monitor de categoria e remoção da Lacoste de todas as superfícies de busca (UX-01, UX-02, UX-06, UX-07, UX-08, COMP-08)
- [x] **Phase 39: Cobertura de Marcas — Hugo Boss & Zara** - Varredura e monitoramento por categoria da Hugo Boss funcionando; spike-gated onboarding da Zara (GO/NO-GO antes do engine) (COMP-06, COMP-07) (completed 2026-06-30)
- [x] **Phase 40: Onboarding por URL & Workflows de Adição ao Monitoramento** - Cadastro de marca só pela URL, detecção automática de engine + nome, botão "adicionar ao monitoramento" nas três superfícies de busca e toggles de ativar/desativar para marketplaces virtuais (UX-03, UX-04, UX-05) (completed 2026-06-30)
- [ ] **Phase 41: Abstração de Frete & Marcas Não-VTEX** - Camada de abstração de frete por engine (BaseShipping + implementações Wake/Shopify), fechamento do gap de frete do Buckman (VTEX) e VTEX permanece no VtexApiClient (FRET-07)
- [ ] **Phase 42: Frete para Marketplaces & Matriz Multi-Regional** - Cálculo de frete para Mercado Livre, Netshoes e Amazon; Matriz de Frete Multi-Regional com CEPs-chave das 5 regiões do Brasil, on-demand com throttle e cache (FRET-08, FRET-09)
- [ ] **Phase 43: Violação de MAP & Selos de Promoção** - Regras de preço mínimo (MAP) por produto/marca/categoria com sinalização de vendedores infratores; extração estruturada de selos de oferta e condições de pagamento (MAP-01, PROMO-01)
- [ ] **Phase 44: Ruptura de Estoque & Avaliações Reforçadas** - Percentual de produtos esgotados por marca na varredura; profundidade de estoque via cart-probe de 999 unidades (sessões efêmeras + throttle); notas e comentários reforçados para todas as marcas com paginação e dedup (STOCK-01, STOCK-02, REVW-01)
- [ ] **Phase 45: Análise de Sortimento** - Cron que varre categorias e contabiliza produtos por atributo canônico, gerando snapshots para identificar buracos no catálogo; depende dos atributos canônicos (PARID) e da persistência SQLite (SORT-01)

## Phase Details

### Phase 37: Paridade de Atributos & Fundação SQLite

**Goal**: Todo produto retornado pelo sistema carrega o mesmo conjunto de atributos canônicos (cor, fit, tecido, tamanho, composição, gênero) independentemente da marca ou engine — e o operador consegue ver, por marca, qual porcentagem dos campos canônicos está sendo preenchida versus ausente na fonte.
**Depends on**: Nothing (fase fundacional do v4.0; opera sobre engines e parsers existentes)
**Requirements**: PARID-01, PARID-02, PARID-03, PARID-04
**Success Criteria** (what must be TRUE):

  1. Existe um vocabulário canônico de atributos documentado e centralizado (`attribute_normalizer.py`) que todos os engines chamam antes de popular `RawProductBronze.specifications`.
  2. Para marcas hoje deficientes (Levi's, Calvin Klein, Zapalla, Austral, Track & Field, Richards, Hugo Boss), os campos canônicos (ex.: `color`, `fit`, `material`) aparecem preenchidos nos resultados de busca quando a fonte os contém — sem sobrescrever o `specifications` bruto original.
  3. Nomes de atributos divergentes entre engines (ex.: `Cor2`, `Corte`, `Composição do produto`) são normalizados/aliasados para as chaves canônicas de forma aditiva, verificável por teste unitário por alias.
  4. O operador acessa um relatório de cobertura de atributos (endpoint ou log estruturado) que distingue "campo canônico não extraído" de "campo ausente na fonte" para cada marca.
  5. Dados analíticos e de série temporal (snapshots de atributos, contagens futuras de sortimento) são persistidos em SQLite (`backend/data/analytics.db`) — configuração inicial e schema validados; JSON permanece para config.

**Plans**: 5 plans
Plans:

- [x] 44-01-PLAN.md - Shared Phase 44 contracts, config, and rupture summary helper
- [x] 44-02-PLAN.md - Scheduled and manual category scan rupture summary wiring
- [x] 44-03-PLAN.md - Explicit monitor-product stock-depth cart-probe action
- [ ] 44-04-PLAN.md - On-demand compact review comments and provider states
- [ ] 44-05-PLAN.md - Monitor modal stock/review operator actions

**UI hint**: yes

### Phase 38: UX de Busca & Monitoramento — Quick Wins

**Goal**: As telas de monitor de categoria e varredura funcionam corretamente em viewports menores; a lista de monitoramento exibe o valor da promoção; o histórico de buscas fica acessível no canto superior direito em todas as abas; o campo de SKU valida o padrão e o CEP fica inline; o monitor de categoria inicia a varredura automaticamente ao selecionar uma categoria; e a Lacoste deixa de aparecer em qualquer superfície de busca.
**Depends on**: Nothing (mudanças de frontend e chokepoint de marcas; independente das fases de atributos e cobertura)
**Requirements**: UX-01, UX-02, UX-06, UX-07, UX-08, COMP-08
**Success Criteria** (what must be TRUE):

  1. Em viewport de 768px (tablet), o monitor de categoria e a varredura por categoria exibem todo o conteúdo sem overflow horizontal ou elementos sobrepostos.
  2. Na lista de monitoramento de preços, cada produto exibe o valor da promoção (`price_discount`) quando disponível, além do preço cheio — sem nova chamada de rede.
  3. O histórico de buscas (comparativa e por SKU) está acessível por um ícone/botão no canto superior direito em ambas as abas de busca.
  4. Na busca por SKU, o campo aceita somente strings no padrão `ML.05.XXXXXXX` (validado no frontend) e o campo de CEP fica na mesma linha do input do SKU, igual ao layout da busca comparativa.
  5. Ao selecionar uma categoria no monitor de categoria, a primeira varredura dispara automaticamente sem necessidade de clique em "iniciar" — e os resultados aparecem na lista.
  6. A Lacoste não aparece como opção selecionável em nenhuma superfície (busca comparativa, busca por SKU, varredura por categoria, scheduler, export) — garantido pelo chokepoint `list_brands(active_only=True)` e coberto por teste de regressão.

**Plans**: TBD
**UI hint**: yes

### Phase 39: Cobertura de Marcas — Hugo Boss & Zara

**Goal**: A varredura e o monitoramento por categoria da Hugo Boss funcionam end-to-end (de/para de categorias VTEX mapeadas), e a viabilidade de extração pública da Zara é verificada por um spike GO/NO-GO — com o engine Zara construído apenas em GO, ou o requisito deferrido com evidência em NO-GO.
**Depends on**: Phase 37 (atributos canônicos disponíveis para testar paridade nas novas categorias da Hugo Boss)
**Requirements**: COMP-06, COMP-07
**Success Criteria** (what must be TRUE):

  1. O operador consegue selecionar uma categoria da Hugo Boss no monitor de categoria e a varredura retorna produtos reais (título + URL + preço) com o mesmo schema canônico das demais marcas VTEX.
  2. O scheduler de 10 minutos inclui a Hugo Boss nas categorias monitoradas e detecta novos produtos corretamente — sem falso positivo de "produto novo" em re-execuções de categoria inalterada.
  3. Para a Zara: um spike documentado (GO/NO-GO) valida se produto + preço são extraíveis publicamente antes de qualquer código de engine; resultado registrado em `spikes/010-zara-product-price/REPORT.md`.
  4. Em GO da Zara: operador onboarda a Zara e a busca retorna produtos reais (título + URL + preço); em NO-GO: COMP-07 é formalmente deferido para backlog com evidência e nenhum engine incompleto é commitado.

**Plans**: TBD

### Phase 40: Onboarding por URL & Workflows de Adição ao Monitoramento

**Goal**: Um operador cadastra uma nova marca colando apenas a URL — o sistema detecta o engine e infere o nome para confirmação — e consegue adicionar qualquer produto ao monitoramento diretamente das telas de busca comparativa, busca por SKU e monitor de categoria; os marketplaces virtuais têm toggles de ativar/desativar respeitados pelo serviço de busca cruzada.
**Depends on**: Phase 38 (UX base estável antes de adicionar novos fluxos de interação)
**Requirements**: UX-03, UX-04, UX-05
**Success Criteria** (what must be TRUE):

  1. Ao colar uma URL de marca no campo de onboarding, o sistema chama `POST /brands/identify`, detecta o engine via `detect_engine` e infere o nome da marca (domínio / título / JSON-LD) — apresentando um formulário pré-preenchido para confirmação antes de salvar, com campo de override manual disponível.
  2. Da busca comparativa, da busca por SKU e do monitor de categoria, o operador consegue clicar em "Adicionar ao monitoramento" em qualquer produto — e o produto é adicionado ao monitor de preços sem duplicata (dedup por url + marca), independentemente da superfície de origem.
  3. Os marketplaces virtuais (Mercado Livre, Netshoes, Amazon) têm toggles de ativar/desativar visíveis na tela de configurações; desativá-los faz o `cross_marketplace_service` excluir o marketplace das buscas imediatamente na próxima execução.

**Plans**: 5 (3/5 complete)
**UI hint**: yes

### Phase 41: Abstração de Frete & Marcas Não-VTEX

**Goal**: O sistema calcula frete para marcas que não usam VTEX (Wake Commerce, Shopify) por meio de uma abstração de frete por engine — e fecha o gap de frete do Buckman (VTEX) — sem quebrar o caminho existente do VTEX no `VtexApiClient`.
**Depends on**: Phase 37 (schema canônico estável para campos de frete), Phase 40 (onboarding de marcas estável)
**Requirements**: FRET-07
**Success Criteria** (what must be TRUE):

  1. Existe uma abstração `BaseShipping` com implementações por engine (`WakeShipping`, `ShopifyShipping`) em `services/shipping/`; o resolver seleciona a implementação pelo engine da marca sem lógica espalhada nos callers.
  2. Uma busca por produto na Richards (Wake) retorna `shipping_cost` e `shipping_time` preenchidos quando o CEP padrão está configurado — campos que hoje ficam nulos para marcas não-VTEX.
  3. O frete do Buckman (VTEX) está calculado e exibido na busca por SKU, fechando o gap identificado no v3.0.
  4. O caminho de frete VTEX existente (`VtexApiClient`) permanece inalterado e continua funcionando para todas as marcas VTEX — garantido por testes de regressão.

**Plans**: TBD

### Phase 42: Frete para Marketplaces & Matriz Multi-Regional

**Goal**: O sistema calcula frete para os três marketplaces (Mercado Livre, Netshoes, Amazon) e permite ao operador solicitar a Matriz de Frete Multi-Regional — frete para CEPs-chave das 5 regiões do Brasil — de forma on-demand, com throttle e cache por (SKU, CEP), sem nunca executar inline durante buscas ao vivo.
**Depends on**: Phase 41 (abstração de frete estável antes de adicionar novos providers)
**Requirements**: FRET-08, FRET-09
**Success Criteria** (what must be TRUE):

  1. Uma busca cruzada nos marketplaces (Mercado Livre, Netshoes, Amazon) retorna `shipping_cost` e `shipping_time` preenchidos quando o CEP padrão está configurado — cobrindo os três marketplaces.
  2. O operador consegue solicitar a Matriz de Frete Multi-Regional para um produto e receber o custo/prazo para CEPs-chave de todas as 5 regiões do Brasil (Sul, Sudeste, Centro-Oeste, Nordeste, Norte).
  3. A matriz de frete usa uma lista curada de CEPs configuráveis (`backend/data/cep_matrix.json`), aplica throttle entre requisições e armazena cache por `(sku, cep)` — a segunda solicitação para o mesmo par é servida do cache sem nova requisição.
  4. O cálculo da matriz nunca é executado inline durante uma varredura ou busca ao vivo — apenas on-demand ou em batch controlado — garantido por guard na chamada e coberto por teste.

**Plans**: TBD

### Phase 43: Violação de MAP & Selos de Promoção

**Goal**: O operador define preços mínimos permitidos (MAP) por produto, marca ou categoria e o sistema sinaliza produtos anunciados abaixo do MAP identificando o vendedor infrator; os produtos retornam selos de oferta e condições de pagamento em um campo estruturado de promoções.
**Depends on**: Phase 37 (atributos canônicos e schema de produto estáveis), Phase 41 (frete calculado para contexto de preço total)
**Requirements**: MAP-01, PROMO-01
**Success Criteria** (what must be TRUE):

  1. O operador define uma regra MAP (preço mínimo) para um produto ou categoria via UI ou endpoint — persistida em `backend/data/map_rules.json` — e nos resultados de busca produtos abaixo do MAP são sinalizados com badge de violação e nome do vendedor infrator.
  2. A comparação de violação usa o campo de preço anunciado correto (preço de venda, não preço cheio/riscado) — evitando falsos positivos com preços promocionais legítimos.
  3. Produtos de marcas que expõem selos de oferta ("Leve 3 pague 2", "15% OFF no Pix", parcelamento) retornam o campo `promotions` estruturado (lista com tipo + valor + texto bruto) — com o texto bruto preservado quando não parseável.
  4. O campo `promotions` é aditivo ao schema existente — produtos sem selos retornam lista vazia, sem quebrar engines que não suportam extração de promoções.

**Plans**: TBD

### Phase 44: Ruptura de Estoque & Avaliações Reforçadas

**Goal**: A varredura por categoria registra a porcentagem de produtos esgotados por marca; a profundidade de estoque é capturável via cart-probe de 999 unidades em varreduras controladas com sessões efêmeras e throttle; notas e comentários são extraídos para todas as marcas com paginação limitada e dedup.
**Depends on**: Phase 37 (schema canônico para campos de estoque), Phase 39 (Hugo Boss por categoria funcional para testar ruptura)
**Requirements**: STOCK-01, STOCK-02, REVW-01
**Success Criteria** (what must be TRUE):

  1. Após uma varredura por categoria, o relatório por marca inclui a porcentagem de produtos com `in_stock=False` — distinguindo "esgotado" de "não verificado" — para cada marca varrida.
  2. O operador consegue solicitar a profundidade de estoque de um produto específico em uma varredura controlada; o resultado é rotulado como "máximo observado (estimativa via cart-probe)" com o valor retornado pelo endpoint de carrinho.
  3. O cart-probe usa sessões Playwright efêmeras e isoladas com cleanup garantido, aplica throttle e nunca é invocado durante buscas ao vivo — apenas em varreduras controladas explícitas.
  4. Para todas as marcas com provider de avaliações identificado (Trustvox, VTEX native, etc.), a busca por produto retorna `rating` (nota média), `review_count` e pelo menos uma página de comentários — com dedup por ID de review e paginação limitada a N páginas configurável.

**Plans**: TBD

### Phase 45: Análise de Sortimento

**Goal**: Um cron de análise de sortimento varre categorias configuradas e gera snapshots com contagem de produtos por atributo canônico (ex.: polos por cor, por tecido), persistidos em SQLite, para que o operador identifique buracos no catálogo ao comparar execuções ao longo do tempo.
**Depends on**: Phase 37 (atributos canônicos confiáveis + SQLite schema), Phase 39 (cobertura de categorias completa incluindo Hugo Boss)
**Requirements**: SORT-01
**Success Criteria** (what must be TRUE):

  1. Um cron agendado (configurável, independente do scheduler de monitoramento de 10 min) varre categorias selecionadas e persiste snapshots de contagem por atributo canônico no SQLite — sem bloquear buscas ao vivo.
  2. O operador acessa um relatório de sortimento que mostra, para uma categoria e período, os atributos com menor cobertura (ex.: "polo azul: 2 SKUs vs. polo branco: 12 SKUs") — identificando buracos no catálogo.
  3. Dois snapshots consecutivos da mesma categoria podem ser comparados, mostrando atributos que desapareceram ou surgiram entre execuções.
  4. O cron é seguro para múltiplas execuções concorrentes: SQLite com writes transacionais, sem race condition com o scheduler de categoria existente.

**Plans**: TBD

## Progress

**Execution Order:**
Phases ativas executam em ordem numérica: 37 → 38 → 39 → 40 → 41 → 42 → 43 → 44 → 45. Phase 38 (UX quick wins) é independente e pode rodar em paralelo com 37; Phase 39 depende de 37 (atributos canônicos) e 38 (UX base); Phase 40 depende de 38; Phase 41 depende de 37; Phase 42 depende de 41; Phase 43 depende de 37 e 41; Phase 44 depende de 37 e 39; Phase 45 depende de 37 e 39 (última — precisa do SQLite e dos atributos confiáveis).

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 19-21. v1.10 (Relevância & IA) | v1.10 | - | Complete | shipped |
| 22-23. v1.11 (Precisão SKU) | v1.11 | - | Complete | shipped |
| 24. Exportação Excel | v1.12 | - | Complete | shipped |
| 25-29. v2.0 (Concorrentes & Confiabilidade) | v2.0 | - | Complete | shipped |
| 30. Detecção de Engine SFCC & Wake | v3.0 | 3/3 | Complete | 2026-06-23 |
| 31. Engine SFCC (Browser Público) | v3.0 | 3/3 | Complete | 2026-06-24 |
| 32. Engine Wake Commerce — Richards | v3.0 | 3/3 | Complete | 2026-06-25 |
| 33. Frete via Checkout nos Sites VTEX | v3.0 | 3/3 | Complete | 2026-06-26 |
| 34. Extração de Banners Desktop | v3.0 | 4/4 | Complete | 2026-06-23 |
| 35. Publicação de Banners no SharePoint | v3.0 | 0/? | Not started | - |
| 36. Onboarding das Marcas Concorrentes Restantes | v3.0 | 3/3 | Complete (NO-GO) | 2026-06-25 |
| 37. Paridade de Atributos & Fundação SQLite | v4.0 | 0/? | Not started | - |
| 38. UX de Busca & Monitoramento — Quick Wins | v4.0 | 0/? | Not started | - |
| 39. Cobertura de Marcas — Hugo Boss & Zara | v4.0 | 3/3 | Complete    | 2026-06-30 |
| 40. Onboarding por URL & Workflows de Adição | v4.0 | 5/5 | Complete    | 2026-06-30 |
| 41. Abstração de Frete & Marcas Não-VTEX | v4.0 | 0/? | Not started | - |
| 42. Frete para Marketplaces & Matriz Multi-Regional | v4.0 | 0/? | Not started | - |
| 43. Violação de MAP & Selos de Promoção | v4.0 | 0/? | Not started | - |
| 44. Ruptura de Estoque & Avaliações Reforçadas | v4.0 | 3/5 | In Progress|  |
| 45. Análise de Sortimento | v4.0 | 0/? | Not started | - |
