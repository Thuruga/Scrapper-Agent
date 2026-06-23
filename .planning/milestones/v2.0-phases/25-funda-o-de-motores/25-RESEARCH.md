# Phase 25: Fundação de Motores — Research

**Researched:** 2026-06-18
**Domain:** Python FastAPI — engine detection hardening + brand activation chokepoint
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** `detect_engine` deixa de retornar `"vtex"` como fallback final (linha 53). Passa a retornar `"unknown"` quando HTML obtido com sucesso mas nenhum marcador positivo de VTEX ou Shopify é encontrado.
- **D-02:** Adicionar probe positivo de Wake Commerce (ref.: Shop2gether). Mesmo reconhecendo Wake, `detect_engine` retorna `"unknown"` (Wake não suportado neste milestone); a distinção serve para confiança/log, não habilita busca.
- **D-03:** Falha transitória de rede (timeout/erro em todos os probes, sem HTML) → retorna `"unknown"`. `detect_engine` só roda no add-time; falha é recuperável pelo operador. Sem reclassificação automática de marcas já cadastradas.
- **D-04:** Quando cadastro detecta `"unknown"`, marca é salva com `engine="unknown"` e `is_active=False`. Chokepoint `active_only` já a exclui da busca. Resposta da rota deve expor o estado.
- **D-05:** Desativar apenas seta flag `is_active=False`. Exclusão ocorre pelo chokepoint no próximo ciclo. Sem cancelamento ativo de monitores em execução (diferente do `delete_brand`).
- **D-06:** Endpoint `PATCH /brands/{brand_key}/active` com body `{ "is_active": boolean }` (set explícito, idempotente). Persistir via `_save`/`_upsert_to_supabase`/`_save_to_json`.
- **D-07:** Assinatura `list_brands(self, active_only: bool = False)`. Default `False` preserva comportamento atual.
- **D-08:** `active_only=True` em: busca (routes_search.py L144,209,228), scheduler/factory (factory.py L70), monitoramento (price_monitor_service/category_monitor_service). Default `False` em: `GET /brands/` (routes_brands.py L72), `category_mapping.py:161`. Marketplaces virtuais sempre ativos.

### Claude's Discretion
- Forma exata do probe Wake (D-02): quais marcadores, ordem, timeout
- Definição precisa de "sinal positivo VTEX/Shopify" confiável (endurecer o HTML fallback frouxo `"vtex" in html_lower`)

### Deferred Ideas (OUT OF SCOPE)
- Engine Wake Commerce real (COMP-FUT-01, v3.0)
- Engines SFCC (Lacoste/Hugo Boss) e Inditex/Zara (COMP-FUT-02/03)
- Reclassificação automática de engine de marcas já cadastradas
- Painel/diagnóstico de saúde por categoria (Phase 29, DIAG-01/02)
- UI de gestão de marcas toggle ativar/desativar (Phase 27, MGMT-02)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| COMP-02 | Quando a plataforma de um site não é suportada, o sistema a identifica (`engine="unknown"` + probe Wake Commerce) em vez de cair em VTEX por padrão, e a marca incompatível não entra silenciosamente na busca | Seções: Wake Commerce Detection, VTEX/Shopify Hardening, detect_engine refactor pattern |
| MGMT-01 | Usuário pode ativar/desativar uma marca; uma marca inativa é excluída da busca, do monitoramento, da exportação e do scheduler (aplicação do flag `is_active` no ponto único `list_brands`) | Seções: Chokepoint Refactor, PATCH endpoint, call-site audit |
</phase_requirements>

---

## Summary

Esta phase entrega dois blocos ortogonais de backend que são pré-requisito para todas as outras phases do milestone v2.0:

**Bloco 1 (COMP-02):** `detect_engine` (`api/routes_brands.py:14-53`) hoje retorna `"vtex"` como fallback final incondicional (L53), o que silencia falhas de detecção. A mudança é cirúrgica: substituir o `return "vtex"` por `return "unknown"` e inserir um probe Wake Commerce (via `fbitsstatic.net` no HTML e/ou endpoint `/api/fbits/graphql`) antes do fallback VTEX. O HTML probe VTEX atual (`"vtex" in html_lower`) é frouxo — Wake Commerce usa infraestrutura VTEX então contém a string; endurecer para `vtexassets.com` ou `vtexcommercestable.com` (já presentes como checks secundários). O `create_brand` handler recebe o resultado e, se `"unknown"`, persiste a marca com `is_active=False` sem lançar exceção.

**Bloco 2 (MGMT-01):** `brand_service.list_brands()` (L207) retorna todos os registros incondicionalmente. Adicionar `active_only: bool = False` e filtrar quando `True`. Seis call sites existentes mantêm o default `False` (nenhum quebra); 4 sites de busca/scheduler explicitamente passam `True`. Novo endpoint `PATCH /brands/{brand_key}/active` persiste o flag via `_save()`. O campo `is_active` já existe no modelo Pydantic e em `brands.json` — sem migração de schema. A coluna Supabase deve ser verificada antes da release em produção.

