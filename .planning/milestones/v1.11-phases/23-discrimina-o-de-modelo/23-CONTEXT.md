# Phase 23: Discriminação de Modelo - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous) — 3 grey areas, todas aceitas como recomendadas

<domain>
## Phase Boundary

**Entrega:** Entre produtos da **marca correta** (já filtrados pelo gate de marca da Phase 22),
garantir que o topo do resultado da busca por SKU é o **modelo/linha específico** buscado — e não
um modelo Aramis adjacente — combinando duas alavancas: (1) model-words mais decisivas no score de
texto e (2) o sinal visual CLIP como **desempate** entre candidatos da mesma marca quando o texto
é ambíguo.

**Problema concreto (diagnóstico — falso positivo "Aramis errado"):**
- **Causa A:** `_apply_model_word_penalty` (`services/nlp_service.py`) é multiplicativo e brando —
  não separa duas polos Aramis diferentes. Hoje, `model_ratio < 0.50` com marca presente apenas
  multiplica por `0.70` (`NLP_MODEL_PENALTY_HEAVY_WITH_BRAND`), deixando o item próximo/acima do
  cutoff (60 com vision).
- **Causa B (estrutural):** o CLIP só roda nos top-N candidatos **já escolhidos pelo texto**
  (`top_candidates` em `cross_marketplace_service.py`). Se o texto já elegeu o modelo errado, o
  visual entra no score final (peso 0.40) mas **confirma**, não atua como desempate explícito entre
  candidatos da mesma marca.

**Em escopo (Phase 23):**
- Reforçar a discriminação de modelo entre candidatos da MESMA marca (MODEL-01).
- Promover o visual a desempate explícito quando o texto está ambíguo entre candidatos da mesma
  marca (MODEL-02).
- Tornar o comportamento configurável (.env), com flag de rollback.

**Fora de escopo (Phase 23):**
- Gate/penalidade de marca errada → já entregue na Phase 22 (BRAND-01/02/03).
- Sinal de identidade além do EAN (filtro de marca nativo, ID de catálogo) → IDENT-01, adiado.
- Novo modelo NLP / lista curada de model-words por linha Aramis → fora de escopo (manutenção).
- Qualquer mudança que viole a pureza de `services/relevance_gates.py` (LOCKED na Phase 22).
</domain>

<decisions>
## Implementation Decisions

### Estratégia de discriminação de modelo (model-words) — ACEITO

- **Mecanismo:** reforçar a **penalidade multiplicativa existente** em
  `_apply_model_word_penalty` (ajustar os multiplicadores `WITH_BRAND` via config). NÃO introduzir
  gate rígido de model-words — model-words são *fuzzy* (variantes de cor/tamanho/abreviação) e um
  gate arriscaria descartar variantes legítimas; a penalidade reforçada é reversível via config e
  satisfaz o critério 3 (rebaixar abaixo da régua).
- **Gatilho:** a discriminação reforçada aplica-se **apenas quando a marca da query bate no título**
  (caso "mesmo fabricante, qual modelo?"). O gate de marca da Phase 22 já tratou marca errada;
  isolar o problema de modelo evita penalização dupla. Espelha o branch `brand_present` já existente
  em `_apply_model_word_penalty`.
- **Definição de "model-word":** manter a **heurística atual** (palavra ≥3 chars, ∉
  `brand_and_category_words`, ∉ `stop_words`, derivada do título oficial). Zero vocabulário novo a
  manter — o título oficial Aramis já define as model-words por exclusão.
- **`model_ratio ≈ 0` (mesma marca, zero model-words em comum):** a penalidade deve ser forte o
  suficiente para **rebaixar o item abaixo da régua de corte** — marca certa + zero model-words =
  linha claramente diferente = falso positivo "Aramis errado" (critério 3 direto).

### Visual (CLIP) como desempate — ACEITO

- **Definição de "texto ambíguo" (MODEL-02):** **janela de proximidade configurável** entre
  candidatos da mesma marca — dois candidatos cujos scores de texto estão dentro de ~N pontos um do
  outro são considerados ambíguos. "Ambíguo" é relativo entre candidatos (robusto a deslocamentos de
  calibração), não uma faixa absoluta de score.
