# Phase 28: Persistência da Busca Entre Abas - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-21
**Phase:** 28-persist-ncia-da-busca-entre-abas
**Areas discussed:** Escopo das buscas, O que persiste, Notificação fora da aba, Fronteira da persistência

---

## Escopo das buscas

| Option | Description | Selected |
|--------|-------------|----------|
| Comparativa + SKU | As duas buscas síncronas ganham o store global; CategoryPage só com o fix de WS cleanup | ✓ (após resolução do conflito) |
| Só a Comparativa | Segue o critério #1 ao pé da letra; SKU continuaria se perdendo | |
| Comparativa + SKU + scrape | Persistir também o progresso/logs do scrape da CategoryPage | (escolha inicial, revertida) |

**User's choice:** Inicialmente "Comparativa + SKU + scrape"; após eu apontar o conflito com o critério #4, o usuário decidiu: "Ignore esse ponto. Mantenha somente para o SKU e busca comparativa."
**Notes:** Conflito surfaçado: persistir o scrape exigiria manter o WebSocket vivo entre abas (oposto do critério #4 que pede fechar o WS no unmount), e o endpoint `/ws/${jobId}` aparenta não ter replay → reconexão perderia eventos. Resolução: CategoryPage recebe apenas o WS cleanup; scrape não persiste.

---

## O que persiste

| Option | Description | Selected |
|--------|-------------|----------|
| Tudo (estado completo) | Inputs + filtros + resultados + seleção, mesmo sem busca rodando | ✓ |
| Só busca + resultados | Inputs/filtros zeram quando não há busca ativa | |
| Só enquanto rodando | Resultado some ao sair após concluir | |

**User's choice:** Tudo (estado completo)
**Notes:** Atende "estado de seleção preservado" do goal; é o que o store naturalmente guarda; comportamento mais intuitivo.

---

## Notificação fora da aba

| Option | Description | Selected |
|--------|-------------|----------|
| Toast sempre (global) | Toast via sonner ao concluir qualquer busca; global, aparece em qualquer aba | ✓ |
| Toast só fora da aba | Suprime o toast quando já está na aba da busca | |
| Toast + badge no menu | Toast + indicador no item do menu lateral, some ao visitar | |

**User's choice:** Toast sempre (global)
**Notes:** Reusa o `sonner` (já dependência); por ser global cobre o caso "em outra aba" do critério #2 sem lógica extra. Comportamento novo — hoje a busca síncrona não emite toast de conclusão.

---

## Fronteira da persistência

| Option | Description | Selected |
|--------|-------------|----------|
| Só troca de aba (memória) | Store em memória; zera num reload da página | ✓ |
| Também sobrevive a reload | persist + sessionStorage; some ao fechar a aba do navegador | |
| Sobrevive até fechar navegador | persist + localStorage; dura entre sessões | |

**User's choice:** Só troca de aba (memória)
**Notes:** Casa com "entre abas" (PERS-01); evita serializar o `ComparisonResult` (potencialmente grande); sem scope creep.

---

## Claude's Discretion

- Estrutura interna do store (unificado vs slices por aba).
- Semântica de cancelamento (AbortController) ao iniciar nova busca antes do término (critério #3).
- Prevenção de duplo-fetch no mount/remount (critério #3).
- Ponto exato de disparo do toast de conclusão (action do store vs componente).
- Forma exata do `useEffect` de cleanup do WS na CategoryPage.

## Deferred Ideas

- Persistir o progresso do scrape da CategoryPage entre abas — descartado (conflito com critério #4 / exigiria replay no backend).
- Sobrevivência a reload/refresh (sessionStorage/localStorage) — fora do escopo "entre abas".
- Todo revisado-não-incorporado: "Reforçar discriminação de modelo" (domínio de relevância / Phase 23, fora de escopo).
