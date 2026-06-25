# Roadmap: Intelligence Scraper

## Milestones

- ✅ **v1.10 Refatoração do Motor de Relevância & Performance da IA** - Phases 19-21 (shipped)
- ✅ **v1.11 Precisão da Busca por SKU** - Phases 22-23 (shipped)
- ✅ **v1.12 Exportação Excel da Busca por SKU** - Phase 24 (shipped)
- ✅ **v2.0 Cobertura de Concorrentes & Confiabilidade** - Phases 25-29 (shipped — ver `.planning/milestones/v2.0-ROADMAP.md`)
- 🚧 **v3.0 Expansão Multi-Plataforma de Concorrentes & Frete VTEX** - Phases 30-35 (active)

**Milestone Goal (v3.0):** Onboardar marcas concorrentes que rodam fora do VTEX, entregar o cálculo de frete VTEX pendente do v2.0 e automatizar a extração dos banners desktop com publicação no SharePoint.

## Overview

Com a fundação de motores (engine factory + `detect_engine` + flag `is_active`) já shipped no v2.0, o v3.0 expande a cobertura competitiva para plataformas que hoje caem em `unknown`. A pedra fundamental é ensinar `detect_engine` a reconhecer `sfcc` e `wake` (Phase 30): sem isso, Lacoste/HugoBoss/Richards seriam auto-desativadas no cadastro. Com a detecção pronta, dois engines novos são construídos em paralelo lógico: SFCC público (Phase 31, caminho validado por spike — só catálogo + preço) e Wake Commerce (Phase 32, **precedido de um spike de confirmação do token GraphQL** antes de comprometer o engine completo). O frete VTEX (Phase 33) é ortogonal aos engines novos — usa o caminho interno do `VtexApiClient` já existente — e pode rodar em paralelo.

O milestone também incorpora a frente de banners, validada por um protótipo executado nos 13 sites ativos. A Phase 34 transforma o spike em um motor de extração desktop observável, cobrindo todos os slides de imagem do hero e reconhecendo vídeos intercalados. A Phase 35 publica os arquivos e metadados no SharePoint; começa por um gate de conectividade, destino e permissões, pois essas informações são dependências externas ainda não disponíveis.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Phases 19-29 pertencem a milestones CONCLUÍDOS (v1.10-v2.0). As phases ativas do v3.0 são **30-36**.

- [x] **Phase 30: Detecção de Engine SFCC & Wake** - `detect_engine` reconhece e rotula `sfcc` e `wake` (em vez de `unknown`), liberando o cadastro dessas marcas com o engine correto (COMP-05) (completed 2026-06-23)
- [x] **Phase 31: Engine SFCC (Browser Público) — Lacoste & HugoBoss** - Onboarding e busca das marcas SFCC via extração pública browser-rendered (JSON-LD / OpenGraph): catálogo + preço apenas (COMP-03) (completed 2026-06-24)
- [x] **Phase 32: Engine Wake Commerce — Richards** - Spike de confirmação do GraphQL + `TCS-Access-Token` e, se validado, engine Wake completo para onboarding e busca da Richards (COMP-04) (completed 2026-06-25)
- [ ] **Phase 33: Frete via Checkout nos Sites VTEX** - Cálculo de preço e prazo de frete via checkout simulation nos sites de marca VTEX, com contrato de unidade (centavos→reais) documentado e detecção de frete grátis (FRET-05)
- [x] **Phase 34: Extração de Banners Desktop** - Motor reutilizável percorre as marcas ativas, coleta todos os slides de imagem do carrossel principal e produz arquivos originais, metadados e relatório visual auditável (BANNER-01, BANNER-02, BANNER-03, BANNER-04) (completed 2026-06-23)
- [ ] **Phase 35: Publicação de Banners no SharePoint** - Configuração segura do destino e publicação idempotente dos banners e metadados, com resultado por arquivo e gate inicial de acesso/permissões (BANNER-05, BANNER-06)
- [x] **Phase 36: Onboarding das Marcas Concorrentes Restantes — Lacoste (anti-bot) & Zara** - Gate de viabilidade executado: Lacoste NO-GO no envelope público stealth permitido, mantida inativa; Zara reavaliada e promovida para fase futura dedicada (completed 2026-06-25)

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

**Plans**: 3 plans
**Wave 1**

- [x] 30-01-PLAN.md — detect_engine: flip Wake branch to "wake" + last-resort SFCC browser probe (demandware markers)
- [x] 30-02-PLAN.md — EngineFactory.get_engine guard: raise NotImplementedError for sfcc/wake (no silent VTEX fallback)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 30-03-PLAN.md — test_engine_detection.py: regression base + SFCC/Wake/anti-false-positive + SC-3 stays-active

### Phase 31: Engine SFCC (Browser Público) — Lacoste & HugoBoss