- **Como desempata:** dentro da janela de empate, o candidato de **maior `image_score` fica acima** —
  desempate explícito no ranking, verificável. Satisfaz MODEL-02 ("desempate, não apenas confirmação
  pós-texto").
- **Onde implementar:** **etapa de reordenação no `cross_marketplace_service`**, mantendo
  `services/relevance_gates.py` **PURO** (decisão LOCKED da Phase 22 — lógica cross-candidato e
  conhecimento de marca vivem no serviço, não nas funções puras de gate). O desempate é cross-candidato
  por natureza, então não cabe em `compute_final_match_score` (que é por-candidato).
- **Fallback sem sinal visual** (sem imagem de referência, download falhou, `AI_AVAILABLE=False`,
  `image_score==0`): cai no **comportamento atual** (ordena por `final_match_score` e depois `preco`).
  O desempate visual é aditivo — zero regressão no caminho anti-WAF/sem-vision.

### Configurabilidade, segurança e validação — ACEITO

- **Parâmetros novos** (janela de ambiguidade; quaisquer multiplicadores reforçados) ficam em
  `RelevanceSettings` (`config.py`, .env-overridable), como `BRAND_GATE_ENABLED` e os
  `NLP_MODEL_PENALTY_*`. Zero hardcode no fluxo de decisão (consistência com BRAND-03).
- **Flag de rollback:** novo `VISUAL_TIEBREAK_ENABLED` (default `True`) governa o desempate visual —
  simetria com `BRAND_GATE_ENABLED`, rollback rápido se a cobertura cair, e testável on/off
  (anti-tautologia). O reforço de model-words é feito ajustando os multiplicadores
  `NLP_MODEL_PENALTY_*` já existentes (tunáveis — não exige flag on/off novo).
- **Testes-âncora obrigatórios (5):**
  1. Dois polos Aramis (modelo correto vs. adjacente) → o **modelo correto fica no topo** (MODEL-01).
  2. Empate de texto (dentro da janela) entre dois candidatos da mesma marca → o de **maior
     `image_score` fica acima** (MODEL-02).
  3. Modelo claramente diferente (`model_ratio ≈ 0`, mesma marca) → **rebaixado abaixo da régua**
     (critério 3).
  4. **Não-regressão:** modelo + marca corretos permanecem no topo (critério 4).
  5. **Sem vision** (`image_score==0` / `VISUAL_TIEBREAK_ENABLED=false`) → fallback por texto,
     zero regressão.
- **Fonte de validação:** **fixtures sintéticas determinísticas** (text/image scores controlados)
  para os testes unitários (o pipeline de relevância é puro/testável offline); `data/search_history.json`
  (jobs `type=="cross"`) como referência para **calibrar os thresholds** manualmente — lembrando que
  os scores armazenados são anteriores às novas penalidades (recalcular ao vivo se necessário).

### Discrição do Claude (planner decide)
- Nome exato e default da config key da janela de ambiguidade (ex: `VISUAL_TIEBREAK_TEXT_WINDOW`,
  em pontos 0–100) e os valores reforçados dos multiplicadores `NLP_MODEL_PENALTY_HEAVY_WITH_BRAND` /
  `_MED_WITH_BRAND` — calibrados para que `model_ratio≈0` caia < cutoff sem derrubar variantes
  legítimas. Calibrar contra `search_history.json`.
- Onde exatamente inserir a etapa de reordenação (antes da régua de corte / antes do cap por
  plataforma) e se o desempate deve ser um predicado/função pura de nível de módulo importável pelos
  testes (padrão `passes_brand_gate` da Phase 22, anti-tautologia HIGH-1).
- Se o desempate agrupa por `(plataforma, marca)` ou só por marca ao definir "candidatos da mesma
  marca" para a janela.
- Estrutura exata dos testes (mirror de `tests/test_brand_gate.py` / `tests/test_relevance_gates.py`).
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `services/nlp_service.py` — `_apply_model_word_penalty` (lines 212-266) já implementa a estrutura
  de penalidade por `model_ratio` com branch `brand_present`; o reforço é ajuste de multiplicadores
  + (se preciso) endurecer a faixa de `model_ratio≈0`. `_clean_text`, `brand_and_category_words`,
  `known_brands_for_detection` reusáveis. `brand_is_present` (Phase 22) disponível para identificar
  "candidatos da mesma marca".
- `services/cross_marketplace_service.py` — `passes_brand_gate` (módulo, lines 16-38) é o padrão
  para um predicado/função pura importável pelos testes. A ordenação final vive em
  `produtos_filtrados.sort(key=lambda x: (-final_match_score, preco))` (line 253); `image_match_score`
  já está em cada dict de candidato (line 213). Ponto de inserção do desempate: após os scores finais
  e antes/junto da ordenação.
- `services/relevance_gates.py` — `compute_final_match_score` (gates "texto domina"),
  `compute_min_score_cutoff`. **Manter PURO** (LOCKED Phase 22).
- `config.py` — `RelevanceSettings` (lines 194-338): bloco `NLP_MODEL_PENALTY_*` (lines 253-276) e
  o idioma `Field(default=..., description=...)`; `BRAND_GATE_ENABLED` (lines 216-224) como template
  do novo flag.
- `data/nlp_vocabulary.json` — `known_brands_for_brand_detection` (aramis, reserva, tommy);
  `brand_names`/`category_words`/`colors` definem o que NÃO é model-word.

### Established Patterns
- **Função/predicado puro de nível de módulo** importado tanto por produção quanto por testes
  (anti-tautologia HIGH-1) — `passes_brand_gate`.
- **Config-flag lida inline, passada como argumento** — sem hardcode no fluxo (BRAND-03).
- **Pureza de `relevance_gates.py`** — lógica cross-candidato/marca fica no serviço, não nas funções
  puras (LOCKED Phase 22).
- **Estilo de teste** — `tests/test_brand_gate.py` / `tests/test_relevance_gates.py`: uma
  `class Test<Behavior>`, `assert ... is True/False`, teste-âncora obrigatório, teste on/off do flag.

### Integration Points
- O reforço de model-words entra em `calculate_text_score` → `_apply_model_word_penalty`
  (`nlp_service.py`), afetando o `text_match_score` antes da seleção de `top_candidates`.
- O desempate visual entra em `compare_product` (`cross_marketplace_service.py`) na etapa de
  ordenação dos candidatos da mesma marca, após o cálculo de `final_match_score`.
- Novos campos de config consumidos via o singleton `relevance_settings`.

</code_context>

<specifics>
## Specific Ideas

- Teste-âncora central (MODEL-01): duas polos Aramis no resultado (modelo buscado vs. linha
  adjacente) — o modelo correto deve terminar no topo.
- Teste-âncora MODEL-02: dois candidatos Aramis com `text_match_score` dentro da janela de
  ambiguidade — o de maior `image_match_score` deve ficar acima do outro (o visual desempata).
- Teste-âncora critério 3: candidato Aramis com `model_ratio ≈ 0` deve cair **abaixo** do cutoff
  (deixa de competir pelo topo), mesmo sendo da marca correta.
- Teste de não-regressão: buscas com modelo+marca corretos permanecem no topo.
- Teste de fallback/flag-off: `VISUAL_TIEBREAK_ENABLED=false` ou `image_score==0` → ordenação atual
  (texto → preço), zero regressão.
- Calibrar os multiplicadores reforçados e a janela contra `data/search_history.json` (jobs
  `type=="cross"`), recalculando scores ao vivo (os históricos são pré-penalidade).

</specifics>

<deferred>
## Deferred Ideas

- **IDENT-01** — Sinal de identidade de produto além do EAN (filtro de marca nativo nas APIs, ID de
  catálogo do marketplace). Adiado — research question, sem phase neste milestone. Ver
  `.planning/research/questions.md`.
- **Lista curada de model-words por linha Aramis** — descartada nesta phase (manutenção contínua);
  a heurística por exclusão é suficiente para os critérios.

</deferred>

---

*Phase: 23-discrimina-o-de-modelo*
*Context gathered: 2026-06-13 (smart discuss — autonomous)*
