# Phase 37: Paridade de Atributos & Fundação SQLite - Context

**Gathered:** 2026-07-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Entregar um contrato canônico único de produto entre todas as engines para que as extrações retornem o mesmo conjunto de informações e o Excel exponha as mesmas colunas em todos os casos.

O foco desta phase é padronizar a extração e o shape dos dados, preservando o comportamento atual do sistema fora desse eixo. O usuário explicitamente removeu da phase - e do projeto como um todo - qualquer uso de SQLite, relatório de cobertura, nova persistência analítica ou histórico dedicado para esta iniciativa.

</domain>

<decisions>
## Implementation Decisions

### Contrato canônico de produto
- **D-01:** Os campos canônicos obrigatórios do produto ficam em inglês e são: `brand`, `url`, `price_full`, `price_discount`, `product_name`, `product_description`, `composition`, `available_colors`, `available_sizes`, `product_code`, `category`, `rating`, `review_count`.
- **D-02:** Esses campos definem o sucesso da paridade desta phase. Outros campos podem continuar existindo no payload interno, mas não entram no mínimo obrigatório de padronização.
- **D-03:** `product_code` significa o código comercial visível na PDP/listagem. Se a fonte não expuser esse código de forma clara, o campo deve ficar `null`.
- **D-04:** Se um campo obrigatório não existir na fonte, o produto continua válido e o campo fica vazio/`null`. Não descartar o produto por incompletude de atributo.
- **D-05:** O Excel deve sair desse contrato canônico com colunas fixas e consistentes entre engines, deixando blanks quando a fonte não trouxer o dado.

### Fronteira da phase e preservação de comportamento
- **D-06:** O objetivo principal da phase é que todas as engines extraiam as mesmas informações e as disponibilizem de forma padronizada no Excel.
- **D-07:** O sistema deve permanecer "exatamente como está hoje" fora da padronização das extrações. Não introduzir mudanças de UX, relatórios operacionais, novos fluxos de consulta ou persistência adicional.
- **D-08:** SQLite não entra nesta phase e não entra no projeto. Toda a parte de `analytics.db`, snapshots históricos e fundação analítica prevista no roadmap atual deve ser ignorada no planejamento.
- **D-09:** Não é necessário relatório de cobertura de atributos. A phase não deve introduzir endpoint, log estruturado, export ou histórico dedicado para medir preenchimento por marca.
- **D-10:** A padronização deve ser aditiva e compatível com o código atual: o planner pode usar mapeamento/aliasing entre campos existentes (`raw_title`, `raw_description`, `specifications`, campos tipados) e os nomes canônicos em inglês, desde que preserve os fluxos atuais.

### Claude's Discretion
- Onde colocar a utilidade central de normalização/mapeamento de atributos.
- Se os nomes canônicos em inglês passam a existir diretamente nos modelos internos ou se ficam garantidos na fronteira de exportação/serialização, desde que o Excel e o contrato de extração final usem os nomes canônicos definidos acima.
- Como distribuir o trabalho entre engines mais completas (VTEX/Shopify/Wake) e engines mais pobres em atributos (SFCC/Zara/marketplaces), desde que a saída final fique uniforme.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Escopo e overrides do usuário
- `.planning/ROADMAP.md` § `Phase 37: Paridade de Atributos & Fundação SQLite` - objetivo original da phase; as partes de SQLite e relatório de cobertura estão explicitamente sobrescritas por este CONTEXT.md.
- `.planning/REQUIREMENTS.md` § `PARID-01..04` - origem do requisito de paridade; `PARID-04` deve ser reinterpretado à luz da decisão do usuário de não criar relatório de cobertura.
- `.planning/PROJECT.md` - objetivo do milestone v4.0 e lista de marcas com lacunas atuais de atributos.
- `.planning/STATE.md` - decisão herdada `v4.0 PARID/additive` (normalização aditiva) e notas que ainda presumem SQLite; o planner deve seguir este CONTEXT.md quando houver conflito.