**Recomendação primária:** Implementar na ordem Bloco 1 → Bloco 2, pois a detecção `"unknown"` alimenta D-04 que depende do chokepoint `active_only` já funcionando.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Platform detection (detect_engine) | API Layer (`routes_brands.py`) | — | Roda apenas no add-time; acesso à sessão HTTP compartilhada está no módulo de rota |
| Brand activation flag persistence | Service Layer (`brand_service._save`) | DB Layer (Supabase / brands.json) | `_save` abstrai o backend; a rota delega ao serviço |
| Active-only filtering | Service Layer (`brand_service.list_brands`) | — | Chokepoint único — zero lógica de filtro nos call sites |
| PATCH /brands/{key}/active endpoint | API Layer (`routes_brands.py`) | Service Layer | Rota fina; regra de negócio no serviço |
| Scheduler brand list | Service Layer (`engines/factory.py`) | — | `search_all_brands` consome `list_brands(active_only=True)` |
| Wake Commerce probe logic | API Layer (`detect_engine`) | — | Probe HTTP inline na função de detecção |

---

## Standard Stack

### Core (existing — no new installs required)
| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| `aiohttp` | >=3.9.0 | HTTP probes em `detect_engine` | Já em use |
| `fastapi` | >=0.110.0 | Novo endpoint PATCH | Já em use |
| `pydantic` | >=2.0 | Modelo `DynamicBrand.is_active` | Já em use |
| `supabase/postgrest` | >=2.0.0 | Persistência Supabase (prod) | Já em use |

### Testing (existing)
| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| `pytest` | (installed) | Framework de testes | Já em use — sem pytest.ini; run com `pytest tests/` |
| `unittest.mock` | stdlib | Mocking de aiohttp responses | Já usado nos testes existentes |

**Nenhum pacote novo é necessário para esta phase.** [VERIFIED: codebase inspection]

---

## Package Legitimacy Audit

> Esta phase não instala nenhum pacote externo novo. Todos os pacotes usados já estão em `requirements.txt` e em uso no projeto.

| Package | Status |
|---------|--------|
| `aiohttp` | Em uso — sem alteração |
| `fastapi` | Em uso — sem alteração |
| `pydantic` | Em uso — sem alteração |

**Packages removed due to slopcheck:** none
**Packages flagged as suspicious:** none

---

## Architecture Patterns

### System Architecture Diagram

```
BRAND ADD FLOW (COMP-02)
========================
POST /brands/ (engine=="auto")
    │
    ▼
detect_engine(domain)
    ├─→ [1] Shopify probe: GET /collections.json → "collections" in JSON → return "shopify"
    ├─→ [2] VTEX probe: GET /api/catalog_system/pub/category/tree/1 → HTTP 200 → return "vtex"
    ├─→ [3] Wake probe: HTML contains "fbitsstatic.net" OR POST /api/fbits/graphql → return "unknown" (log "wake_detected")
    ├─→ [4] HTML hardened: "vtexassets.com" OR "vtexcommercestable.com" → return "vtex"
    │       HTML: "cdn.shopify.com" OR "window.shopify" → return "shopify"
    └─→ [5] All failed/timeout → return "unknown"
    │
    ▼
create_brand handler
    ├─ engine == "unknown" → brand.is_active = False, brand.engine = "unknown", _save()
    │   response: DynamicBrand (engine="unknown", is_active=False) — HTTP 200, not error
    └─ engine != "unknown" → normal flow, is_active = True (default)

BRAND LIST / SEARCH FLOW (MGMT-01)
===================================
list_brands(active_only=False)  ←── GET /brands/ (UI management)
list_brands(active_only=True)   ←── factory.search_all_brands() (search)
                                ←── routes_search.py L144, L209, L228
                                     (both brand key validation + default brand set)

Virtual marketplaces (ML/Netshoes/Amazon) are appended AFTER list_brands() call
in GET /brands/ — they are unaffected by the active_only filter.

PATCH /brands/{key}/active
    │
    ▼
brand_service.set_active(brand_key, is_active: bool)
    │
    ▼
brand.is_active = is_active → _save(brand)  → Supabase upsert OR brands.json write
```

### Recommended Project Structure

No new directories. Changes are localized to:

```
api/
└── routes_brands.py        # detect_engine hardening + PATCH endpoint
services/
└── brand_service.py        # list_brands(active_only) + set_active()
tests/
└── test_engine_detection.py   # NEW — COMP-02 tests
└── test_brand_active.py       # NEW — MGMT-01 tests
```

---

## Wake Commerce Detection — Research Findings

### Definitive Markers [VERIFIED: wakecommerce.readme.io, api.fbits.net]

**CDN domain (strongest signal):**
Wake Commerce uses `fbitsstatic.net` for all static assets (CSS, JS, images). Any HTML page of a Wake Commerce storefront will contain URLs matching `*.fbitsstatic.net/sf/`. This is the most reliable single signal.

