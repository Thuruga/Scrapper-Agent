# Phase 40: Onboarding por URL & Workflows de Adição ao Monitoramento - Context

**Gathered:** 2026-06-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Esta phase entrega três fluxos de UX/backend independentes, todos com requisitos travados pelo ROADMAP (success criteria 1–3) — aqui decidimos **como** implementar, não **o quê**:

1. **Onboarding por URL (UX-03):** operador cola apenas a URL de uma marca; o sistema detecta o engine (`detect_engine`) e infere o nome, apresentando um formulário pré-preenchido para confirmação **antes de salvar**, com override manual disponível.
2. **Adicionar ao monitoramento (UX-04):** das três superfícies de busca (comparativa, por SKU e monitor de categoria), o operador adiciona qualquer produto ao **monitor de preços** com um clique, sem duplicata (dedup por url+marca), independentemente da superfície de origem.
3. **Toggles de marketplace (UX-05):** os marketplaces virtuais (Mercado Livre, Netshoes, Amazon) ganham toggles ativar/desativar; desativá-los faz o `cross_marketplace_service` excluir o marketplace das buscas imediatamente na próxima execução.

**Fronteiras travadas:**
- Reusa o chokepoint único de ativação `list_brands(active_only=True)` e o toggle por linha `PATCH /brands/{brand_key}/active` (MGMT-01/MGMT-02) — sem criar segundo mecanismo de "marca ativa".
- Reusa `detect_engine` (já reconhece vtex/wake/sfcc/zara/mercadolivre/netshoes/amazon) e o caminho `engine="auto"` do `create_brand`.
- Reusa o price_monitor existente (`POST /monitor/start`) como alvo do "adicionar ao monitoramento" — **não** o monitor de categoria.
- Sem novas capacidades fora destes três fluxos (frete, MAP, estoque etc. são outras phases).

</domain>

<decisions>
## Implementation Decisions

### Onboarding por URL (UX-03)
- **D-01 [inferência de nome]:** Inferir o nome da marca por ordem de precedência **JSON-LD/OG (`brand`/`organization`/`og:site_name`) → `<title>` → domínio** (ex.: `hugoboss.com.br` → "Hugo Boss"). Reaproveitar a resposta do fetch da home que o `detect_engine` já faz — sem request HTTP extra. O campo de nome é **sempre editável** no formulário de confirmação.
- **D-02 [fluxo identify vs salvar — dois endpoints]:** Criar `POST /brands/identify` como **dry-run**: detecta engine + infere nome + normaliza domínio e **NÃO persiste**. A UI mostra o formulário pré-preenchido; o operador confirma/edita; o `POST /brands/` **existente** salva. Separação limpa — `create_brand` permanece o ponto único de escrita, intacto.
- **D-03 [engine='unknown' no identify]:** Quando o identify detecta `engine='unknown'`, **avisar e permitir override manual** do engine, ou salvar mesmo assim (cai inativo via D-04 do `create_brand`: `unknown → is_active=False`, já implementado). **Não travar** o cadastro.

### Adicionar ao monitoramento (UX-04)
- **D-04 [alvo = price_monitor]:** O "Adicionar ao monitoramento" tem como alvo o **monitor de preços** (`POST /monitor/start` em `routes_product.py`), passando `url` + `brand` do card. **Não** é o monitor de categoria (`routes_monitor.py /category`).
- **D-05 [parâmetros = defaults fixos, 1 clique]:** Clique único adiciona com `interval`/`duration` **padrão**, sem modal. Operador ajusta depois na aba de monitores. Fricção mínima, condizente com "adicionar de qualquer tela com um clique".
- **D-06 [semântica de duração persistente]:** Monitorar preço de concorrente é acompanhamento contínuo — o monitor **não deve expirar sozinho cedo**. Usar duração longa ou tratar `0`/`None` como **indefinido** (a representação exata fica a critério do planner, dado que `PriceMonitorConfig` hoje tem `duration_hours`). Operador para manualmente.
- **D-07 [botão nas três superfícies]:** O botão "Adicionar ao monitoramento" aparece de forma consistente nas três superfícies (busca comparativa, busca por SKU, monitor de categoria), todas chamando o mesmo endpoint/fluxo idempotente.

