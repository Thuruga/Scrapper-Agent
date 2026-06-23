# Phase 22: Gate de Marca - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning
**Source:** Decisão direta pós-spike (explore → spike 001/002 → milestone v1.11)

<domain>
## Phase Boundary

**Entrega:** Um gate rígido de marca que impede produtos de marca ausente/divergente de
aparecerem no resultado da busca por SKU, fechando o vazamento atual onde o resgate visual do
motor de relevância (v1.10) reabilita um concorrente parecido.

**Problema concreto validado (spike 001):** numa busca pelo SKU de uma polo Aramis, um polo
**Hering** tem o score de texto corretamente penalizado para **40.9** por
`_apply_brand_penalty` em `services/nlp_service.py` — MAS o Gate 1 em
`services/relevance_gates.py` (`if image_score >= 85 and text_score >= 40: return max(image_score, text_score)`)
o **resgata para final = 85**, acima do cutoff (60), e o exibe. A penalidade de marca no texto
é anulada pelo gate de resgate visual. Reproduzido ao vivo.

**Em escopo:**
- Filtrar itens de marca ausente quando a query especifica marca conhecida, independentemente do score.
- Tornar o comportamento configurável.

**Fora de escopo (Phase 22):**
- "Aramis errado" / discriminação de modelo (mesma marca, modelo errado) → Phase 23.
- Sinal de identidade além do EAN (filtro de marca nativo nas APIs, ID de catálogo) → IDENT-01, adiado.
- Qualquer válvula de resgate visual para itens brand-absent → INVALIDADA no spike 002.
</domain>

<decisions>
## Implementation Decisions

### Localização do gate — LOCKED
- O gate de marca é um **filtro pós-score independente**, aplicado em
  `services/cross_marketplace_service.py` **depois** de calcular o `final_match_score` e
  **antes** da régua de corte/exibição (no ponto onde hoje se monta `produtos_filtrados`).
- `services/relevance_gates.py` **permanece puro** (sem conhecimento de marca/título). NÃO
  passar informação de marca para as funções puras de gate.
- Razão: independência de qualquer gate atual/futuro — mesmo que o Gate 1 visual eleve o score,
  o filtro remove o item de marca ausente. Satisfaz BRAND-02 estruturalmente.

### Gatilho do gate — LOCKED
- O gate só dispara quando a query especifica uma **marca conhecida** — espelha exatamente o
  gatilho de `_apply_brand_penalty`: marca da query ∈ `known_brands_for_detection` do vocabulário.
- Se a query não especifica marca conhecida, o gate é no-op (não filtra nada).

### Critério de descarte — LOCKED
- Um item é descartado se o título do marketplace **não contém nenhuma** das marcas conhecidas
  presentes na query, usando a mesma normalização de texto do `nlp_service` (acentos/lowercase/limpeza).
- Reusar a tokenização/limpeza existente do `nlp_service` — não reimplementar.

### Configurabilidade — LOCKED (BRAND-03)
- Ativação do gate (e qualquer limiar) lida de `RelevanceSettings` (config.py / .env). Sem
  hardcode no fluxo de decisão. Default: gate **ativo**.

### Discrição do Claude (planner decide)
- Onde colocar o helper de detecção de marca: preferencialmente um método público em
  `nlp_service` (ex: `brand_is_present(official_title, market_title) -> bool`) que reusa
  `_clean_text` + `known_brands_for_detection`, chamado pelo serviço no filtro. Mantém a lógica
  de marca onde o vocabulário já vive e preserva a pureza de `relevance_gates`.
- Nome exato da config key (ex: `BRAND_GATE_ENABLED`).
- Estrutura dos testes unitários (o caso Hering é um teste-âncora obrigatório).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Motor de relevância e scoring
- `services/cross_marketplace_service.py` — pipeline de scoring; ponto onde `final_match_score`
  é calculado e `produtos_filtrados` é montado (onde o filtro de marca entra).
- `services/relevance_gates.py` — funções PURAS de gate (`compute_final_match_score`,
  `compute_min_score_cutoff`); manter puras. Linha do vazamento: o Gate `if i >= HIGH_IMAGE_SCORE and t >= MED_TEXT_FLOOR: return max(i, t)`.
- `services/nlp_service.py` — `_apply_brand_penalty` (gatilho de marca a espelhar),
  `_clean_text`, `known_brands_for_detection`.
- `config.py` — `RelevanceSettings` (onde adicionar a config do gate).
- `data/nlp_vocabulary.json` — `known_brands_for_brand_detection` (hoje: aramis, reserva, tommy).

### Evidência validada
- `.planning/spikes/001-brand-gate-impact/README.md` — VALIDATED; o caso Hering reproduzido,
  baixo risco de cobertura (95% dos itens exibidos já contêm a marca; brand-absent de visual
  alto = look-alikes de concorrente).
- `.planning/spikes/002-visual-rescue-valve/README.md` — INVALIDATED; NÃO reintroduzir válvula visual.
- `.planning/notes/diagnostico-falsos-positivos-busca-sku.md` — diagnóstico das causas-raiz.
</canonical_refs>

<specifics>
## Specific Ideas

- Teste-âncora obrigatório: query oficial Aramis (com "aramis") vs. título "Camisa Polo Básica
  Masculina Manga Curta Em Piquet Hering" com `image_match_score=85` → resultado deve ser
  **descartado** (não aparece), mesmo que `compute_final_match_score(40.9, 85) == 85`.
- Teste de não-regressão: itens cujo título contém "aramis" continuam passando (95% dos casos reais).
- Teste de no-op: query sem marca conhecida → gate não filtra nada.
- `data/search_history.json` (jobs `type=="cross"`) serve de fonte de casos reais para validação,
  lembrando que os scores armazenados são anteriores à penalidade de marca (recalcular ao vivo).
</specifics>

<deferred>
## Deferred Ideas

- **Phase 23** — Discriminação de modelo ("Aramis errado"). Ver `.planning/todos/pending/reforcar-discriminacao-modelo.md`.
- **IDENT-01** — Sinal de identidade de produto além do EAN. Ver `.planning/research/questions.md`.
</deferred>

---

*Phase: 22-gate-de-marca*
*Context gathered: 2026-06-13 (decisão direta pós-spike)*
