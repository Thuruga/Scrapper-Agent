# Phase 43: Violação de MAP & Selos de Promoção - Context

**Gathered:** 2026-07-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Entregar duas capacidades de inteligência competitiva sobre o resultado de produto já existente:

1. **MAP-01:** o operador define regras de preço mínimo permitido (MAP) por produto, categoria ou marca; o sistema sinaliza produtos anunciados abaixo do MAP, identificando o vendedor infrator.
2. **PROMO-01:** o sistema extrai selos de oferta e condições de pagamento em um campo estruturado de promoções, preservando o texto bruto quando não houver parse confiável.

O foco da phase é **detectar, persistir, expor e visualizar** essas informações sem quebrar o contrato atual de busca/exportação. A lógica deve ser aditiva sobre os modelos e as superfícies existentes de resultado.

**Fronteiras travadas pelo roadmap/requirements:**
- As regras MAP vivem em `backend/data/map_rules.json`.
- A violação deve usar o **preço anunciado correto** (preço efetivo de venda), nunca o preço cheio/riscado.
- `promotions` é um novo campo estruturado, aditivo: produtos sem promoção retornam lista vazia.
- O resultado deve funcionar tanto para marcas próprias quanto para marketplaces, com seller/infrator explícito quando disponível.

</domain>

<decisions>
## Implementation Decisions

### Modelo de regra MAP
- **D-01 [precedência por especificidade]:** Quando múltiplas regras MAP forem aplicáveis ao mesmo produto, a precedência é `product > category > brand`. A regra mais específica vence; não há merge de pisos entre escopos.
- **D-02 [identidade de regra por produto]:** Regras de produto devem preferir `product_code` como identidade principal quando esse código existir e for comercialmente legível. Como fallback seguro, a regra pode armazenar também a URL normalizada do produto. O planner pode escolher a chave exata, desde que suporte produto sem `product_code` sem inventar ID interno opaco.
- **D-03 [shape mínimo da regra]:** Cada regra persistida em `map_rules.json` deve ser serializável em JSON simples e incluir, no mínimo: `scope` (`product`/`category`/`brand`), identificador do alvo, `min_price`, `active`, timestamps de auditoria e metadados opcionais (`brand`, `notes`). O formato exato pode ser refinado pelo planner, mas sem exigir banco novo nem migração pesada.
- **D-04 [persistência atômica]:** A escrita de `map_rules.json` deve seguir o padrão já usado em `brand_service.py`: diretório garantido, arquivo temporário e replace atômico. Não escrever diretamente no arquivo final.

### Base de comparação da violação
- **D-05 [preço anunciado efetivo]:** A verificação de violação usa o preço efetivo anunciado ao comprador, isto é, o mesmo valor resolvido hoje como preço de venda (`price_discount` quando presente e não-delta; `price_full` quando não houver desconto). Nunca usar o preço cheio/riscado como base da infração.
- **D-06 [frete não entra no veredito]:** `shipping_price` e `landed_price` podem ser exibidos como contexto adicional para análise comercial, mas **não** entram no cálculo de violação MAP. O veredito é sobre o preço anunciado do produto, não sobre o total entregue.
- **D-07 [sem falso positivo por ausência de preço]:** Se o produto não tiver preço efetivo resolvível, o sistema não deve marcar violação. O planner pode surfacear estado neutro (`not_applicable`/`unknown`) ou apenas ausência de badge, mas nunca inferir violação sem preço confiável.

### Seller / infrator
- **D-08 [marketplaces usam seller real]:** Para marketplaces, o infrator deve usar o seller extraído do produto/PDP quando disponível. O sistema já tem precedência e limpeza de seller em `seller_extraction.py`; essa lógica deve ser reaproveitada antes de cair em defaults.
- **D-09 [brand sites contam como first-party]:** Em sites próprios de marca sem seller terceirizado, o infrator deve ser a própria marca/storefront (`brand_name`/`brand`) com um marcador conceitual de first-party. Não deixar o campo vazio quando a própria marca anuncia abaixo do MAP.
- **D-10 [default de marketplace não é seller real]:** Se a extração só encontrar o nome default do marketplace (`Mercado Livre`, `Amazon`, `Netshoes`) ou nenhum seller confiável, o sistema pode usar esse valor como fallback de exibição, mas deve distingui-lo conceitualmente de seller terceirizado real. O planner pode usar um campo auxiliar (`seller_is_default` / `seller_type`) se ajudar a UI.

