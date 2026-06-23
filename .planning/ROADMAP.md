# Roadmap: Intelligence Scraper

## Milestones

- ✅ **v1.10 Refatoração do Motor de Relevância & Performance da IA** - Phases 19-21 (shipped)
- ✅ **v1.11 Precisão da Busca por SKU** - Phases 22-23 (shipped)
- ✅ **v1.12 Exportação Excel da Busca por SKU** - Phase 24 (shipped)
- ✅ **v2.0 Cobertura de Concorrentes & Confiabilidade** - Phases 25-29 (shipped — ver `.planning/milestones/v2.0-ROADMAP.md`)
- 🚧 **v3.0 Expansão Multi-Plataforma de Concorrentes & Frete VTEX** - Phases 30-33 (active)

**Milestone Goal (v3.0):** Onboardar marcas concorrentes que rodam fora do VTEX — construindo dois engines novos (SFCC público via browser e Wake Commerce via GraphQL) — e entregar o cálculo de frete VTEX que ficou pendente do v2.0.

## Overview

Com a fundação de motores (engine factory + `detect_engine` + flag `is_active`) já shipped no v2.0, o v3.0 expande a cobertura competitiva para plataformas que hoje caem em `unknown`. A pedra fundamental é ensinar `detect_engine` a reconhecer `sfcc` e `wake` (Phase 30): sem isso, Lacoste/HugoBoss/Richards seriam auto-desativadas no cadastro. Com a detecção pronta, dois engines novos são construídos em paralelo lógico: SFCC público (Phase 31, caminho validado por spike — só catálogo + preço) e Wake Commerce (Phase 32, **precedido de um spike de confirmação do token GraphQL** antes de comprometer o engine completo). O frete VTEX (Phase 33) é ortogonal aos engines novos — usa o caminho interno do `VtexApiClient` já existente — e pode rodar em paralelo.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Phases 19-29 pertencem a milestones CONCLUÍDOS (v1.10-v2.0). As phases ativas do v3.0 são **30-33**.

- [ ] **Phase 30: Detecção de Engine SFCC & Wake** - `detect_engine` reconhece e rotula `sfcc` e `wake` (em vez de `unknown`), liberando o cadastro dessas marcas com o engine correto (COMP-05)
- [ ] **Phase 31: Engine SFCC (Browser Público) — Lacoste & HugoBoss** - Onboarding e busca das marcas SFCC via extração pública browser-rendered (JSON-LD / OpenGraph): catálogo + preço apenas (COMP-03)
- [ ] **Phase 32: Engine Wake Commerce — Richards** - Spike de confirmação do GraphQL + `TCS-Access-Token` e, se validado, engine Wake completo para onboarding e busca da Richards (COMP-04)
- [ ] **Phase 33: Frete via Checkout nos Sites VTEX** - Cálculo de preço e prazo de frete via checkout simulation nos sites de marca VTEX, com contrato de unidade (centavos→reais) documentado e detecção de frete grátis (FRET-05)

## Phase Details

### Phase 30: Detecção de Engine SFCC & Wake

**Goal**: Ao cadastrar uma marca SFCC (Lacoste, HugoBoss) ou Wake (Richards), o sistema reconhece a plataforma e atribui o engine correto (`sfcc` / `wake`) em vez de cair em `unknown` e auto-desativar a marca — destravando o onboarding das Phases 31 e 32.
**Depends on**: Nothing (fundação do milestone; opera sobre `detect_engine` e `EngineFactory` já shipped no v2.0)
**Requirements**: COMP-05
**Success Criteria** (what must be TRUE):

  1. Ao chamar `detect_engine` para um domínio SFCC (ex.: Lacoste ou HugoBoss), o retorno é `"sfcc"` — não `"unknown"` nem `"vtex"`.
  2. Ao chamar `detect_engine` para o domínio da Richards (Wake), o retorno é `"wake"` — não `"unknown"` (que era o comportamento de fallback do v2.0 via `fbitsstatic.net`).
  3. Ao cadastrar uma marca via `POST /brands/` com engine `auto`, uma marca SFCC ou Wake é persistida com o engine detectado e **permanece ativa** (não é auto-desativada pela regra D-04 de engine desconhecido).
  4. Domínios que não são SFCC, Wake, VTEX nem Shopify continuam retornando `"unknown"` e sendo auto-desativados — a detecção nova não introduz falsos positivos.

**Plans**: TBD

### Phase 31: Engine SFCC (Browser Público) — Lacoste & HugoBoss

