# Phase 29: Diagnóstico de Categorias Vazias/Erro - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-22
**Phase:** 29-diagn-stico-de-categorias-vazias-erro
**Areas discussed:** Mecanismo de probe, Escopo & gatilho, Taxonomia 3 estados, Painel na UI

---

## Escopo & gatilho

### Cobertura de marcas/categorias
| Option | Description | Selected |
|--------|-------------|----------|
| Ativas c/ categorias mapeadas | Só marcas ativas com de/para canônico | |
| Todas as marcas (incl. inativas) | Inclui inativas e engine 'unknown'; foge do chokepoint active_only | ✓ |
| Você decide | Critério a cargo do planner | |

**User's choice:** Todas as marcas (incl. inativas).
**Notes:** Diagnóstico é observabilidade — operador precisa enxergar inativas/problemáticas. Bypassa de propósito o chokepoint `active_only` (D-01).

### Cobertura — marcas sem mapping / motor não-VTEX
| Option | Description | Selected |
|--------|-------------|----------|
| Status especial, sem probe | Aparecem com marcador, mas não são probadas (probe VTEX-only) | ✓ |
| Puladas silenciosamente | Só VTEX com mappings entram | |
| Você decide | Forma exata ao planner | |

**User's choice:** Status especial, sem probe (D-02).

### Sinalização ativo/inativo
| Option | Description | Selected |
|--------|-------------|----------|
| Sim, marcar inativas | Distinção visual (como SettingsPage) p/ não confundir inativa com erro | ✓ |
| Não, tratar igual | Sem distinção de estado | |

**User's choice:** Sim, marcar inativas (D-03).

### Gatilho
| Option | Description | Selected |
|--------|-------------|----------|
| On-demand, 1 marca ou todas | Botão por marca + 'todas'; resultado fresco | ✓ |
| Apenas on-demand por 1 marca | Só individual | |
| Agendado em background | Job periódico c/ cache | |

**User's choice:** On-demand, 1 marca ou todas (D-04).

### Execução
| Option | Description | Selected |
|--------|-------------|----------|
| Síncrono (espera e retorna) | Endpoint dispara probes concorrentes e retorna o relatório | ✓ |
| Job assíncrono c/ WebSocket | Reusa infra de scrape-category-multi | |

**User's choice:** Síncrono (D-05).

---

## Mecanismo de probe

### Como probar
| Option | Description | Selected |
|--------|-------------|----------|
| Probe dedicado leve | 1 chamada à Search API no path, sem fallback full-text nem pipeline | ✓ |
| Reusar engine.search() | Com fallback desligado; arrasta reviews/frete/NLP | |
| Reusar run_bulk_scrape | Varredura completa, pesado | |

**User's choice:** Probe dedicado leve (D-07).

### Fidelidade da requisição
| Option | Description | Selected |
|--------|-------------|----------|
| Requisição crua (status real) | Sem retries/domínio estável/Playwright | ✓ |
| Cliente resiliente (_request_json) | Mascara 403/500 reais | |

**User's choice:** Requisição crua (D-08).

### Sinal ok vs vazia
| Option | Description | Selected |
|--------|-------------|----------|
| Presença na página 0 + total do header | Lista p0 + header 'resources' p/ contagem | ✓ |
| Só presença na página 0 | Sem contagem total | |
| Você decide | Planner define sinal | |

**User's choice:** Presença na página 0 + total do header (D-09).

---

## Taxonomia 3 estados

### Marcas headless/FastStore (domínio estável)
| Option | Description | Selected |
|--------|-------------|----------|
| Resolver domínio 1x por marca | Resolve base correto antes; depois probes crus por categoria | ✓ |
| Cru sempre no domínio público | HTML-no-público vira erro (falso positivo em massa) | |
| Você decide | Estratégia ao planner | |

**User's choice:** Resolver domínio 1x por marca (D-10).

### Classificação de respostas não-200 / não-404-500
| Option | Description | Selected |
|--------|-------------|----------|
| Tudo → 'erro' + detalhe | 403/429/timeout/rede/HTML → erro; nuance no error_detail | ✓ |
| Estados extras (bloqueado/timeout) | Quebra o contrato de 3 estados | |
| Você decide | Mapeamento ao planner | |

**User's choice:** Tudo → 'erro' + detalhe (D-11).

### Mapping stale
| Option | Description | Selected |
|--------|-------------|----------|
| 'vazia' + expor URL probada | 200+0 = vazia; URL no painel p/ inspeção humana | ✓ |
| Validar path contra a árvore | Marca 'erro' se path não existir; +req/código | |
| Você decide | Planner decide | |

**User's choice:** 'vazia' + expor URL probada (D-12).

---

## Painel na UI

### Local
| Option | Description | Selected |
|--------|-------------|----------|
| Nova aba 'Diagnóstico' | Aba dedicada no sidebar | ✓ |
| Dentro de 'Varredura por Categoria' | Sub-painel na aba category | |
| Dentro de Configurações/Marcas | Junto da gestão de marcas | |
| Você decide | Local ao planner | |

**User's choice:** Nova aba 'Diagnóstico' (D-13).

### Layout
| Option | Description | Selected |
|--------|-------------|----------|
| Lista agrupada por marca | Card por marca, chips por categoria; lida com escopo heterogêneo | ✓ |
| Matriz/heatmap marca × categoria | Escaneável, mas ragged (N/A) | |
| Você decide | Layout ao planner | |

**User's choice:** Lista agrupada por marca (D-14).

### Detalhe (http_status/error_detail/URL)
| Option | Description | Selected |
|--------|-------------|----------|
| Linha expansível | Chip na linha; expande p/ status + detalhe + URL | ✓ |
| Tudo visível na linha | Polui com muitas categorias | |
| Você decide | Forma ao planner | |

**User's choice:** Linha expansível (D-15).

### Acionamento e loading
| Option | Description | Selected |
|--------|-------------|----------|
| Botão por marca + 'Diagnosticar todas' | Loading na marca em execução | ✓ |
| Só 'Diagnosticar todas' | Não atende 'acionar para uma marca' | |
| Você decide | Ergonomia ao planner | |

**User's choice:** Botão por marca + 'Diagnosticar todas' (D-16).

---

## Claude's Discretion

- Resolução exata path→URL via `resolve_category_for_brands` (incl. tratamento de `vtex_fq`).
- Grau de concorrência dos probes e respeito a rate-limit.
- Forma exata do marcador "sem mapeamento / motor não suportado".
- Quantos itens pedir na página 0 (`_to=0` vs `_to=9`).
- Nome/forma do endpoint e dos modelos Pydantic de resposta.
- Teste de contrato offline/determinístico do classificador.

## Deferred Ideas

- Persistência/cache de resultados + agendamento em background (job periódico estilo category_monitor).
- Probe de motores não-VTEX (Shopify, marketplaces virtuais, engine 'unknown').
- Validar path contra a árvore de categorias p/ distinguir stale de vazia sazonal.
- Auto-ação sobre categorias vazias/erro (Out of Scope — DIAG só reporta).