### Dedup do produto monitorado (UX-04)
- **D-08 [normalização de URL — conservadora]:** Antes de comparar (dedup por **url+marca**), normalizar: host em lowercase, remover `www`, forçar `https`, remover trailing slash, e descartar **apenas** params de tracking conhecidos (`utm_*`, `gclid`, `fbclid`). **Manter** o resto do path+query — para não fundir SKUs distintos que se diferenciam por query (ex.: `?skuId=`).
- **D-09 [comportamento idempotente com feedback]:** Se já monitorado **e ativo** → toast "já está em monitoramento" (no-op; não cria segundo nem reinicia). Se existe mas está **parado** → **reativa** o monitor existente. (Hoje cada `start` gera `job_id` novo via uuid sem checar duplicata — esta phase introduz a checagem.)

### Toggles de marketplace (UX-05)
- **D-10 [persistência — promover a brands reais + reusar is_active]:** Promover Mercado Livre / Netshoes / Amazon a **entradas reais em `brands.json`** com `is_active`, toggladas pelo `PATCH /brands/{brand_key}/active` **existente** — mesmo chokepoint e mesma UI por linha do MGMT-01/MGMT-02. **Remover a injeção em runtime** do `list_brands()` (`routes_brands.py:133-160`). Esta phase passa a **exibir** o toggle que o MGMT-02 escondia para marketplace virtual.
- **D-11 [enforcement — por request]:** O `cross_marketplace_service` monta `self.engines` **a cada `cross_marketplace_search`**, lendo o estado ativo na hora e incluindo só os marketplaces ativos. Atende o critério "desativar exclui imediatamente na próxima execução" sem reiniciar o servidor. (Hoje `self.engines` é um dict hardcoded fixo no `__init__`.)

### Claude's Discretion
- UI/UX exata: aparência e posição dos toggles na tela de configurações; estilo do formulário de confirmação do onboarding; rótulo/ícone do botão "Adicionar ao monitoramento" — a critério do planner / `/gsd-ui-phase`, mantendo consistência visual com o app (distinção visual de inativas do MGMT-02).
- Valores numéricos exatos dos defaults de `interval`/`duration` (D-05/D-06) e a representação concreta de "indefinido" em `PriceMonitorConfig`.
- Forma exata da normalização de URL (D-08) — função utilitária reusável; lista exata de tracking params a descartar, desde que cubra utm_*/gclid/fbclid.
- Se marketplaces desativados continuam visíveis (cinza) nos filtros de busca ou somem — desde que o `cross_marketplace_service` os exclua de fato (D-11).
- Estrutura do `brand_key` dos marketplaces promovidos (D-10) — preservar os keys atuais (`mercado_livre`, `netshoes`, `amazon`) para não quebrar referências existentes.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requisito & Roadmap
- `.planning/ROADMAP.md` §"Phase 40: Onboarding por URL & Workflows de Adição ao Monitoramento" — Goal, requirements (UX-03, UX-04, UX-05), e os 3 success criteria (forma exata: `POST /brands/identify`, dedup por url+marca, toggles respeitados pelo `cross_marketplace_service`).
- `.planning/REQUIREMENTS.md` — UX-03 (onboarding por URL), UX-04 (adicionar ao monitoramento idempotente), UX-05 (toggles de marketplace).
- `.planning/PROJECT.md` — milestone v4.0, categoria "C — UX de Monitoramento & Busca".

### Fases anteriores (padrões a seguir)
- `.planning/phases/25-*/` e `.planning/phases/27-*/` — MGMT-01 (`PATCH /brands/{key}/active` + chokepoint `list_brands(active_only=True)`) e MGMT-02 (campo unificado de gestão de marcas, toggle por linha, distinção visual de inativas, toggle escondido para marketplace virtual — que esta phase passa a exibir).
- `.planning/phases/39-cobertura-de-marcas-hugo-boss-zara/39-CONTEXT.md` — padrão de onboarding via `brand.mappings` dinâmicos e reuso do `DynamicBrand`.