### Contrato de dados e exportação
- `backend/core/models.py` - contrato atual de `RawProductBronze` e `SearchProductResult`, incluindo campos tipados já existentes e `specifications`.
- `backend/api/routes_search.py` - caminho atual de exportação, incluindo o flatten de `specifications` para colunas de Excel.
- `backend/services/engines/base_engine.py` - contrato compartilhado e validação `RawProductBronze`-compatible para todas as engines.

### Engines em escopo da paridade
- `backend/services/vtex_api_scraper.py` - referência mais rica hoje para `composition`, cores, tamanhos e `specifications`.
- `backend/services/shopify_api_client.py` - mapeamento atual da Shopify para `RawProductBronze`.
- `backend/services/engines/wake_engine.py` - engine Wake/Richards em escopo de paridade.
- `backend/services/engines/sfcc_parser.py` - parser SFCC hoje com atributos esparsos; gap importante da phase.
- `backend/services/engines/zara_parser.py` - parser Zara hoje com `specifications` vazio.
- `backend/services/engines/amazon_engine.py` - caminho marketplace Amazon em escopo da uniformização.
- `backend/services/engines/mercado_livre_engine.py` - caminho marketplace Mercado Livre em escopo da uniformização.
- `backend/services/engines/netshoes_engine.py` - caminho marketplace Netshoes em escopo da uniformização.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RawProductBronze` já oferece um ponto central com campos tipados (`composition`, `available_colors`, `available_sizes`) e o bag `specifications`.
- `base_engine.validate_single` / `validate_and_filter` já impõem o contrato mínimo sem exigir todos os novos campos canônicos preenchidos.
- `routes_search.py` já transforma `specifications` em colunas de Excel, então existe um seam claro para unificar nomes e ordem de colunas.
- `vtex_api_scraper.py` e `shopify_api_client.py` já mostram exemplos concretos de extração mais rica de atributos que podem servir de padrão para as demais engines.

### Established Patterns
- A normalização de atributos deve ser aditiva e backward-compatible, nunca destruindo o bag bruto original.
- O sistema já tolera produtos com atributos parciais desde que passem pelos invariantes centrais do modelo; esta phase deve preservar essa filosofia.
- Cada engine monta um payload `RawProductBronze`-compatible próprio, o que favorece um normalizador compartilhado ou um mapeamento comum antes da exportação.

### Integration Points
- Uma utilidade central de aliasing/normalização chamada pelas engines ou por uma camada comum antes da serialização final.
- Os builders/mappers de `RawProductBronze` em `vtex_api_scraper.py`, `shopify_api_client.py`, `wake_engine.py`, `sfcc_parser.py`, `zara_parser.py` e nas engines de marketplace.
- O caminho de exportação em `backend/api/routes_search.py` para garantir colunas fixas em inglês no Excel.

</code_context>

<specifics>
## Specific Ideas

- O Excel é a superfície principal de sucesso desta phase: mesmas colunas, mesmos nomes em inglês, blanks quando a fonte não expõe o valor.
- `product_code` deve ser o código comercial legível pelo operador, nunca um ID interno inventado como fallback silencioso.
- `stock_availability`, `sub_category`, `collection`, `campaign` e outros sinais podem continuar existindo, mas não fazem parte do contrato obrigatório travado nesta discussão.

</specifics>

<deferred>
## Deferred Ideas

Nenhuma. SQLite e relatório de cobertura não foram deferidos para outra phase; foram explicitamente removidos do projeto/escopo pelo usuário.

### Reviewed Todos (not folded)
- `audit-category-mappings-all-brands.md` - trata de mapeamentos de categoria/onboarding, não da padronização do contrato de produto/Excel.
- `hugoboss-vtex-io-category-scan.md` - trata de varredura de categoria Hugo Boss, já endereçada em outra frente do roadmap.
- `reforcar-discriminacao-modelo.md` - trata de relevância/model discrimination, fora do objetivo de paridade de atributos.
- `zara-comp07-deferred.md` - trata da cobertura Zara/engine, não da uniformização do shape exportado.

</deferred>

---

*Phase: 37-Paridade de Atributos & Fundação SQLite*
*Context gathered: 2026-07-03*