### Campo estruturado de promoções
- **D-11 [campo aditivo]:** Adicionar `promotions: List[...]` ao contrato de produto retornado pela busca e exportação, com default `[]` tanto em `RawProductBronze` quanto em `SearchProductResult` (ou na fronteira equivalente escolhida pelo planner).
- **D-12 [tipos mínimos recomendados]:** O conjunto mínimo de tipos normalizados para esta phase é:
  - `pix_discount`
  - `percentage_discount`
  - `bundle`
  - `installments`
  - `generic_badge`
  O planner pode adicionar tipos extras (`fixed_amount_discount`, etc.) se surgirem evidências baratas, mas esses cinco cobrem o requisito sem overfitting.
- **D-13 [raw_text sempre preservado]:** Toda promoção estruturada deve preservar `raw_text`. Quando o parser não conseguir normalizar valores com confiança, ainda assim deve retornar um item `generic_badge` com o texto bruto em vez de descartar a informação.
- **D-14 [shape mínimo da promoção]:** Cada item em `promotions` deve carregar pelo menos `type` e `raw_text`. Campos normalizados como `value`, `unit`, `installments_count`, `installment_amount`, `payment_method`, `parsed` podem ser opcionais e aditivos.
- **D-15 [múltiplas promoções por produto]:** O campo aceita múltiplos itens por produto. Não colapsar parcelamento, desconto Pix e selo de bundle em um único texto se a fonte os expõe separadamente.

### Superfície operacional
- **D-16 [entregar endpoint + UI mínima]:** A phase deve entregar **os dois** caminhos: endpoint(s) para criar/listar/atualizar regras MAP e uma UI mínima para o operador gerenciar regras sem editar JSON manualmente. O roadmap aceita "UI ou endpoint", mas o default recomendado é sair com ambos para tornar o recurso realmente operável.
- **D-17 [UI incremental nas superfícies existentes]:** A visualização deve reutilizar os cards/resultados já existentes em `frontend/src/App.tsx`, acrescentando badges/linhas contextuais para:
  - violação MAP
  - seller/infrator
  - promoções estruturadas
  Não criar tela paralela de resultados para esta phase.
- **D-18 [edição de regras fora do card do produto]:** A UI de cadastro/edição de regras MAP pode viver em um modal ou painel simples, separado do card, para evitar inflar a busca comparativa. O planner decide a ergonomia exata, mas o fluxo deve suportar regra por marca, categoria e produto.

### Exportação e compatibilidade
- **D-19 [export aditivo]:** O Excel/serialização não deve quebrar consumidores atuais. O planner pode optar por:
  - colunas novas derivadas para MAP/promoções; ou
  - serialização textual estável de `promotions`
  desde que o contrato existente continue válido.
- **D-20 [compatibilidade com histórico]:** Registros antigos de histórico/busca sem `promotions` ou metadados MAP devem continuar válidos com defaults seguros.

### Claude's Discretion
- Nome exato do serviço de regras MAP, modelos Pydantic e endpoints REST.
- Se o rule identifier de produto guarda `product_code`, `url_normalized` ou ambos, desde que respeite D-02.
- Exato shape do badge/linha de UI para violação e promoções.
- Estratégia de parser por engine/site para promoções: parser dedicado por engine, helpers comuns por regex, ou mistura de ambos.
- Exata estratégia de exportação para promoções/MAP, desde que seja aditiva.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requisito e roadmap
- `.planning/ROADMAP.md` § `Phase 43: Violação de MAP & Selos de Promoção` - goal, dependencies e success criteria.
- `.planning/REQUIREMENTS.md` - `MAP-01` e `PROMO-01`.
- `.planning/PROJECT.md` - milestone v4.0, eixo "Inteligência Competitiva".
- `.planning/STATE.md` - estado acumulado do roadmap v4.0 e decisões já entregues nas phases 37/41/42.

### Fases anteriores obrigatórias
- `.planning/phases/37-paridade-de-atributos-funda-o-sqlite/37-CONTEXT.md` - contrato canônico/aditivo de produto e filosofia de compatibilidade.
- `.planning/phases/41-abstracao-de-frete-marcas-nao-vtex/41-CONTEXT.md` - semântica de `shipping_price`/`landed_price` como contexto separado.
- `.planning/phases/42-frete-para-marketplaces-matriz-multi-regional/42-CONTEXT.md` - seller/frete já surfacados na busca e UI incremental de cards.

