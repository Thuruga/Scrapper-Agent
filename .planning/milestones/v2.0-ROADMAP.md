# Roadmap: Intelligence Scraper

## Milestones

- ✅ **v1.10 Refatoração do Motor de Relevância & Performance da IA** - Phases 19-21 (shipped)
- ✅ **v1.11 Precisão da Busca por SKU** - Phases 22-23 (shipped)
- ✅ **v1.12 Exportação Excel da Busca por SKU** - Phase 24 (shipped)
- 🚧 **v2.0 Cobertura de Concorrentes & Confiabilidade** - Phases 25-29 (active)

**Milestone Goal (v2.0):** Ampliar a cobertura competitiva (5 marcas VTEX + gestão/desativação) e elevar a confiabilidade da plataforma (busca que sobrevive à troca de abas, histórico completo de buscas e cálculo de frete por checkout nos sites de marca VTEX).

## Overview

Com a exportação Excel entregue (Phase 24), v2.0 adiciona três eixos ortogonais: cobertura competitiva (onboard de marcas concorrentes com engine verificada, desativação real), robustez de UX (busca viva entre abas, histórico completo) e observabilidade operacional (frete checkout). A fundação backend (Phase 25) habilita todos os demais: o gate de engine desconhecida previne poluição silenciosa e o chokepoint `list_brands(active_only)` garante que desativação seja real.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Phases 19-24 pertencem aos milestones v1.10-v1.12 (CONCLUÍDOS e shipped). As phases ativas são 25-29.

- [x] **Phase 25: Fundação de Motores** - Detecção de plataforma não suportada (`detect_engine` retorna `"unknown"` + probe Wake) e aplicação real do flag `is_active` no chokepoint `list_brands` (COMP-02, MGMT-01)
- [x] **Phase 26: Onboarding das 5 Marcas VTEX** - Cadastro das marcas concorrentes VTEX com engine reconfirmada por `detect_engine` na adição e mapeamento de categorias (COMP-01) (completed 2026-06-19)
- [x] **Phase 27: Histórico Completo + Gestão de Marcas na UI** - Buscas comparativas salvas no histórico, `preloadedJobId` propagado em `App.tsx`, campo de gestão de marcas na interface (HIST-01, HIST-02, MGMT-02) (completed 2026-06-20)
- [x] **Phase 28: Persistência da Busca Entre Abas** - Estado de busca em andamento migrado para store zustand global; busca sobrevive à troca de abas sem cancelamento nem perda de resultado (PERS-01) (completed 2026-06-22)
- [ ] **Phase 29: Frete via Checkout nos Sites VTEX** - Cálculo de preço e prazo de frete via checkout simulation nos sites de marca VTEX, com contrato de unidade (centavos→reais) documentado e testado (FRET-05)

## Phase Details

<details>
<summary>✅ v1.10 (Phases 19-21) - SHIPPED — ver histórico abaixo</summary>

### Phase 19: Clean Code & Refatoração Base

**Goal**: Centralizar a lógica de texto no serviço correto e limpar o serviço de marketplace.
**Requirements**: NLP-01, NLP-02
**Success Criteria** (atingidos):

  1. `_calcular_relevancia` e `_STOP_WORDS` não existem mais em `cross_marketplace_service.py`.
  2. Remoção de cores e validação de texto ocorrem estritamente no `nlp_service.py`.

**Plans**: Complete

### Phase 20: Motor de Relevância - Decision Gates

**Goal**: Substituir a média linear rígida por uma árvore de decisão baseada em gates.
**Requirements**: REL-01, REL-02, REL-03, REL-04
**Success Criteria** (atingidos):

  1. Gate 1 (Visual ≥ 85% e Texto ≥ 40%) e Gate 2 (Texto ≥ 85% e Visual ≥ 45%) implementados.
  2. Fallback (Gate 3) para média ponderada quando os limites não são atingidos.

**Plans**: Complete

### Phase 21: IA Visual - Batching e Concorrência

**Goal**: Acelerar a inferência de imagem via processamento em lote.
**Requirements**: VIS-01, VIS-02, VIS-03
**Success Criteria** (atingidos):

  1. Download assíncrono concorrente + inferência CLIP em batch + cegueira de cor (grayscale).

**Plans**: Complete

</details>

<details>
<summary>✅ v1.11 (Phases 22-23) - SHIPPED</summary>

#### Phase 22: Gate de Marca