**GraphQL endpoint:**
The Wake Commerce Storefront API GraphQL endpoint is `storefront-api.fbits.net/graphql`. A probe POST to `https://{domain}/api/fbits/graphql` (or checking for `storefront-api.fbits.net` in HTML) may reveal the platform, but the canonical `storefront-api.fbits.net/graphql` is the authoritative endpoint.

**TCS-Access-Token header:**
Required header for authenticated Wake Commerce GraphQL queries. Its presence as a cookie or injected variable in the HTML source can confirm Wake, but extracting it requires parsing — HTML CDN check is simpler.

### Recommended Probe Implementation [ASSUMED — based on CDN evidence from docs]

```python
# Wake Commerce probe — Step 3 in detect_engine (before HTML VTEX fallback)
# Check HTML for fbitsstatic.net CDN (authoritative Wake marker)
try:
    async with session.get(base_url, timeout=aiohttp.ClientTimeout(total=5), headers=headers) as resp:
        html = await resp.text()
        html_lower = html.lower()
        # Wake Commerce CDN marker — appears on all fbitsstatic-served storefronts
        if "fbitsstatic.net" in html_lower:
            logger.info("detect_engine: Wake Commerce detected for %s (fbitsstatic.net marker)", domain)
            return "unknown"
        # Hardened VTEX: require CDN domain, not just the string "vtex"
        if "vtexassets.com" in html_lower or "vtexcommercestable.com" in html_lower:
            return "vtex"
        # Hardened Shopify: require CDN domain or meta generator
        if "cdn.shopify.com" in html_lower or '"generator" content="shopify"' in html_lower:
            return "shopify"
except Exception as e:
    logger.debug("detect_engine HTML probe failed for %s: %s", domain, e)
# All probes failed or inconclusive
return "unknown"
```

**Why `fbitsstatic.net` is the right probe:**
- It's the official CDN for Wake Commerce static assets [VERIFIED: wakecommerce.readme.io/docs/arquivos-estaticos]
- It is unique to Wake — no other major platform uses this domain
- It appears in HTML without authentication — visible on any public storefront page
- Avoids the false-positive risk of `"vtex" in html_lower` (Wake uses VTEX infrastructure for checkout/CDN layers, so "vtex" appears in Wake HTML too)

---

## VTEX/Shopify Detection — Hardening

### Current State: HTML Probe is Loose [VERIFIED: codebase inspection]

```python
# Line 45 — current (PROBLEMATIC)
if "vtexassets.com" in html_lower or "vtexcommercestable.com" in html_lower or "vtex" in html_lower:
    return "vtex"
```

The third condition `"vtex" in html_lower` is too broad. Wake Commerce storefronts (e.g. Shop2gether) contain the string "vtex" because they use VTEX checkout/token infrastructure. This causes the false-positive where a Wake brand gets registered as VTEX.

### Hardened Detection Order

| Step | Probe | Signal | Confidence |
|------|-------|--------|-----------|
| 1 | `GET /collections.json` → JSON with "collections" key | Shopify | HIGH |
| 2 | `GET /api/catalog_system/pub/category/tree/1` → HTTP 200 | VTEX | HIGH |
| 3 | HTML: `fbitsstatic.net` present | Wake → "unknown" | HIGH |
| 4 | HTML: `vtexassets.com` OR `vtexcommercestable.com` | VTEX | HIGH |
| 5 | HTML: `cdn.shopify.com` OR `"generator" content="shopify"` | Shopify | HIGH |
| 6 | All failed | → "unknown" | — |

**Rationale for removing `"vtex" in html_lower` from the fallback:**
- Steps 2 and 4 already cover all legitimate VTEX stores via domain-specific strings
- The generic string "vtex" appears in Wake, some marketplace pages, and even ad networks that mention VTEX
- Dropping it from the fallback only affects sites that contain "vtex" as text but NOT `vtexassets.com` — an extremely rare genuine VTEX store

**Ordering matters:** Wake probe (Step 3) MUST come before VTEX HTML probe (Step 4) because Wake HTML contains VTEX CDN references.

---

## Chokepoint Refactor Pattern

### Current `list_brands` Signature [VERIFIED: services/brand_service.py:207]

```python
def list_brands(self) -> List[DynamicBrand]:
    self._check_reload()
    return list(self.brands.values())
```

### Target Signature [ASSUMED — follows locked decision D-07]

```python
def list_brands(self, active_only: bool = False) -> List[DynamicBrand]:
    self._check_reload()
    brands = list(self.brands.values())
    if active_only:
        brands = [b for b in brands if b.is_active]
    return brands
```

**This is a backward-compatible change.** All existing call sites pass no argument → get `active_only=False` → behavior unchanged.

### Call-Site Audit [VERIFIED: codebase grep]

