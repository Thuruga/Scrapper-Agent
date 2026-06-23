# Phase 26: Onboarding das 5 Marcas VTEX - Context

**Gathered:** 2026-06-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Registrar as **5 marcas concorrentes em VTEX confirmada** — Levi's, Calvin Klein, Zapalla, Austral e Track & Field — no sistema, com:

1. **Engine reconfirmada** por `detect_engine` no momento da adição (não assumida manualmente), via o caminho `create_brand` (engine `"auto"`) já existente desde a Phase 25.
2. **Categorias mapeadas** (subset núcleo comparável) por marca, prontas para busca e monitoramento.
3. **Busca por marca retornando produtos reais** para cada uma das 5.

**Descoberta-chave (molda o escopo):** a busca por marca (`engine_factory.search_all_brands` → `VTEXEngine.search(query)`) é **por query e NÃO consome os mappings de categoria**. Logo, o **critério de sucesso 1** ("busca retorna produtos reais") só exige a marca registrada como `engine="vtex"` com `domain` válido. Os mappings de categoria (taxonomia canônica em `services/category_mapping.py`) alimentam o **category-scan / monitoramento** e o futuro **diagnóstico da Phase 29 (DIAG-01/02)** — não a busca por query.

**Fora do escopo desta phase:**
- Marcas em plataforma não suportada — **Richards** (Wake), **Lacoste / Hugo Boss** (SFCC), **Zara** (Inditex). Movidas para Future Requirements (COMP-FUT-01/02/03). Se um operador tentar adicioná-las, a detecção da Phase 25 (COMP-02) as identifica como `"unknown"` e as mantém inativas.
- Construir qualquer engine novo (Wake/SFCC/Inditex) — os spikes SFCC 003-006 são insumo de milestone futuro, não desta phase.
- UI de gestão de marcas (Phase 27, MGMT-02) — esta phase é backend/seed.
- Diagnóstico de saúde de categorias (Phase 29, DIAG-01/02).
- Frete via checkout (Phase 30, FRET-05).

</domain>

<decisions>
## Implementation Decisions

### Identidade das 5 marcas (fornecida pelo usuário)
- **D-01:** Domínios e `brand_key` fornecidos pelo usuário — o researcher **pula** a etapa de descoberta de storefronts. Tabela canônica de identidade:

  | `brand_key` | `brand_name` | `domain` (armazenado, sem scheme) |
  |---|---|---|
  | `levis` | Levi's | `www.levi.com.br` |
  | `calvinklein` | Calvin Klein | `www.calvinklein.com.br` |
  | `zapalla` | Zapalla | `www.zapalla.com.br` |
  | `austral` | Austral | `secure.austral.com.br` ⚠️ |
  | `trackfield` | Track & Field | `www.tf.com.br` |

- **D-02 (⚠️ risco a reconfirmar):** O domínio da **Austral** veio como `secure.austral.com.br`. Subdomínio `secure.` é atípico para storefront (normalmente é host de checkout). Como `detect_engine` usa `allow_redirects=False` (`api/routes_brands.py:44`), se esse host redirecionar para `www.austral.com.br` o probe de HTML falha silenciosamente. **Ação na execução:** testar variações (`www.austral.com.br`, sem-`www`) e ajustar o `domain` para o que `detect_engine` reconfirmar como `"vtex"`.

### Profundidade do mapeamento de categorias
- **D-03:** Mapear um **subset núcleo comparável**, não o catálogo inteiro. Por marca, mapear **somente as categorias que a marca de fato tem**, descobertas via `discover_categories`.
- **D-04:** **Ancorar na taxonomia canônica já existente** (`camisas`, `polos`, `camisetas`, `calcas`, `bermudas`, `jaquetas` — slugs de `services/category_mapping.py:_RAW_CATEGORIES`). Mapear, por marca, as canônicas que existirem. Isso preserva o "banana com banana" (comparabilidade entre marcas) que é o propósito do de/para canônico. **Não** criar taxonomia livre por marca (quebraria comparabilidade).
- **D-05 (tensão registrada, decisão consciente):** O **goal** da phase diz "categorias mapeadas", mas **nenhum dos 3 critérios de sucesso testa mappings** (testam busca, engine=vtex e exclusão das não-suportadas) e a busca não usa mappings. O mapeamento núcleo é entregue para preparar Phase 29/monitoramento, ciente de que os critérios formais já passariam só com o registro + busca verificada.