**Goal**: Um operador consegue onboardar Lacoste e HugoBoss e buscar seus produtos (catálogo + preço) via extração pública browser-rendered (JSON-LD / OpenGraph), com o novo `SFCCEngine` plugado na `EngineFactory` — sem frete/checkout, estoque por CEP, OCAPI/SCAPI ou bypass de anti-bot.
**Depends on**: Phase 30 (a detecção precisa rotular `sfcc` para que Lacoste/HugoBoss sejam cadastradas com o engine certo em vez de inativadas)
**Requirements**: COMP-03
**Success Criteria** (what must be TRUE):

  1. Com Lacoste e HugoBoss cadastradas, uma busca por produto retorna itens reais (título, URL e preço) para cada uma das duas marcas — extraídos de JSON-LD / OpenGraph na página renderizada, não de HTTP direto (que é bloqueado por 403).
  2. O `SFCCEngine` está registrado na `EngineFactory` e é selecionado automaticamente para marcas com `engine="sfcc"`, implementando os métodos do `BaseEngine` necessários para catálogo e busca.
  3. O preço extraído de cada produto SFCC é exibido na unidade correta (reais) nos resultados da busca, consistente com os demais engines.
  4. `calculate_shipping` do `SFCCEngine` não tenta calcular frete (escopo público sem checkout): retorna ausência de frete de forma explícita, sem erro e sem badge de "Frete Grátis" indevido.

**Plans**: TBD

### Phase 32: Engine Wake Commerce — Richards

**Goal**: Confirmar empiricamente o fluxo GraphQL + `TCS-Access-Token` da Wake contra a Richards (spike gating) e, uma vez validado, entregar o `WakeEngine` plugado na `EngineFactory` para que o operador onboarde e busque produtos da Richards.
**Depends on**: Phase 30 (a detecção precisa rotular `wake` para cadastrar a Richards com o engine certo). O build do engine é internamente gated pelo spike de confirmação (Wave 0) antes do commit do engine completo.
**Requirements**: COMP-04
**Success Criteria** (what must be TRUE):

  1. **Gate (Wave 0):** Um spike de confirmação demonstra, contra a Richards (ou Shop2gether), que o endpoint GraphQL da Wake responde com produtos quando recebe o header `TCS-Access-Token` da loja — produzindo uma decisão registrada de GO/NO-GO antes de qualquer código do engine completo.
  2. Com a Richards cadastrada e o token configurado, uma busca por produto retorna itens reais (título, URL e preço) via a API GraphQL da Wake — não via o caminho VTEX (que retorna 0 produtos para lojas Wake).
  3. O `WakeEngine` está registrado na `EngineFactory` e é selecionado automaticamente para marcas com `engine="wake"`, enviando o `TCS-Access-Token` por loja em cada requisição GraphQL.
  4. O `TCS-Access-Token` da Richards é configurado por loja (não hardcoded global) e a ausência/erro de token produz uma falha clara e diagnosticável, não 0 produtos silenciosos.

**Plans**: TBD

### Phase 33: Frete via Checkout nos Sites VTEX

**Goal**: O sistema calcula preço e prazo de frete via checkout simulation para os sites de marca VTEX que hoje retornam vazio, com unidade corretamente convertida (centavos para reais) e detecção de frete grátis — usando o caminho interno do `VtexApiClient` (não o hook `calculate_shipping`, por decisão arquitetural do v2.0).
**Depends on**: Nothing (ortogonal aos engines novos; opera sobre marcas VTEX já onboardadas no v2.0 e o `VtexApiClient` existente). Pode rodar em paralelo com as Phases 30-32.
**Requirements**: FRET-05
**Success Criteria** (what must be TRUE):

  1. Uma busca por produto em qualquer site de marca VTEX onboardado retorna `shipping_cost` com valor em reais (não em centavos) e `shipping_time` com prazo de entrega — campos que hoje ficam vazios/nulos.
  2. Quando o frete é gratuito, o campo `is_free_shipping` é `true` e `shipping_cost` é `0.0` — distinguível de um frete não calculado (que permanece nulo, não `0.0`).
  3. O contrato de unidade (centavos→reais, divisão por 100) está documentado no caminho de frete VTEX e coberto por ao menos um teste de range que detecta regressão de unidade (ex.: valor acima de R$ 1.000 sem frete grátis é suspeito).

**Plans**: TBD

## Progress

**Execution Order:**
Phases ativas executam em ordem numérica: 30 → 31 → 32 → 33. Phase 33 (frete VTEX) é independente das Phases 30-32 e pode ser paralelizada; Phase 31 e Phase 32 dependem ambas da Phase 30. O build do engine na Phase 32 é gated pelo spike de confirmação (Wave 0) interno.

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 19-21. v1.10 (Relevância & IA) | v1.10 | - | Complete | shipped |
| 22-23. v1.11 (Precisão SKU) | v1.11 | - | Complete | shipped |
| 24. Exportação Excel | v1.12 | - | Complete | shipped |
| 25-29. v2.0 (Concorrentes & Confiabilidade) | v2.0 | - | Complete | shipped |
| 30. Detecção de Engine SFCC & Wake | v3.0 | 0/? | Not started | - |
| 31. Engine SFCC (Browser Público) | v3.0 | 0/? | Not started | - |
| 32. Engine Wake Commerce — Richards | v3.0 | 0/? | Not started | - |
| 33. Frete via Checkout nos Sites VTEX | v3.0 | 0/? | Not started | - |