| File | Line | Caller | Action |
|------|------|--------|--------|
| `api/routes_brands.py` | 72 | `GET /brands/` (UI management) | **Keep `active_only=False` (default)** — must show inactive brands |
| `api/routes_search.py` | 144 | `search_products` POST — brand validation + default set | **Pass `active_only=True`** |
| `api/routes_search.py` | 209 | `search_products_get` GET — build `all_brands` | **Pass `active_only=True`** |
| `api/routes_search.py` | 228 | `export_search_products` — brand validation + default set | **Pass `active_only=True`** |
| `services/engines/factory.py` | 70 | `search_all_brands` default brand list | **Pass `active_only=True`** |
| `services/category_mapping.py` | 161 | `get_canonical_categories` — builds category UI | **Keep default `False`** (D-08: gate is at search time) |
| `api/routes_category.py` | 176 | `scrape_category_multi` — brand validation | **Pass `active_only=True`** — inactive brands should not be valid targets for category scan |

> Note: `routes_category.py:176` uses `list_brands()` to build `all_brands` dict for validation. If an inactive brand is passed, it should be rejected. This is slightly stricter than D-08 which says "category_mapping.py:161 keeps False" — but the *scrape_category_multi validator* is a different call than the *get_canonical_categories* function. The former should enforce `active_only=True`; the latter can keep `False`. Planner should confirm.

### `price_monitor_service.py` — No `list_brands` Calls [VERIFIED: codebase grep]

`price_monitor_service.py` does not call `list_brands()`. It manages individual monitors by `job_id`; monitors are started per URL/brand, not enumerated from the brand list. D-05's "next cycle" exclusion applies via `factory.search_all_brands` (which does use `list_brands`), not via price monitor.

### `category_monitor_service.py` — No `list_brands` Calls [VERIFIED: codebase grep]

`category_monitor_service.py` also does not call `list_brands()`. It loads monitored categories from Supabase or local JSON (`load_monitored_categories`). D-08 lists it as a consumer but the code path is indirect: category scan is triggered by scheduler reading pre-saved monitor configs, not by enumerating active brands. The brand check at scan time could be `brand_service.get_brand(brand_key)` + check `is_active`. Planner needs to decide if the scan check is in scope for Phase 25 or deferred.

---

## `PATCH /brands/{brand_key}/active` Endpoint

### Body Schema [ASSUMED — follows locked decision D-06]

```python
class BrandActiveUpdate(BaseModel):
    is_active: bool

@router.patch("/brands/{brand_key}/active", response_model=DynamicBrand)
async def set_brand_active(brand_key: str, payload: BrandActiveUpdate):
    """Ativa ou desativa uma marca (idempotente, não é toggle)."""
    brand = brand_service.set_active(brand_key, payload.is_active)
    if not brand:
        raise HTTPException(status_code=404, detail="Marca não encontrada")
    return brand
```

### `set_active` in BrandManagerService [ASSUMED — follows locked decisions D-05/D-06]

```python
def set_active(self, brand_key: str, is_active: bool) -> Optional[DynamicBrand]:
    key = brand_key.lower()
    if key not in self.brands:
        return None
    self.brands[key].is_active = is_active
    self._save(self.brands[key])
    return self.brands[key]
```

---

## D-04: Unknown Engine → Auto-Deactivate on Create

### `create_brand` Handler Modification [ASSUMED — follows locked decision D-04]

