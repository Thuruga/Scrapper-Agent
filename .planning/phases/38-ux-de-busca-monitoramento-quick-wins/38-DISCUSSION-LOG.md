# Phase 38: UX de Busca & Monitoramento — Quick Wins - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-01
**Phase:** 38-ux-de-busca-monitoramento-quick-wins
**Areas discussed:** Cálculo do preço de promoção no monitor, Comportamento após a 1ª varredura automática (UX-08), Textos de toast/tooltip marcados como suposição

---

## Cálculo do preço de promoção no monitor

| Pergunta | Opções | Selecionada |
|---|---|---|
| Detecção de mudança deve considerar preço com desconto? | Preço efetivo (com desconto) / Manter só preço cheio / Deixe a Claude decidir | ✓ Preço efetivo (com desconto) |
| Monitores já ativos sem histórico de desconto — aceitável só popular na próxima checagem? | Sim, popular só na próxima checagem / Forçar recheck imediato / Deixe a Claude decidir | ✓ Sim, popular só na próxima checagem |
| WebSocket `price_update` deve incluir `price_discount`? | Incluir no push do WebSocket / Só no próximo GET /monitors / Deixe a Claude decidir | ✓ Incluir no push do WebSocket |

**Notas:** Descoberta feita durante a discussão (não era conhecida de antemão): `price_monitor_service.py` grava `price_full` como `last_price` e nunca captura `price_discount`; a detecção de mudança hoje ignora promoções que não alteram o preço cheio. Isso elevou a área de "ajuste visual" para "correção de comportamento de monitoramento".

---

## Comportamento após a 1ª varredura automática (UX-08)

| Pergunta | Opções | Selecionada |
|---|---|---|
| O que acontece quando a varredura automática termina? | Abre o modal de produtos automaticamente / Só atualiza a linha na tabela / Deixe a Claude decidir | ✓ Abre o modal de produtos automaticamente |
| Operador fica bloqueado enquanto a varredura roda? | Modal fecha na hora, varredura em background / Modal só fecha ao terminar / Deixe a Claude decidir | ✓ Modal fecha na hora, varredura em background |

**Notas:** O UI-SPEC.md havia adotado a opção mais conservadora (só atualizar status na tabela) como mínimo aceitável, deixando a abertura automática do modal como "enhancement se trivial". A discussão travou a versão mais explícita, alinhada à letra do requisito UX-08 e do success criterion 5 do ROADMAP.

---

## Textos de toast/tooltip marcados como suposição

| Pergunta | Opções | Selecionada |
|---|---|---|
| Tooltip do ícone de histórico: "Ver histórico de buscas"? | Sim / Deixe a Claude decidir | ✓ Sim, usar como está |
| Toasts de sucesso/falha do auto-sweep estão bons? | Sim, usar os dois como estão / Deixe a Claude decidir | ✓ Sim, usar os dois como estão |
| Erro inline do SKU inválido está bom? | Sim, usar como está / Deixe a Claude decidir | ✓ Sim, usar como está |

**Notas:** Todas as três strings marcadas "(assumption — confirm)" no `38-UI-SPEC.md` foram confirmadas sem alteração.

---

## Claude's Discretion

- Nomes exatos dos novos campos de preço no backend (`PriceMonitorConfig`/`PriceHistoryEntry`), desde que `last_price` continue sendo o preço efetivo.
- Orquestração interna do fluxo fechar-modal → spinner → sweep em background → abrir modal de produtos.
- Qual endpoint/serviço de scan existente é reaproveitado para o auto-sweep.
- Todos os detalhes visuais/layout já travados em `38-UI-SPEC.md` (UX-01, UX-06, UX-07, COMP-08) — fora do escopo desta discussão.

## Deferred Ideas

- `cap-search-history-list.md` (paginação do histórico de buscas) — capacidade nova, não parte da Phase 38.
- `audit-category-mappings-all-brands.md`, `reforcar-discriminacao-modelo.md`, `zara-comp07-deferred.md`, `hugoboss-vtex-io-category-scan.md` — avaliados via `todo.match-phase`, sem relação real com o escopo desta phase; usuário confirmou manter todos fora.
