# Phase 25: Fundação de Motores - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-18
**Phase:** 25-funda-o-de-motores
**Areas discussed:** Nenhuma — usuário optou por não discutir as áreas cinzentas apresentadas

---

## Áreas cinzentas apresentadas (multiSelect)

Quatro áreas foram identificadas e apresentadas para seleção. O usuário respondeu via "Other": **"Esses itens não precisam ser discutidos"** — nenhuma área foi selecionada para discussão.

| Área apresentada | Descrição | Selecionada |
|------------------|-----------|-------------|
| Cadastro com engine 'unknown' | Bloquear o cadastro (erro) vs salvar a marca como inativa/sinalizada | |
| O que conta como 'não suportada' | Falha transitória → unknown e exclui, ou tratar diferente; probe Wake positivo vs só parar de assumir VTEX | |
| Desativar e trabalho em andamento | Cancelar monitores/jobs já agendados, ou só excluir dos próximos ciclos | |
| Escopo do chokepoint active_only | Quais consumidores filtram inativas e onde inativas ainda aparecem | |

**User's choice:** "Esses itens não precisam ser discutidos" (nenhuma área selecionada).
**Notes:** O usuário confia nos success criteria do ROADMAP. Todas as decisões foram tomadas por discrição do Claude e registradas em CONTEXT.md como D-01..D-08, com rationale derivado dos critérios + leitura do código.

---

## Claude's Discretion

Todas as decisões D-01..D-08 (em CONTEXT.md) foram tomadas por discrição do Claude, por escolha explícita do usuário de não discutir:

- **Detecção (COMP-02):** fallback final vira `"unknown"`; probe Wake positivo retornando `"unknown"`; falha transitória → `"unknown"` apenas no add-time (sem reclassificação automática).
- **Cadastro unknown:** salvar como inativa/sinalizada (não bloquear com erro).
- **Desativar:** apenas seta o flag; exclusão via chokepoint no próximo ciclo; sem cancelamento ativo de monitores.
- **Endpoint:** `PATCH /brands/{key}/active` com body `{is_active: bool}` (set explícito, idempotente).
- **Chokepoint:** `list_brands(active_only=False)` default; busca/scheduler/monitor/export passam `True`; gestão UI mantém `False`.

## Deferred Ideas

- Engine Wake Commerce real (Richards/Shop2gether) → COMP-FUT-01 (v3.0).
- Engines SFCC (Lacoste/Hugo Boss) e Inditex/Zara → COMP-FUT-02/03; spikes 003-006 já exploraram SFCC público via browser.
- Reclassificação automática de engine de marcas já cadastradas — fora do escopo.
- Painel de diagnóstico de saúde por categoria → Phase 29 (DIAG-01/02).
- UI de gestão (toggle ativar/desativar) → Phase 27 (MGMT-02).