```python
@router.post("/brands/", response_model=DynamicBrand)
async def create_brand(brand_data: DynamicBrandCreate):
    try:
        if brand_data.engine == "auto":
            brand_data.engine = await detect_engine(brand_data.domain)

        # D-04: unknown engine → mark inactive, do not raise error
        if brand_data.engine == "unknown":
            brand_data_dict = brand_data.model_dump()
            brand_data_dict["is_active"] = False
            from core.models import DynamicBrandCreate
            brand_data = DynamicBrandCreate(**brand_data_dict)
            # Note: DynamicBrandCreate doesn't have is_active; set on the persisted brand

        saved = brand_service.add_brand(brand_data)
        if brand_data.engine == "unknown":
            # Ensure is_active is False on saved record
            saved = brand_service.set_active(saved.brand_key, False)
        return saved
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

**Simpler alternative:** Modify `brand_service.add_brand` to accept `is_active` override, or have `create_brand` call `set_active` after `add_brand`. The `set_active` call after `add_brand` is cleaner and reuses the persistence path. [ASSUMED]

---

## Persistence: Supabase Column Check

### `is_active` in `brands.json` [VERIFIED: data/brands.json inspection]

The field `is_active: true` already exists in all records in `data/brands.json`. `model_dump()` serializes it; `_save_to_json` writes it. No migration needed for JSON backend.

### `is_active` in Supabase [ASSUMED — not directly inspectable]

The `_upsert_to_supabase` method calls `brand.model_dump()` and sends all fields including `is_active`. However, the Supabase table schema must have the `is_active` column. If it was created before the field was added to the model, the column may not exist. **This must be verified before production deployment.**

**Migration query (if column missing):**
```sql
ALTER TABLE brands ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
```

`_supabase_row_to_brand` calls `DynamicBrand.model_validate(row)` — if `is_active` is missing from the row, Pydantic will use the field default (`True`). This means existing brands without the column silently load as active, which is the correct behavior.

---

## Virtual Marketplaces — Active Filter Guard

### `GET /brands/` Injects Virtual Brands [VERIFIED: api/routes_brands.py:74-103]

After `brand_service.list_brands()`, the route appends three `DynamicBrand` objects for `mercado_livre`, `netshoes`, and `amazon` without `is_active` set (uses Pydantic default `True`). These virtual brands are not in `brand_service.brands` dict and are not affected by the `active_only` filter. No change needed for this case.

For `routes_search.py:144` — the validation and default brand set also appends virtual marketplaces after `list_brands()`. The search endpoints correctly include virtual marketplaces regardless of `active_only`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP mocking in tests | Custom fake aiohttp session | `unittest.mock.MagicMock` with `__aenter__`/`__aexit__` | Project already uses this pattern; no new dependency |
| Supabase schema detection | Custom schema inspector | Add `IF NOT EXISTS` to migration SQL + manual check | Simple, safe, idempotent |
| Custom toggle logic | Separate `activate`/`deactivate` methods | Single `set_active(brand_key, bool)` method | Idempotent set semantics per D-06 |
| Per-call-site filtering | Add `if brand.is_active` at each consumer | Single `list_brands(active_only=True)` | Any missed call site defeats the entire feature |

---

## Common Pitfalls

### Pitfall 1: Wake false-negative — Wake HTML also contains VTEX strings
**What goes wrong:** Wake Commerce storefronts contain "vtex" in HTML (checkout tokens, VTEX-based CDN). Current Step 3 `"vtex" in html_lower` catches Wake as VTEX. The fix: probe Step 3 (Wake/HTML) must run BEFORE the VTEX HTML check (Step 4) and must use `fbitsstatic.net` specifically, not the generic "vtex" string.
**How to avoid:** Order: [Shopify API, VTEX API, Wake HTML, VTEX-CDN HTML, Shopify-CDN HTML, fallback unknown]
**Warning signs:** Shop2gether domain returns "vtex" from `detect_engine`

### Pitfall 2: "unknown" engine skips the `is_active=False` auto-set
**What goes wrong:** `DynamicBrandCreate` does not have `is_active`. `add_brand` creates a `DynamicBrand` with default `is_active=True`. If `create_brand` doesn't explicitly call `set_active(key, False)` after `add_brand`, the brand is active.
**How to avoid:** After `add_brand`, call `brand_service.set_active(saved.brand_key, False)` when `engine=="unknown"`. The `set_active` → `_save` path is the canonical write path.
**Warning signs:** Brand with `engine="unknown"` appearing in search results

### Pitfall 3: Supabase column missing
**What goes wrong:** In production with Supabase, `_upsert_to_supabase` calls `.upsert(row)` where `row` includes `is_active`. If the column doesn't exist in the Supabase table, the upsert raises an error or silently drops the field (behavior depends on Supabase REST configuration).
**How to avoid:** Run `ALTER TABLE brands ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;` before deploying. Treat this as a required setup step, not optional.
**Warning signs:** `[ERROR] Falha ao salvar no Supabase` in logs; `is_active` not persisted after PATCH

### Pitfall 4: `routes_search.py` builds two brand lists
**What goes wrong:** Each search endpoint builds `all_brands` from `list_brands()` (for validation AND as default targets). If only the factory's `search_all_brands` receives `active_only=True` but the route's validation list still uses `False`, inactive brands remain valid filter values even though they're excluded from actual search.
**How to avoid:** Both the validation list (line 144) and the factory call must use `active_only=True`. Check all three occurrences: L144, L209, L228.
**Warning signs:** Client can pass `brands=["inactive_brand"]` without 400 error, but gets empty results — confusing UX

### Pitfall 5: `detect_engine` uses `SessionManager.get_session()` — shared state in tests
**What goes wrong:** `detect_engine` imports `SessionManager` which creates a shared `aiohttp.ClientSession`. In tests running with `asyncio.run()`, the session may not be initialized or may be reused between tests.
**How to avoid:** In tests, patch `SessionManager.get_session` to return a mock session before calling `detect_engine`. The project pattern (from `test_cross_marketplace_service.py`) is to use `asyncio.run()` for async; do the same here with proper mock injection.

### Pitfall 6: Default `active_only=False` must NOT change for `GET /brands/`
**What goes wrong:** If the planner changes the default to `True` for "safety", `GET /brands/` (routes_brands.py:72) starts returning only active brands, breaking the management UI (operators can't see/reactivate inactive brands).
**How to avoid:** Keep `active_only=False` as the default. Call sites that need filtering explicitly pass `True`. The management route must stay at default.

---

## Code Examples

### Patching SessionManager for async detect_engine tests [ASSUMED — adapted from project pattern]

```python
# tests/test_engine_detection.py
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