**Goal**: Um operador consegue onboardar Lacoste e HugoBoss e buscar seus produtos (catálogo + preço) via extração pública browser-rendered (JSON-LD / OpenGraph), com o novo `SFCCEngine` plugado na `EngineFactory` — sem frete/checkout, estoque por CEP, OCAPI/SCAPI ou bypass de anti-bot.
**Depends on**: Phase 30 (a detecção precisa rotular `sfcc` para que Lacoste/HugoBoss sejam cadastradas com o engine certo em vez de inativadas)
**Requirements**: COMP-03
**Success Criteria** (what must be TRUE):

  1. Com Lacoste e HugoBoss cadastradas, uma busca por produto retorna itens reais (título, URL e preço) para cada uma das duas marcas — extraídos de JSON-LD / OpenGraph na página renderizada, não de HTTP direto (que é bloqueado por 403).
  2. O `SFCCEngine` está registrado na `EngineFactory` e é selecionado automaticamente para marcas com `engine="sfcc"`, implementando os métodos do `BaseEngine` necessários para catálogo e busca.
  3. O preço extraído de cada produto SFCC é exibido na unidade correta (reais) nos resultados da busca, consistente com os demais engines.
  4. `calculate_shipping` do `SFCCEngine` não tenta calcular frete (escopo público sem checkout): retorna ausência de frete de forma explícita, sem erro e sem badge de "Frete Grátis" indevido.

**Plans**: 3 plans

**Wave 0**

- [x] 31-01-PLAN.md — sfcc_parser.py (BR price `parse_price_br` + JSON-LD/OG extraction) + test_sfcc_engine.py scaffold; Backstage-standards prerequisite gate

**Wave 1** *(blocked on Wave 0)*

- [x] 31-02-PLAN.md — SFCCEngine search core (native search render → PDP enrichment, Semaphore(3), calculate_shipping→None) + factory.py guard split (SC-1..SC-4)

**Wave 2** *(blocked on Wave 1)*

- [x] 31-03-PLAN.md — discover_categories()/get_catalog() reais com fallback de stub gracioso (D-05/D-06)

### Phase 32: Engine Wake Commerce — Richards

**Goal**: Confirmar empiricamente o fluxo GraphQL + `TCS-Access-Token` da Wake contra a Richards (spike gating) e, uma vez validado, entregar o `WakeEngine` plugado na `EngineFactory` para que o operador onboarde e busque produtos da Richards.
**Depends on**: Phase 30 (a detecção precisa rotular `wake` para cadastrar a Richards com o engine certo). O build do engine é internamente gated pelo spike de confirmação (Wave 0) antes do commit do engine completo.
**Requirements**: COMP-04
**Success Criteria** (what must be TRUE):

  1. **Gate (Wave 0):** Um spike de confirmação demonstra, contra a Richards (ou Shop2gether), que o endpoint GraphQL da Wake responde com produtos quando recebe o header `TCS-Access-Token` da loja — produzindo uma decisão registrada de GO/NO-GO antes de qualquer código do engine completo.
  2. Com a Richards cadastrada e o token configurado, uma busca por produto retorna itens reais (título, URL e preço) via a API GraphQL da Wake — não via o caminho VTEX (que retorna 0 produtos para lojas Wake).
  3. O `WakeEngine` está registrado na `EngineFactory` e é selecionado automaticamente para marcas com `engine="wake"`, enviando o `TCS-Access-Token` por loja em cada requisição GraphQL.
  4. O `TCS-Access-Token` da Richards é configurado por loja (não hardcoded global) e a ausência/erro de token produz uma falha clara e diagnosticável, não 0 produtos silenciosos.

**Plans**: 3 plans

**Wave 0** *(GATE — spike de confirmação GO/NO-GO; gateia Wave 1+)*

- [x] 32-01-PLAN.md — spike 007-wake-graphql-token-confirmation: experiment.py + REPORT.md com veredito GO/NO-GO (token GraphQL+TCS-Access-Token; Richards/Shop2gether) (SC-1)

**Wave 1** *(blocked on Wave 0 — só executa se REPORT.md = GO; em NO-GO o WakeEngine é deferido por D-03)*

- [x] 32-02-PLAN.md — WakeEngine: campo wake_access_token (models.py) + engine (busca GraphQL + token por loja + stubs) + wiring na EngineFactory (SC-2/SC-3/SC-4) (completed 2026-06-25)

**Wave 2** *(blocked on Wave 1)*

- [x] 32-03-PLAN.md — test_wake_engine.py (SC-2/SC-3/SC-4/D-06/D-08) + remoção do guard obsoleto test_factory_wake_still_raises + regressão da suite completa (completed 2026-06-25)

### Phase 33: Frete via Checkout nos Sites VTEX

