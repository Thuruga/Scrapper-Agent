# Phase 25: Fundação de Motores - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Fundação backend do milestone v2.0. Entrega duas capacidades ortogonais, ambas pré-requisito das demais phases:

1. **Detecção de plataforma não suportada (COMP-02):** `detect_engine` para de cair silenciosamente em VTEX e passa a retornar `"unknown"` quando não há sinal positivo de uma plataforma suportada, incluindo um probe positivo de Wake Commerce. Marca em plataforma não suportada não entra silenciosamente na busca.
2. **Aplicação real do flag `is_active` (MGMT-01):** o flag `is_active` (hoje existente no modelo mas ignorado em todo lugar) passa a ser respeitado por um único chokepoint, `list_brands(active_only=True)`. Desativar uma marca a remove de busca, monitoramento, exportação e scheduler; reativar a traz de volta no próximo ciclo. `GET /brands/` continua retornando inativas (opt-in, não default global).

**Fora do escopo desta phase:** construir qualquer engine novo (Wake/SFCC/Inditex) — só detecção/sinalização; UI de gestão de marcas (Phase 27, MGMT-02); onboarding das marcas VTEX (Phase 26).

</domain>

<decisions>
## Implementation Decisions

> **Nota:** o usuário optou por **não discutir** as áreas cinzentas ("Esses itens não precisam ser discutidos"). As decisões D-01..D-08 abaixo são **discricionárias (Claude)**, derivadas dos success criteria do ROADMAP + leitura do código. São defaults sólidos para destravar pesquisa/planejamento — o usuário pode sobrescrever qualquer uma antes do planejamento.