def _make_mock_response(status: int, json_data=None, text_data=""):
    """Build a mock aiohttp response for use as async context manager."""
    resp = MagicMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data or {})
    resp.text = AsyncMock(return_value=text_data)
    # async context manager support
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp

def _make_mock_session(responses: dict):
    """
    responses: {url_substring: mock_response}
    session.get(url) returns the matching response.
    """
    session = MagicMock()
    def _get(url, **kwargs):
        for key, resp in responses.items():
            if key in url:
                return resp
        raise aiohttp.ClientError("no mock for " + url)
    session.get = _get
    session.post = MagicMock(side_effect=aiohttp.ClientError("blocked"))
    return session

class TestDetectEngine:
    def test_shopify_detected_via_collections_json(self):
        mock_resp = _make_mock_response(200, json_data={"collections": [{"id": 1}]})
        mock_session = _make_mock_session({"collections.json": mock_resp})
        with patch("api.routes_brands.SessionManager.get_session", new=AsyncMock(return_value=mock_session)):
            from api.routes_brands import detect_engine
            result = asyncio.run(detect_engine("test.myshopify.com"))
        assert result == "shopify"

    def test_vtex_detected_via_category_tree(self):
        # collections.json → 404; VTEX category tree → 200
        no = _make_mock_response(404)
        vtex = _make_mock_response(200)
        mock_session = _make_mock_session({
            "collections.json": no,
            "category/tree/1": vtex,
        })
        with patch("api.routes_brands.SessionManager.get_session", new=AsyncMock(return_value=mock_session)):
            from api.routes_brands import detect_engine
            result = asyncio.run(detect_engine("www.aramis.com.br"))
        assert result == "vtex"

    def test_wake_commerce_returns_unknown(self):
        # All API probes fail; HTML contains fbitsstatic.net
        no = _make_mock_response(404)
        html_wake = _make_mock_response(200, text_data='<script src="https://shop2gether.fbitsstatic.net/sf/bundle?type=js"></script>')
        mock_session = _make_mock_session({
            "collections.json": no,
            "category/tree/1": no,
            "shop2gether.com.br": html_wake,  # home page fallback
        })
        with patch("api.routes_brands.SessionManager.get_session", new=AsyncMock(return_value=mock_session)):
            from api.routes_brands import detect_engine
            result = asyncio.run(detect_engine("www.shop2gether.com.br"))
        assert result == "unknown"

    def test_all_probes_fail_returns_unknown(self):
        no = _make_mock_response(404)
        empty_html = _make_mock_response(200, text_data="<html><body>generic page</body></html>")
        mock_session = _make_mock_session({
            "collections.json": no,
            "category/tree/1": no,
            "generic": empty_html,
        })
        with patch("api.routes_brands.SessionManager.get_session", new=AsyncMock(return_value=mock_session)):
            from api.routes_brands import detect_engine
            result = asyncio.run(detect_engine("www.genericstore.com.br"))
        assert result == "unknown"
```

### `list_brands(active_only)` test pattern [ASSUMED — follows project's sync test style]

```python
# tests/test_brand_active.py
from services.brand_service import BrandManagerService
from core.models import DynamicBrandCreate

def _make_service_with_brands():
    """Returns a BrandManagerService with in-memory test data (no file I/O)."""
    svc = BrandManagerService.__new__(BrandManagerService)
    svc.brands = {}
    svc.last_modified = 0
    import asyncio
    svc.updated_event = asyncio.Event()
    # Add two brands: one active, one inactive
    from core.models import DynamicBrand
    svc.brands["active_brand"] = DynamicBrand(
        brand_key="active_brand", brand_name="Active", domain="active.com",
        engine="vtex", is_active=True
    )
    svc.brands["inactive_brand"] = DynamicBrand(
        brand_key="inactive_brand", brand_name="Inactive", domain="inactive.com",
        engine="unknown", is_active=False
    )
    return svc

class TestListBrandsActiveOnly:
    def test_default_returns_all_brands(self):
        svc = _make_service_with_brands()
        result = svc.list_brands()
        assert len(result) == 2

    def test_active_only_excludes_inactive(self):
        svc = _make_service_with_brands()
        result = svc.list_brands(active_only=True)
        assert len(result) == 1
        assert result[0].brand_key == "active_brand"

    def test_active_only_false_returns_all(self):
        svc = _make_service_with_brands()
        result = svc.list_brands(active_only=False)
        assert len(result) == 2

class TestSetActive:
    def test_deactivate_brand(self):
        svc = _make_service_with_brands()
        # Bypass _save for unit test
        import unittest.mock
        with unittest.mock.patch.object(svc, "_save"):
            result = svc.set_active("active_brand", False)
        assert result is not None
        assert result.is_active is False
        assert svc.brands["active_brand"].is_active is False

    def test_reactivate_brand(self):
        svc = _make_service_with_brands()
        with unittest.mock.patch.object(svc, "_save"):
            result = svc.set_active("inactive_brand", True)
        assert result.is_active is True

    def test_set_active_unknown_key_returns_none(self):
        svc = _make_service_with_brands()
        result = svc.set_active("nonexistent", True)
        assert result is None
