---
phase: 28
slug: persist-ncia-da-busca-entre-abas
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-21
---

# Phase 28 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> **Nota:** este projeto frontend não possui infraestrutura de testes automatizados
> (`frontend/package.json` não tem Jest/Vitest/Playwright). Os 4 critérios de sucesso
> são validados por **UAT manual** com auxílio do DevTools. Ver RESEARCH.md › Arquitetura de Validação.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Nenhum instalado (sem Jest/Vitest/Playwright) |
| **Config file** | none — não há suíte de testes no frontend |
| **Quick run command** | `cd frontend && npm run build` (type-check + build como porta de fumaça) |
| **Full suite command** | UAT manual — ver "Manual-Only Verifications" |
| **Estimated runtime** | ~build em segundos; UAT manual ~5 min |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm run build` (garante que tipos e build continuam verdes)
- **After every plan wave:** UAT manual dos critérios afetados pela wave
- **Before `/gsd-verify-work`:** Build verde + UAT completo dos 4 critérios
- **Max feedback latency:** build em segundos; UAT ~5 min

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (WS cleanup) | — | 1 | PERS-01 / Critério #4 | — | N/A | manual + build | `cd frontend && npm run build` | N/A — manual | ⬜ pending |
| (zustand store) | — | 1 | PERS-01 / Critério #1,#3 | — | N/A | manual + build | `cd frontend && npm run build` | N/A — manual | ⬜ pending |
| (toast conclusão) | — | 2 | PERS-01 / Critério #2 | — | N/A | manual + build | `cd frontend && npm run build` | N/A — manual | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*A coluna Plan/Task ID será preenchida quando os PLAN.md forem gerados; o mapa acima reflete os agrupamentos de critério.*

---

## Wave 0 Requirements

- [ ] `frontend/package.json` — adicionar `zustand` (^5.0.14) às dependências (D-10)
- [ ] Nenhuma infraestrutura de testes a criar — todos os testes são UAT manuais

*Existing infrastructure: nenhuma suíte automatizada; `npm run build` é a única porta automatizada (type-check).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Estado da busca sobrevive à troca de aba | PERS-01 / Critério #1 | Sem framework de teste de UI; requer interação real de troca de aba | 1. Iniciar busca Comparativa longa (muitas marcas). 2. Com spinner ativo, trocar para outra aba. 3. Voltar para Comparativa. 4. Verificar: spinner ainda ativo, query/selectedBrands preservados, resultados não perdidos, busca **não** reiniciada. 5. Repetir para busca por SKU. |
| Toast de conclusão fora da aba | PERS-01 / Critério #2 | Notificação global visual; requer observação fora da aba de busca | 1. Iniciar busca Comparativa. 2. Navegar para outra aba antes de concluir. 3. Verificar: toast de sucesso aparece na aba atual. 4. Voltar à Comparativa: resultados disponíveis. |
| Sem duplo-fetch + cancelamento | PERS-01 / Critério #3 | Requer inspeção de DevTools Network | *Sem duplo-fetch:* DevTools › Network, iniciar busca, trocar aba, voltar → apenas **1** request `POST /search`. *Cancelamento:* iniciar busca A, antes de concluir iniciar busca B → request A = "Canceled", B prossegue, só toast de B aparece. |
| WS cleanup da CategoryPage | PERS-01 / Critério #4 | Requer inspeção de DevTools Console/Network-WS | 1. DevTools › Console. 2. Aba Categorias, iniciar varredura. 3. Com WS ativo (logs aparecendo), navegar para outra aba. 4. Verificar: **nenhum** log novo após a troca; Network › WS mostra conexão "Closed". |

---

## Validation Sign-Off

- [ ] Todos os comportamentos têm UAT manual definido (sem framework automatizado disponível)
- [ ] Sampling continuity: `npm run build` verde após cada task
- [ ] Wave 0 cobre a instalação do zustand
- [ ] No watch-mode flags
- [ ] Feedback latency: build em segundos
- [ ] `nyquist_compliant: true` set in frontmatter (após sign-off)

**Approval:** pending
