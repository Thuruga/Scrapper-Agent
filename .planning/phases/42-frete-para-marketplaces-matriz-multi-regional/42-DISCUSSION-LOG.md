# Phase 42: Frete para Marketplaces & Matriz Multi-Regional - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-01
**Phase:** 42-Frete para Marketplaces & Matriz Multi-Regional
**Areas discussed:** Netshoes/anti-bot, Prazo de entrega, Matriz — UI e escopo de engines, CEPs, Cache/TTL

---

## Netshoes — estratégia dado o bloqueio Akamai conhecido

| Option | Description | Selected |
|--------|-------------|----------|
| Tentar ao vivo, cair em blocked | Reusa o `_run_playwright_shipping` existente; se falhar (cenário confirmado), retorna estado `blocked` explícito | ✓ |
| Declarar unsupported/blocked direto | Sem tentativa ao vivo nesta fase, documenta limitação de infra | |
| Deixar a critério do Claude | Claude decide seguindo o precedente do spike-gate da Phase 41 | |

**User's choice:** Tentar ao vivo, cair em blocked.
**Notes:** Alinhado ao precedente de Phase 41 (D-12/D-14) — tentar, documentar evidência, declarar estado real em vez de hard-codar de saída.

---

## Prazo de entrega (shipping_time) — profundidade do esforço

| Option | Description | Selected |
|--------|-------------|----------|
| Melhor esforço por marketplace | ML via API estruturada; Amazon/Netshoes via parse de texto de entrega no DOM | ✓ |
| Só onde há dado estruturado (ML) | Amazon/Netshoes ficam só com raw_text, sem estimated_delivery_days numérico | |
| Deixar a critério do Claude | Claude decide a profundidade por marketplace | |

**User's choice:** Melhor esforço por marketplace.
**Notes:** ML já expõe prazo estruturado na resposta de `/shipping_options`; Amazon já lê `_read_delivery_text` (só falta extrair prazo, não só preço); Netshoes recebe o mesmo tratamento quando não bloqueada.

---

## Matriz Multi-Regional — ponto de entrada na UI

| Option | Description | Selected |
|--------|-------------|----------|
| Botão nos cards de resultado existentes | Reusa os pontos onde já existe "Calcular Frete" (comparativa, SKU, cross-marketplace) | ✓ |
| Painel/modal dedicado | Nova tela/modal separado, desacoplado das buscas existentes | |
| Deixar a critério do Claude | Claude decide a superfície exata durante o planejamento | |

**User's choice:** Botão nos cards de resultado existentes.

---

## Matriz Multi-Regional — escopo de engines

| Option | Description | Selected |
|--------|-------------|----------|
| Todos os engines, sempre | Botão aparece sempre; resposta mostra estado real por região (available/unsupported/blocked) | ✓ |
| Só engines com frete disponível | Botão oculto/desabilitado para engines sem frete real | |
| Deixar a critério do Claude | Claude decide seguindo padrão visual já estabelecido | |

**User's choice:** Todos os engines, sempre.
**Notes:** Consistente com o padrão "nunca esconder, sempre estado explícito" das Phases 41/44.

---

## Matriz Multi-Regional — lista de CEPs por região

| Option | Description | Selected |
|--------|-------------|----------|
| Claude escolhe (capitais) | Um CEP representativo por capital/região como default inicial, editável depois | ✓ |
| Usuário informa CEPs específicos | Lista exata fornecida pelo usuário | |

**User's choice:** Claude escolhe (capitais).

---

## Cache da Matriz — TTL

| Option | Description | Selected |
|--------|-------------|----------|
| TTL curto (algumas horas) | Cache expira sozinho após tempo curto configurável | ✓ |
| Sem expiração automática | Cache permanente até limpeza manual/deploy | |
| Deixar a critério do Claude | Claude escolhe um TTL conservador seguindo padrão de config.py | |

**User's choice:** TTL curto (algumas horas).
**Notes:** Valor exato do TTL fica a critério do planner, seguindo o padrão de constantes nomeadas já usado em `config.py` (Phase 44: `STOCK_PROBE_THROTTLE_SECONDS`, `MAX_REVIEW_PAGES`).

---

## Claude's Discretion

- Nomes exatos das classes/arquivos dos novos providers de marketplace em `services/shipping/`.
- Forma exata de extrair prazo por marketplace (seletor/regex/campo de API).
- Layout exato da UI da Matriz Regional (tabela de 5 linhas, modal, tooltip, etc.).
- Valor exato do TTL do cache, throttle entre requisições da matriz, e CEP específico de cada capital.
- Persistência da matriz (JSON local vs. SQLite da Phase 37, dependendo do estado real da Phase 37 no momento do planejamento).
- Decomposição exata do resolver para os 3 novos engines de marketplace.

## Deferred Ideas

- Proxy residencial/pago ou bypass de anti-bot para desbloquear a Netshoes de verdade — fora desta fase.
- Migrar a matriz para SQLite antes da Phase 37 existir de fato.
- UI de analytics/dashboard sobre variação histórica de frete por região.
- Ampliar a matriz para múltiplos produtos de uma vez (lote) — roadmap trava "um produto"; lote fica para fase futura se necessário.

### Reviewed Todos (not folded)
- `.planning/todos/pending/reforcar-discriminacao-modelo.md` — match automático 0.6, mas é sobre discriminação de modelo/marca na busca por SKU, não frete.
- `.planning/todos/pending/audit-category-mappings-all-brands.md` — match automático 0.2 (só "phase"), pertence a paridade de atributos.
- `.planning/todos/pending/hugoboss-vtex-io-category-scan.md` — match automático 0.2, pertence a categoria Hugo Boss.
- `.planning/todos/pending/zara-comp07-deferred.md` — match automático 0.2, pertence a Zara/COMP-07.