### Mecanismo de onboarding & persistência dos mappings
- **D-06:** **Script seed idempotente** (não cadastro manual via API/Swagger). O script, por marca: chama `create_brand` com `engine="auto"` (reconfirma engine — satisfaz critério 2) → roda `discover_categories` → grava os mappings. Re-executável sem duplicar.
- **D-07:** Mappings gravados em **`DynamicBrand.mappings`** (data-driven, como a marca `bck`), **não** hardcoded em `_RAW_CATEGORIES`. Justificativa: `resolve_category_for_brands` / `get_canonical_categories` já consultam mappings dinâmicos (hardcoded primeiro, depois dinâmico), então slugs canônicos funcionam sem tocar código; persiste corretamente via `brand_service`; sem mudança de código. **NÃO** editar `services/category_mapping.py`.
- **D-08:** Persistência **dual dev/prod** é invariante: o script grava via `brand_service` (`_save` → Supabase em prod via `SUPABASE_URL`/`SUPABASE_KEY`, `brands.json` em dev). Garantir que `engine`, `is_active` e `mappings` caiam nos dois caminhos.
- **D-09:** Casamento path→slug por **auto-match por nome + revisão humana**. O script normaliza os nomes das categorias descobertas e os casa com os labels canônicos, **imprime o de/para proposto por marca**, e só persiste após confirmação do operador. Evita gravar path errado silenciosamente em nome ambíguo (ex.: "Camisas Masculinas" vs "Camisas").

### Definição de "pronto" & tratamento de falha
- **D-10:** Verificação em duas camadas: (a) **smoke ao vivo** na execução — 1 query por marca confirmando ≥1 produto real (valida critério 1); (b) **teste offline/determinístico de contrato** — marca registrada com `engine="vtex"`, `is_active=True` e mappings persistidos, **sem rede** (alinhado à filosofia de testes do projeto: offline/determinístico, sem WAF). O teste ao vivo por marca foi **rejeitado** (frágil: WAF/geo/lentidão).
- **D-11:** Se `detect_engine` **não** retornar `"vtex"` para alguma das 5: `"unknown"` **não** é estado final aceitável. **Investigar + re-tentar** — testar variações de domínio (www/sem-www), checar 403/redirect (caso `secure.austral`), corrigir o `domain` e re-rodar até `detect_engine` confirmar `"vtex"`. A marca permanece **inativa** (Phase 25 D-04) até a reconfirmação. **Override manual para `vtex` foi rejeitado** (viola critério 2: "reconfirmado por `detect_engine`, não assumido manualmente").

### Claude's Discretion
- Forma exata do auto-match de nomes (normalização: lowercase, sem acento, singular/plural, "masculino/masculina") fica a critério do planner/executor, desde que haja revisão humana (D-09).
- Nome/localização do script seed (ex.: `scripts/onboard_vtex_brands.py`) e seu modo de invocação ficam a critério do planner, mantendo idempotência (D-06) e persistência dual (D-08).
- Termo de query do smoke por marca (D-10a) fica a critério da execução (ex.: um termo genérico de moda masculina que exista em todas).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & Requisitos (LOCKED)
- `.planning/ROADMAP.md` — §"Phase 26: Onboarding das 5 Marcas VTEX": goal + 3 success criteria (fonte de verdade do escopo)
- `.planning/REQUIREMENTS.md` — COMP-01 (onboarding das 5 marcas VTEX com engine reconfirmada via `detect_engine`); §Future Requirements COMP-FUT-01/02/03 (marcas não-suportadas explicitamente fora desta phase)
- `.planning/PROJECT.md` — contexto do milestone v2.0; "Onboarding às cegas" proibido por design

### Decisões herdadas da Phase 25 (fundação — pré-requisito)
- `.planning/phases/25-funda-o-de-motores/25-CONTEXT.md` — D-01..D-04 (`detect_engine` retorna `"unknown"`, probe Wake, `create_brand` salva `"unknown"` como inativo), D-07/D-08 (chokepoint `list_brands(active_only)`)

