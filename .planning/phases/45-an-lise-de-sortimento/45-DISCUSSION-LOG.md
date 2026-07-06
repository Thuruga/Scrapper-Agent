# Phase 45: Análise de Sortimento - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-05
**Phase:** 45-Análise de Sortimento
**Areas discussed:** Persistência analítica, Fonte das categorias, Recorte do relatório, Superfície de consumo, Comparação entre snapshots

---

## Persistência analítica

| Option | Description | Selected |
|--------|-------------|----------|
| JSON como fonte de verdade | Mantém o veto ao SQLite e segue o padrão atual de artefatos locais. | ✓ |
| SQLite como fonte de verdade | Reabre a decisão da Phase 37 para consultas históricas mais pesadas. | |
| Híbrido | SQLite para consulta/comparação e JSON para debug/export. | |
| Outro | Resposta livre. | |

**User's choice:** JSON como fonte de verdade  
**Notes:** Follow-up decisions captured in this area: um arquivo por categoria por execução; lookup do snapshot anterior via nome canônico + manifesto/índice; snapshot guarda agregados + evidência mínima, sem catálogo completo persistido.

---

## Fonte das categorias

| Option | Description | Selected |
|--------|-------------|----------|
| Reusar exatamente as categorias monitoradas | Sortimento lê direto de `monitored_categories.json`. | |
| Lista própria de categorias de sortimento | Cadastro totalmente separado do monitor. | |
| Híbrido | Lista própria de sortimento, alimentada a partir do monitor. | ✓ |
| Outro | Resposta livre. | |

**User's choice:** Híbrido  
**Notes:** Follow-up decisions captured in this area: sincronização automática one-way a partir do monitor; categorias sincronizadas entram no cadastro de sortimento desativadas por padrão.

---

## Recorte do relatório

| Option | Description | Selected |
|--------|-------------|----------|
| Conjunto enxuto e padronizado | Focar em poucas dimensões de alto valor analítico. | ✓ |
| Quase tudo que vier da Phase 37 | Incluir o máximo de atributos canônicos possível. | |
| Configuração por categoria | Cada categoria define suas próprias dimensões principais. | |
| Outro | Resposta livre. | |

**User's choice:** Conjunto enxuto e padronizado  
**Notes:** Follow-up decisions captured in this area: v1 com `cor + tamanho + composição`; valores ausentes entram como bucket explícito `não informado`.

---

## Superfície de consumo

| Option | Description | Selected |
|--------|-------------|----------|
| Endpoint/JSON exportável primeiro | Entrega backend antes de UI. | |
| Tela na UI já na primeira versão | A feature já nasce orientada ao operador final. | ✓ |
| Ambos na mesma fase | Entrega backend + UI de forma simultânea como escopo principal. | |
| Outro | Resposta livre. | |

**User's choice:** Tela na UI já na primeira versão  
**Notes:** Follow-up decisions captured in this area: a tela será um dashboard visual com cards e gráficos; o conteúdo deve combinar deltas entre snapshots com a distribuição atual; a superfície será uma nova aba/página própria de sortimento.

---

## Comparação entre snapshots

| Option | Description | Selected |
|--------|-------------|----------|
| Último vs anterior | Baseline simples e rápido para leitura recorrente. | ✓ |
| Escolha manual de dois snapshots | Comparação totalmente livre já na experiência inicial. | |
| Ambos | Abre em último vs anterior, mas permite trocar para qualquer par. | |
| Outro | Resposta livre. | |

**User's choice:** Último vs anterior  
**Notes:** Follow-up decisions captured in this area: sem snapshot anterior, mostrar `baseline inicial`; deltas em absoluto + percentual; cálculo principal por dimensão separada, não por combinações cartesianas.

---

## the agent's Discretion

- Esquema exato dos snapshots JSON e do manifesto/índice.
- Serviço/backend owner da sincronização one-way e da geração dos snapshots.
- Nomes finais dos endpoints, tipos TypeScript e layout visual detalhado dos cards/gráficos.
- Formato exato da evidência mínima persistida em cada snapshot.

## Deferred Ideas

- Drill-down futuro por combinações de dimensões (`cor + tamanho + composição`).
- Comparação arbitrária entre snapshots fora do padrão `último vs anterior`.
- Primeira versão backend-only/export-only, sem UI dedicada.
