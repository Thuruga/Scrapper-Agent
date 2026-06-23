---
phase: 25-fundacao-de-motores
reviewed: 2026-06-18T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - api/routes_brands.py
  - api/routes_category.py
  - api/routes_search.py
  - core/models.py
  - services/brand_service.py
  - services/engines/factory.py
  - tests/test_brand_active.py
  - tests/test_engine_detection.py
findings:
  critical: 4
  warning: 4
  info: 2
  total: 10
status: issues_found
---

# Phase 25: Code Review Report

**Reviewed:** 2026-06-18T00:00:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Phase 25 delivers `detect_engine` hardening (Wake/fbitsstatic.net probe, `allow_redirects=False`, unknown fallback), the `list_brands(active_only)` chokepoint, `set_active` persistence, `BrandActiveUpdate` PATCH endpoint, and `active_only=True` adoption across call sites. The core mechanics are structurally sound; the Wake probe is correctly ordered before the VTEX HTML check, `GET /brands/` is correctly unfiltered, and `set_active` does call `_save`. However, four blockers were found: a redirect-bypass that allows HTML scraping of attacker-controlled content despite `allow_redirects=False`, a silent data loss in `add_brand` that discards the resolved `engine` on re-registration, a `NoneType` crash in `resolved_url` when both fields are omitted, and a key-format mismatch that allows inactive brands to pass validation in `POST /search`. Four warnings cover `_save_to_json` error-swallowing, `sort` field being unvalidated, `updated_event.set()/.clear()` race, and stale test docstrings describing already-passing RED scenarios as still-RED.

---

## Critical Issues

### CR-01: `allow_redirects=False` reads body from redirect response, bypassing domain-identity guarantee

**File:** `api/routes_brands.py:44-46`

**Issue:** The security comment at line 41 asserts that `allow_redirects=False` prevents reading HTML from an attacker-redirected domain. This is partially correct — it stops following the redirect — but `aiohttp` will still return the body of the *redirect response itself* (status 301/302) and `resp.text()` is called unconditionally on whatever status comes back. A domain that serves a 302 with a short HTML body containing `fbitsstatic.net` or `vtexassets.com` markers in the redirect document could cause a false positive or false negative classification. More critically, a domain under attacker control could serve a crafted redirect body to force `"vtex"` classification. The intent of the probe is to read the HTML of the canonical homepage; that requires either following redirects (and accepting the trade-off) or asserting `resp.status == 200` before reading the body.

```python
# Fix: only parse HTML when the response is a genuine 200 OK
async with session.get(
    base_url,
    timeout=aiohttp.ClientTimeout(total=5),
    headers=headers,
    allow_redirects=False,
) as resp:
    if resp.status != 200:
        raise aiohttp.ClientError(f"Non-200 status {resp.status} (likely redirect)")
    html = await resp.text()
    html_lower = html.lower()
    # ... probes continue ...
```

This preserves the redirect-safety guarantee: a 3xx response is treated as "inconclusive" and falls through to `return "unknown"`.

---

### CR-02: `add_brand` silently discards resolved `engine` on re-registration of an existing brand

**File:** `services/brand_service.py:188-198`

**Issue:** When `POST /brands/` is called for an already-registered brand, `add_brand` only updates `domain` and `brand_name` (lines 191-192). The `engine` field — which was just resolved by `detect_engine` — is silently dropped. This means:

1. A brand initially registered as `engine="vtex"` that is re-submitted after the domain migrates to Shopify will remain `engine="vtex"` in storage even though detection returned `"shopify"`.
2. More critically in the Phase 25 context: a brand re-submitted with `engine="auto"` that resolves to `"unknown"` will have `saved.engine == "vtex"` (old persisted value), so the `if saved.engine == "unknown":` guard at `routes_brands.py:85` will **never fire** for re-registered brands. The brand will not be deactivated despite the unknown detection result.

```python
def add_brand(self, data: DynamicBrandCreate) -> DynamicBrand:
    key = data.brand_key.lower().strip()
    if key in self.brands:
        self.brands[key].domain = data.domain
        self.brands[key].brand_name = data.brand_name
        # FIX: also update engine if it was resolved (not still "auto")
        if data.engine and data.engine != "auto":
            self.brands[key].engine = data.engine
    else:
        new_brand = DynamicBrand(**data.model_dump())
        self.brands[key] = new_brand
    self._save(self.brands[key])
    return self.brands[key]
```

---

### CR-03: `NoneType` crash in `resolved_url` when both `category_path` and `custom_url` are None

**File:** `api/routes_category.py:55-68`

**Issue:** `ScrapeCategoryRequest` declares both `category_path` and `custom_url` as `Optional[str] = None`. The method `resolved_url()` checks `self.custom_url` first (line 56), then falls through to use `self.category_path`. In the `except` branch (line 63-68), line 67 calls `self.category_path.startswith("/")` unconditionally. When `category_path` is `None` (a client sends neither field), this raises `AttributeError: 'NoneType' object has no attribute 'startswith'`, crashing the request outside any HTTP error handler.