### Código a alterar/reusar
- `backend/api/routes_brands.py` — `detect_engine(domain)` (l.14), `create_brand` com `engine="auto"` (l.103-125), injeção runtime de marketplaces no `list_brands()` (l.133-160, a remover em D-10), `set_brand_active` / `PATCH /active` (l.207).
- `backend/api/routes_product.py` — `POST /monitor/start` (l.24, alvo do "adicionar ao monitoramento", D-04), `GET /monitors`, `stop/resume/delete`.
- `backend/services/price_monitor_service.py` — `PriceMonitorService.start_monitor(job_id, url, brand, interval, duration)` e persistência em `data/price_monitors.json` (D-05/D-06/D-09).
- `backend/services/cross_marketplace_service.py` — `self.engines` hardcoded no `__init__` (l.154-157) e `asyncio.gather` sobre os engines (l.321) — ponto de enforcement por request (D-11).
- `backend/core/models.py` — `DynamicBrand`, `DynamicBrandCreate`, `PriceMonitorConfig` (campo `duration_hours`), `CategoryMapping`, `BrandActiveUpdate`.
- `backend/services/brand_service.py` — `add_brand`, `list_brands`, `set_active` (chokepoint de ativação; marketplaces promovidos passam por aqui em D-10).
- `backend/data/brands.json` — onde os marketplaces promovidos passam a viver (D-10).
- `frontend/src/api/client.ts` — `startMonitor`, `getMonitors`, `getBrands`/toggle de marca; precisa de método para `POST /brands/identify` (D-02) e botão "adicionar ao monitoramento" nas 3 telas.
- `frontend/src/App.tsx` — orquestração das telas de busca comparativa / SKU / monitor de categoria (onde entra o botão de D-07).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `detect_engine(domain)` (`routes_brands.py:14`) já faz fetch da home e reconhece vtex/wake/sfcc/zara/mercadolivre/netshoes/amazon — base do `POST /brands/identify` (D-01/D-02). A mesma resposta HTTP alimenta a inferência de nome.
- `create_brand` já suporta `engine="auto"` → `detect_engine` e já trata `engine="unknown"` marcando `is_active=False` (D-04 da Phase 36) — D-03 reusa isso sem reimplementar.
- `POST /monitor/start` + `PriceMonitorService.start_monitor` já recebem `url`+`brand` e persistem em `price_monitors.json` — pronto para ser o alvo do "adicionar ao monitoramento" (D-04); falta só dedup (D-08/D-09) e defaults (D-05).
- `PATCH /brands/{brand_key}/active` + `set_active` + chokepoint `list_brands(active_only=True)` (MGMT-01) — reuso direto para os toggles de marketplace (D-10).
- `frontend/src/api/client.ts` já tem `startMonitor`, `getMonitors`, gestão de marcas e toggle — estende-se com `identify` e o botão por card.

### Established Patterns
- Ativação de marca passa por um **chokepoint único** (`list_brands(active_only=True)`); novas ativações reusam `PATCH /active` em vez de mecanismos paralelos (motivação de D-10).
- Marcas concorrentes adicionadas usam `DynamicBrand` + `brand.mappings` dinâmicos (Phase 39).
- Engines de marketplace retornam `BrandSearchResult`/`SearchProductResult`; o `cross_marketplace_service` agrega via `asyncio.gather` (ponto de filtragem para D-11).

### Integration Points
- **Onboarding:** novo `POST /brands/identify` (dry-run) → form de confirmação no frontend → `POST /brands/` (escrita).
- **Monitoramento:** botão por card nas 3 telas → `POST /monitor/start` com dedup por url+marca normalizada → `price_monitors.json`.
- **Toggles:** marketplaces movidos da injeção runtime do `list_brands()` para `brands.json` → `PATCH /active` → leitura por request no `cross_marketplace_service`.

</code_context>

<specifics>
## Specific Ideas

- O critério #1 do roadmap nomeia explicitamente o endpoint `POST /brands/identify` — o downstream deve usar esse nome.
- Preservar os `brand_key` atuais dos marketplaces (`mercado_livre`, `netshoes`, `amazon`) ao promovê-los a `brands.json`, para não quebrar referências em `cross_marketplace_service` e filtros existentes.

</specifics>

<deferred>
## Deferred Ideas

None — discussão ficou dentro do escopo da phase (3 success criteria do roadmap).

</deferred>

---

*Phase: 40-onboarding-por-url-workflows-de-adi-o-ao-monitoramento*
*Context gathered: 2026-06-29*