**Goal**: Quando a query por SKU especifica uma marca conhecida, garantir que produtos sem essa marca no título sejam descartados do resultado final — fechando o vazamento atual em que o gate de resgate visual (`if img>=85 and text>=40: max(img,text)` em `services/relevance_gates.py`) reabilita um concorrente parecido cujo texto já foi penalizado por `_apply_brand_penalty`.
**Depends on**: Nothing (primeira phase do milestone; opera sobre o motor v1.10 já shipped)
**Requirements**: BRAND-01, BRAND-02, BRAND-03
**Success Criteria** (atingidos):

  1. Uma busca pelo SKU de uma polo Aramis não exibe a polo Hering (marca ausente no título), mesmo quando o score visual da Hering é alto (≥ 85).
  2. Quando a query especifica uma marca conhecida, nenhum produto cujo título não contém essa marca aparece acima da régua de corte.
  3. Buscas cujo título já contém a marca da query continuam exibidas.
  4. A ativação e o limiar do gate de marca são lidos de configuração, sem valores hardcoded.

**Plans**: 1 plan

- [x] 22-01-PLAN.md — Filtro de marca pós-score independente do visual

#### Phase 23: Discriminação de Modelo

**Goal**: Entre produtos da marca correta, garantir que o topo do resultado é o modelo/linha específico buscado — e não um modelo Aramis adjacente — usando model-words decisivas e o sinal visual CLIP como desempate quando o texto está ambíguo.
**Depends on**: Phase 22 (o gate de marca elimina primeiro o ruído de marca errada, isolando o problema de modelo entre candidatos da mesma marca)
**Requirements**: MODEL-01, MODEL-02
**Success Criteria** (atingidos):

  1. Para um SKU Aramis com vários modelos similares no catálogo, o item no topo do resultado é o modelo correto.
  2. Quando dois candidatos da mesma marca têm score de texto ambíguo, o de maior similaridade visual ao produto oficial fica acima do outro.
  3. Um produto da marca correta mas de modelo claramente diferente é rebaixado abaixo da régua.
  4. Buscas com modelo correto e marca correta permanecem no topo (sem regressão).

**Plans**: 2 plans (2 waves)

- [x] 23-01-PLAN.md — Lever 1 (MODEL-01): reforçar penalidades NLP
- [x] 23-02-PLAN.md — Lever 2 (MODEL-02): apply_visual_tiebreak + _detect_candidate_brand

</details>

<details>
<summary>✅ v1.12 (Phase 24) - SHIPPED</summary>

#### Phase 24: Exportação Excel da Busca por SKU

**Goal**: O usuário pode selecionar quais produtos exportar nos resultados da busca por SKU e baixar um arquivo Excel com os campos exibidos no card — sem que o backend re-execute a busca ou re-raspe qualquer produto.
**Depends on**: Nothing (opera sobre a UI e a rota cross-marketplace já existentes; não altera o motor de relevância)
**Requirements**: EXPORT-01, EXPORT-02, EXPORT-03, EXPORT-04, EXPORT-05, EXPORT-06
**Success Criteria** (atingidos):

  1. Cada card de resultado na busca por SKU exibe um checkbox; o usuário pode marcar e desmarcar itens individualmente, e o estado de seleção persiste enquanto os resultados estão exibidos.
  2. Um controle "selecionar todos" alterna entre marcar todos os cards e desmarcar todos, refletindo o estado imediatamente em cada checkbox individual.
  3. Ao clicar em Exportar, um diálogo apresenta duas opções — "Todos" e "Apenas selecionados" — e só prossegue com o download após a escolha do usuário.
  4. O arquivo baixado é um `.xlsx` válido, abrível no Excel/LibreOffice, com uma linha por produto e as colunas: plataforma, vendedor, título, preço do produto, frete, preço total (landed), frete grátis, score de match, similar (sim/não) e URL.
  5. O conteúdo do Excel é idêntico ao que está exibido na tela no momento da exportação: mesmos vendedores, preços, fretes e scores — o backend não re-executa a busca nem consulta scrapers.
  6. O nome do arquivo baixado inclui o SKU/query da busca e um timestamp (ex.: `busca_sku_polo_piquet_aramis_20260615_143022.xlsx`).

**Plans**: 3 plans (3 waves)

**Wave 1**

- [x] 24-01-PLAN.md — Wave 0: test scaffold tests/test_export_cross_marketplace.py (backend contract, RED)
- [x] 24-02-PLAN.md — Wave 1: backend endpoint POST /search/cross-marketplace/export + Pydantic models + _sanitize_cell

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 24-03-PLAN.md — Wave 2: frontend selection + select-all + export dialog + ApiClient.exportCrossMarketplace + CSS

**UI hint**: yes

</details>

### 🚧 v2.0 Cobertura de Concorrentes & Confiabilidade (In Progress)

#### Phase 25: Fundação de Motores