The upstream check at `routes_category.py:114-115` validates that the resolved URL is non-empty but it never runs because the crash occurs inside `resolved_url()` before `scrape_category` can inspect the result.

```python
def resolved_url(self) -> str:
    if self.custom_url:
        return clean_url(self.custom_url)
    if not self.category_path:          # FIX: guard missing field
        return ""
    try:
        mapping = resolve_category_for_brands(self.category_path, [self.brand])
        return mapping[self.brand.lower()]["url"]
    except Exception:
        brand_info = brand_service.get_brand(self.brand.lower())
        domain = brand_info.domain if brand_info else ""
        path = (
            self.category_path
            if self.category_path.startswith("/")
            else f"/{self.category_path}"
        )
        return f"https://{domain}{path}"
```

---

### CR-04: Key-format mismatch lets inactive brands bypass validation in `POST /search`

**File:** `api/routes_search.py:144-155` and `services/engines/factory.py:22-28`

**Issue:** The validation list at `routes_search.py:144-145` is built from `brand_service.list_brands(active_only=True)`, which returns `brand_key` values as stored (e.g. `"aramis"`, `"reserva"`), plus the three virtual marketplace keys `"mercado_livre"`, `"netshoes"`, `"amazon"` appended verbatim.

`engine_factory.get_engine()` normalises its input by stripping underscores: `brand_key.lower().replace(" ", "").replace("_", "")` (factory.py:22), so `"mercado_livre"` becomes `"mercadolivre"` and correctly matches the factory branch.

However, when a client passes `"mercadolivre"` (no underscore) in the request, the validation check at line 147 does `b.lower() not in all_brands` where `all_brands` contains `"mercado_livre"` (with underscore). `"mercadolivre" not in ["mercado_livre", ...]` evaluates to `True`, so the request is **rejected with 400** even though the factory can handle it. Conversely, a client that passes `"mercado_livre"` passes validation but the factory normalises it to `"mercadolivre"` and correctly routes it — this direction works. The asymmetry means the documented example in the `brands` field description (`"mercadolivre"` — no underscore at line 50) is actually rejected.

More importantly in scope: there is no cross-check that brands present in a user-supplied `request.brands` list but absent from `all_brands` due to `active_only=True` filtering are inactive (vs. simply non-existent). The 400 error message exposes all active brand keys to the caller, which is an information disclosure of the internal brand inventory.

```python
# Fix: normalise marketplace keys consistently in validation list
VIRTUAL_BRAND_KEYS = {"mercado_livre", "mercadolivre", "netshoes", "amazon"}

all_brands = {b.brand_key for b in brand_service.list_brands(active_only=True)}
all_brands |= VIRTUAL_BRAND_KEYS

def _normalise(k: str) -> str:
    return k.lower().replace(" ", "").replace("_", "")

if request.brands:
    invalid = [b for b in request.brands
               if _normalise(b) not in {_normalise(x) for x in all_brands}]
```

---

## Warnings

### WR-01: `_save_to_json` silently swallows write errors — `set_active` can return stale data without persisting

**File:** `services/brand_service.py:74-83`

**Issue:** `_save_to_json` catches all exceptions and logs them (line 83) but does not re-raise. `set_active` calls `_save` which calls `_save_to_json`, then immediately returns the mutated in-memory brand object. If the file write fails (disk full, permission error), the caller gets a successful return value (`is_active=False`) while the file still has the old state. On the next process restart the brand will appear active again. The test at `test_brand_active.py:123` mocks `_save` to avoid I/O, so this failure mode is not covered.

```python
def _save_to_json(self):
    try:
        self._ensure_db_dir()
        with open(DB_FILE, "w", encoding="utf-8") as f:
            data = {k: v.model_dump() for k, v in self.brands.items()}
            json.dump(data, f, indent=2, ensure_ascii=False)
        self.updated_event.set()
        self.updated_event.clear()
    except Exception as e:
        logger.error(f"[ERROR] Erro ao salvar brands.json: {e}")
        raise  # FIX: propagate so callers can return 500 instead of silent success
```

---

### WR-02: `sort` field in `SearchRequest` accepts arbitrary strings — no validation

**File:** `api/routes_search.py:58-61`

**Issue:** `sort` is declared as `Optional[str]` with a default of `"relevance"`. The docstring lists four valid values (`relevance`, `price_asc`, `price_desc`, `top_selling`) but there is no Pydantic validator, `Literal` type, or `Enum` constraint. A client can pass any string; the value is forwarded directly to `engine_factory.search_all_brands()` and then to individual engine `search()` calls. Downstream engines may silently ignore unknown values or produce incorrect ordering without surfacing an error. The same applies to the `GET /search` handler's `sort` query parameter (line 191).