### Código tocado / consumido nesta phase
- `api/routes_brands.py` — `detect_engine` (L14-69; reconfirmação de engine), `create_brand` (L72-94; engine=`"auto"` → detect, `"unknown"`→inativo D-04), `GET /brands/{key}/discover` (L134-153; descoberta de categorias), `PUT /brands/{key}/mappings` (L165-173; persiste mappings)
- `services/brand_service.py` — `add_brand`, `set_active`, `update_mappings`, `_save`/`_upsert_to_supabase`/`_save_to_json` (persistência dual dev/prod)
- `services/category_mapping.py` — `_RAW_CATEGORIES` (L45-118; slugs canônicos a ancorar — D-04), `resolve_category_for_brands` (L191; já consulta mappings dinâmicos), `get_canonical_categories` (L143; merge de mappings dinâmicos)
- `services/engines/vtex_engine.py` — `discover_categories` (L20-53; auto-discovery via `VtexApiClient.fetch_categories`), `search` (L62-84; busca por query — NÃO usa mappings)
- `services/engines/factory.py` — `get_engine` (resolve por campo `engine`), `search_all_brands` (L47-92; busca comparativa por marca, `active_only=True`)
- `core/models.py` — `DynamicBrand` / `DynamicBrandCreate` / `CategoryMapping` (`canonical_slug`/`vtex_fq_path`/`label`)
- `data/brands.json` — formato de referência (aramis/reserva/tommy = VTEX hardcoded; bck = mappings dinâmicos)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Caminho de onboarding completo já existe**: `POST /brands/` (`create_brand`) reconfirma engine; `GET /brands/{key}/discover` lista a árvore de categorias VTEX; `PUT /brands/{key}/mappings` persiste o de/para. O script seed orquestra esses três — não há fluxo novo a inventar.
- **`VTEXEngine.discover_categories`** → `VtexApiClient.fetch_categories(domain)` → `_flatten_vtex_tree` devolve lista plana `{name, path}` pronta para auto-match (D-09).
- **`resolve_category_for_brands` / `get_canonical_categories`** já fazem fallback hardcoded→dinâmico — mappings dinâmicos com slugs canônicos aparecem automaticamente no select e na resolução de busca por categoria.
- **`brand_service._save`** abstrai Supabase vs `brands.json` — reusar para a persistência dual (D-08) sem ramificar I/O.

### Established Patterns
- Marca VTEX no `brands.json`: `engine="vtex"`, `vtex_account` pode ser `null` (Aramis/Reserva/Tommy/Hering têm `null`; o `VtexApiClient` resolve pelo `domain`). `mappings: []` é o estado inicial; `bck` mostra mappings dinâmicos populados.
- Rotas finas em `api/`, lógica em `services/` — o script seed deve delegar ao `brand_service`/engines, não reimplementar regra.
- Reconfirmação de engine é **add-time only** (Phase 25 D-03) — não há reclassificação periódica de marcas já cadastradas.

### Integration Points
- Script seed → `create_brand` (reconfirma engine) → `discover_categories` (árvore) → auto-match+revisão → `update_mappings` (persiste). Tudo via service/engine layer.
- Após onboarding, as 5 entram automaticamente em `list_brands(active_only=True)` (busca/scheduler/monitor/export) — D-08 da Phase 25 já garante o filtro nos call sites.
- `GET /brands/` injeta marketplaces virtuais (ML/Netshoes/Amazon) — não confundir com as 5 marcas reais.

</code_context>

<specifics>
## Specific Ideas

- Domínios fornecidos verbatim pelo usuário (D-01). Austral com `secure.` é o único ponto de atenção (D-02).
- Filosofia de teste do projeto é **offline/determinística** (notas de spike: "sem rede/WAF") — daí o teste de contrato offline + smoke ao vivo manual (D-10), e a rejeição de teste automatizado ao vivo por marca.
- Comparabilidade ("banana com banana") é o valor central do de/para canônico — daí ancorar nos slugs existentes em vez de taxonomia livre (D-04).

</specifics>

<deferred>
## Deferred Ideas

- **Engines de marcas não-suportadas** — Wake (Richards / COMP-FUT-01), SFCC (Lacoste, Hugo Boss / COMP-FUT-02), Inditex (Zara / COMP-FUT-03). Os spikes SFCC 003-006 (`VALIDATED_LIVE_E2E_PUBLIC_BROWSER`) são insumo de milestone futuro, não desta phase.
- **Mapeamento de categorias completo** (catálogo inteiro por marca) — esta phase entrega só o núcleo comparável (D-03). Ampliar cobertura é evolução futura, possivelmente atrelada à Phase 29 (diagnóstico).
- **Diagnóstico de saúde de categorias** (ok/vazia/erro por marca) — Phase 29 (DIAG-01/02); consome os mappings criados aqui.
- **UI de gestão de marcas** (adicionar/remover/ativar-desativar) — Phase 27 (MGMT-02).
- **Frete via checkout nos sites VTEX** — Phase 30 (FRET-05).

### Reviewed Todos (not folded)
- **"Reforçar discriminação de modelo (model-words + visual como desempate)"** (`reforcar-discriminacao-modelo.md`, score 0.6) — match fraco por palavras genéricas (como/phase/marca/busca). É relevância da busca por SKU (domínio das Phases 22-23), não onboarding de marcas. **Não incorporado** — fora do escopo desta phase.

</deferred>

---

*Phase: 26-onboarding-das-5-marcas-vtex*
*Context gathered: 2026-06-19*
