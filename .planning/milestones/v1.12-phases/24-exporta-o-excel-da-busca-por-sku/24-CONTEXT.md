# Phase 24: Exportação Excel da Busca por SKU - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

O usuário pode selecionar quais produtos exportar nos resultados da busca por SKU (cross-marketplace) e baixar um arquivo `.xlsx` com os campos exibidos no card — **sem que o backend re-execute a busca ou re-raspe qualquer produto**. A exportação reflete exatamente o que está na tela no momento.

Entrega: (1) seleção por card + "selecionar todos" no frontend; (2) diálogo de exportação ("Todos" / "Apenas selecionados"); (3) novo endpoint `POST /search/cross-marketplace/export` que recebe os itens já exibidos no body e devolve um `.xlsx`; (4) download via blob no navegador com nome significativo.

Fora de escopo: histórico de exportações e unificação com o export por marca (Future Requirements `EXPORT-HIST-01`, `EXPORT-UNIFY-01`); qualquer alteração no motor de relevância ou na rota `/cross-marketplace`.

</domain>

<decisions>
## Implementation Decisions

### Selection UX (per card)
- Checkbox posicionado como overlay no canto superior esquerdo do card; usar `stopPropagation`/`preventDefault` para que marcar/desmarcar NÃO dispare a navegação do link `<a>` do card.
- Estado inicial ao carregar resultados: nada selecionado (opt-in do usuário).
- "Selecionar todos": um único toggle global no header dos resultados (abrange todos os marketplaces).
- Exibir contador "N selecionado(s)" próximo ao botão de exportar.

### Export Trigger & Dialog
- Botão de exportar no header dos resultados, reutilizando o estilo existente `.btn-excel` + ícone `FileSpreadsheet` (mesmo padrão da SearchPage).
- Diálogo com duas opções: "Todos" (sempre habilitado) e "Apenas selecionados" (desabilitado quando 0 selecionados).
- Após a exportação concluir: manter a seleção intacta (não limpar).
- Feedback durante a exportação: spinner no botão + toast de erro via `sonner`; sucesso = download do navegador.

### Excel Content & Formatting
- Cabeçalhos das colunas em Português: Plataforma, Vendedor, Título, Preço, Frete, Preço Total, Frete Grátis, Score de Match, Similar, URL.
- Booleanos renderizados como "Sim" / "Não" (Frete Grátis, Similar).
- Frete não calculado (`shipping_price === null`): Frete = "A calcular"; Preço Total = preço do produto (nunca um 0 enganoso).
- Score de match como inteiro arredondado (ex.: 87).
- Ordem das linhas: preservar a ordem exibida na tela (agrupada por marketplace, `_display_order`) — fidelidade exigida pelo EXPORT-05.

### Endpoint & Payload
- Payload: frontend envia os objetos de item exibidos completos; o backend seleciona/mapeia as 10 colunas.
- Token do nome do arquivo: `search_query` com fallback para `target_sku`. Padrão: `busca_sku_<query>_<YYYYMMDD_HHMMSS>.xlsx`.
- Array de itens vazio: backend retorna HTTP 400.
- Nome da planilha (sheet): "Busca SKU".

### Claude's Discretion
- Estrutura exata do modelo Pydantic da requisição (nome dos campos do item), desde que cubra as 10 colunas.
- Detalhes de estilo do checkbox/diálogo dentro das convenções existentes (`.stock-toggle`, glass tokens) — a definir no UI-SPEC.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Padrão de geração de Excel** em `export_search_products` ([api/routes_search.py:181-296](api/routes_search.py)): `io.BytesIO()` → `pd.ExcelWriter(engine='openpyxl')` → `df.to_excel(index=False)` → `StreamingResponse` com `Content-Disposition: attachment; filename="..."` e `Access-Control-Expose-Headers: Content-Disposition`. Sanitizador de nome + timestamp já presente. pandas + openpyxl já são dependências.
- **Campos do item de resultado** já carregam tudo o que precisamos, construídos em `build_formatted_results` ([services/relevance_gates.py:248-282](services/relevance_gates.py)): `marketplace`, `seller`, `title`, `price`, `shipping_price`, `landed_price`, `is_free_shipping`, `final_match_score`/`match_score`, `is_similar`, `url`, além de `is_buybox_winner`, `_display_order`.
- **Download via blob** em `ApiClient.exportSearch` ([frontend/src/api/client.ts](frontend/src/api/client.ts) ≈105-140): fetch → ler filename do `Content-Disposition` → `blob()` → object-URL → click em âncora → revoke. Modelo direto para `exportCrossMarketplace`.
- **Convenções de seleção** no frontend: `toggleBrand`/`selectAllBrands`/`clearBrands` (App.tsx ≈634-646) e checkbox estilizado `.stock-toggle` (App.css ≈569-612).
- **Botão Excel** existente `.btn-excel` + `FileSpreadsheet` (lucide-react) na SearchPage.

### Established Patterns
- Backend: FastAPI, `APIRouter(prefix="/search")`, todas as rotas atrás de `X-API-Key` (`Depends(verify_api_key)`). Modelos Pydantic `BaseModel` com `Field(...)`.
- Frontend: React 19 + TypeScript + Vite, `App.tsx` único, CSS puro com tokens (glass), ícones `lucide-react`, toasts `sonner`. Estado via hooks (sem Redux).
- A página alvo é o componente `CrossMarketplacePage` ([frontend/src/App.tsx](frontend/src/App.tsx) ≈882-1187); cards renderizados como `<a>` agrupados por marketplace.

### Integration Points
- Novo endpoint `POST /search/cross-marketplace/export` em `api/routes_search.py`, ao lado de `/cross-marketplace` e `/export`.
- Novo método `ApiClient.exportCrossMarketplace(...)` em `frontend/src/api/client.ts`.
- Estado de seleção + botão de export + diálogo dentro de `CrossMarketplacePage`.
- CSS de modal (`.modal-overlay`/`.modal-content`) ainda NÃO definido em App.css — será adicionado (ou usar componente existente) conforme tokens de marca.

</code_context>

<specifics>
## Specific Ideas

- Exemplo de nome de arquivo esperado (do success criteria): `busca_sku_polo_piquet_aramis_20260615_143022.xlsx`.
- O endpoint existente `POST /search/export` re-executa a busca e re-raspa detalhes — comportamento explicitamente PROIBIDO aqui; reaproveitar apenas o padrão de montagem do `.xlsx`, não o fluxo de busca.
- Fidelidade (EXPORT-05) é garantida por construção: o frontend envia exatamente os itens exibidos e o backend não recomputa nada.

</specifics>

<deferred>
## Deferred Ideas

- Histórico de exportações (`EXPORT-HIST-01`) — Future Requirement, fora do v1.12.
- Unificação com o export por marca (`EXPORT-UNIFY-01`) — Future Requirement, fora do v1.12.

</deferred>