```python
from typing import Literal
sort: Optional[Literal["relevance", "price_asc", "price_desc", "top_selling"]] = Field(
    default="relevance",
    description="Ordenação: 'relevance', 'price_asc', 'price_desc', 'top_selling'.",
)
```

---

### WR-03: `updated_event.set()` immediately followed by `.clear()` creates a race window

**File:** `services/brand_service.py:80-81`

**Issue:** In `_save_to_json`, `self.updated_event.set()` is called synchronously followed immediately by `self.updated_event.clear()`. Any coroutine waiting on `await self.updated_event.wait()` will only be woken if it is scheduled *within the same event-loop tick* between these two calls, which is impossible in synchronous code — `asyncio.Event.set()` in a sync context schedules wakeups but they cannot actually execute until the event loop yields. The result is that the event fires and clears before any waiter can observe it, making this signalling mechanism a no-op. Any subsystem relying on this event for invalidation notifications will silently never trigger.

```python
# Fix: either use an asyncio.Queue for reliable notification, or
# schedule the clear after yielding control:
self.updated_event.set()
# Do NOT immediately clear — let waiters wake on the next loop iteration.
# Clear should be done after the event is processed, or use a Queue instead.
```

---

### WR-04: `GET /search` (`search_products_get`) computes `brands_searched` after the search, creating a response/reality mismatch

**File:** `api/routes_search.py:196-216`

**Issue:** `search_products_get` passes `brands=None` to `engine_factory.search_all_brands()` (line 200), which internally calls `brand_service.list_brands(active_only=True)` to determine the actual target set. After the search completes, `search_products_get` separately calls `brand_service.list_brands(active_only=True)` again (line 209) to build `brands_searched` for the response. If a brand changes active status between the two calls (e.g. via a concurrent PATCH), `brands_searched` will not match the brands that were actually searched. This is a TOCTOU gap. The analogous POST handler (`search_products`) builds the list before calling the factory (line 144) and passes it explicitly, so it does not have this problem.

```python
# Fix: have engine_factory.search_all_brands return the resolved brand list
# alongside results, or compute it once before calling the factory:
target_brands = [b.brand_key for b in brand_service.list_brands(active_only=True)]
target_brands.extend(["mercado_livre", "netshoes", "amazon"])
brand_results = await engine_factory.search_all_brands(
    query=q,
    brands=target_brands,  # pass explicitly
    ...
)
return ComparisonResult(query=q, brands_searched=target_brands, results=brand_results)
```

---

## Info

### IN-01: Test docstrings declare RED state for scenarios that are now GREEN

**File:** `tests/test_engine_detection.py:7-12`, `tests/test_brand_active.py:7-12`

**Issue:** Both test files were authored as "RED tests" written before the implementation. The implementation in this phase has satisfied all the requirements. The docstrings still say things like "RED: list_brands nao tem este param → TypeError" and "RED: set_active nao existe → AttributeError". Running these tests green while their docs say they should be red is misleading for future maintainers. The test class docstrings and individual test docstrings should be updated to reflect that they now verify passing behaviour, not anticipated failures.

**Fix:** Update class/method docstrings to remove RED-phase language. For example, `test_wake_commerce_returns_unknown` docstring says "RED: o codigo atual nao proba Wake — cai no fallback 'vtex' (L53). Esta falha e esperada ate a implementacao de Wave 1." This is no longer true.

---

### IN-02: Virtual marketplace injection in `GET /brands/` appended on every request — duplicates on concurrent calls are not guarded

**File:** `api/routes_brands.py:97-131`

**Issue:** `brand_service.list_brands()` returns a mutable list from `list(self.brands.values())` (brand_service.py:209). The route then calls `.append()` on this list three times (lines 103, 112, 121). While the list itself is a fresh copy each call (safe for concurrent requests), the pattern is fragile: if `list_brands()` were ever changed to return a cached or shared list, the appends would accumulate across requests, causing the virtual brands to appear multiple times. A more robust approach is to construct the injected list separately rather than mutating the returned list.

**Fix:**
```python
async def list_brands():
    brands = brand_service.list_brands()
    virtual = [
        DynamicBrand(brand_key="mercado_livre", brand_name="Mercado Livre",
                     domain="mercadolivre.com.br", engine="mercadolivre", mappings=[]),
        DynamicBrand(brand_key="netshoes", brand_name="Netshoes",
                     domain="netshoes.com.br", engine="netshoes", mappings=[]),
        DynamicBrand(brand_key="amazon", brand_name="Amazon",
                     domain="amazon.com.br", engine="amazon", mappings=[]),
    ]
    return brands + virtual
```

---

_Reviewed: 2026-06-18T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