**Goal**: O sistema calcula preço e prazo de frete via checkout simulation para os sites de marca VTEX que hoje retornam vazio, com unidade corretamente convertida (centavos para reais) e detecção de frete grátis — usando o caminho interno do `VtexApiClient` (não o hook `calculate_shipping`, por decisão arquitetural do v2.0).
**Depends on**: Nothing (ortogonal aos engines novos; opera sobre marcas VTEX já onboardadas no v2.0 e o `VtexApiClient` existente). Pode rodar em paralelo com as Phases 30-32.
**Requirements**: FRET-05
**Success Criteria** (what must be TRUE):

  1. Uma busca por produto em qualquer site de marca VTEX onboardado retorna `shipping_cost` com valor em reais (não em centavos) e `shipping_time` com prazo de entrega — campos que hoje ficam vazios/nulos.
  2. Quando o frete é gratuito, o campo `is_free_shipping` é `true` e `shipping_cost` é `0.0` — distinguível de um frete não calculado (que permanece nulo, não `0.0`).
  3. O contrato de unidade (centavos→reais, divisão por 100) está documentado no caminho de frete VTEX e coberto por ao menos um teste de range que detecta regressão de unidade (ex.: valor acima de R$ 1.000 sem frete grátis é suspeito).

**Plans**: 3 plans
**Wave 1**

- [ ] 33-01-PLAN.md — Parser puro de frete (vtex_shipping.py) + evolução aditiva dos modelos (shipping_options) + testes test-first

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 33-02-PLAN.md — Rewire de _fetch_shipping (SKU+seller, retry único, estados explícitos, shipping_options) + endpoint read-only de CEP padrão + testes de contrato

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 33-03-PLAN.md — Frontend: loader de config, init único de CEP, bloqueio de CEP inválido, render de todas as modalidades (Truck/CheckCircle2) com fallback legado

### Phase 34: Extração de Banners Desktop

**Goal**: Um operador executa, sob demanda, a extração dos banners desktop de todas as marcas ativas e recebe todos os slides de imagem do carrossel principal da primeira tela, com arquivos originais, metadados e evidências visuais — sem falsos positivos de logos/produtos e sem parar o lote quando um site falha.
**Depends on**: Nothing (ortogonal aos engines e ao frete; parte do spike validado em `testes/extrair_banners.py` e da infraestrutura Playwright existente)
**Requirements**: BANNER-01, BANNER-02, BANNER-03, BANNER-04
**Success Criteria** (what must be TRUE):

  1. Uma execução desktop (`1366×768`) percorre todas as marcas ativas cadastradas e extrai cada slide de imagem do primeiro grande carrossel/hero, inclusive slides ocultos ou carregados ao avançar — sem incluir logos, cards de produto ou seções inferiores.
  2. Cada item extraído preserva o arquivo original e registra marca, URL de origem, link de destino, texto alternativo, dimensões, tipo de mídia, data da coleta e hash SHA-256.
  3. Carrosséis com vídeos intercalados continuam sendo percorridos até o final; os vídeos são contabilizados no resultado, mas não são classificados nem baixados como banners de imagem.
  4. O lote produz JSON, CSV, galeria visual e screenshot por site; uma falha de navegação ou download fica atribuída à marca/item e não interrompe as demais.
  5. O conjunto de referência do spike permanece reproduzível: os 13 sites ativos completam a execução e os casos VTEX/Shopify representativos passam por conferência visual sem falsos positivos conhecidos.

**Plans**: TBD

### Phase 35: Publicação de Banners no SharePoint

**Goal**: O operador configura um destino SharePoint e publica os banners desktop coletados e seus metadados de forma segura e idempotente, organizados por marca e com rastreabilidade de sucesso ou falha por arquivo.
**Depends on**: Phase 34 (a publicação consome o contrato estável de arquivos e metadados do motor de extração). O build começa por um gate de confirmação do site/biblioteca de destino, credenciais e permissões disponíveis.
**Requirements**: BANNER-05, BANNER-06
**Success Criteria** (what must be TRUE):

  1. **Gate de acesso:** um teste de conectividade confirma o site/biblioteca de destino e as permissões necessárias antes da implementação completa; ausência de credenciais ou permissão gera diagnóstico explícito.
  2. Segredos e identificadores sensíveis do SharePoint são fornecidos por configuração externa e não aparecem hardcoded no repositório, JSON/CSV, galeria ou logs.
  3. Banners originais e metadados são publicados no destino configurado com organização por marca; o relatório local registra o resultado do envio por item.
  4. Reexecutar a publicação com o mesmo SHA-256 não cria duplicatas; arquivos novos ou alterados são distinguíveis e publicados conforme a política documentada.
  5. Uma falha no SharePoint não apaga nem invalida a coleta local, permitindo correção de acesso e nova tentativa sem raspar os sites novamente.