### Código a alterar/reusar
- `backend/core/models.py` - `RawProductBronze`, `SearchProductResult`, `resolve_effective_price`, campos de seller/frete e seam natural para `promotions`/MAP metadata.
- `backend/api/routes_search.py` - modelos/serialização de busca, exportação e respostas sob demanda.
- `backend/services/product_contract.py` - export canônico e colunas derivadas; ponto natural para acrescentar campos/export de promoções.
- `backend/services/brand_service.py` - padrão de persistência JSON atômica a ser espelhado em `map_rules.json`.
- `backend/services/cross_marketplace_service.py` - enriquecimento de seller/preço em marketplaces; relevante para surfacing de infrator.
- `backend/services/engines/seller_extraction.py` - regras de extração e diferenciação entre seller real e default de marketplace.
- `frontend/src/App.tsx` / `frontend/src/api/client.ts` - cards de resultado, badges de desconto e fluxos de chamada já existentes.
- `backend/data/` - padrão de arquivos JSON locais já adotado pelo projeto (`brands.json`, `price_monitors.json`, `shipping_matrix_cache.json`).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `resolve_effective_price` / `resolve_original_price` em `backend/core/models.py` já capturam a semântica correta de preço efetivo vs. preço cheio; Phase 43 deve reutilizar isso para evitar lógica duplicada e falsos positivos.
- `SearchProductResult` já carrega `seller`, `shipping_price` e `landed_price`, então a UI e a exportação já têm pontos naturais para contexto de MAP sem reinventar o shape.
- `brand_service.py` já demonstra um padrão limpo de persistência JSON local com validate-on-read e replace atômico.
- `seller_extraction.py` já diferencia seller real de defaults de marketplace; isso reduz risco de atribuir um marketplace inteiro como infrator terceirizado quando o seller não foi encontrado.
- `App.tsx` já tem badges visuais de desconto e áreas pequenas de metadata por produto; a visualização de promoções/MAP pode seguir esse padrão incremental.

### Established Patterns
- Mudanças de schema devem ser aditivas, com defaults seguros e compatibilidade com histórico/exportações antigas.
- Dados ausentes não invalidam o produto; o sistema prefere `null`/lista vazia a descartar item.
- Persistência local em JSON é uma escolha aceita no projeto quando o requisito pede configuração/estado simples do operador.
- Estados explícitos são preferíveis a inferências otimistas: sem preço confiável, sem seller confiável ou sem parse confiável de promoção não devem virar dados falsos.

### Current Constraints
- Nem todas as engines expõem promoções da mesma forma; algumas terão parse estruturado rico, outras só texto bruto.
- `seller` hoje existe principalmente no resultado enxuto de busca; o planner deve decidir se a origem da violação vive só na fronteira de resposta ou também no modelo bronze.
- O contrato canônico atual de exportação não inclui promoções/MAP; qualquer extensão precisa evitar quebra em planilhas/consumidores existentes.

### Integration Points
- Serviço dedicado de MAP rules em `backend/services/` consumido por rotas FastAPI e pelos fluxos de busca/enriquecimento.
- Enriquecimento de produto após resolução do preço efetivo e seller, antes de serializar a resposta final.
- UI de busca comparativa e cross-marketplace como superfícies primárias para badges e contexto de violação/promoção.

</code_context>

<specifics>
## Specific Ideas

- **Default recomendado de regra por produto:** armazenar `{scope: "product", product_code?, product_url?}` e considerar match por `product_code` quando existir; URL normalizada cobre os casos sem código comercial.
- **Default recomendado de violação no payload:** expor algo como `map_violation` / `map_rule_applied` / `map_price_floor` de forma aditiva, sem remover nenhum campo atual.
- **Default recomendado de promoções no payload:** lista de objetos compactos e estáveis, por exemplo:
  - `{"type":"pix_discount","value":15,"unit":"percent","payment_method":"pix","raw_text":"15% OFF no Pix"}`
  - `{"type":"installments","installments_count":10,"installment_amount":39.9,"raw_text":"10x de R$ 39,90 sem juros"}`
  - `{"type":"bundle","raw_text":"Leve 3 pague 2"}`
- **Default recomendado de first-party seller:** usar o nome da marca (`brand_name`/`brand`) quando não houver seller terceirizado, com semântica clara de loja própria.

</specifics>

<deferred>
## Deferred Ideas

- Cálculo de violação baseado em `landed_price` (produto + frete) como veredito oficial - fora desta phase; manter apenas como contexto.
- Analytics/histórico de violações MAP ao longo do tempo - pode virar fase futura, mas não é necessário para operar a regra agora.
- Painel analítico dedicado de promoções/MAP por marca/categoria - fora desta phase; usar as superfícies de resultado existentes.
- Normalização perfeita/universal de todo tipo de promoção de todos os engines - não bloquear a phase; texto bruto preservado já atende o requisito quando o parse não fecha.

### Reviewed Todos (not folded)
- `.planning/todos/pending/reforcar-discriminacao-modelo.md` - trata de relevância/model discrimination, não de MAP/promoções.
- `.planning/todos/pending/cap-search-history-list.md` - trata de histórico/listagem, não da regra de preço/promotions.
- `.planning/todos/pending/audit-category-mappings-all-brands.md` - categoria/onboarding, fora do eixo de inteligência competitiva desta phase.

</deferred>

---

*Phase: 43-Violação de MAP & Selos de Promoção*
*Context gathered: 2026-07-03*