```

---

## State of the Art

| Old Approach | Current Approach | Status |
|--------------|------------------|--------|
| `return "vtex"` fallback in `detect_engine` | `return "unknown"` + Wake probe | Phase 25 target |
| `list_brands()` returns all unconditionally | `list_brands(active_only=False)` with filter | Phase 25 target |
| No PATCH endpoint for `is_active` | `PATCH /brands/{key}/active` | Phase 25 target |

**Deprecated/outdated:**
- `"vtex" in html_lower` as a catch-all in `detect_engine` Step 3: must be replaced by `vtexassets.com` / `vtexcommercestable.com` check (already present as secondary conditions but the fallback `"vtex"` substring kills them)

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Wake probe uses `fbitsstatic.net` in HTML as primary marker | Wake Detection | If Shop2gether doesn't serve this domain in HTML, probe misses Wake — but the fallback is `"unknown"` anyway, so the system still works correctly; it just can't log "wake_detected" |
| A2 | `set_active()` is the new method name in `brand_service` | Chokepoint Refactor | Name is cosmetic; planner can choose any name |
| A3 | `create_brand` calls `set_active` after `add_brand` for unknown engine | D-04 implementation | If implemented differently (e.g., modifying `add_brand` to accept `is_active`), behavior is equivalent |
| A4 | `routes_category.py:176` `scrape_category_multi` should use `active_only=True` | Call-site audit | D-08 says only to confirm in Phase 29; planner can defer this call site |
| A5 | Supabase `brands` table may lack `is_active` column | Persistence section | If column exists, no action needed; if missing and not added, production upserts fail or silently drop the field |
| A6 | `category_monitor_service` does NOT enumerate brands via `list_brands` | Call-site audit | Verified by grep; but if a scheduler trigger was added after the codebase was last inspected, it could be missed |

---

## Open Questions

1. **Does Supabase `brands` table have `is_active` column in production?**
   - What we know: `data/brands.json` has it; `DynamicBrand` model has it with `default=True`
   - What's unclear: Whether the Supabase schema was updated when `is_active` was added to the model
   - Recommendation: Add an explicit setup step in Wave 0: `ALTER TABLE brands ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;`

2. **Should `scrape_category_multi` (routes_category.py:176) enforce `active_only=True`?**
   - What we know: D-08 explicitly defers `category_mapping.py:161` to Phase 29; but the scrape validator is a different function
   - What's unclear: Whether an inactive brand being valid as a scrape target is acceptable for Phase 25
   - Recommendation: Include `active_only=True` in the scrape validator — consistency with search; deferred brands can always be added back in Phase 29 if needed

3. **Is `detect_engine` transitional timeout vs permanent "unknown" distinction needed in the response?**
   - What we know: D-03 says transient failures → `"unknown"`; D-04 says `"unknown"` → `is_active=False`
   - What's unclear: Whether a timeout-caused `"unknown"` should also yield `is_active=False`, or if the operator might prefer to retry manually
   - Recommendation: All `"unknown"` outcomes → `is_active=False` per D-04. The log message should distinguish timeout from Wake detection so operators understand why.

---

## Environment Availability

| Dependency | Required By | Available | Notes |
|------------|------------|-----------|-------|
| `pytest` | All tests | assumed ✓ | No pytest.ini found; run with `pytest tests/` from project root |
| `aiohttp` | `detect_engine` probes | ✓ | In requirements.txt, in active use |
| `supabase/postgrest` | Prod persistence | ✓ (prod only) | Dev uses brands.json; no Supabase needed for tests |
| Network access to shop2gether.com.br | Manual probe validation | Not tested | Not needed for automated tests; only for manual verification |

---

## Validation Architecture

> `workflow.nyquist_validation: true` in `.planning/config.json` — section required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (no config file found — inferred from test files in `tests/`) |
| Config file | None — run from project root with `pytest tests/` |
| Quick run command | `pytest tests/test_engine_detection.py tests/test_brand_active.py -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COMP-02 | `detect_engine` returns `"shopify"` for Shopify domain | unit | `pytest tests/test_engine_detection.py::TestDetectEngine::test_shopify_detected_via_collections_json -x` | ❌ Wave 0 |
| COMP-02 | `detect_engine` returns `"vtex"` for VTEX domain | unit | `pytest tests/test_engine_detection.py::TestDetectEngine::test_vtex_detected_via_category_tree -x` | ❌ Wave 0 |
| COMP-02 | `detect_engine` returns `"unknown"` for Wake Commerce domain (fbitsstatic.net in HTML) | unit | `pytest tests/test_engine_detection.py::TestDetectEngine::test_wake_commerce_returns_unknown -x` | ❌ Wave 0 |
| COMP-02 | `detect_engine` returns `"unknown"` when all probes fail | unit | `pytest tests/test_engine_detection.py::TestDetectEngine::test_all_probes_fail_returns_unknown -x` | ❌ Wave 0 |
| COMP-02 | Brand with `engine="unknown"` is saved with `is_active=False` | integration | `pytest tests/test_engine_detection.py::TestCreateBrandUnknown -x` | ❌ Wave 0 |
| MGMT-01 | `list_brands()` (no args) returns all brands | unit | `pytest tests/test_brand_active.py::TestListBrandsActiveOnly::test_default_returns_all_brands -x` | ❌ Wave 0 |
| MGMT-01 | `list_brands(active_only=True)` excludes inactive brands | unit | `pytest tests/test_brand_active.py::TestListBrandsActiveOnly::test_active_only_excludes_inactive -x` | ❌ Wave 0 |
| MGMT-01 | `set_active(key, False)` sets `is_active=False` and persists | unit | `pytest tests/test_brand_active.py::TestSetActive::test_deactivate_brand -x` | ❌ Wave 0 |
| MGMT-01 | `set_active(key, True)` reactivates and persists | unit | `pytest tests/test_brand_active.py::TestSetActive::test_reactivate_brand -x` | ❌ Wave 0 |
| MGMT-01 (SC-4) | `GET /brands/` returns inactive brands (active_only opt-in not global default) | integration | `pytest tests/test_brand_active.py::TestBrandRouteReturnsInactive -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_engine_detection.py tests/test_brand_active.py -x -q`
- **Per wave merge:** `pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_engine_detection.py` — covers COMP-02 (all detect_engine scenarios + create_brand unknown)
- [ ] `tests/test_brand_active.py` — covers MGMT-01 (list_brands active_only + set_active + route behavior)