**Plans**: TBD

## Progress

**Execution Order:**
Phases ativas executam em ordem numérica: 30 → 31 → 32 → 33 → 34 → 35 → 36. Phase 33 (frete VTEX) e Phase 34 (extração de banners) são independentes das Phases 30-32 e podem ser paralelizadas; Phase 31 e Phase 32 dependem da Phase 30. Phase 35 depende da Phase 34 e começa por um gate de acesso ao SharePoint. Phase 36 depende das Phases 31/32 e é gateada internamente pelo spike 36-01; 36-02/36-03 só rodam em GO. O build do engine na Phase 32 é gated pelo spike de confirmação (Wave 0) interno.

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 19-21. v1.10 (Relevância & IA) | v1.10 | - | Complete | shipped |
| 22-23. v1.11 (Precisão SKU) | v1.11 | - | Complete | shipped |
| 24. Exportação Excel | v1.12 | - | Complete | shipped |
| 25-29. v2.0 (Concorrentes & Confiabilidade) | v2.0 | - | Complete | shipped |
| 30. Detecção de Engine SFCC & Wake | v3.0 | 3/3 | Complete    | 2026-06-23 |
| 31. Engine SFCC (Browser Público) | v3.0 | 3/3 | Complete   | 2026-06-24 |
| 32. Engine Wake Commerce — Richards | v3.0 | 3/3 | Complete    | 2026-06-25 |
| 33. Frete via Checkout nos Sites VTEX | v3.0 | 0/? | Not started | - |
| 34. Extração de Banners Desktop | v3.0 | 4/4 | Complete   | 2026-06-23 |
| 35. Publicação de Banners no SharePoint | v3.0 | 0/? | Not started | - |
| 36. Onboarding das Marcas Concorrentes Restantes | v3.0 | 3/3 | Complete (NO-GO) | 2026-06-25 |

### Phase 36: Onboarding das Marcas Concorrentes Restantes — Lacoste (anti-bot) & Zara

**Goal**: Habilitar a busca ao vivo da **Lacoste** (SFCC) — hoje cadastrada porém **inativa** por bloqueio anti-bot (HTTP direto 403 e "Access Denied" 296B mesmo no Playwright headless, na home e na busca) — por meio de uma estratégia anti-bot (browser stealth / proxy residencial / fingerprint real), iniciando por um **gate de viabilidade GO/NO-GO** antes de investir no fetcher completo; e **reavaliar** a viabilidade pública da **Zara/Inditex**. Entregar a Lacoste ativa com ≥1 produto (título + URL + preço) na busca OU registrar formalmente a inviabilidade com evidência.
**Requirements**: COMP-03 (gap: Lacoste ao vivo — Hugo Boss já entregue como VTEX, Richards como Wake), COMP-FUT-03 (Zara/Inditex — reavaliar)
**Depends on**: Phase 31 (SFCCEngine + correção double-www) e Phase 32 (padrão de onboarding por evidência). Ortogonal às Phases 33 (frete VTEX) e 35 (SharePoint).
**Plans:** 3 plans
**Success Criteria** (o que deve ser VERDADE):

- Gate de viabilidade anti-bot da Lacoste com veredito **GO/NO-GO** documentado ANTES de qualquer investimento no fetcher completo (espelha o padrão spike-gate da Phase 32).
- Em **GO**: Lacoste `is_active=True` e `search_all_brands("camisa", brands=["lacoste"])` retorna ≥1 produto com título + URL (domínio Lacoste) + preço; suíte de testes verde, sem regressão nos engines existentes.
- Em **NO-GO**: inviabilidade registrada com evidência (resposta do anti-bot, técnicas testadas) e Lacoste permanece inativa com a decisão documentada.
- Zara/Inditex reavaliada: caminho público validado (→ promover a requisito ativo) OU mantida deferida (COMP-FUT-03) com razão atualizada.
- Escopo: catálogo + preço apenas; sem frete/checkout/estoque por CEP. Acesso restrito a dados públicos de catálogo (sem evasão para fins maliciosos).

**Outcome (2026-06-25):** Lacoste `NO-GO` dentro do envelope permitido (baseline e stealth retornaram HTTP 403, 296B, `Access Denied`); `lacoste.is_active=false` permanece. Zara carregou home/search públicos e deve virar fase futura dedicada para validar contrato produto+preço antes de qualquer engine.

Plans:

- [x] 36-01-PLAN.md — Gate Lacoste/Zara executado: REPORT.md com Lacoste `NO-GO` e Zara `PROMOVER_REQUISITO_FUTURO`
- [x] 36-02-PLAN.md — Skipped por gate: Lacoste `NO-GO`, nenhum SFCCAntiBotFetcher implementado
- [x] 36-03-PLAN.md — Skipped por gate: sem ativação, `lacoste.is_active=false`
