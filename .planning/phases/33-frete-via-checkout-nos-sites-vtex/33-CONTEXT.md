# Phase 33: Frete via Checkout nos Sites VTEX - Context

**Gathered:** 2026-06-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Entregar preço e prazo de frete para produtos encontrados nos sites de marca VTEX, consultando a simulação pública de checkout com SKU e CEP. A fase cobre o fluxo de busca das marcas VTEX, a representação de múltiplas modalidades de entrega domiciliar, a apresentação no resultado e os estados de falha por produto.

O cálculo continua no caminho interno do `VtexApiClient`; não deve ser roteado pelo hook genérico `BaseEngine.calculate_shipping`. Frete para SFCC, Wake, Shopify e marketplaces não faz parte desta fase. A padronização visual posterior da busca por SKU foi registrada como follow-up, não como expansão da Phase 33.

</domain>

<decisions>
## Implementation Decisions

### Arquitetura herdada e contrato de unidade
- **D-01:** O frete VTEX continua sendo calculado internamente pelo `VtexApiClient`, usando `/api/checkout/pub/orderForms/simulation`; não rotear pelo hook genérico `calculate_shipping`.
- **D-02:** Valores retornados pela VTEX em centavos devem ser convertidos para reais por divisão por 100. Frete grátis é `0.0`; frete não calculado ou sem cotação não pode ser representado como zero.
- **D-03:** A fase cobre somente sites de marca VTEX. SFCC, Wake, Shopify e marketplaces permanecem fora deste fluxo.

### Uso do CEP
- **D-04:** O campo de CEP inicia preenchido com `DEFAULT_CEP`, visível e editável; o destino nunca deve ser aplicado silenciosamente.
- **D-05:** Se o usuário alterar o valor e o CEP estiver inválido ou incompleto, a busca é bloqueada e mostra erro claro. Não executar silenciosamente sem frete e não restaurar o padrão por conta própria.
- **D-06:** Um CEP válido informado pelo usuário é lembrado durante a sessão e compartilhado entre novas buscas/abas, mas não persiste após recarregar o aplicativo; no reload, volta ao `DEFAULT_CEP`.
- **D-07:** Com CEP válido, o frete é calculado automaticamente em toda busca, sem toggle ou cálculo manual posterior.
- **D-08:** No resultado VTEX, preço do produto e frete permanecem campos visualmente separados. Não somar nem exibir um “valor final”/`landed_price` nesta superfície. Não remover o comportamento global existente nesta fase; a padronização das outras superfícies é follow-up.

### Modalidades de entrega
- **D-09:** Exibir todas as modalidades de entrega domiciliar retornadas pela VTEX. Retirada em loja/pickup deve ser completamente excluída da lista e nunca pode gerar “Frete Grátis”.
- **D-10:** Ordenar modalidades válidas por menor preço e, em empate, por menor prazo.
- **D-11:** Exibir o prazo no formato “Até X dias úteis”, preservando a semântica de `bd` da VTEX; não converter para data de calendário.
- **D-12:** Quando houver modalidade gratuita e alternativas pagas, mostrar todas e destacar “Frete Grátis”. Pela ordenação de preço, a gratuita aparece primeiro.

### Falhas e indisponibilidade
- **D-13:** Timeout, erro HTTP ou falha temporária de uma cotação não remove o produto nem derruba a busca. Manter o produto e mostrar “Frete temporariamente indisponível”; os demais produtos continuam normalmente.
- **D-14:** Uma resposta válida da VTEX sem modalidade de entrega domiciliar para o CEP deve mostrar “Entrega indisponível para este CEP”, distinta de falha técnica.
- **D-15:** Falhas temporárias recebem uma nova tentativa automática, curta e isolada por produto. Se a tentativa falhar, preservar o produto com o estado temporariamente indisponível.
- **D-16:** Se parte das modalidades estiver incompleta ou malformada, descartar somente essas entradas e mostrar as opções válidas. Exibir erro apenas quando nenhuma modalidade utilizável restar.

### Claude's Discretion
- Estrutura exata do modelo para a coleção de modalidades, desde que preserve o contrato e as decisões acima.
- Timeout, pequeno atraso da única retentativa e mecanismo de isolamento/concurrency por produto.
- Critérios técnicos para identificar pickup e modalidades malformadas a partir do payload VTEX.
- Layout exato da lista de modalidades no card, mantendo preço do produto e frete separados.
- Decomposição de helpers, nomes internos e organização dos testes conforme os padrões do repositório.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requisito e escopo
- `.planning/ROADMAP.md` §“Phase 33: Frete via Checkout nos Sites VTEX” — goal, independência das engines novas e success criteria da fase.
- `.planning/REQUIREMENTS.md` §“Frete (Checkout) — carregado do v2.0” — requisito FRET-05 e exclusão do frete Shopify para FRET-06.
- `.planning/PROJECT.md` §“Current Milestone: v3.0” — objetivo do milestone e fronteiras de plataforma.
- `.planning/STATE.md` §“Accumulated Context / Decisions” — decisão arquitetural de manter o frete no caminho interno do `VtexApiClient`.
- `.planning/milestones/v2.0-ROADMAP.md` §“Phase 29: Frete via Checkout nos Sites VTEX” — origem do carryover, semântica centavos→reais, frete grátis e teste de range.

