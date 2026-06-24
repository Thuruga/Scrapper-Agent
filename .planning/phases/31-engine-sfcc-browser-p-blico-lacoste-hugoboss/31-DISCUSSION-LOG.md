# Phase 31: Engine SFCC (Browser Público) — Lacoste & HugoBoss - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-24
**Phase:** 31-Engine SFCC (Browser Público) — Lacoste & HugoBoss
**Areas discussed:** Locale e moeda (reais), Como a busca funciona, Escopo de catálogo/categorias, Enriquecimento por PDP

---

## Locale e moeda (reais)

| Option | Description | Selected |
|--------|-------------|----------|
| Loja BR (.com.br) | Onboardar a loja brasileira de cada marca, preço em reais nativamente | ✓ |
| Loja US + converter | Manter caminho dos spikes (US, USD) e converter para reais | |
| BR onde houver, US como fallback | Preferir .com.br; US se não houver storefront BR | |

**User's choice:** Loja BR (.com.br) — via "Other": "https://www.hugoboss.com.br/ Hugo Boss tem loja BR".
**Notes:** Usuário confirmou que HugoBoss tem storefront BR, resolvendo a incerteza levantada na opção. Lacoste → lacoste.com.br. Preço em reais nativo, sem conversão. Flag p/ research: confirmar que os domínios .com.br são SFCC e expõem JSON-LD/OG; ajustar parser de preço para formato BR (`R$ x,xx`).

---

## Como a busca funciona

| Option | Description | Selected |
|--------|-------------|----------|
| Página de busca do site | Renderizar a URL de busca nativa, extrair cards, enriquecer via PDP | ✓ |
| Navegação por categoria | Sem busca textual; varrer categoria e filtrar por relevância (caminho dos spikes) | |
| Busca do site + fallback categoria | Tentar busca nativa; cair para categoria se falhar | |

**User's choice:** Página de busca do site.
**Notes:** Flag p/ research: descobrir padrão de URL de busca SFCC nas lojas BR e confirmar resposta sem login/anti-bot.

---

## Escopo de catálogo/categorias

| Option | Description | Selected |
|--------|-------------|----------|
| Stub gracioso (só busca) | discover_categories/get_catalog retornam vazio; foco em busca+preço (SC-1..4) | |
| Catálogo completo agora | Descoberta real da árvore de categorias; Lacoste/HugoBoss na tela de monitoramento | ✓ |
| Discovery mínimo p/ busca | Sem catálogo na UI, só descoberta interna p/ a busca funcionar | |

**User's choice:** Catálogo completo (opção B) — após pedido de esclarecimento ("O que você quer dizer com isso?"), explicado em texto plano (busca de produto vs. monitorar categoria inteira), e o usuário escolheu B.
**Notes:** Registrado que B expande além das SC-1..4 e não foi validado pelos spikes (descoberta de árvore de categorias). Adicionado guard pragmático (D-06): gated por research; fallback para stub se inviável, com catálogo completo virando follow-up.

---

## Enriquecimento por PDP

| Option | Description | Selected |
|--------|-------------|----------|
| Top-N por relevância | Abrir PDP só dos N mais relevantes | |
| Enriquecer todos | Abrir PDP de todos os resultados até max_results (máxima fidelidade) | ✓ |
| Só quando faltar campo | Card por padrão; PDP só se faltar preço/imagem | |

**User's choice:** Enriquecer todos.
**Notes:** Alinhado ao valor central "alta fidelidade de dados". Nota p/ planner (D-08): manter max_results modesto (sugestão 10) e usar concorrência/throttle controlados para limitar custo e exposição anti-bot. Usuário optou por não fixar o número (deixou a critério do planner).

---

## Claude's Discretion

- Valor padrão de `max_results` / profundidade de varredura.
- Forma exata do retorno de `calculate_shipping` (None vs. ShippingInfo de ausência).
- Estratégia concreta JSON-LD vs. OpenGraph vs. texto de card por marca (segue evidência dos spikes 005/006).
- Nomes de classes/constantes/markers e estrutura dos testes (convenções do repo).

## Deferred Ideas

- Frete/checkout/estoque por CEP para SFCC — fora de escopo do milestone.
- OCAPI/SCAPI — fora de escopo (sem credenciais).
- Catálogo/monitoramento de categorias SFCC como follow-up — só se o research reprovar a descoberta da árvore SFCC pública (D-06).
- Zara / Inditex IOP — COMP-FUT-03, deferido.
- Reviewed todo "Reforçar discriminação de modelo" — fora de escopo (precisão da busca por SKU, não engine SFCC).
