# Phase 42: Frete para Marketplaces & Matriz Multi-Regional - Research

**Researched:** 2026-07-02
**Domain:** Shipping provider extension (Mercado Livre / Amazon / Netshoes) + on-demand multi-region CEP quoting with cache/throttle
**Confidence:** MEDIUM-HIGH (architecture and code paths verified directly against the repo; the two external facts that could not be verified live — ML's `/shipping_options` field names and CEP validity for capitals — are corroborated by multiple independent secondary sources, not primary docs)

## Summary

This phase is almost entirely a **wiring and adaptation** exercise, not new architecture. Phase 41 already built the exact contract (`BaseShipping`, `ShippingCalculation`, `ShippingState`, `resolve_shipping_provider`) that this phase extends with three new providers. All three marketplace engines already have working ad-hoc shipping logic (`calculate_shipping`/`calculate_shipping_advanced`) proven live in production debugging sessions (`.planning/debug/monitor-marketplace-pendente.md`): Mercado Livre resolves via a real public API (`api.mercadolibre.com/items/{id}/shipping_options`) with a Playwright fallback that defeats the Anubis PoW challenge; Amazon reads a delivery-message DOM block with CAPTCHA detection; Netshoes has a full Playwright CEP-modal flow that is reliably defeated by Akamai's edge block (documented, reproducible, infra-only limitation — not a parser bug).

The work is: (1) wrap each engine's existing logic inside a new `BaseShipping` subclass that maps ad-hoc dict output into `ShippingCalculation`/`ShippingInfo`, adding delivery-time extraction where missing (Amazon); (2) register the three engines in `resolve_shipping_provider`; (3) build a new, independent on-demand "Matriz Regional" feature — a small orchestration layer that calls the *same* resolver 5 times (once per curated CEP) with throttle and `(product-identity, cep)` caching, backed by a new JSON file (`backend/data/cep_matrix.json` for the CEP list, plus a JSON cache file following the existing `backend/data/*.json` local-storage pattern) since Phase 37/SQLite is confirmed **not yet delivered** (`[ ]` in ROADMAP.md as of this research).

**Primary recommendation:** Build `MercadoLivreShipping`, `AmazonShipping`, `NetshoesShipping` in `backend/services/shipping/` as thin adapters over each engine's already-proven `calculate_shipping`/`calculate_shipping_advanced`/`_run_playwright_shipping` methods (do not rewrite the scraping logic — only reshape output and add Netshoes' `blocked` state and Amazon's delivery-time parsing). Build the regional matrix as a new standalone module (`backend/services/shipping/regional_matrix.py` or similar) that is a *caller* of `resolve_shipping_provider`, never a modification to it, with an explicit boolean/context guard that live-scan code paths cannot reach.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Marketplace shipping quote (cost+time) | API/Backend (`services/shipping/*.py`) | — | Pure server-side HTTP/Playwright calls to marketplace APIs/PDPs; no browser-tier logic needed |
| Shipping provider resolution | API/Backend (`services/shipping/resolver.py`) | — | Single chokepoint per Phase 41 convention; must not be duplicated |
| Regional CEP matrix orchestration | API/Backend (new service module) | Database/Storage (JSON cache file) | Batches 5 resolver calls with throttle; persists cache between requests |
| CEP curated list | Database/Storage (`backend/data/cep_matrix.json`) | — | Static config data, editable by operator per D-08 |
| Matrix cache `(sku, cep)` | Database/Storage (JSON file, TTL-bound) | — | Phase 37/SQLite not yet delivered; JSON is the confirmed fallback (D-16 in CONTEXT.md) |
| "Matriz Regional" trigger button | Browser/Client (`frontend/src/App.tsx`) | — | UI action next to existing "Calcular Frete" buttons (D-06) |
| Guard against inline matrix execution | API/Backend (call-site check in matrix service, never in resolver) | — | Resolver must stay generic and reusable; the guard belongs to the matrix orchestration entrypoint only |

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Frete de marketplaces (FRET-08)**
- **D-01 [Netshoes — tentar ao vivo, cair em `blocked`]:** Reusar `_run_playwright_shipping`/CEP modal; em falha (Akamai — evidência já documentada), cair em estado `blocked` explícito, nunca frete falso/zero.
- **D-02 [Prazo de entrega — melhor esforço por marketplace]:** Extrair prazo nos 3 marketplaces, não só custo. ML já tem prazo estruturado em `/shipping_options`. Amazon: estender `_parse_shipping_text` para também extrair prazo. Netshoes: mesmo tratamento quando não bloqueada; se bloqueada, `blocked` cobre custo e prazo juntos.
- **D-03 [Consolidar no `BaseShipping`]:** Criar `MercadoLivreShipping`, `AmazonShipping`, `NetshoesShipping` (nomes a critério do planner) em `backend/services/shipping/`, registrados em `resolve_shipping_provider`. Reusar a lógica ad-hoc já validada em cada engine, adaptando para `ShippingCalculation`/`ShippingInfo`.
- **D-04 [Endpoint único]:** `/search/calculate-shipping-brand` passa a suportar `engine in {mercadolivre, amazon, netshoes}` via resolver. `/search/calculate-shipping` (legado, usado pela UI cross-marketplace) pode continuar existindo como está, sem lógica nova.
- **D-05 [UI cross-marketplace já existe]:** Botão "Calcular Frete" já existe em `frontend/src/App.tsx` (~L2525) e em `_enrich_pdp_and_shipping`. Esta fase garante que preenche prazo e trata `blocked` sem quebrar a UI — sem criar botão novo.

**Matriz de Frete Multi-Regional (FRET-09)**
- **D-06 [Ponto de entrada — reusar botões existentes]:** Ação "Matriz Regional" ao lado dos botões "Calcular Frete" já existentes (`frontend/src/App.tsx`, ~L1777 e ~L2525). Sem painel/tela dedicada nova.
- **D-07 [Escopo de engines — todos, sempre]:** Botão aparece para qualquer engine com provider de frete implementado (VTEX, Wake, Shopify, ML, Amazon, Netshoes), inclusive quando o resultado é `unsupported`/`blocked` em todas as 5 regiões. Nunca esconder a ação para evitar falha esperada.
- **D-08 [CEPs — capitais por região, curados por Claude]:** `backend/data/cep_matrix.json` começa com 1 CEP por capital/região; curadoria exata a critério do planner/pesquisa; arquivo editável depois.
- **D-09 [Cache — TTL curto]:** Cache por `(sku, cep)` expira em horas (não permanente); segue padrão de `config.py` (`STOCK_PROBE_THROTTLE_SECONDS`); valor exato a critério do planner; deve ser setting nomeado, não hardcoded.
- **D-10 [Guard contra execução inline]:** Chamada de matriz precisa de guard explícito e testado que impede execução a partir de `cross_marketplace_search`/`run_category_scan`; só alcançável pela ação on-demand "Matriz Regional" por produto.

### Claude's Discretion
- Nomes exatos das classes/arquivos dos novos providers de marketplace em `services/shipping/`.
- Forma exata de extrair prazo por marketplace (seletor/regex/campo de API) — preservando `raw_text` quando não houver parse confiável.
- Layout exato da UI da Matriz Regional (tabela de 5 linhas, modal, tooltip, etc.).
- Valor exato do TTL do cache (D-09), do throttle entre requisições da matriz e dos CEPs de cada capital (D-08).
- Persistência da matriz: JSON local (Phase 37/SQLite não entregue — **confirmado nesta pesquisa**, ver seção "Phase 37 Status" abaixo).
- Decomposição exata de `resolve_shipping_provider` para os 3 novos engines (classes separadas vs. `MarketplaceShipping` parametrizada).

### Deferred Ideas (OUT OF SCOPE)
- Proxy residencial/pago ou bypass de anti-bot para desbloquear Netshoes de verdade.
- Migrar a matriz para SQLite antes da Phase 37 existir de fato.
- UI de analytics/dashboard sobre a matriz (histórico de variação de frete por região).
- Ampliar a matriz para múltiplos produtos de uma vez (lote) — roadmap trava "para um produto".

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FRET-08 | Sistema calcula frete para os marketplaces (ML, Netshoes, Amazon) | Confirmed exact locations of `calculate_shipping`/`calculate_shipping_advanced`/`_run_playwright_shipping` in all 3 engines; confirmed `BaseShipping`/`ShippingCalculation` contract from Phase 41; confirmed ML API field shape (MEDIUM confidence, see Open Questions); confirmed Amazon delivery-text selectors already exist; confirmed Netshoes `blocked` evidence and existing `StockDepthState.BLOCKED` precedent for UI vocabulary |
| FRET-09 | Matriz de Frete Multi-Regional com guard-rails (on-demand, throttle, cache por sku+cep, CEPs curados) | Confirmed Phase 37/SQLite NOT delivered (JSON is correct default); confirmed `config.py` throttle/TTL naming convention (`STOCK_PROBE_THROTTLE_SECONDS` pattern); confirmed 5 valid capital CEPs (MEDIUM confidence, web-corroborated); confirmed existing JSON-file persistence pattern in `backend/data/*.json`; confirmed `resolve_shipping_provider` as single chokepoint to reuse (not reimplement) per product×CEP call; confirmed guard precedent in Phase 44 (`STOCK_PROBE` guard: only invoked from controlled scan paths, never live search) |

## Project Constraints (from CLAUDE.md)

- **Coding standards lookup required:** Project instructs to consult `backstage_get_coding_standards` via Backstage MCP before any code change. **This session had no `.mcp.json` configured** (only `.mcp.json.example` present) — same exception already granted and documented in prior phases (`[33-01/Backstage-exception]` in STATE.md). The planner/executor should re-check for `.mcp.json` at execution time; if still absent, follow the same exception precedent (Clean Code + existing neighbor-file conventions + refactoring.guru principles).
- **Commit convention:** Conventional Commits with scope when domain is clear.
- **Branch naming:** `feat/`, `fix/`, `chore/`, `refactor/`, `docs/` from `main`. Current branch is `fix/marketplace-price-monitor` (pre-existing, not created by this phase).
- **PRs required for `main`. Never commit directly to `main`.**
- **Code quality:** Clean Code + refactoring.guru principles — no over-engineering. This directly supports the "wrap, don't rewrite" recommendation below: the marketplace shipping logic already works and is battle-tested; new providers should be thin adapters, not reimplementations.

## Standard Stack

### Core
No new third-party packages are required. All work reuses libraries already present and imported elsewhere in the codebase.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `aiohttp` | (already installed — used by `wake.py`/`shopify.py`) | Async HTTP for ML's public shipping API (`api.mercadolibre.com`) | Matches existing `WakeShipping`/`ShopifyShipping` provider pattern exactly |
| `curl_cffi` | (already installed — used across all 3 marketplace engines) | Impersonated HTTP session for Amazon/Netshoes PDP fetch, ML item resolution | Already the primary fetch path in all 3 engines; reuse, don't replace |
| `playwright` (sync + async APIs) | (already installed) | Fallback rendering for ML (Anubis), Amazon (CAPTCHA), Netshoes (CEP modal + Akamai probe) | Already wired via `BrowserManager` and inline `sync_playwright`/`async_playwright` calls in each engine |
| `BeautifulSoup` (bs4) | (already installed) | HTML parsing for delivery-time/price extraction | Already used throughout `amazon_engine.py`/`netshoes_engine.py`/`mercado_livre_engine.py` |

### Supporting
No supporting libraries needed beyond stdlib (`json`, `time`/`asyncio.sleep` for throttle, `pathlib`).

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| JSON file cache for `(sku, cep)` | SQLite (Phase 37 schema) | Phase 37 not delivered — SQLite would be premature infra; JSON matches every other Phase 37-blocked precedent (D-16 in 44-CONTEXT.md, and this phase's own CONTEXT.md D-16 equivalent) |
| Throttle via `asyncio.sleep` between matrix CEP calls | A queue/worker with rate limiter library | Existing `STOCK_PROBE_THROTTLE_SECONDS` pattern (Phase 44) uses plain `asyncio.sleep` — no external rate-limit library anywhere in the codebase; introducing one would be inconsistent over-engineering |

**Installation:** None required — this phase adds zero new dependencies.

**Version verification:** N/A (no new packages).

## Package Legitimacy Audit

**Not applicable — this phase installs no new external packages.** All functionality is built from already-installed libraries (`aiohttp`, `curl_cffi`, `playwright`, `bs4`) and stdlib. No `slopcheck`/registry verification needed.

## Architecture Patterns

### System Architecture Diagram

```
                         ┌─────────────────────────────┐
                         │  frontend/src/App.tsx        │
                         │  "Calcular Frete" button      │
                         │  (existing, ~L1777 / ~L2525)  │
                         │  + NEW "Matriz Regional" btn   │
                         │  (D-06, next to it)            │
                         └───────────┬──────────────┬────┘
                                     │              │
                     single CEP     │              │  5 CEPs (on-demand)
                                     ▼              ▼
        ┌────────────────────────────────┐   ┌──────────────────────────────┐
        │ POST /search/calculate-shipping-│   │ POST /search/calculate-      │
        │ brand  (existing endpoint,       │   │ shipping-matrix (NEW)         │
        │ extended to accept engine in     │   │                                │
        │ {mercadolivre,amazon,netshoes})  │   │ Guard: only reachable from     │
        └───────────────┬─────────────────┘   │ this route — NEVER from        │
                         │                     │ cross_marketplace_search or    │
                         ▼                     │ run_category_scan (D-10)       │
        ┌────────────────────────────────┐    └───────────────┬────────────────┘
        │ resolve_shipping_provider(brand)│                    │
        │ (existing chokepoint, extended  │◄───────────────────┘  calls resolver
        │  with 3 new engine branches)    │      5x (once per curated CEP),
        └───────────────┬─────────────────┘      with throttle between calls
                         │
       ┌─────────────────┼──────────────────┐
       ▼                 ▼                  ▼
┌─────────────┐  ┌──────────────┐  ┌──────────────────┐
│ MercadoLivre │  │ AmazonShipping│  │ NetshoesShipping  │
│ Shipping     │  │               │  │                    │
│ (NEW, wraps  │  │ (NEW, wraps   │  │ (NEW, wraps        │
│ existing     │  │ existing      │  │ existing           │
│ calculate_   │  │ calculate_    │  │ _run_playwright_   │
│ shipping +   │  │ shipping_     │  │ shipping; maps      │
│ _run_        │  │ advanced +    │  │ Akamai failure to   │
│ playwright_  │  │ _parse_       │  │ ShippingState.      │
│ shipping)    │  │ shipping_text)│  │ BLOCKED (new state) │
└──────┬───────┘  └───────┬───────┘  └─────────┬──────────┘
       │                  │                    │
       ▼                  ▼                    ▼
  api.mercadolibre    Amazon PDP DOM       Netshoes CEP modal
  .com/items/{id}/    (#deliveryBlock      (Playwright) →
  shipping_options    Message, etc.) +     Akamai "Access
  (real API) +        CAPTCHA detection    Denied" (~343B,
  Playwright/Anubis                        documented, no
  fallback                                 content ever served)

                                     │
                                     ▼
                    ┌─────────────────────────────────┐
                    │ Matrix cache (NEW):                │
                    │ backend/data/                       │
                    │   shipping_matrix_cache.json        │
                    │ Key: (product-identity, cep)        │
                    │ TTL: hours (config setting)          │
                    └─────────────────────────────────┘
                                     │
                    ┌─────────────────────────────────┐
                    │ backend/data/cep_matrix.json (NEW)  │
                    │ 5 curated capital CEPs, editable     │
                    │ by operator (D-08)                    │
                    └─────────────────────────────────┘
```

**Guard-rail placement:** `cross_marketplace_search` (routes_search.py L446) and `run_category_scan` (category_monitor_service.py L43) must NOT import or call the matrix orchestration module at all — the guard is architectural (no call path exists), reinforced by a test that asserts neither function references the matrix module/function by name (see Common Pitfalls → Pitfall 4).

### Recommended Project Structure
```
backend/services/shipping/
├── base.py                    # existing — BaseShipping, ShippingCalculation, ShippingState
├── resolver.py                # existing — extend with 3 new engine branches
├── wake.py                    # existing, untouched
├── shopify.py                 # existing, untouched
├── unsupported.py             # existing, untouched
├── mercado_livre.py           # NEW — MercadoLivreShipping
├── amazon.py                  # NEW — AmazonShipping
├── netshoes.py                # NEW — NetshoesShipping
└── regional_matrix.py         # NEW — matrix orchestration (throttle + cache + guard)
backend/data/
├── cep_matrix.json            # NEW — curated CEP list (D-08)
└── shipping_matrix_cache.json # NEW — (product_id, cep) → result + TTL timestamp
backend/config.py              # extend Settings with SHIPPING_MATRIX_* constants
backend/api/routes_search.py   # extend calculate-shipping-brand engine branch check;
                                # add POST /search/calculate-shipping-matrix (NEW)
frontend/src/App.tsx           # extend isBrandShippingSupported (~L1708) to include
                                # mercadolivre/amazon/netshoes; add "Matriz Regional"
                                # button next to existing buttons (~L1777, ~L2525)
```

### Pattern 1: Thin BaseShipping adapter over existing engine logic
**What:** Each new provider class implements `async def calculate(product, zipcode, brand) -> ShippingCalculation` by delegating to the marketplace engine's already-proven method, then reshaping the dict result into `ShippingInfo`/`ShippingCalculation`.
**When to use:** For all 3 marketplace providers — this is exactly what D-03 mandates and what `WakeShipping`/`ShopifyShipping` already demonstrate as the house pattern.
**Example (Mercado Livre — sketch based on verified existing code):**
```python
# Source: backend/services/shipping/wake.py (existing pattern) +
#         backend/services/engines/mercado_livre_engine.py (existing logic, verified)
from services.shipping.base import (
    BaseShipping, ShippingCalculation, ShippingState,
    get_field, is_url_allowed_for_brand, normalize_zipcode, sorted_shipping_options,
)
from services.engines.mercado_livre_engine import MercadoLivreEngine


class MercadoLivreShipping(BaseShipping):
    def __init__(self, engine: MercadoLivreEngine | None = None) -> None:
        self.engine = engine or MercadoLivreEngine()

    async def calculate(self, product, zipcode, brand) -> ShippingCalculation:
        try:
            cep = normalize_zipcode(zipcode)
        except ValueError:
            return ShippingCalculation(state=ShippingState.UNAVAILABLE_FOR_CEP, message="CEP invalido")

        product_url = str(get_field(product, "url", "") or "")
        if not is_url_allowed_for_brand(product_url, brand):
            return ShippingCalculation(state=ShippingState.UNSUPPORTED,
                                        message="URL do produto nao pertence ao dominio da marca")

        # Reuse existing, already-live-tested logic — do not reimplement.
        result = await self.engine.calculate_shipping_advanced(product_url, cep)
        if not result:
            return ShippingCalculation(state=ShippingState.TEMPORARY_FAILURE,
                                        message="Frete temporariamente indisponivel")
        # Map existing {"is_free_shipping":..., "shipping_price":...} shape into ShippingInfo,
        # extending with estimated_delivery_days once D-02 API field mapping is confirmed live.
        ...
```
**Note:** This example is illustrative of the adapter pattern, not a finished implementation — the planner/executor must decide exact field mapping once ML's live API response is inspected (see Open Questions).

### Pattern 2: Blocked state (new `ShippingState.BLOCKED`)
**What:** Add a fourth explicit state to `ShippingState` (currently `AVAILABLE`, `UNAVAILABLE_FOR_CEP`, `TEMPORARY_FAILURE`, `UNSUPPORTED`) for Netshoes' documented Akamai edge-block, matching the exact precedent already established in `backend/services/stock_depth/base.py` (`StockDepthState.BLOCKED`).
**When to use:** Only for Netshoes shipping when both curl_cffi and Playwright are confirmed blocked at the edge (343-byte "Access Denied" response, zero `__INITIAL_STATE__`, zero JSON-LD — the exact diagnostic already captured in `.planning/debug/monitor-marketplace-pendente.md`).
**Example:**
```python
# Source: backend/services/stock_depth/base.py (existing precedent, verified)
class ShippingState:
    AVAILABLE = "available"
    UNAVAILABLE_FOR_CEP = "unavailable_for_cep"
    TEMPORARY_FAILURE = "temporary_failure"
    UNSUPPORTED = "unsupported"
    BLOCKED = "blocked"  # NEW — mirrors StockDepthState.BLOCKED

DEFAULT_MESSAGES = {
    # ...existing entries...
    ShippingState.BLOCKED: "Bloqueado (anti-bot)",  # exact vocabulary from
    # frontend/src/App.tsx:437 — reuse verbatim for UI consistency (specifics section)
}
```

### Pattern 3: Regional matrix as a resolver *caller*, never a resolver *modification*
**What:** The matrix service loops over the 5 curated CEPs and calls `resolve_shipping_provider(brand)` once, then `provider.calculate(product, cep, brand)` 5 times (once per CEP) with a throttle sleep between calls and a cache check before each call.
**When to use:** For the entire FRET-09 implementation. Never add CEP-looping logic inside `resolver.py` or any `BaseShipping` subclass — that would violate the single-provider-per-call contract from Phase 41 and make VTEX/Wake/Shopify base classes aware of matrix concerns they don't need.
**Example (sketch):**
```python
# NEW file: backend/services/shipping/regional_matrix.py
import asyncio
import time

from services.shipping.resolver import resolve_shipping_provider
from services.shipping.base import get_field
from config import settings  # SHIPPING_MATRIX_THROTTLE_SECONDS, SHIPPING_MATRIX_CACHE_TTL_SECONDS

async def calculate_regional_matrix(product, brand, cep_list: list[dict]) -> list[dict]:
    """Called ONLY from the on-demand 'Matriz Regional' route handler.
    NEVER call this from cross_marketplace_search or run_category_scan (D-10)."""
    provider = resolve_shipping_provider(brand)
    product_identity = _stable_identity(product)  # URL-based when sku absent (Pitfall 6)
    results = []
    for i, region_cep in enumerate(cep_list):
        cep = region_cep["cep"]
        cached = _read_cache(product_identity, cep)
        if cached is not None:
            results.append({**region_cep, **cached})
            continue
        if i > 0:
            await asyncio.sleep(settings.SHIPPING_MATRIX_THROTTLE_SECONDS)
        calculation = await provider.calculate(product, cep, brand)
        _write_cache(product_identity, cep, calculation)
        results.append({**region_cep, "state": calculation.state, ...})
    return results
```

### Anti-Patterns to Avoid
- **Rewriting marketplace scraping logic from scratch:** All 3 engines already have live-confirmed working paths (ML/Amazon confirmed by user live test; Netshoes confirmed blocked with clear evidence). Rewriting risks regressing what already works. Wrap, don't rewrite (D-03, and CLAUDE.md's "no over-engineering" directive).
- **Putting matrix-looping logic inside `resolve_shipping_provider` or any `BaseShipping.calculate`:** Breaks the single-CEP-per-call contract every existing provider (VTEX, Wake, Shopify) relies on.
- **Faking a `blocked`→`0.0`/free-shipping fallback for Netshoes:** Violates the "no frete falso" rule inherited from Phase 33/41 (`0.0` means confirmed free; `None`/dedicated state means not calculated).
- **Hardcoding CEP values inline in Python instead of `cep_matrix.json`:** Roadmap explicitly names this file path; hardcoding would violate D-08 and make the list non-editable by the operator.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Shipping provider dispatch by engine | A new if/elif chain scattered across routes/services | Extend existing `resolve_shipping_provider` (single chokepoint, D-03 explicit) | Phase 41 already established this must be the only decision point |
| Explicit non-availability states | Ad-hoc string literals or booleans per provider | Extend existing `ShippingState` class with `BLOCKED` | Matches `StockDepthState.BLOCKED` precedent exactly; keeps state vocabulary centralized |
| Rate limiting between matrix CEP calls | A rate-limiter library or token bucket | `asyncio.sleep(settings.SHIPPING_MATRIX_THROTTLE_SECONDS)` | Exact pattern already used for `STOCK_PROBE_THROTTLE_SECONDS` in Phase 44; no rate-limit library exists anywhere in this codebase |
| Local key-value cache with TTL | A caching library (e.g., `cachetools`, `diskcache`) | Plain JSON file with a `checked_at` timestamp per key, following `backend/data/*.json` local-storage pattern (`_load_local`/`_save_local` style seen in `category_monitor_service.py`) | Every other local persistence need in this repo (monitors, search history, stock summaries) uses raw JSON files with the same load/save helper shape; introducing a caching library would be the only exception and adds a dependency for no proven need at this data volume (5 CEPs × N products) |
| Product identity key for cache | Reusing VTEX's `sku_id`/`seller_id` fields with new semantics | Normalized product URL (already the primary key `SearchProductResult.url` uses across the app) as the stable half of the cache key, falling back to `shipping_sku`/`shipping_product_id` when present (Wake/Shopify already populate these per Phase 41 D-18) | Phase 41 D-18 explicitly says not to reuse `sku_id`/`seller_id` with ambiguous semantics; URL is already the de-facto stable identifier used throughout (dedup, monitors, exports) |

**Key insight:** Every piece of infrastructure this phase needs — provider resolution, throttle constants, blocked-state vocabulary, JSON local persistence — already exists in the codebase in a form built for almost this exact purpose (Phase 41 shipping abstraction, Phase 44 stock-probe guard-rails and blocked state, Phase 38-44 JSON monitor persistence). The task is disciplined reuse, not new design.

## Common Pitfalls

### Pitfall 1: `resolve_shipping_provider` import cycles when adding marketplace engine imports
**What goes wrong:** `resolver.py` currently does lazy imports inside each `if engine == ...` branch (`from services.shipping.shopify import ShopifyShipping` inside the function body, not at module top). If the new marketplace providers import their engine classes (`MercadoLivreEngine`, `AmazonEngine`, `NetshoesEngine`) at module level, and those engine modules transitively import something that imports `services.shipping` (unlikely today, but `factory.py` imports all engines eagerly), a cycle could form.
**Why it happens:** `services/engines/factory.py` eagerly imports `MercadoLivreEngine`, `AmazonEngine`, `NetshoesEngine` at module top (verified — lines 5-7). If any of the new `services/shipping/*.py` provider modules are imported by `factory.py` in the future, or if the engine modules ever import from `services.shipping`, a cycle forms.
**How to avoid:** Follow the exact existing pattern in `resolver.py` — import the new provider classes lazily inside the `if engine == "..."` branch, exactly as `WakeShipping`/`ShopifyShipping` already do. Do not import `MercadoLivreEngine` at the top of the new `mercado_livre.py` shipping provider file if avoidable; import it inside `__init__` or the `calculate` method if it turns out to be needed, mirroring `resolver.py`'s own lazy-import discipline.
**Warning signs:** `ImportError: cannot import name X from partially initialized module` at app startup.

### Pitfall 2: `UnsupportedShipping` fallback silently swallowing the 3 new engines if resolver branches are misordered or misspelled
**What goes wrong:** `resolve_shipping_provider` does `engine = str(get_field(brand, "engine", "") or "").lower()`. Brands.json confirms the engine strings are exactly `"mercadolivre"`, `"netshoes"`, `"amazon"` (no underscore — verified in `backend/data/brands.json` lines 567-617). If the new resolver branches check for `"mercado_livre"` (with underscore, matching `brand_key` instead of `engine`) they will never match and silently fall through to `UnsupportedShipping`.
**Why it happens:** The `brand_key` for Mercado Livre is `mercado_livre` (underscore) but the `engine` field is `mercadolivre` (no underscore) — this exact ambiguity already caused a real bug fixed in `.planning/debug/monitor-marketplace-pendente.md` (Round 2, hypothesis D) and required `normalize_brand_key` centralization in `factory.py`. The same trap applies here on the `engine` field.
<br>**How to avoid:** Match `resolve_shipping_provider`'s existing `if engine == "shopify"` / `if engine == "wake"` style using the exact `engine` field values confirmed in brands.json: `"mercadolivre"`, `"amazon"`, `"netshoes"`. Add a resolver test asserting each of the 3 exact strings resolves to the correct provider class (mirrors existing `test_shipping_resolver.py` structure).
**Warning signs:** New marketplace shipping calls always return `state="unsupported"` even for ML which should resolve.

### Pitfall 3: Netshoes `blocked` state accidentally treated as `unsupported` by the frontend, hiding the D-07 "always show the action" requirement
**What goes wrong:** The frontend's `isBrandShippingSupported` gate (`App.tsx` L1708: `brand?.engine === 'shopify' || brand?.engine === 'wake'`) currently hides the "Calcular Frete" button entirely for unlisted engines. If the planner extends this list to include marketplaces but the UI's state-rendering logic doesn't distinguish `blocked` from `unsupported`/generic failure, Netshoes could either wrongly hide the whole feature (violating D-07) or wrongly display a generic "Frete indisponível" instead of the specific "Bloqueado (anti-bot)" message (violating the "specifics" vocabulary requirement).
**Why it happens:** The existing frontend shipping-state rendering (`App.tsx` ~L1745-1830) branches on `hasOptions`/`calculated`/`isLoading` but has no explicit `blocked` branch today — it was designed before this state existed in `ShippingState`.
**How to avoid:** When adding `ShippingState.BLOCKED`, also add explicit UI handling that renders the exact string `"Bloqueado (anti-bot)"` (matching `App.tsx:437`'s existing monitor-panel vocabulary verbatim) rather than falling through to a generic message. For the Matrix table (D-07), ensure `blocked` rows render this same label per-region rather than being omitted.
**Warning signs:** Netshoes shows no "Calcular Frete"/"Matriz Regional" action at all (contradicts D-07), or shows an inconsistent bloqueio message that doesn't match the monitor panel's existing vocabulary.

### Pitfall 4: Guard against inline execution proven only by "no call today," not by an enforced boundary
**What goes wrong:** A common false sense of safety is verifying `cross_marketplace_search` and `run_category_scan` don't *currently* call the matrix function, then considering D-10 satisfied. Future code changes (e.g., someone enriching category scan results with "extra shipping context") could accidentally import and call the matrix module without anyone noticing, since Python has no compile-time enforcement here.
**Why it happens:** Unlike a type system or a dependency-injection boundary, nothing prevents `category_monitor_service.py` from doing `from services.shipping.regional_matrix import calculate_regional_matrix` next month.
**How to avoid:** Write an explicit regression test that statically inspects (via `inspect.getsource` or `ast`) or dynamically asserts that `cross_marketplace_search`'s and `run_category_scan`'s call graphs never reach the matrix function — the same spirit as Phase 44's cart-probe guard-rails test that asserts controlled-scan-only invocation. At minimum, add a docstring warning + a runtime guard flag/parameter (e.g., require an explicit `triggered_by="on_demand_matrix_button"` context marker that only the new route passes) so an accidental call raises rather than silently executing inline during a live scan.
**Warning signs:** Category scans or comparative searches become measurably slower (5x shipping calls × N products) with no accompanying log evidence of a deliberate matrix request.

### Pitfall 5: TTL cache never expiring because `checked_at` comparison uses inconsistent timezone-naive/aware datetimes
**What goes wrong:** JSON-stored timestamps are easy to get wrong (naive `datetime.now()` vs. `datetime.now(timezone.utc)`) causing TTL comparisons to always pass or always fail depending on server timezone.
**Why it happens:** No existing JSON-cache-with-TTL pattern in this codebardase to copy verbatim (the VTEX cache in `VTEX_CACHE_TTL_SECONDS` is in-memory, not JSON-file-backed) — this is genuinely new ground, unlike most of this phase.
**How to avoid:** Use `time.time()` (a plain float epoch seconds) instead of `datetime` objects for the cache's `checked_at` field, exactly avoiding timezone ambiguity. Compare `time.time() - cached["checked_at"] < settings.SHIPPING_MATRIX_CACHE_TTL_SECONDS`.
**Warning signs:** Cache appears to work in dev then behaves differently after deploy to a server with a different system timezone.

### Pitfall 6: Product identity for the cache key is not always `sku` — CONTEXT.md flags this explicitly
**What goes wrong:** The success criteria literally says "cache por `(sku, cep)`" but `SearchProductResult.sku_id` is a VTEX-specific field (populated for VTEX SKU/seller identity, per Phase 33). Marketplace products (ML/Amazon/Netshoes) do not populate `sku_id` — they use `shipping_product_id`/`shipping_variant_id`/`shipping_sku` (Phase 41 D-18 fields) or nothing at all if the provider derives identity purely from URL.
**Why it happens:** The roadmap/requirements language ("sku, cep") predates the marketplace-specific reality that "sku" is not a universal identifier across engines.
**How to avoid:** Use normalized product URL as the primary half of the cache key for all engines (already the de-facto stable identifier elsewhere in the app — dedup, exports, monitors), falling back to `shipping_sku`/`shipping_product_id` only as an optional secondary/display field, never as the sole key. This satisfies the spirit of "cache by product+cep" without assuming a field that most engines don't populate.
**Warning signs:** Cache never hits for any non-VTEX engine because `sku_id` is always `None` for those products.

## Code Examples

### Existing verified Mercado Livre shipping call (reuse target for D-03 wrapping)
```python
# Source: backend/services/engines/mercado_livre_engine.py (verified, lines 649-736, 738-829)
async def calculate_shipping(self, product: Any, zipcode: str) -> Optional[Dict[str, Any]]:
    # extracts item_id via regex \bMLB-?(\d{6,})\b or resolves from PDP HTML
    # calls _fetch_shipping_options(item_id, zipcode)

async def _fetch_shipping_options(self, item_id: str, zipcode: str) -> Optional[Dict[str, Any]]:
    api_url = f"https://api.mercadolibre.com/items/{item_id}/shipping_options?zip_code={zipcode}"
    # returns {"is_free_shipping": bool, "shipping_price": float} today —
    # DOES NOT currently extract estimated_delivery_time (D-02 gap to close)

async def calculate_shipping_advanced(self, url: str, zipcode: str) -> Optional[Dict[str, Any]]:
    shipping_info = await self.calculate_shipping(url, zipcode)
    if shipping_info:
        return shipping_info
    return await asyncio.to_thread(self._run_playwright_shipping, url, zipcode)  # Anubis-resistant fallback
```

### Existing verified Amazon delivery-text extraction (extend for D-02 delivery time)
```python
# Source: backend/services/engines/amazon_engine.py (verified, lines 480-519)
async def _read_delivery_text(self, page) -> str:
    selectors = [
        "#mir-layout-DELIVERY_BLOCK",
        "#mir-layout-DELIVERY_BLOCK-slot-PRIMARY_DELIVERY_MESSAGE_LARGE",
        "#mir-layout-DELIVERY_BLOCK-slot-SECONDARY_DELIVERY_MESSAGE_LARGE",
        "#deliveryBlockMessage",
        "#contextualIngressPtLabel_deliveryShortLine",
        "[data-csa-c-delivery-price]",
    ]
    # ...collects visible text from these selectors...

def _parse_shipping_text(self, text: str) -> Optional[Dict[str, Any]]:
    # currently only extracts is_free_shipping / shipping_price via regex on "R$ X,XX"
    # D-02 requires extending this to ALSO extract a delivery-time phrase, e.g. matching
    # "Receba em até N dias úteis" / "Chegará entre DD e DD de mês" patterns from the SAME
    # text blob already being read — no new page reads needed, only a new regex branch.
```

### Existing verified Netshoes CEP-modal flow + Akamai block signature (D-01 basis)
```python
# Source: backend/services/engines/netshoes_engine.py (verified, lines 556-635)
def _run_playwright_shipping(self, url: str, zipcode: str) -> Optional[Dict[str, Any]]:
    # navigates, clicks "Enviar para", fills #cepModal, reads .shipping/.freight classes
    # THIS is the flow to reuse — it already exists and already fails with a clean signal
    # (documented Akamai "Access Denied" ~343 bytes, confirmed 2026-07-01 live test —
    #  see .planning/debug/monitor-marketplace-pendente.md "Verdict Netshoes" section)
```

### Existing `BLOCKED` state precedent to mirror exactly
```python
# Source: backend/services/stock_depth/base.py (verified, line 15) — direct precedent
class StockDepthState:
    ESTIMATED = "estimated"
    AVAILABILITY_ONLY = "availability_only"
    UNAVAILABLE = "unavailable"
    UNSUPPORTED = "unsupported"
    BLOCKED = "blocked"          # <-- exact pattern to replicate in ShippingState
    TEMPORARY_FAILURE = "temporary_failure"

# Source: frontend/src/App.tsx (verified, line 437) — exact UI vocabulary to reuse
# {m.last_status === 'blocked' ? 'Bloqueado (anti-bot)' : 'Indisponível'}
```

### Existing config throttle constant naming convention to follow for D-09/matrix
```python
# Source: backend/config.py (verified, lines 133-153) — Phase 44 precedent
STOCK_PROBE_THROTTLE_SECONDS: float = Field(
    default=2.0,
    description="Throttle fixo entre probes de profundidade de estoque.",
)
STOCK_PROBE_TIMEOUT_SECONDS: int = Field(default=8, ...)
MAX_STOCK_DEPTH_PROBES_PER_BRAND: int = Field(default=3, ...)
# NEW settings should follow this exact naming/doc-string style, e.g.:
# SHIPPING_MATRIX_THROTTLE_SECONDS: float = Field(default=2.0, description="...")
# SHIPPING_MATRIX_CACHE_TTL_SECONDS: int = Field(default=21600, description="6h default — D-09 'curto'")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Ad-hoc `{"is_free_shipping": bool, "shipping_price": float}` dicts returned per-engine | Structured `ShippingCalculation`/`ShippingInfo` with explicit `state` enum | Phase 41 (2026-06-29/07-02) | This phase must migrate the 3 marketplace engines' ad-hoc dicts into the structured contract — the dicts themselves keep working as internal implementation detail wrapped by the new provider classes |
| `calculate_shipping` returning `None` on any failure (ambiguous: unsupported? blocked? no CEP coverage?) | Explicit `ShippingState` enum distinguishing `unavailable_for_cep` / `temporary_failure` / `unsupported` / (NEW) `blocked` | Phase 33 → Phase 41 → this phase | Removes ambiguity between "Netshoes never works" (should be `blocked`, permanent/infra) and "temporary network blip" (`temporary_failure`, worth retrying) |

**Deprecated/outdated:** None — this phase builds forward on Phase 41's contract without deprecating anything from it.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Exact JSON field names in `api.mercadolibre.com/items/{id}/shipping_options` response for cost and estimated delivery time (`cost`, `estimated_delivery_time.date`, `.shipping`, `.handling`, `.unit`, `.time_frame.from/.to`) | Summary, Code Examples, D-02 support | If field names differ from what secondary sources report, the delivery-time parsing branch added to `_fetch_shipping_options` will silently extract `None` for time — degrades gracefully (falls back to cost-only, matching today's behavior) but does not fully satisfy D-02's "melhor esforço" bar until corrected against a live response. **Mitigation:** the existing code already calls this live endpoint in production (`_fetch_shipping_options`, verified) — the planner/executor should log and inspect one real response payload during implementation rather than trusting this research's secondary-source field names blindly. |
| A2 | Exact CEP values for one representative capital per region are valid, in-range, deliverable postal codes: São Paulo-SP `01310-100` (Sudeste), Porto Alegre-RS `90010-150`/`90010-270` (Sul), Brasília-DF `70040-010`/`70040-000` (Centro-Oeste), Salvador-BA `40020-000` (Nordeste), Manaus-AM `69010-001`/`69010-970` (Norte) | D-08, Open Questions | Low risk — CEPs are only used as quote inputs to already-tolerant provider `calculate()` methods, which already handle `unavailable_for_cep` gracefully; a slightly wrong (but well-formed 8-digit) CEP degrades to a normal "unavailable for this CEP" state rather than crashing anything. The operator can edit `cep_matrix.json` freely (D-08 explicitly allows this). |
| A3 | Netshoes' Akamai block is permanent/infra-level and will still be blocking during this phase's implementation (not fixed since 2026-07-01) | D-01, Pitfall 3, Code Examples | If Akamai's block has lifted since the last live test, `blocked` state logic still works correctly (it only triggers on evidence of a block); no harm if unused. If it's still blocking, the `blocked` mapping is the correct behavior per D-01. |

**If this table is empty:** N/A — see entries above; all other architectural claims were verified directly by reading source files in this repository.

## Open Questions

1. **Exact live JSON shape of `api.mercadolibre.com/items/{id}/shipping_options`**
   - What we know: The endpoint is already called successfully in production code (`_fetch_shipping_options`, verified) and returns at minimum an `options` array with `cost` per option (confirmed by reading the existing working code, which does `opt.get("cost", 0.0)`). Secondary sources (developer docs summarized via search, official docs blocked scraping with 403) describe an `estimated_delivery_time` object with `date`/`shipping`/`handling`/`unit`/`time_frame` fields.
   - What's unclear: Whether `estimated_delivery_time` is present on every option or only some; exact nesting/naming in the *current* live API version (docs could have drifted since training data or since the secondary sources were indexed).
   - Recommendation: During implementation, log one full raw JSON response from a live call (the endpoint is already reachable and used today) before writing the parsing logic, rather than coding blind against the secondary-source field description above.

2. **Whether the "Matriz Regional" button should be visually distinguished when all 5 regions are expected to return `blocked`/`unsupported` (e.g., Netshoes, SFCC)**
   - What we know: D-07 mandates the action always appears, even for guaranteed-failure engines, to "never hide an expected failure."
   - What's unclear: Whether showing a spinner/loading state for 5 calls that the system already knows will all fail (Netshoes) creates a confusing UX (user waits for 5 sequential API calls that were foreseeable failures).
   - Recommendation: Left to planner's discretion (matches CONTEXT.md's "Claude's Discretion" on exact UI layout) — a reasonable middle ground is to still run all 5 calls (for consistency and auditability) but consider a fast-fail short-circuit only if the engine is already known unsupported at the resolver level (i.e., `UnsupportedShipping` returns immediately without 5x network attempts) — Netshoes still attempts live (per D-01, "tentar ao vivo"), so this optimization would only apply to genuinely `unsupported` engines like SFCC, not to `blocked` ones.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python (backend runtime) | All new provider/service code | ✓ | 3.14 (per `.pyc` cache tags: `cpython-314`) | — |
| pytest | Hermetic test suite for new providers/resolver/matrix | ✓ | 9.0.3 (per `.pyc` cache tags) | — |
| Playwright (Chromium) | ML Anubis fallback, Amazon CAPTCHA fallback, Netshoes CEP-modal/Akamai probe | ✓ (already used successfully by all 3 engines in live tests) | — | — |
| Network access to `api.mercadolibre.com`, `amazon.com.br`, `netshoes.com.br` | Live shipping quote calls | Not verifiable in this sandboxed research session (no live network calls attempted here); confirmed reachable in prior live user tests per debug doc | — | Tests must remain hermetic (fake session/fixtures) per Established Patterns; live verification is a manual/UAT step, consistent with Phase 41's precedent ("Manual browser UAT de frete ainda é desejável") |

**Missing dependencies with no fallback:** None identified.

**Missing dependencies with fallback:** Live network reachability for the 3 marketplace APIs/sites — not independently re-verified in this research session; existing debug evidence (2026-07-01 live tests) is the fallback source of truth, and hermetic tests avoid the need for live network in CI.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | none detected at root — pytest auto-discovers `backend/tests/test_*.py` |
| Quick run command | `cd backend && python -m pytest tests/test_shipping_resolver.py tests/test_shipping_engines.py -q` |
| Full suite command | `cd backend && python -m pytest -q` (454+ tests passing per most recent debug doc entry; 24 passed confirmed live in this research session for the shipping/stock-depth subset) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FRET-08 | `resolve_shipping_provider` returns `MercadoLivreShipping`/`AmazonShipping`/`NetshoesShipping` for the exact engine strings `mercadolivre`/`amazon`/`netshoes` | unit | `pytest tests/test_shipping_resolver.py -x` | ✅ (extend existing file) |
| FRET-08 | ML provider returns `AVAILABLE` state with cost+delivery-time populated from a fake shipping_options response | unit | `pytest tests/test_shipping_engines.py -k mercado_livre -x` | ❌ Wave 0 (new test cases in existing or new file) |
| FRET-08 | Amazon provider extracts delivery-time text alongside price from a fixture delivery-block HTML | unit | `pytest tests/test_shipping_engines.py -k amazon -x` | ❌ Wave 0 |
| FRET-08 | Netshoes provider returns `BLOCKED` state (not `temporary_failure`, not fake `0.0`) when Playwright flow returns the documented Akamai signature | unit | `pytest tests/test_shipping_engines.py -k netshoes_blocked -x` | ❌ Wave 0 |
| FRET-08 | `/search/calculate-shipping-brand` accepts `engine in {mercadolivre, amazon, netshoes}` without 400 | integration | `pytest tests/test_non_vtex_shipping_route.py -x` | ❌ Wave 0 (extend existing file) |
| FRET-09 | Matrix service returns 5 region results for a product+brand, one per curated CEP | unit | `pytest tests/test_shipping_regional_matrix.py -x` | ❌ Wave 0 (new file) |
| FRET-09 | Second matrix request for the same `(product, cep)` is served from cache (resolver/provider NOT called again) | unit | `pytest tests/test_shipping_regional_matrix.py -k cache_hit -x` | ❌ Wave 0 |
| FRET-09 | Matrix throttles between CEP calls (asserts `asyncio.sleep` called with configured value between requests, not before the first) | unit | `pytest tests/test_shipping_regional_matrix.py -k throttle -x` | ❌ Wave 0 |
| FRET-09 | `cross_marketplace_search` and `run_category_scan` never import/call the matrix module (guard) | regression | `pytest tests/test_shipping_regional_matrix.py -k guard_no_inline -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_shipping_resolver.py tests/test_shipping_engines.py tests/test_shipping_regional_matrix.py -q`
- **Per wave merge:** `cd backend && python -m pytest -q` (full suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_shipping_regional_matrix.py` — new file, covers FRET-09 cache/throttle/guard
- [ ] New test cases inside `backend/tests/test_shipping_engines.py` (or new `test_marketplace_shipping.py`) — covers FRET-08 provider mapping for all 3 engines including the `BLOCKED` state
- [ ] Extend `backend/tests/test_shipping_resolver.py` — 3 new resolver branch assertions
- [ ] Extend `backend/tests/test_non_vtex_shipping_route.py` (or equivalent route test) — `/calculate-shipping-brand` accepting marketplace engines
- [ ] Frontend: no test runner exists (confirmed precedent: `[44-05/typecheck-tdd]` in STATE.md uses `tsc --noEmit` as the TDD substitute) — new frontend changes (button, blocked-state rendering) should be verified via `npm run build`/`tsc --noEmit`, matching Phase 44's established frontend verification pattern

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | This phase adds no new auth surface; existing `X-API-Key` (`INTERNAL_API_KEY`) middleware already covers all `/search/*` routes |
| V3 Session Management | No | No session state introduced |
| V4 Access Control | Yes | New `/search/calculate-shipping-matrix` endpoint must be covered by the same API-key middleware as every other `/search/*` route — verify no new route bypasses it |
| V5 Input Validation | Yes | New `cep_matrix.json` entries and any matrix request body must validate CEP format (`^\d{5}-?\d{3}$`, matching existing `CalculateBrandShippingRequest.zipcode` pattern) and product URL must pass `is_url_allowed_for_brand` (existing SSRF mitigation from Phase 41, reused as-is) |
| V6 Cryptography | No | No cryptographic operations introduced |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SSRF via attacker-supplied product URL routed to an arbitrary internal/external host during matrix shipping calculation | Spoofing/Tampering | Reuse `is_url_allowed_for_brand` (existing, verified in `services/shipping/base.py`) — validate the product URL's host matches the persisted brand domain before any outbound call, exactly as `WakeShipping`/`ShopifyShipping` already do |
| CEP/PII-adjacent data leaking into logs | Information Disclosure | Existing rule from Phase 41 D-21 ("CEP nao deve ser logado em info/error") — the new matrix logging (throttle events, cache hits/misses) must log the *region label* (e.g., "Sudeste") rather than the raw CEP value where possible, or at minimum avoid logging CEP at `info`/`error` level, consistent with existing provider logging style (`logger.warning("...brand=%s status=%s", brand_key, type(exc).__name__)` — never interpolates the CEP itself) |
| Cache-key collision/poisoning if product identity key is derived from unsanitized user-controlled input (e.g., raw URL with tracking params) | Tampering | Reuse the existing URL normalization discipline already established for dedup elsewhere in the app (`normalize_url` in `routes_brands.py`/monitor flows) when deriving the cache key's product-identity half, so that `?utm_source=x` variants of the same product URL correctly hit the same cache entry rather than fragmenting the cache |
| Denial-of-wallet / excessive outbound calls if the matrix guard (D-10) is bypassed and triggered inline during a large category scan (N products × 5 CEPs × 3 marketplace engines) | Denial of Service (self-inflicted) | The D-10 guard itself is the primary mitigation — see Pitfall 4. Additionally, `MAX_STOCK_DEPTH_PROBES_PER_BRAND`-style per-brand/per-request caps could be considered if the planner wants defense-in-depth, though not explicitly required by CONTEXT.md |

## Sources

### Primary (HIGH confidence)
- Direct repository reads (this session): `backend/services/shipping/{base,resolver,wake,shopify,unsupported}.py`, `backend/services/engines/{mercado_livre,amazon,netshoes,factory,base_engine}.py`, `backend/services/stock_depth/base.py`, `backend/services/stock_depth_service.py`, `backend/config.py`, `backend/core/models.py`, `backend/services/cross_marketplace_service.py`, `backend/api/routes_search.py`, `backend/services/category_monitor_service.py`, `backend/data/brands.json`, `frontend/src/App.tsx`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `.planning/phases/41-.../41-CONTEXT.md`, `.planning/phases/42-.../42-CONTEXT.md`, `.planning/debug/monitor-marketplace-pendente.md`
- Live pytest run in this session confirming baseline green: `backend/tests/test_shipping_resolver.py`, `backend/tests/test_stock_depth_service.py` (24 passed)

### Secondary (MEDIUM confidence)
- [Mercado Livre Developers — Calculate shipping costs & handling time](https://developers.mercadolibre.com.ar/en_us/calculate-shipping-costs-handling-time) — summarized via WebSearch (direct fetch returned HTTP 403); describes `estimated_delivery_time` object shape (`type`, `date`, `shipping`, `handling`, `unit`, `time_frame`, `pay_before`) and `cost`/`list_cost` fields. **Not independently confirmed against a live response in this session** — flagged in Assumptions Log (A1).
- CEP validity for the 5 curated capitals — cross-referenced across multiple independent sources: [codigo-postal.org (São Paulo Centro)](https://codigo-postal.org/en-us/brazil/sp/sao-paulo/centro/), [postal-codes.cybo.com (Brasília 70040)](https://postal-codes.cybo.com/brazil/70040_bras%C3%ADlia), [siterastreio.com.br (Manaus 69010-970)](https://www.siterastreio.com.br/cep/69010970), [guiadoscorreios.com.br (Salvador 40020-000, Comércio/Centro)](https://www.guiadoscorreios.com.br/agencia-dos-correios/central-comercio-salvador-ba), [cepdobrasil.com.br (Porto Alegre 90010 range)](https://www.cepdobrasil.com.br/rio-grande-do-sul/porto-alegre-rs.html)

### Tertiary (LOW confidence)
- None — all findings above were either directly verified in-repo or cross-referenced across ≥2 independent secondary sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies; 100% reuse of already-installed, already-imported libraries verified by reading actual import statements
- Architecture: HIGH — the entire provider/resolver contract, JSON persistence pattern, throttle config pattern, and BLOCKED-state precedent were read directly from source files in this repository, not inferred
- Pitfalls: HIGH — 4 of 6 pitfalls are grounded in documented, resolved bugs from this exact codebase's own debug history (`.planning/debug/monitor-marketplace-pendente.md`); the remaining 2 (TTL timezone, cache-key identity) are grounded in the explicit gaps CONTEXT.md itself flags as open (D-16 equivalent, Pitfall 6)
- External API/data facts (ML response shape, CEP validity): MEDIUM — could not be verified against a live call/lookup in this sandboxed research session (docs site returned 403; no live network testing performed here), but corroborated by ≥2 independent sources each and flagged explicitly in the Assumptions Log for confirmation during implementation

**Research date:** 2026-07-02
**Valid until:** 30 days (stable internal architecture); external API shape (A1) should be re-confirmed against one live call at implementation time regardless of this validity window, since it was never independently verified here