### Código canônico
- `backend/services/vtex_api_scraper.py` — implementação parcial de `_fetch_shipping`, chamada ao checkout simulation e integração assíncrona com a busca.
- `backend/services/engines/vtex_engine.py` — delegação de `search` e `run_bulk_scrape` ao `VtexApiClient`; `calculate_shipping` genérico permanece fora deste caminho.
- `backend/core/models.py` — `ShippingInfo`, `SearchProductResult` e semântica atual de `shipping`, `is_free_shipping`, `shipping_price` e `landed_price`.
- `backend/config.py` — configuração existente `DEFAULT_CEP`.
- `backend/api/routes_search.py` — validação de CEP, `include_shipping` e contratos de resposta/exportação.
- `frontend/src/App.tsx` — campo de CEP, acionamento atual de `include_shipping` e renderização atual de um único `ShippingInfo`.
- `frontend/src/stores/searchStore.ts` — estado em memória que já preserva o CEP durante a sessão/entre abas.
- `backend/tests/test_vtex_api_client.py` — testes de caracterização existentes para conversão de unidade, prazo, frete grátis e indisponibilidade.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `VtexApiClient._fetch_shipping`: já envia SKU, CEP e seller para o endpoint de simulation, converte centavos para reais e interpreta `shippingEstimate`; deve evoluir de uma única SLA mais barata para uma coleção filtrada e ordenada.
- `VtexApiClient.search` / `scrape_category_paged`: já propagam `zipcode` e `include_shipping` e executam tarefas de frete com `asyncio.gather`.
- `ShippingInfo` e `SearchProductResult`: fornecem o contrato atual, mas representam uma única modalidade; o planner deve escolher uma evolução compatível para múltiplas opções e estados distintos.
- `settings.DEFAULT_CEP`: configuração existente que pode alimentar o valor inicial visível.
- `useSearchStore`: mantém CEP em memória entre abas sem persistência em reload, exatamente o ciclo de vida escolhido.
- Fakes de sessão em `test_vtex_api_client.py`: permitem testar checkout simulation sem rede real.

### Established Patterns
- Requisições de busca já aceitam CEP opcional no formato `00000-000` ou oito dígitos e enviam `include_shipping` ao engine.
- Sessões HTTP são compartilhadas via `SessionManager`; cotações por produto são assíncronas e uma falha não deve interromper o lote.
- A interface já renderiza `ShippingInfo`, mas apenas uma modalidade e prazo genérico em dias; a fase precisa ampliar essa apresentação.
- `0.0` significa frete grátis; `None` significa ausência de valor calculado. Esses estados não são intercambiáveis.

### Integration Points
- `backend/services/vtex_api_scraper.py`: parsing, filtro de pickup, ordenação, retry e classificação dos estados.
- `backend/core/models.py`: contrato de múltiplas modalidades sem confundir grátis, indisponível e erro temporário.
- `backend/api/routes_search.py`: serialização e validação do CEP/resultado.
- `frontend/src/App.tsx` e `frontend/src/stores/searchStore.ts`: CEP padrão visível, bloqueio de CEP inválido e lista de opções no card.
- `backend/tests/test_vtex_api_client.py` e testes de frontend/API pertinentes: regressão de unidade, múltiplas SLAs, pickup, ordenação, dias úteis, retry e isolamento de falha.

</code_context>

<specifics>
## Specific Ideas

- Textos definidos: “Frete Grátis”, “Até X dias úteis”, “Frete temporariamente indisponível” e “Entrega indisponível para este CEP”.
- Uma modalidade gratuita deve continuar acompanhada das opções pagas; não esconder alternativas mais rápidas.
- O valor do frete aparece separado do preço do produto, sem fórmula visual de soma nesta superfície.

</specifics>

<deferred>
## Deferred Ideas

- Padronizar a busca por SKU e os marketplaces para seguir o mesmo fluxo visual: preço do produto e frete separados, sem exibição de preço total. É uma alteração transversal fora da Phase 33 e deve entrar como follow-up prioritário.
- Frete por checkout em sites Shopify permanece FRET-06, dependente de validação de viabilidade própria.

### Reviewed Todos (not folded)
- “Reforçar discriminação de modelo (model-words + visual como desempate)” — match por palavras genéricas (`marca`, `busca`); trata da precisão da busca por SKU e não do frete VTEX.

</deferred>

---

*Phase: 33-Frete via Checkout nos Sites VTEX*
*Context gathered: 2026-06-24*