**Goal**: O sistema detecta plataformas não suportadas em vez de cair silenciosamente no engine VTEX, e marcas inativas são excluídas automaticamente de todas as operações (busca, monitoramento, exportação e scheduler) por um único chokepoint.
**Depends on**: Nothing (fundação backend; pré-requisito para todas as phases do milestone)
**Requirements**: COMP-02, MGMT-01
**Success Criteria** (what must be TRUE):

  1. Quando `detect_engine` é chamado para um domínio Wake Commerce (ex.: Shop2gether), retorna `"unknown"` em vez de `"vtex"`, e a marca correspondente não entra na busca (zero resultados mascarados).
  2. Ao desativar uma marca via `PATCH /brands/{key}/active`, ela desaparece dos resultados da busca por marca, da exportação e da fila do scheduler sem que qualquer outra rota seja modificada — a exclusão ocorre exclusivamente pelo chokepoint `list_brands(active_only=True)`.
  3. Ao reativar a mesma marca, ela volta a aparecer nas buscas imediatamente na próxima chamada.
  4. A rota `GET /brands/` (usada pela UI de gestão) continua retornando marcas inativas para que possam ser reativadas — o filtro `active_only` é opt-in, não o padrão global.

**Plans**: 4 plans (3 waves)

**Wave 0**

- [x] 25-00-PLAN.md — Wave 0: RED test scaffolds tests/test_engine_detection.py + tests/test_brand_active.py (COMP-02 + MGMT-01)

**Wave 1** *(parallel; disjoint files)*

- [x] 25-01-PLAN.md — COMP-02: detect_engine hardening (unknown fallback + Wake probe) + create_brand unknown→inactive
- [x] 25-02-PLAN.md — MGMT-01: list_brands(active_only) chokepoint + set_active (service layer)

**Wave 2** *(blocked on Wave 1)*

- [x] 25-03-PLAN.md — MGMT-01: PATCH /brands/{key}/active endpoint + active_only=True call sites (search/scheduler/category-scan)

---

#### Phase 26: Onboarding das 5 Marcas VTEX

**Goal**: As cinco marcas concorrentes em plataforma VTEX confirmada estão cadastradas no sistema com engine verificada, categorias mapeadas e prontas para busca e monitoramento.
**Depends on**: Phase 25 (gate de engine desconhecida deve existir antes de registrar marcas; marca com engine `"unknown"` fica inativa automaticamente em vez de poluir a busca)
**Requirements**: COMP-01
**Success Criteria** (what must be TRUE):

  1. Uma busca por marca retorna produtos reais para cada uma das cinco marcas: Levi's, Calvin Klein, Zapalla, Austral e Track & Field.
  2. O `engine` de cada marca registrada é `"vtex"` — reconfirmado por `detect_engine` no momento da adição, não assumido manualmente.
  3. As marcas em plataformas não suportadas (Richards, Lacoste, Hugo Boss, Zara) **não** são onboardadas neste milestone (movidas para Future Requirements); se um operador tentar adicioná-las, a detecção da Phase 25 (COMP-02) as identifica como plataforma não suportada e impede o cadastro silencioso como VTEX.

**Plans**: 2 plans (2 waves)

**Wave 1**

- [x] 26-01-PLAN.md — Wave 0: offline contract test tests/test_vtex_brand_onboarding_contract.py (COMP-01, D-10b)

**Wave 2** *(blocked on Wave 1)*

- [x] 26-02-PLAN.md — Idempotent seed script scripts/onboard_vtex_brands.py (engine reconfirm + Austral retry + relative-path mappings + dual persistence)

---

#### Phase 27: Histórico Completo + Gestão de Marcas na UI

**Goal**: Todas as buscas ficam registradas no histórico (comparativa e por SKU), qualquer busca salva pode ser reaberta para reexibição, e o usuário tem um campo único na interface para adicionar, remover e ativar/desativar marcas.
**Depends on**: Phase 25 (o toggle de ativar/desativar na UI consome o endpoint `PATCH /brands/{key}/active` criado ali)
**Requirements**: HIST-01, HIST-02, MGMT-02
**Success Criteria** (what must be TRUE):

  1. Após executar uma busca comparativa por marca, o item aparece na lista de histórico com tipo `"search"` e pode ser reaberto — os resultados são reexibidos sem nova raspagem.
  2. Ao clicar em qualquer entrada do histórico (comparativa ou por SKU), o usuário é levado à aba correta e os resultados são exibidos; o `preloadedJobId` é propagado corretamente por `App.tsx` para o componente de destino.
  3. A interface de configurações exibe um campo unificado de gestão de marcas onde o usuário pode adicionar uma nova marca, remover uma existente e ativar/desativar — tudo em um único lugar, sem navegação extra.

**Plans**: 4 plans (3 waves)

**Wave 0**

- [x] 27-00-PLAN.md — Wave 0: RED test scaffold tests/test_search_history_comparative.py (HIST-01 shape contract + FAILED path + service round-trip)

**Wave 1** *(parallel; disjoint files)*

