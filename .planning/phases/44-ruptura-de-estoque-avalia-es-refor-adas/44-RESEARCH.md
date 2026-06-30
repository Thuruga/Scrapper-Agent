# Phase 44: Ruptura de Estoque & Avaliações Reforçadas - Research

**Researched:** 2026-06-29  
**Domain:** FastAPI/Pydantic scraper analytics, VTEX/Wake/SFCC/Shopify stock signals, Playwright cart-probe isolation, review providers  
**Confidence:** MEDIUM-HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

Fonte desta seção: copied verbatim from `.planning/phases/44-ruptura-de-estoque-avalia-es-refor-adas/44-CONTEXT.md`. [CITED: .planning/phases/44-ruptura-de-estoque-avalia-es-refor-adas/44-CONTEXT.md]

### Locked Decisions

#### Métrica de ruptura por marca
- **D-01 [denominador verificado]:** `rupture_pct` deve usar apenas produtos com estoque verificado: `out_of_stock / (in_stock + out_of_stock)`. Produtos com `stock_availability is None` entram em `unknown_stock` e não afetam o percentual.
- **D-02 [fonte da verdade]:** Persistir um resumo por execução/varredura, reutilizável por varredura manual e scheduler, com pelo menos: `total_products`, `in_stock_count`, `out_of_stock_count`, `unknown_stock_count`, `verified_stock_count`, `rupture_pct`, `brand`, `scan_id/monitor_id` e timestamp.
- **D-03 [lacuna não é erro]:** Engines/marcas que não conseguem verificar estoque naquela varredura aparecem no relatório com `unknown_stock`; `rupture_pct` fica `null` se não houver nenhum produto verificado. Isso é diferente de falha técnica da varredura.
- **D-04 [produto com variações]:** No nível agregado do produto, `stock_availability=True` se qualquer variação/tamanho tiver estoque. Produto só conta como esgotado quando nenhuma variação disponível for encontrada.

#### Operação do cart-probe
- **D-05 [sob demanda por produto]:** O operador dispara profundidade de estoque sob demanda para um produto específico de uma varredura controlada. Não executar probe em massa por padrão.
- **D-06 [persistência no produto do scan]:** O resultado do probe deve ser salvo no registro do produto daquela execução de varredura, com campos aditivos como `stock_depth_estimate`, `stock_depth_state`, `stock_depth_checked_at`, `stock_depth_source` e rótulo de "máximo observado/estimativa via cart-probe".
- **D-07 [limites conservadores]:** Começar com limite conservador: 1 produto por ação, throttle fixo, timeout curto, cleanup sempre, e máximo configurável pequeno por marca/execução. O número exato fica para o planner, mas deve ser baixo por padrão.
- **D-08 [estados explícitos]:** Se o cart-probe não medir profundidade, salvar estado explícito sem inventar quantidade. Estados mínimos: `estimated`, `unavailable`, `unsupported`, `blocked`, `temporary_failure`.
- **D-09 [sem false data]:** `0` só pode significar indisponibilidade/estoque zero quando o provider realmente retornar isso de forma confiável. Falha, bloqueio, unsupported ou timeout nunca viram quantidade zero.

#### Comentários de avaliações
- **D-10 [comentários sob demanda]:** Busca normal e varredura devem continuar leves, trazendo `rating` e `review_count` quando disponível. Comentários completos são carregados sob demanda por produto.
- **D-11 [schema compacto]:** Cada comentário retornado/salvo deve ser estruturado e compacto: `review_id`, `rating`, `title`, `text`, `author`, `created_at`, `source_provider`, e `source_ref`/`raw_url` quando existir.
- **D-12 [paginação limitada]:** Paginação de comentários é configurável com default pequeno, provavelmente 1 ou 2 páginas por produto. Dedup obrigatório por `review_id`; se provider não expõe ID estável, derivar hash estável de campos estruturados.
- **D-13 [provider coverage]:** A fase deve auditar/configurar providers conhecidos. Marcas sem caminho identificado ficam com `reviews_state="unsupported"` e não quebram busca/varredura.
- **D-14 [sem payload bruto pesado]:** Não persistir payload bruto completo de reviews por padrão. Payload bruto pode ser log/debug temporário em spike/teste, mas o contrato de produto deve ser o schema compacto.

#### Dependências e guardrails
- **D-15 [Hugo Boss dependency]:** O todo `.planning/todos/pending/hugoboss-vtex-io-category-scan.md` deve ser tratado como dependência/risco para usar Hugo Boss como prova de ruptura por categoria. Phase 44 não deve mascarar o problema com `0 produtos`; planner deve resolver ou declarar dependência antes de UAT com Hugo Boss.
- **D-16 [Phase 37 dependency]:** Phase 44 depende do schema canônico/SQLite previsto para Phase 37, mas nenhum `37-CONTEXT.md` existe nesta workspace no momento da captura. Planner deve verificar o estado real da Phase 37 antes de escolher onde persistir summaries e comentários.

