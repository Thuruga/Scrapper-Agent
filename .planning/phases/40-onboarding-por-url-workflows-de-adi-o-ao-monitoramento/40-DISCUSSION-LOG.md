# Phase 40: Onboarding por URL & Workflows de Adição ao Monitoramento - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-29
**Phase:** 40-onboarding-por-url-workflows-de-adi-o-ao-monitoramento
**Areas discussed:** Inferência de nome + confirmação, Alvo e parâmetros do "Adicionar ao monitoramento", Dedup do produto monitorado, Persistência + enforcement dos toggles de marketplace

---

## Inferência de nome + confirmação (UX-03)

### Inferência de nome — ordem de precedência
| Option | Description | Selected |
|--------|-------------|----------|
| JSON-LD/OG → <title> → domínio | Tenta brand/organization/og:site_name, cai pro <title>, por último deriva do domínio; reusa o fetch do detect_engine; sempre editável | ✓ |
| Domínio primeiro | Deriva do domínio direto; título/JSON-LD secundários | |
| Só <title> + edição manual | Pega o <title> e operador limpa à mão | |

### Fluxo identify (dry-run) vs salvar
| Option | Description | Selected |
|--------|-------------|----------|
| Dois endpoints: /identify (dry-run) + /brands/ salva | identify detecta engine+nome+domínio sem persistir; create_brand existente salva após confirmação | ✓ |
| Endpoint único com flag confirm | POST /brands/ com confirm=false (preview) / true (salva) | |

### Engine='unknown' no identify
| Option | Description | Selected |
|--------|-------------|----------|
| Avisar + permitir override manual | Aviso na UI; operador escolhe engine ou salva inativo (D-04) | ✓ |
| Bloquear salvar até resolver engine | Não cria marca unknown | |
| Salvar inativo automaticamente, sem aviso | Comportamento atual do create_brand | |

**User's choice:** Todas as opções recomendadas.
**Notes:** Reuso do fetch do detect_engine evita request extra; create_brand permanece o único ponto de escrita.

---

## Alvo e parâmetros do "Adicionar ao monitoramento" (UX-04)

### De onde vêm interval e duration
| Option | Description | Selected |
|--------|-------------|----------|
| Defaults fixos, 1 clique sem modal | Adiciona com padrões; ajuste posterior na aba de monitores | ✓ |
| Modal pedindo interval/duration | Configura antes de criar | |
| Config global de defaults | Defaults de uma config global editável | |

### Semântica de duração (price_monitor auto-para após duration_hours)
| Option | Description | Selected |
|--------|-------------|----------|
| Persistente / efetivamente indefinido | Não expira cedo; duração longa ou 0/None = indefinido; operador para manualmente | ✓ |
| Duração padrão curta (24–72h) | Monitor expira sozinho; re-adicionar para continuar | |

**User's choice:** Todas as opções recomendadas.
**Notes:** Alvo confirmado = price_monitor (POST /monitor/start), não o monitor de categoria.

---

## Dedup do produto monitorado (UX-04)

### Normalização de URL
| Option | Description | Selected |
|--------|-------------|----------|
| Conservadora | lowercase host, sem www, https, sem trailing slash, remove só tracking params (utm_*/gclid/fbclid); mantém path+query | ✓ |
| Match exato de string | Sem normalização | |
| Agressiva (só host+path) | Descarta toda querystring (risco de fundir SKUs) | |

### Comportamento ao detectar duplicata
| Option | Description | Selected |
|--------|-------------|----------|
| Idempotente com feedback | Toast se já ativo (no-op); reativa se parado | ✓ |
| No-op silencioso | Sem feedback | |
| Só toast, nunca religa | Operador religa manualmente | |

**User's choice:** Todas as opções recomendadas.
**Notes:** Hoje cada start gera job_id novo sem dedup — phase introduz a checagem.

---

## Persistência + enforcement dos toggles de marketplace (UX-05)

### Onde mora o estado on/off
| Option | Description | Selected |
|--------|-------------|----------|
| Promover a entradas reais em brands.json + reusar is_active | Toggle via PATCH /active existente; remove injeção runtime do list_brands(); exibe toggle antes escondido (MGMT-02) | ✓ |
| Arquivo de settings novo (marketplace_settings.json) | Flags isoladas; segundo mecanismo de ativação | |
| Flag em config/relevance_settings existente | Reusa config global; mistura com settings de relevância | |

### Onde o cross_marketplace_service lê o estado
| Option | Description | Selected |
|--------|-------------|----------|
| Por request, no início da busca | Monta self.engines só com ativos a cada cross_marketplace_search | ✓ |
| No construtor / boot do serviço | Lê uma vez; só vale após restart (não atende "imediatamente") | |

**User's choice:** Todas as opções recomendadas.
**Notes:** Consistente com MGMT-01 (chokepoint único de ativação). Preservar brand_keys atuais dos marketplaces.

---

## Claude's Discretion

- UI/UX exata (toggles, formulário de confirmação, rótulo/ícone do botão) — planner / `/gsd-ui-phase`.
- Valores numéricos dos defaults de interval/duration e representação de "indefinido" em PriceMonitorConfig.
- Forma exata da função de normalização de URL e lista de tracking params.
- Se marketplaces desativados ficam visíveis (cinza) ou somem dos filtros.
- Estrutura interna ao promover marketplaces — preservar brand_keys `mercado_livre`/`netshoes`/`amazon`.

## Deferred Ideas

Nenhuma — discussão ficou dentro do escopo da phase (3 success criteria do roadmap).