- [x] 27-01-PLAN.md — HIST-01: persist comparative POST /search (create_job type="search" → COMPLETED inner-list / FAILED) (api/routes_search.py)
- [x] 27-02-PLAN.md — MGMT-02: ApiClient.setBrandActive + SettingsPage active toggle + inactive distinction + virtual-marketplace guard (client.ts, App.tsx SettingsPage)

**Wave 2** *(blocked on Wave 1)*

- [x] 27-03-PLAN.md — HIST-02: App-level preloadedJobId state + renderTab propagation to both pages + reusable HistoryList per tab (App.tsx)

**UI hint**: yes

---

#### Phase 28: Persistência da Busca Entre Abas

**Goal**: Uma busca em andamento continua ativa ao navegar para outra aba e ao voltar — progresso, resultados parciais e estado de seleção são preservados sem cancelamento nem dupla execução.
**Depends on**: Phase 27 (o store global precisa saber qual job precarregar ao reabrir histórico; o preloadedJobId já deve estar fluindo em App.tsx)
**Requirements**: PERS-01
**Success Criteria** (what must be TRUE):

  1. Com uma busca em andamento na aba de busca por marca, ao trocar para outra aba e voltar, a busca continua em execução e os resultados já carregados são visíveis — nenhum resultado é perdido e a busca não é reiniciada.
  2. Ao completar a busca enquanto o usuário está em outra aba, a notificação de conclusão aparece e os resultados estão disponíveis ao retornar.
  3. Não ocorre duplo-fetch (a busca não dispara duas vezes ao montar/remontar o componente de busca), e o cancelamento correto é aplicado quando o usuário inicia uma nova busca antes do término da anterior.
  4. O cleanup do WebSocket da `CategoryPage` é executado ao desmontar o componente, sem conexões pendentes ou logs intercalados após a saída.

**Plans**: 3 plans (2 waves)

**Wave 1** *(parallel; disjoint files)*

- [x] 28-01-PLAN.md — WS cleanup useEffect na CategoryPage (D-02/D-09, prerequisito; App.tsx)
- [x] 28-02-PLAN.md — instalar zustand@5.0.14 + signal?: AbortSignal no ApiClient + criar searchStore.ts (useSearchStore)

**Wave 2** *(blocked on Wave 1; App.tsx ownership + consome o store)*

- [x] 28-03-PLAN.md — migrar SearchPage + CrossMarketplacePage para useSearchStore + toast de conclusão + UAT manual dos 4 critérios

**UI hint**: yes

---

#### Phase 29: Frete via Checkout nos Sites VTEX

**Goal**: O sistema calcula preço e prazo de frete via checkout simulation para os sites de marca VTEX que hoje retornam vazio, com unidade corretamente convertida (centavos para reais) e detecção de frete grátis.
**Depends on**: Phase 26 (as marcas VTEX precisam estar cadastradas para que o frete seja testável contra sites reais; Phase 25 garante que apenas sites VTEX chegam ao engine correto)
**Requirements**: FRET-05
**Success Criteria** (what must be TRUE):

  1. Uma busca por produto em qualquer site de marca VTEX onboardado retorna `shipping_cost` com valor em reais (não em centavos) e `shipping_time` com prazo de entrega — campos que hoje ficam vazios/nulos.
  2. Quando o frete é gratuito, o campo `is_free_shipping` é `true` e `shipping_cost` é `0.0` — distinguível de um frete não calculado.
  3. O contrato de unidade (centavos→reais, divisão por 100) está documentado em `BaseEngine.calculate_shipping` e coberto por ao menos um teste de range que detecta regressão de unidade (ex.: valor acima de R$ 1.000 sem frete grátis é suspeito).

**Plans**: TBD

## Progress

**Execution Order:**
Phases ativas executam em ordem numérica: 25 → 26 → 27 → 28 → 29 → 30

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 19. Clean Code & Refatoração Base | v1.10 | - | Complete | shipped |
| 20. Motor de Relevância - Decision Gates | v1.10 | - | Complete | shipped |
| 21. IA Visual - Batching e Concorrência | v1.10 | - | Complete | shipped |
| 22. Gate de Marca | v1.11 | 1/1 | Complete | 2026-06-13 |
| 23. Discriminação de Modelo | v1.11 | 2/2 | Complete | 2026-06-13 |
| 24. Exportação Excel da Busca por SKU | v1.12 | 3/3 | Complete | 2026-06-15 |
| 25. Fundação de Motores | v2.0 | 4/4 | Complete    | 2026-06-18 |
| 26. Onboarding das 5 Marcas VTEX | v2.0 | 2/2 | Complete   | 2026-06-19 |
| 27. Histórico Completo + Gestão de Marcas na UI | v2.0 | 4/4 | Complete    | 2026-06-20 |
| 28. Persistência da Busca Entre Abas | v2.0 | 3/3 | Complete    | 2026-06-22 |
| 29. Frete via Checkout nos Sites VTEX | v2.0 | 0/? | Not started | - |