### Detecção de plataforma não suportada (COMP-02)
- **D-01:** `detect_engine` ([api/routes_brands.py:14-53](api/routes_brands.py#L14-L53)) deixa de retornar `"vtex"` como fallback final (linha 53 — causa-raiz do mascaramento). Passa a retornar `"unknown"` quando o HTML é obtido com sucesso mas nenhum marcador positivo de VTEX ou Shopify é encontrado.
- **D-02:** Adicionar um **probe positivo de Wake Commerce** (ref.: Shop2gether) — não basta "parar de assumir VTEX". Reconhecer marcadores Wake (endpoint GraphQL Wake / header `TCS-Access-Token` / assets no HTML). Mesmo reconhecendo Wake, `detect_engine` retorna `"unknown"` (Wake não é suportado neste milestone); a distinção serve para confiança/log, não habilita busca. Critério 1 cita explicitamente "probe Wake"; ver `COMP-FUT-01`.
- **D-03:** Falha **transitória** de rede (timeout/erro em todos os probes, sem HTML) é tratada como inconclusiva → retorna `"unknown"`. Como `detect_engine` só roda no add-time (`create_brand` com `engine == "auto"`), a falha é recuperável pelo operador (re-adicionar). **Não** há reclassificação automática de marcas já cadastradas/ativas — evita derrubar uma VTEX válida por blip de rede.

### Cadastro com engine "unknown"
- **D-04:** Quando o cadastro detecta `"unknown"`, a marca é **salva com `engine="unknown"` e `is_active=False`** (sinalizada, não bloqueada com erro HTTP). O chokepoint `active_only` já a exclui da busca → zero poluição; o operador a vê na gestão e entende que a plataforma não é suportada. Isso **não** viola "Onboarding às cegas" (Out of Scope) porque a marca é explicitamente sinalizada e excluída, não cadastrada silenciosamente como VTEX (alinhado a Phase 26 critério 3: "marca com engine 'unknown' fica inativa automaticamente"). A resposta da rota deve expor o estado (engine unknown + inativa).

### Semântica de desativar/reativar (MGMT-01)
- **D-05:** Desativar **apenas seta o flag** `is_active=False`. A exclusão de busca/scheduler/monitoramento ocorre porque esses consumidores enumeram via `list_brands(active_only=True)` e a marca cai fora do **próximo ciclo**. **Não** há cancelamento ativo de monitores em execução (diferente do `delete_brand`, que chama `monitor_service.delete_monitors_by_brand`). Critério 2 exige "a exclusão ocorre exclusivamente pelo chokepoint... sem que qualquer outra rota seja modificada"; critério 3 exige reativação imediata.
- **D-06:** Contrato do endpoint: `PATCH /brands/{brand_key}/active` com body `{ "is_active": boolean }` (set explícito, idempotente — não toggle), alinhado ao nome no ROADMAP. Persistir `is_active` no backend ativo reusando `_save`/`_upsert_to_supabase`/`_save_to_json` ([services/brand_service.py:180-186](services/brand_service.py#L180-L186)). Garantir que o campo/coluna `is_active` exista no Supabase **e** no `brands.json`.

### Escopo do chokepoint `list_brands(active_only)`
- **D-07:** Assinatura `list_brands(self, active_only: bool = False)`. Default `False` preserva o comportamento atual e satisfaz o critério 4 (opt-in, não default global).
- **D-08:** Passam `active_only=True`: busca ([routes_search.py:144,209,228](api/routes_search.py#L144)), scheduler/factory ([factory.py:70](services/engines/factory.py#L70) `target_brands`), monitoramento (`price_monitor_service` / `category_monitor_service`) e exportação (deriva da busca). Permanecem com default `False`: `GET /brands/` ([routes_brands.py:72](api/routes_brands.py#L72), gestão UI) e operações por chave específica (`/discover`, `/mappings`, que usam `get_brand`, não `list`). `category_mapping.py:161` mantém `False` por ora (setup de mapeamento; o gate de busca já filtra na hora da busca) — revisitar na Phase 29 se necessário. Marketplaces virtuais injetados em `GET /brands/` (mercado_livre/netshoes/amazon) permanecem sempre ativos.

### Claude's Discretion
Todas as decisões acima (D-01..D-08) são discricionárias por escolha do usuário. Pontos com maior margem para o planner/researcher refinarem: a forma exata do probe Wake (D-02) e a definição precisa de "sinal positivo VTEX/Shopify" confiável (hoje o HTML fallback `"vtex" in html_lower` é frouxo e pode dar falso-positivo — vale endurecer).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & Requisitos (LOCKED)
- `.planning/ROADMAP.md` — §"Phase 25: Fundação de Motores": goal + 4 success criteria (a fonte de verdade do escopo)
- `.planning/REQUIREMENTS.md` — COMP-02 (detecção `"unknown"` + probe Wake), MGMT-01 (`is_active` aplicado no chokepoint `list_brands`)
- `.planning/PROJECT.md` — contexto do milestone v2.0; Wake explicitamente fora do escopo ("não será construído neste milestone"); "Onboarding às cegas" proibido por design
- `.planning/REQUIREMENTS.md` §Future Requirements — COMP-FUT-01 (engine Wake/Shop2gether, GraphQL + `TCS-Access-Token`): referência para o probe Wake da D-02

### Código tocado nesta phase
- `api/routes_brands.py` — `detect_engine` (L14-53; fallback `return "vtex"` em L53 é o alvo da D-01), `create_brand` (L56-66, onde o "unknown" será tratado por D-04), `list_brands`/`GET /brands/` (L69-103), `delete_brand` (L148-160, padrão de cleanup de monitores — referência para D-05)
- `services/brand_service.py` — `list_brands` (L207, chokepoint a evoluir com `active_only`), `_save`/`_upsert_to_supabase`/`_save_to_json` (L154-186, persistência de `is_active`)
- `core/models.py` — `DynamicBrand.is_active` (L232, default `True`, hoje nunca lido), `engine` default `"vtex"` (L224)

### Consumidores de `list_brands()` (impactados por D-08)
- `api/routes_search.py` L144, L209, L228 — busca (active_only=True)
- `services/engines/factory.py` L70 — `target_brands` do scheduler (active_only=True)
- `services/price_monitor_service.py`, `services/category_monitor_service.py`, `services/orchestrator*.py` — monitoramento/scheduler (active_only=True)
- `api/routes_category.py` L176, `services/category_mapping.py` L161 — categoria/mapeamento (mantêm default False)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `detect_engine` já encadeia Shopify→VTEX→HTML-fallback; a mudança é trocar o fallback final e inserir o probe Wake — não reescrever do zero.
- `BrandManagerService._save` abstrai Supabase vs `brands.json`; reusar para persistir `is_active` sem ramificar lógica nova de I/O.
- `delete_brand` demonstra o padrão de cleanup ativo de monitores (`monitor_service.delete_monitors_by_brand`) — referência direta caso a D-05 venha a mudar para cancelamento imediato.

### Established Patterns
- `brand_service` é singleton consumido em ~6 módulos; a nova assinatura `list_brands(active_only=False)` **deve** manter default retrocompatível.
- Persistência dual: Supabase em produção (via `SUPABASE_URL`/`SUPABASE_KEY`), `brands.json` em dev. O campo `is_active` precisa existir nos dois caminhos (model já tem; conferir migração/coluna Supabase).
- Rotas finas em `api/`, lógica em `services/` — o `PATCH /brands/{key}/active` deve delegar ao `brand_service`, não conter regra de negócio na rota.

### Integration Points
- Novo `PATCH /brands/{brand_key}/active` → `brand_service` (set `is_active` + `_save`).
- `list_brands(active_only=True)` é o único ponto de exclusão; busca/scheduler/monitor/export apenas trocam a chamada.
- `GET /brands/` injeta marketplaces virtuais (ML/Netshoes/Amazon) sem `is_active` → tratá-los como sempre ativos ao aplicar o filtro.

</code_context>

<specifics>
## Specific Ideas

- O usuário declarou explicitamente que as áreas cinzentas **não precisam ser discutidas** — confia nos critérios de sucesso do ROADMAP. As decisões D-01..D-08 são os defaults adotados; sobrescrever antes de `/gsd-plan-phase` se algo divergir da intenção.
- ⚠ Spikes 003-006 (SFCC público via browser) **não estão empacotados** como findings. Rodar `/gsd-spike --wrap-up` se quiser que virem findings reutilizáveis. **Não bloqueiam a Phase 25** — são material de milestone futuro (SFCC = COMP-FUT-02, marcas deferidas).

</specifics>

<deferred>
## Deferred Ideas

- **Engine Wake Commerce real** (onboarding de Richards/Shop2gether): COMP-FUT-01, candidato a v3.0. A Phase 25 só **detecta e exclui** Wake, não constrói o engine.
- **Engines SFCC (Lacoste/Hugo Boss) e Inditex/Zara**: COMP-FUT-02/03. Spikes 003-006 já validaram extração pública via browser (`VALIDATED_LIVE_E2E_PUBLIC_BROWSER`) — insumo para milestone futuro, fora desta phase.
- **Reclassificação automática de engine** de marcas já cadastradas (re-rodar `detect_engine` periodicamente): não pedido; explicitamente fora do escopo (D-03 confina a detecção ao add-time).
- **Painel/diagnóstico de saúde por categoria**: Phase 29 (DIAG-01/02), não aqui.
- **UI de gestão de marcas** (toggle ativar/desativar na interface): Phase 27 (MGMT-02). A Phase 25 só entrega o endpoint `PATCH /brands/{key}/active` que a UI consumirá.

None além das acima — discussão permaneceu dentro do escopo da phase.

</deferred>

---

*Phase: 25-funda-o-de-motores*
*Context gathered: 2026-06-18*