*(Both files are new — no existing test infrastructure covers these requirements)*

---

## Security Domain

> `security_enforcement` not set in config — treated as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | Pydantic model validation on `BrandActiveUpdate` (bool field) and `DynamicBrandCreate`; FastAPI handles 422 for bad types |
| V4 Access Control | no | API uses shared key auth (unchanged); PATCH endpoint follows existing auth model |
| V2 Authentication | no | No auth changes in this phase |
| V6 Cryptography | no | No crypto in this phase |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| PATCH body with non-bool `is_active` | Tampering | Pydantic `bool` type coerces `0`/`1`/`"true"` correctly; strict validation via `model_config` if needed |
| Sending arbitrary `brand_key` in URL | Tampering | `.lower()` normalization in `set_active`; key not found → 404, not data corruption |
| Wake probe following redirect to malicious domain | Spoofing | `aiohttp` follows redirects by default; add `allow_redirects=False` to probe GETs or validate final URL domain matches target domain |

---

## Sources

### Primary (HIGH confidence)
- `api/routes_brands.py` (codebase inspection) — `detect_engine` function, L14-53; fallback L53; create_brand L56-66
- `services/brand_service.py` (codebase inspection) — `list_brands` L207; `_save` L180-186; `_upsert_to_supabase` L154-164
- `core/models.py` (codebase inspection) — `DynamicBrand.is_active` L232; `engine` field L224
- `data/brands.json` (codebase inspection) — `is_active` field present in all records
- `services/engines/factory.py` (codebase inspection) — `search_all_brands` L47-92; `list_brands()` call L70
- `wakecommerce.readme.io/docs/arquivos-estaticos` — `fbitsstatic.net` CDN domain [CITED]
- `wakecommerce.readme.io/docs/storefront-api-explorando-a-api` — GraphQL endpoint at `storefront-api.fbits.net`, TCS-Access-Token header [CITED]

### Secondary (MEDIUM confidence)
- `webreveal.io/blog/how-to-detect-shopify-store.html` — Shopify detection signals: `cdn.shopify.com`, `window.Shopify`, meta generator tag [CITED]
- WebSearch result: Wake Commerce GraphQL playground at `storefront-api.fbits.net/ui/playground` [CITED: search result from storefront-api.fbits.net]

### Tertiary (LOW confidence)
- None — all critical claims verified against code or official docs

---

## Metadata

**Confidence breakdown:**
- detect_engine refactor: HIGH — code fully read, fallback at L53 confirmed, all probes documented
- Wake probe: MEDIUM — `fbitsstatic.net` confirmed from official docs; exact HTML pattern for Shop2gether not live-tested
- Chokepoint pattern: HIGH — code read, all call sites grepped, `is_active` field confirmed in model and JSON
- Supabase schema: LOW — cannot directly inspect production schema; treated as open question
- Testing strategy: HIGH — follows established project patterns from `test_cross_marketplace_service.py` and `test_brand_gate.py`

**Research date:** 2026-06-18
**Valid until:** 2026-07-18 (stable stack; Wake Commerce CDN domain unlikely to change)
