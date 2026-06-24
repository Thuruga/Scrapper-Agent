# Phase 33: Frete via Checkout nos Sites VTEX - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-24
**Phase:** 33-Frete via Checkout nos Sites VTEX
**Areas discussed:** Uso do CEP, Escolha da entrega, Falhas e indisponibilidade

---

## Uso do CEP

| Decision | Options considered | Selected |
|----------|--------------------|----------|
| Empty field | Visible/editable default; explicit only; silent default | Visible/editable `DEFAULT_CEP` |
| Invalid CEP | Block search; search without freight; restore default | Block search with clear error |
| Lifetime of edited CEP | Session; browser persistence; one search | Session only |
| Trigger | Automatic; toggle; after results | Automatic on every search |

**User's choice:** CEP padrão visível e editável, validação bloqueante, memória apenas na sessão e cálculo automático.

**Notes:** O usuário também determinou que preço do produto e frete fiquem separados, sem soma em valor final. Ao esclarecer que o comparativo por SKU é outro fluxo, pediu padronização em toda a aplicação; essa mudança transversal foi registrada como follow-up fora da Phase 33.

---

## Escolha da entrega

| Decision | Options considered | Selected |
|----------|--------------------|----------|
| Options shown | Cheapest home delivery; fastest home delivery; all options | All home-delivery options; exclude pickup |
| Ordering | Price; deadline; store order | Lowest price, then shortest deadline |
| Deadline wording | Up to X business days; X days; calendar date | “Até X dias úteis” |
| Free option | Show all and highlight; free only; no highlight | Show all and highlight “Frete Grátis” |

**User's choice:** Exibir todas as entregas domiciliares, sem retirada em loja, ordenadas por preço/prazo, com dias úteis explícitos e destaque para gratuidade.

**Notes:** Alternativas pagas continuam visíveis quando existe frete grátis.

---

## Falhas e indisponibilidade

| Decision | Options considered | Selected |
|----------|--------------------|----------|
| Per-product technical failure | Keep product; fail search; remove product | Keep product with temporary-unavailable state |
| Valid response without delivery | Explicit CEP-unavailable state; generic temporary state; remove product | “Entrega indisponível para este CEP” |
| Retry | One automatic retry; manual retry; no retry | One automatic retry |
| Partially malformed SLAs | Keep valid; show incomplete; invalidate quote | Keep only valid options |

**User's choice:** Isolar falhas por produto, distinguir indisponibilidade real de erro técnico, repetir uma vez automaticamente e aproveitar modalidades válidas.

**Notes:** A busca e os demais produtos nunca devem cair por causa de uma única cotação.

---

## Claude's Discretion

- Estrutura interna da coleção de modalidades.
- Timeout e atraso da única retentativa.
- Detecção técnica de pickup e payload malformado.
- Layout da lista no card, preservando os campos separados.
- Organização interna de helpers e testes.

## Deferred Ideas

- Padronizar a busca por SKU e os marketplaces para exibir preço do produto e frete separadamente, sem preço total.
- Frete Shopify permanece no requisito futuro FRET-06.
- O todo “Reforçar discriminação de modelo” foi revisado e não incorporado por ser alheio ao frete VTEX.