### Codex's Discretion
- Nome exato dos campos e modelos internos, desde que preservem as semânticas acima e sejam aditivos.
- Se o summary de ruptura fica em JSON local existente, SQLite introduzido pela Phase 37, ou ambos em migração, dependendo do estado real da Phase 37 no momento do planejamento.
- Valor inicial exato de `max_review_pages`, timeout e throttle, desde que defaults sejam conservadores.
- Nome/forma exata do endpoint sob demanda para stock-depth e comentários.

### Deferred Ideas (OUT OF SCOPE)
- UI completa de dashboard/analytics de ruptura, além do necessário para operar/verificar a fase.
- Cart-probe automático para todos os produtos de uma varredura.
- Cart-probe em lote grande por marca.
- Ruptura por SKU/tamanho como métrica principal; Phase 44 consolida no nível produto.
- Persistir payload bruto completo de reviews.
- Heurística genérica agressiva de comentários via HTML/PDP para qualquer marca sem provider identificado.
- Reavaliar Zara/Inditex fora do envelope permitido; segue dependente de outro caminho autorizado.

### Reviewed Todos (not folded)
- `.planning/todos/pending/hugoboss-vtex-io-category-scan.md` - não é dobrado como nova feature de Phase 44; é dependência/risco herdado da Phase 39 para UAT de ruptura com Hugo Boss.
- `.planning/todos/pending/zara-comp07-deferred.md` - Zara segue bloqueada por anti-bot no envelope permitido; não usar como alvo de ruptura/reviews nesta fase.
- `.planning/todos/pending/reforcar-discriminacao-modelo.md` - pertence à precisão de busca por SKU/modelo, não a estoque ou reviews por categoria.
- `.planning/todos/pending/cap-search-history-list.md` - pertence ao histórico de busca/UX, não a Phase 44.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STOCK-01 | Na varredura por categoria, registrar porcentagem de produtos esgotados por marca. [CITED: .planning/REQUIREMENTS.md] | Use a shared rupture-summary helper over `stock_availability`, wired into scheduled monitors and manual category scans. [VERIFIED: codebase grep] |
| STOCK-02 | Capturar profundidade de estoque via requisição de 999 unidades no carrinho, rotulada como máximo observado/estimativa, only in controlled scans with ephemeral Playwright sessions, cleanup and throttle. [CITED: .planning/REQUIREMENTS.md] | Add an explicit on-demand backend action, enforce scan-product identity, use isolated Playwright context/page lifecycle, and persist explicit states. [CITED: https://playwright.dev/python/docs/browser-contexts] |
| REVW-01 | Extrair notas e comentários para marcas com provider, com paginação limitada e dedup. [CITED: .planning/REQUIREMENTS.md] | Extend `review_service.py` from summary-only providers to on-demand page fetchers returning compact review objects and unsupported states. [VERIFIED: codebase grep] |
</phase_requirements>

## Summary

Phase 44 should be planned as a backend-first analytics/provider phase, not as a broad UI/dashboard phase. [VERIFIED: codebase grep] The current code already has canonical product fields for `stock_availability`, `rating`, and `review_count`, plus brand-level `review_provider` and `review_store_id`, so implementation should add fields and services aditively instead of replacing existing result contracts. [VERIFIED: codebase grep]

The main architectural risk is split category execution paths: scheduled category monitors persist `backend/data/monitored_products_{monitor_id}.json`, while manual category scans run orchestrators that generate Excel and do not currently persist a scan artifact. [VERIFIED: codebase grep] The planner should introduce shared helpers for rupture summary, review comments, and stock-depth state, then call them from both scheduled and manual scan surfaces where the success criteria require it. [VERIFIED: codebase grep]

The cart-probe must be treated like the shipping guardrails already present in the project: explicit action, persisted domain/brand identity, no caller-supplied domain trust, timeout, throttle, sibling isolation, and explicit non-zero/non-failure states. [VERIFIED: codebase grep] Playwright documentation supports isolated browser contexts as the standard session isolation primitive, so each probe should create and close a context/page or a short-lived browser wrapper with `finally` cleanup. [CITED: https://playwright.dev/python/docs/browser-contexts]

**Primary recommendation:** Build a small backend domain layer: `stock_summary_service`, `stock_depth_service`, and extended `review_service`, with Pydantic models in `core/models.py`, conservative config in `config.py`, hermetic tests first, and minimal API/client hooks for explicit operator actions. [VERIFIED: codebase grep]

## Project Constraints (from CLAUDE.md)

- Consult Aramis coding standards via Backstage MCP `backstage_get_coding_standards` before code edits; the MCP tool was not available in this session, so planning should include a pre-edit standards check if the tool is available later. [CITED: .claude/CLAUDE.md] [VERIFIED: tool absence]
- Never commit a Backstage PAT or `.mcp.json` with credentials. [CITED: .claude/CLAUDE.md]
- Use Conventional Commits with scope when clear. [CITED: .claude/CLAUDE.md]
- Do not commit directly to `main`; use PR flow for merge. [CITED: .claude/CLAUDE.md]
- Follow Clean Code and refactoring.guru principles without over-engineering. [CITED: .claude/CLAUDE.md]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Rupture percentage by brand | API / Backend | Database / Storage | The backend owns category scan product lists and can compute `True`/`False`/`None` counts before persistence or export. [VERIFIED: codebase grep] |
| Stock-depth cart-probe | API / Backend | Browser / Client automation | The backend must gate explicit operator actions and use Playwright as an automation dependency, not browser UI logic. [CITED: .planning/REQUIREMENTS.md] |
| Review summaries | API / Backend | External review provider APIs | Existing `review_service.py` already routes by persisted brand provider and is called by VTEX search. [VERIFIED: codebase grep] |
| Review comments | API / Backend | Database / Storage | Comments are heavier data and should be fetched on demand, deduped, compacted, and persisted/returned by backend services. [CITED: .planning/phases/44-ruptura-de-estoque-avalia-es-refor-adas/44-CONTEXT.md] |
| Minimal operator actions | Browser / Client | API / Backend | Frontend only needs client methods and small controls/status surfaces; source of truth remains backend scan/product records. [VERIFIED: codebase grep] |
| Persistent scan analytics | Database / Storage | API / Backend | State says v4.0 analytics are intended for SQLite, but Phase 37 artifacts are absent, so persistence must be verified before relying on SQLite. [CITED: .planning/STATE.md] [VERIFIED: filesystem] |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `sqlite3` | Python 3.14.3 runtime | Local analytics persistence if Phase 37 has introduced SQLite | Project state locks SQLite/stdlib for analytics instead of external DB servers. [CITED: .planning/STATE.md] [VERIFIED: environment] |
| FastAPI | installed 0.132.0; registry latest 0.138.2 | API endpoints and background task dispatch | Existing backend route layer uses FastAPI and `BackgroundTasks`; official docs define background tasks as post-response work. [VERIFIED: pip show] [CITED: https://fastapi.tiangolo.com/tutorial/background-tasks/] |
| Pydantic | installed 2.12.5; registry latest 2.13.4 | Request/response/domain models with additive defaults | Existing `core/models.py` uses Pydantic v2 validators and defaults for backward-compatible contracts. [VERIFIED: pip show] [VERIFIED: codebase grep] |
| aiohttp | installed 3.13.3; registry latest 3.14.1 | Async HTTP fetches for review providers and VTEX APIs | Existing VTEX and review services use `aiohttp.ClientSession`; extending them avoids new dependencies. [VERIFIED: pip show] [VERIFIED: codebase grep] |
| Playwright Python | installed 1.58.0; registry latest 1.61.0 | Ephemeral browser sessions for controlled cart-probe | Official Playwright docs describe browser contexts as isolated sessions; current code already has `BrowserManager`. [VERIFIED: pip show] [CITED: https://playwright.dev/python/docs/browser-contexts] |
| pandas/openpyxl | pandas installed 2.3.3 | Existing Excel export path for manual scans | Existing orchestrators consolidate scan results into Excel through pandas; keep export compatibility if adding rupture columns. [VERIFIED: pip show] [VERIFIED: codebase grep] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| React | package manifest `^19.2.5`; npm latest 19.2.7 | Minimal frontend controls/status if planner includes UI action buttons | Existing frontend app is React/Vite; do not introduce a new frontend stack. [VERIFIED: package.json + npm registry] |
| Vite | package manifest `^8.0.16`; npm latest 8.1.0 | Frontend build/dev server | Existing frontend scripts use Vite. [VERIFIED: package.json + npm registry] |
| Zustand | package manifest `^5.0.14`; npm latest 5.0.14 | Existing module-scoped frontend state if UI state is needed | Existing project already uses Zustand stores; no new state library is needed. [VERIFIED: package.json + npm registry] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SQLite/JSON local persistence | Postgres or external DB | External DB server is explicitly out of scope for the milestone. [CITED: .planning/REQUIREMENTS.md] |
| Playwright cart-probe | Raw HTTP cart API only | Raw HTTP may work for VTEX simulation-style endpoints, but requirement explicitly calls for ephemeral Playwright sessions and cleanup for cart-probe. [CITED: .planning/REQUIREMENTS.md] |
| Provider-specific review routes | Generic HTML review scraping for every brand | Generic aggressive scraping is deferred; provider coverage must return `unsupported` for unknown brands. [CITED: .planning/phases/44-ruptura-de-estoque-avalia-es-refor-adas/44-CONTEXT.md] |

**Installation:**
```bash
# No new package install recommended for Phase 44.
# Existing environment should be used:
python -m pytest
python -m playwright --version
```

**Version verification:** Versions above were checked with `pip show`, `pip index versions`, `npm view`, `python -m pytest --version`, and `python -m playwright --version`. [VERIFIED: local commands]

## Package Legitimacy Audit

No new external package installs are recommended for this phase. [VERIFIED: codebase grep] `slopcheck` was installed as a Python package but no `slopcheck` executable was on PATH and `python -m slopcheck` failed, so any future newly proposed packages must be gated by the Package Legitimacy Gate before installation. [VERIFIED: local command]

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| none | — | — | — | — | not run | No new package needed. [VERIFIED: codebase grep] |

**Packages removed due to slopcheck [SLOP] verdict:** none. [VERIFIED: local command]  
**Packages flagged as suspicious [SUS]:** none. [VERIFIED: local command]

## Architecture Patterns

### System Architecture Diagram

```text
Category scan request / scheduler
  -> route or monitor service validates brand/category
  -> engine.run_bulk_scrape(category_url)
  -> RawProductBronze-like product dicts with stock_availability
  -> shared stock_summary_service.compute(products, brand, scan_id)
      -> counts True / False / None
      -> rupture_pct = out_of_stock / verified_stock_count or null
  -> persistence adapter
      -> existing JSON monitor product file, and SQLite if Phase 37 is present
  -> report/API response includes rupture summary

Operator explicit product action
  -> backend endpoint validates scan_id + product identity + brand active
  -> stock_depth_service checks throttle/limits
  -> provider probe
      -> Playwright ephemeral context/page
      -> cart-probe quantity 999
      -> parse provider response
      -> finally close page/context/browser
  -> save stock_depth_* fields on scan product record
  -> return explicit state

Review comments action
  -> endpoint receives brand + product_id/url + max_pages
  -> review_service resolves DynamicBrand.review_provider
  -> provider fetcher pages up to configured cap
  -> normalize compact ReviewComment objects
  -> dedup by review_id or stable hash
  -> persist/return reviews_state + comments
```

### Recommended Project Structure

```text
backend/
├── core/models.py                         # Additive Pydantic models and fields.
├── config.py                              # Conservative probe/review limits.
├── services/
│   ├── stock_summary_service.py           # Pure rupture math and serialization.
│   ├── stock_depth_service.py             # Explicit cart-probe orchestration and throttling.
│   ├── review_service.py                  # Extend existing provider router for comments.
│   └── stock_depth/
│       ├── base.py                        # Provider result/state types if needed.
│       └── vtex.py                        # First provider implementation, if planner scopes VTEX first.
├── api/
│   ├── routes_category.py                 # Manual scan integration/summary response.
│   └── routes_monitor.py                  # Scheduled scan products/summary/depth endpoints.
└── tests/
    ├── test_stock_summary_service.py
    ├── test_stock_depth_service.py
    ├── test_review_comments_service.py
    └── test_phase44_routes.py
```

### Pattern 1: Pure Rupture Summary Helper

**What:** Compute rupture metrics from product records without I/O. [VERIFIED: codebase grep]  
**When to use:** Use in both `run_category_scan` and manual orchestrator results before persistence/export. [VERIFIED: codebase grep]

**Example:**
```python
# Source: local code pattern in backend/core/models.py and Phase 44 D-01.
def compute_stock_summary(products: list[dict], brand: str, scan_id: str) -> dict:
    in_stock = sum(1 for p in products if p.get("stock_availability") is True)
    out_of_stock = sum(1 for p in products if p.get("stock_availability") is False)
    unknown = sum(1 for p in products if p.get("stock_availability") is None)
    verified = in_stock + out_of_stock
    rupture_pct = None if verified == 0 else out_of_stock / verified
    return {
        "brand": brand,
        "scan_id": scan_id,
        "total_products": len(products),
        "in_stock_count": in_stock,
        "out_of_stock_count": out_of_stock,
        "unknown_stock_count": unknown,
        "verified_stock_count": verified,
        "rupture_pct": rupture_pct,
    }
```

### Pattern 2: Ephemeral Playwright Probe Cleanup

**What:** Create isolated browser context/page per probe action and close them in `finally`. [CITED: https://playwright.dev/python/docs/browser-contexts]  
**When to use:** Only inside explicit stock-depth endpoint/service actions, never from search or normal category scan loops. [CITED: .planning/REQUIREMENTS.md]

**Example:**
```python
# Source: Playwright browser contexts docs + local BrowserManager cleanup pattern.
browser = await BrowserManager.get_browser()
context = await browser.new_context()
page = await context.new_page()
try:
    await page.goto(product_url, wait_until="domcontentloaded", timeout=timeout_ms)
    # add one SKU/variant to cart, set requested quantity=999, parse capped/returned quantity
finally:
    await page.close()
    await context.close()
```

### Pattern 3: Provider State Object Instead of Sentinel Numbers

**What:** Return `state`, optional `estimate`, source, and timestamp instead of using `0` for all failure modes. [CITED: .planning/phases/44-ruptura-de-estoque-avalia-es-refor-adas/44-CONTEXT.md]  
**When to use:** Stock-depth probe and review comments provider paths. [VERIFIED: codebase grep]

**Example:**
```python
# Source: local state style in VtexApiClient.simulate_shipping.
return {
    "stock_depth_state": "temporary_failure",
    "stock_depth_estimate": None,
    "stock_depth_source": "cart_probe",
    "stock_depth_label": "máximo observado/estimativa via cart-probe",
}
```

### Anti-Patterns to Avoid

- **Counting `None` as in-stock or out-of-stock:** This corrupts `rupture_pct`; unknown stock belongs outside the denominator. [CITED: .planning/phases/44-ruptura-de-estoque-avalia-es-refor-adas/44-CONTEXT.md]
- **Running cart-probe during `/search`:** The requirement explicitly excludes live search depth probing. [CITED: .planning/REQUIREMENTS.md]
- **Persisting raw review payloads by default:** Phase context locks compact review schema and defers heavy raw payload storage. [CITED: .planning/phases/44-ruptura-de-estoque-avalia-es-refor-adas/44-CONTEXT.md]
- **Using `0` for blocked/timeout/unsupported probe:** Existing shipping tests and Phase 44 decisions require explicit failure states instead of false numeric values. [VERIFIED: codebase grep] [CITED: .planning/phases/44-ruptura-de-estoque-avalia-es-refor-adas/44-CONTEXT.md]
- **Using Hugo Boss monitor `0 produtos` as a successful rupture test:** The pending todo documents that the legacy category monitor returns zero for Hugo Boss until VTEX-IO category scan strategy is fixed. [CITED: .planning/todos/pending/hugoboss-vtex-io-category-scan.md]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Data validation | Ad hoc dict validation | Pydantic models in `core/models.py` | Existing project contracts are Pydantic and additive defaults preserve old data. [VERIFIED: codebase grep] |
| Async provider HTTP | Custom socket/thread HTTP | `aiohttp.ClientSession` | Existing review/VTEX services already use aiohttp and tests fake sessions. [VERIFIED: codebase grep] |
| Browser session automation | Manual Chromium process management | Playwright browser/context/page lifecycle | Playwright contexts are documented as isolated sessions and local `BrowserManager` already centralizes launch args. [CITED: https://playwright.dev/python/docs/browser-contexts] [VERIFIED: codebase grep] |
| Rupture math | Inline repeated counts in routes | Pure `stock_summary_service` helper | Scheduled and manual scan paths both need identical semantics. [VERIFIED: codebase grep] |
| Review dedup | Naive text-only list append | Stable `review_id` or hash over structured fields | Phase context requires dedup by ID or derived stable hash. [CITED: .planning/phases/44-ruptura-de-estoque-avalia-es-refor-adas/44-CONTEXT.md] |

**Key insight:** The hard part is not the formula; it is preserving state semantics across scan paths and providers without turning unknown, unsupported, blocked, or timeout into valid business data. [VERIFIED: codebase grep] [CITED: .planning/phases/44-ruptura-de-estoque-avalia-es-refor-adas/44-CONTEXT.md]

## Common Pitfalls

### Pitfall 1: `unknown_stock` Pollutes Rupture Percentage
**What goes wrong:** `None` stock gets counted as in-stock or out-of-stock. [CITED: .planning/phases/44-ruptura-de-estoque-avalia-es-refor-adas/44-CONTEXT.md]  
**Why it happens:** Existing engines vary in stock maturity and some produce `None`. [VERIFIED: codebase grep]  
**How to avoid:** Count only `True` and `False` in the denominator, and set `rupture_pct=None` when no verified products exist. [CITED: .planning/phases/44-ruptura-de-estoque-avalia-es-refor-adas/44-CONTEXT.md]  
**Warning signs:** A brand with all unknown stock reports `0%` rupture. [CITED: .planning/phases/44-ruptura-de-estoque-avalia-es-refor-adas/44-CONTEXT.md]

### Pitfall 2: Manual and Scheduled Scans Diverge
**What goes wrong:** Monitor JSON gets rupture summary but manual Excel/WebSocket flow does not, or vice versa. [VERIFIED: codebase grep]  
**Why it happens:** `category_monitor_service.run_category_scan`, `run_orchestrator`, and `run_multi_orchestrator` are separate paths. [VERIFIED: codebase grep]  
**How to avoid:** Extract shared summary and persistence adapters before wiring routes. [VERIFIED: codebase grep]  
**Warning signs:** Tests only cover one scan path. [VERIFIED: codebase grep]

### Pitfall 3: Cart-Probe Escapes Controlled Context
**What goes wrong:** A search endpoint or automatic category loop starts probing many products. [CITED: .planning/REQUIREMENTS.md]  
**Why it happens:** Probe helper is exposed as a generic product enrichment function. [ASSUMED]  
**How to avoid:** Put stock-depth behind a distinct route/service requiring scan id and product id, with throttle and per-run caps. [CITED: .planning/phases/44-ruptura-de-estoque-avalia-es-refor-adas/44-CONTEXT.md]  
**Warning signs:** Calls to stock-depth service appear under `routes_search.py` or `VtexApiClient.search`. [VERIFIED: codebase grep]

### Pitfall 4: Provider Comments Become Raw Payload Dumps
**What goes wrong:** Full API responses get stored, expanding local data and leaking provider internals. [CITED: .planning/phases/44-ruptura-de-estoque-avalia-es-refor-adas/44-CONTEXT.md]  
**Why it happens:** Provider payloads are faster to persist than normalized schemas. [ASSUMED]  
**How to avoid:** Normalize to `review_id`, `rating`, `title`, `text`, `author`, `created_at`, `source_provider`, and `source_ref` only. [CITED: .planning/phases/44-ruptura-de-estoque-avalia-es-refor-adas/44-CONTEXT.md]  
**Warning signs:** New fields named `raw_reviews`, `payload`, or large provider JSON columns appear in persisted scan artifacts. [ASSUMED]

### Pitfall 5: Hugo Boss Category UAT Uses a Known-Broken Path
**What goes wrong:** Hugo Boss rupture UAT appears to pass with zero products or fails for the wrong reason. [CITED: .planning/todos/pending/hugoboss-vtex-io-category-scan.md]  
**Why it happens:** The pending todo documents that Hugo Boss category listings require VTEX-IO GraphQL/DOM strategy, while the legacy monitor path returns zero. [CITED: .planning/todos/pending/hugoboss-vtex-io-category-scan.md]  
**How to avoid:** Planner must either fix/sequence the todo before Hugo Boss UAT or use another working brand for automated rupture verification. [CITED: .planning/todos/pending/hugoboss-vtex-io-category-scan.md]  
**Warning signs:** `monitored_products_*` for Hugo Boss is empty after a category scan. [CITED: .planning/todos/pending/hugoboss-vtex-io-category-scan.md]

## Code Examples

### Review Comment Dedup

```python
# Source: Phase 44 D-12.
def review_key(item: dict) -> str:
    if item.get("review_id"):
        return str(item["review_id"])
    raw = "|".join(str(item.get(k) or "") for k in ("rating", "title", "text", "author", "created_at"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
```

### Explicit Unsupported Provider

```python
# Source: existing review_service provider router + Phase 44 D-13.
brand_config = brand_service.get_brand(brand_key)
if not brand_config or brand_config.review_provider in (None, "none"):
    return {"reviews_state": "unsupported", "comments": [], "rating": None, "review_count": None}
```

### Hermetic Async Test Style

```python
# Source: backend/tests/test_vtex_api_client.py.
def test_stock_summary_ignores_unknown():
    products = [
        {"stock_availability": True},
        {"stock_availability": False},
        {"stock_availability": None},
    ]
    summary = compute_stock_summary(products, brand="aramis", scan_id="scan-1")
    assert summary["verified_stock_count"] == 2
    assert summary["unknown_stock_count"] == 1
    assert summary["rupture_pct"] == 0.5
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Treat product availability as a display-only field | Use `stock_availability` as scan analytics input with `None` as unknown | Phase 44 requirement | Planner must add analytics summary, not just UI display. [CITED: .planning/REQUIREMENTS.md] |
| Shipping-style checkout calls mutate product display fields | Phase 44 cart-probe must be a separate explicit estimate with source/state/label | Phase 44 requirement | Planner should not reuse shipping fields for stock depth. [CITED: .planning/REQUIREMENTS.md] |
| Review service returns only `(rating, count)` | Add on-demand compact comments with provider states | Phase 44 requirement | Planner must extend service contract without making normal search heavy. [CITED: .planning/phases/44-ruptura-de-estoque-avalia-es-refor-adas/44-CONTEXT.md] |
| Legacy VTEX category scan for Hugo Boss | VTEX-IO GraphQL/DOM strategy pending | Phase 39 todo, 2026-06-29 | Hugo Boss is a risk until dependency is resolved. [CITED: .planning/todos/pending/hugoboss-vtex-io-category-scan.md] |

**Deprecated/outdated:**
- Using `catalog_system` category scan as sufficient proof for Hugo Boss category rupture is outdated for this workspace. [CITED: .planning/todos/pending/hugoboss-vtex-io-category-scan.md]
- Treating provider absence as a failed search is out of scope; unsupported provider is an explicit state. [CITED: .planning/phases/44-ruptura-de-estoque-avalia-es-refor-adas/44-CONTEXT.md]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Probe helper could accidentally be exposed under normal search if not isolated by route/service. | Common Pitfalls | Planner may under-spec route boundaries and violate STOCK-02 guardrail. |
| A2 | Raw provider payload persistence is tempting because it is faster than schema normalization. | Common Pitfalls | Planner may overbuild storage and violate D-14. |
| A3 | Provider-specific comment endpoint shapes for Trustvox are not fully verified from official docs in this session. | Open Questions | Planner should include a provider spike before locking exact Trustvox comment URL/fields. |

## Open Questions (RESOLVED)

1. **Has Phase 37 actually created SQLite schema/services?**
   - What we know: State says v4.0 analytics migrate to SQLite stdlib, but no Phase 37 directory exists in this workspace. [CITED: .planning/STATE.md] [VERIFIED: filesystem]
   - What's unclear: Whether implementation already exists in dirty files, another worktree, or not yet. [VERIFIED: git status]
   - Recommendation: Planner should start with a persistence checkpoint and choose JSON fallback only if SQLite is absent. [VERIFIED: codebase grep]
   - **RESOLVED:** Plan `44-01` starts with a persistence reality check and uses JSON/local helpers when Phase 37 SQLite artifacts are absent; if a valid SQLite service exists during execution, the executor uses it through a thin adapter without inventing tables or schema pushes.

2. **Which providers truly expose comment pages for current brands?**
   - What we know: `brands.json` has `trustvox` configured only for `aramis`; most brands have `review_provider="none"`. [VERIFIED: codebase grep]
   - What's unclear: Exact comment endpoint and stable ID fields for Trustvox and any VTEX-native brand after provider audit. [ASSUMED]
   - Recommendation: Add a short provider coverage task before implementation locks URL/field mappings. [ASSUMED]
   - **RESOLVED:** Plan `44-04` begins with a `backend/data/brands.json` provider coverage audit/configuration task: supported providers require recorded evidence, and brands without supported-provider evidence get explicit `review_provider="none"` plus unsupported rationale.

3. **Should cart-probe first target VTEX only?**
   - What we know: Existing shipping simulation and SKU/seller selection are strongest for VTEX; non-VTEX stock-depth providers are not established in code. [VERIFIED: codebase grep]
   - What's unclear: Whether Wake/Shopify/SFCC public cart APIs can return capped quantity safely within the phase. [ASSUMED]
   - Recommendation: Plan a provider interface with VTEX implementation first and explicit `unsupported` for others unless a spike proves support. [VERIFIED: codebase grep]
   - **RESOLVED:** Plans use a stock-depth provider interface with VTEX as the first supported implementation and explicit `unsupported` states for other engines unless execution evidence proves support within the phase guardrails.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python | backend/tests/services | yes | 3.14.3 | none needed. [VERIFIED: local command] |
| pip | package metadata checks | yes | 25.3 | none needed. [VERIFIED: local command] |
| pytest module | test execution | yes | 9.0.3 via `python -m pytest` | Use module invocation because `pytest` entry point is not on PATH. [VERIFIED: local command] |
| Playwright Python module | cart-probe/browser tests | yes | 1.58.0 via `python -m playwright --version` | Skip live browser UAT if browsers are not installed; use hermetic service tests. [VERIFIED: local command] |
| `playwright` console script | direct CLI usage | no | — | Use `python -m playwright`. [VERIFIED: local command] |
| Node.js | frontend build/client changes | yes | 24.13.1 | none needed. [VERIFIED: local command] |
| npm | frontend package scripts | yes | 11.8.0 | none needed. [VERIFIED: local command] |
| Context7 CLI | documentation lookup | no | — | Used official docs via web fetch. [VERIFIED: local command] |
| GSD helper CLI | init/graph/commit helpers | no | — | Use explicit file inspection; commit may need manual follow-up if required. [VERIFIED: local command] |
| Backstage MCP standards tool | project coding standards | no | — | Planner should run it if available before implementation edits. [CITED: .claude/CLAUDE.md] [VERIFIED: tool absence] |

**Missing dependencies with no fallback:**
- Backstage coding standards MCP is not available in this session, but implementation should check it if available in a later environment. [CITED: .claude/CLAUDE.md] [VERIFIED: tool absence]

**Missing dependencies with fallback:**
- `pytest`, `playwright`, and `slopcheck` console scripts are not on PATH; use `python -m pytest` and `python -m playwright`, and rerun package legitimacy only if new packages are proposed. [VERIFIED: local command]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3. [VERIFIED: local command] |
| Config file | `pytest.ini` with `testpaths = backend/tests` and `pythonpath = backend`. [VERIFIED: codebase grep] |
| Quick run command | `python -m pytest backend/tests/test_stock_summary_service.py backend/tests/test_review_comments_service.py backend/tests/test_stock_depth_service.py -q` [VERIFIED: local command] |
| Full suite command | `python -m pytest` [VERIFIED: local command] |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| STOCK-01 | `rupture_pct` counts only `True`/`False`, `None` is `unknown_stock`, all-unknown yields `null`. | unit | `python -m pytest backend/tests/test_stock_summary_service.py -q` | no, Wave 0. [VERIFIED: filesystem] |
| STOCK-01 | Scheduled monitor persists scan summary next to products. | integration | `python -m pytest backend/tests/test_phase44_routes.py -q` | no, Wave 0. [VERIFIED: filesystem] |
| STOCK-02 | Probe is explicit, throttled, cleans up Playwright page/context, and returns state not false `0`. | unit | `python -m pytest backend/tests/test_stock_depth_service.py -q` | no, Wave 0. [VERIFIED: filesystem] |
| STOCK-02 | Search routes never invoke stock-depth. | regression | `python -m pytest backend/tests/test_stock_depth_service.py::test_search_path_does_not_call_probe -q` | no, Wave 0. [VERIFIED: filesystem] |
| REVW-01 | Provider fetcher returns rating/count/comments, limits pages, dedups IDs/hash, and `unsupported` for unknown providers. | unit | `python -m pytest backend/tests/test_review_comments_service.py -q` | no, Wave 0. [VERIFIED: filesystem] |

### Sampling Rate
- **Per task commit:** `python -m pytest backend/tests/test_stock_summary_service.py backend/tests/test_review_comments_service.py backend/tests/test_stock_depth_service.py -q`. [VERIFIED: local command]
- **Per wave merge:** `python -m pytest`. [VERIFIED: local command]
- **Phase gate:** Full suite green plus one controlled manual UAT for a non-Hugo-Boss category unless the Hugo Boss VTEX-IO todo is resolved first. [CITED: .planning/todos/pending/hugoboss-vtex-io-category-scan.md]

### Wave 0 Gaps
- [ ] `backend/tests/test_stock_summary_service.py` covers STOCK-01 formula and all-unknown state. [VERIFIED: filesystem]
- [ ] `backend/tests/test_stock_depth_service.py` covers STOCK-02 explicit action, throttle, cleanup, and state mapping with fake Playwright/provider. [VERIFIED: filesystem]
- [ ] `backend/tests/test_review_comments_service.py` covers REVW-01 provider routing, page cap, dedup, and unsupported state. [VERIFIED: filesystem]
- [ ] `backend/tests/test_phase44_routes.py` covers API validation and route wiring if planner adds endpoints. [VERIFIED: filesystem]

Verification performed during research: `python -m pytest backend/tests/test_vtex_api_client.py::TestParseProductDictCharacterization::test_full_parse_in_stock_with_discount backend/tests/test_vtex_shipping.py::TestSelectCandidate -q` passed with 4 tests. [VERIFIED: local command]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | yes | Existing shared API key header pattern in `frontend/src/api/client.ts`; do not expose unauthenticated probe/comment mutation endpoints. [VERIFIED: codebase grep] |
| V3 Session Management | partial | Playwright probe sessions must be ephemeral browser contexts/pages and closed after each action. [CITED: https://playwright.dev/python/docs/browser-contexts] |
| V4 Access Control | yes | Validate `brand_key`, scan id, and product identity server-side before stock-depth mutation. [VERIFIED: codebase grep] |
| V5 Input Validation | yes | Pydantic request models for `scan_id`, `brand_key`, `product_url/product_id`, `max_pages`, and probe quantity cap. [VERIFIED: codebase grep] |
| V6 Cryptography | no new crypto | Use existing hashing only for non-security dedup IDs if provider lacks stable ID. [CITED: .planning/phases/44-ruptura-de-estoque-avalia-es-refor-adas/44-CONTEXT.md] |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Caller supplies arbitrary domain for cart-probe | Tampering / SSRF | Resolve domain from persisted `brand_service` and scan product; existing shipping code documents this pattern. [VERIFIED: codebase grep] |
| Probe flood against competitor cart | Denial of Service | Enforce explicit action, 1 product per action, throttle, timeout, and low per-brand/per-run caps. [CITED: .planning/phases/44-ruptura-de-estoque-avalia-es-refor-adas/44-CONTEXT.md] |
| Review payload bloat or sensitive raw logging | Information Disclosure | Store compact normalized comments only and avoid raw provider payload persistence by default. [CITED: .planning/phases/44-ruptura-de-estoque-avalia-es-refor-adas/44-CONTEXT.md] |
| False business data from failures | Tampering | Map blocked/timeout/unsupported to explicit states and never to numeric zero. [CITED: .planning/phases/44-ruptura-de-estoque-avalia-es-refor-adas/44-CONTEXT.md] |

## Sources

### Primary (HIGH confidence)
- `.planning/phases/44-ruptura-de-estoque-avalia-es-refor-adas/44-CONTEXT.md` - locked Phase 44 decisions, boundaries, deferred items. [CITED: .planning/phases/44-ruptura-de-estoque-avalia-es-refor-adas/44-CONTEXT.md]
- `.planning/REQUIREMENTS.md` - STOCK-01, STOCK-02, REVW-01 and out-of-scope guardrails. [CITED: .planning/REQUIREMENTS.md]
- `.planning/STATE.md` - SQLite analytics intent, guardrails, Hugo Boss/Lacoste state. [CITED: .planning/STATE.md]
- `.claude/CLAUDE.md` - Backstage standards and repo conventions. [CITED: .claude/CLAUDE.md]
- Codebase grep and file reads across `backend/core/models.py`, `backend/services/category_monitor_service.py`, `backend/api/routes_category.py`, `backend/api/routes_monitor.py`, `backend/services/review_service.py`, `backend/services/vtex_api_scraper.py`, `backend/core/browser_manager.py`, `backend/config.py`, `frontend/src/api/client.ts`, and `backend/data/brands.json`. [VERIFIED: codebase grep]
- Playwright Python docs for browser contexts and isolation. [CITED: https://playwright.dev/python/docs/browser-contexts]
- FastAPI background task docs. [CITED: https://fastapi.tiangolo.com/tutorial/background-tasks/]

### Secondary (MEDIUM confidence)
- VTEX Checkout API and Reviews/Ratings API pages were reachable during research, but exact cart-depth and review-comment endpoint mapping still needs provider spike against live brands. [CITED: https://developers.vtex.com/docs/api-reference/checkout-api] [CITED: https://developers.vtex.com/docs/api-reference/reviews-and-ratings-api]
- Python `sqlite3` official docs were reachable; exact schema depends on Phase 37 artifacts. [CITED: https://docs.python.org/3/library/sqlite3.html]

### Tertiary (LOW confidence)
- Trustvox comment endpoint details were not verified from official docs in this session; current code verifies only Trustvox summary via observed existing implementation. [VERIFIED: codebase grep] [ASSUMED]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Existing dependencies, manifests, and installed versions were verified locally; no new packages are needed. [VERIFIED: local command]
- Architecture: MEDIUM-HIGH - Existing scan/review/stock code was inspected, but Phase 37 persistence state is unresolved. [VERIFIED: codebase grep] [VERIFIED: filesystem]
- Pitfalls: HIGH for stock semantics and Hugo Boss risk; MEDIUM for provider comment details. [CITED: .planning/phases/44-ruptura-de-estoque-avalia-es-refor-adas/44-CONTEXT.md] [CITED: .planning/todos/pending/hugoboss-vtex-io-category-scan.md]

**Research date:** 2026-06-29  
**Valid until:** 2026-07-06 for provider endpoint details; 2026-07-29 for local architecture/persistence findings.
