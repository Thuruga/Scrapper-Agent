# Phase 30: Detecção de Engine SFCC & Wake - Pattern Map

**Mapped:** 2026-06-23
**Files analyzed:** 4
**Analogs found:** 4 / 4

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/api/routes_brands.py` | route/utility | request-response + browser I/O | itself (existing `detect_engine`) | exact — extend in place |
| `backend/services/engines/factory.py` | service/factory | request-response | itself (existing `get_engine`) | exact — extend in place |
| `backend/core/browser_manager.py` | utility | file-I/O / browser | itself (`BrowserManager.fetch_html`) | reuse only — no modification |
| `backend/tests/test_engine_detection.py` | test | event-driven mock | itself (existing `_make_mock_session`) | exact — extend in place |

---

## Pattern Assignments

### `backend/api/routes_brands.py` — `detect_engine` extension

**Changes:** (a) flip Wake branch L51-53 from `"unknown"` to `"wake"`; (b) add SFCC browser probe as last step before final `return "unknown"`.

---

#### Change A — Wake flip (L51-53)

**Current code (lines 51-53):**
```python
if "fbitsstatic.net" in html_lower:
    logger.info("detect_engine: Wake Commerce detectado para %s (fbitsstatic.net)", domain)
    return "unknown"
```

**Target pattern:** replace `return "unknown"` with `return "wake"`. No structural change; the marker check, logger.info call, and early return shape stay identical.

**Analog for the return-value flip:** look at the VTEX HTML branch immediately below (lines 58-59) — same shape, already returns a named engine string:
```python
# lines 58-59
if "vtexassets.com" in html_lower or "vtexcommercestable.com" in html_lower:
    return "vtex"
```

---

#### Change B — SFCC browser probe (new Step 6, inserted before final `return "unknown"`)

**Analog — how existing probes are structured (try/except → log → return/fallback):**

Shopify probe (lines 22-30):
```python
# 1. Tenta Shopify via collections.json
try:
    async with session.get(f"{base_url}/collections.json", timeout=aiohttp.ClientTimeout(total=5), headers=headers) as resp:
        if resp.status == 200:
            data = await resp.json()
            if "collections" in data:
                return "shopify"
except Exception as e:
    logger.debug("Detecção Shopify via collections.json falhou para %s: %s", domain, e)
```

VTEX probe (lines 32-38):
```python
# 2. Tenta VTEX via API padrão
try:
    async with session.get(f"{base_url}/api/catalog_system/pub/category/tree/1", timeout=aiohttp.ClientTimeout(total=5), headers=headers) as resp:
        if resp.status == 200:
            return "vtex"
except Exception as e:
    logger.debug("Detecção VTEX via API de categorias falhou para %s: %s", domain, e)
```

HTML fallback with allow_redirects=False (lines 43-65):
```python
try:
    async with session.get(base_url, ..., allow_redirects=False) as resp:
        html = await resp.text()
        html_lower = html.lower()
        if "fbitsstatic.net" in html_lower:
            ...
except Exception as e:
    logger.debug("Detecção via análise do HTML da home falhou para %s: %s", domain, e)
```

**Pattern to copy for SFCC probe:**
```python
# Step 6 (D-01, D-02, D-03, D-07): SFCC browser probe — last resort.
# Renderiza a home via Playwright para expor assets demandware que HTTP direto
# não entrega (403). Exclusivo: demandware.static / demandware.edgesuite.net.
try:
    from core.browser_manager import BrowserManager
    rendered_html = await BrowserManager.fetch_html(f"https://{domain}")
    rendered_lower = rendered_html.lower()
    if "demandware.static" in rendered_lower or "demandware.edgesuite.net" in rendered_lower:
        logger.info("detect_engine: SFCC detectado para %s (demandware marker)", domain)
        return "sfcc"
except Exception as e:
    logger.debug("Detecção SFCC via browser falhou para %s: %s", domain, e)

# Step 7: plataforma desconhecida.
return "unknown"
```

Key points to preserve from existing probe pattern:
- `try/except Exception` — never crash, always degrade to next step (D-04)
- `logger.debug` on failure (not `logger.error` — probe failure is normal)
- `logger.info` on positive match (same as Wake branch L52)
- Exclusive-marker check in lowercased HTML (same as `html_lower` pattern L46)
- `BrowserManager.fetch_html` is the reuse point (D-03); it already runs `sync_playwright` in `asyncio.to_thread` — no extra wrapping needed

---

**Import to add at top of `routes_brands.py` (or inside the try block as shown above):**

`BrowserManager` can be imported at module level following the existing import block (lines 1-9) or lazily inside the try block. Lazy import (inside try) is safer so that a missing Playwright install does not break the whole module on startup. Existing analog: `routes_brands.py` line 188 uses a lazy `from services.price_monitor_service import monitor_service` inside a function body — same pattern applies here.

---

### `backend/services/engines/factory.py` — `EngineFactory.get_engine` guard

**Change:** Add explicit guard for `sfcc` and `wake` before the implicit VTEX fallback at line 45 (D-09, D-10).

**Current code — the gap (lines 42-45):**
```python
if engine_type == "shopify":
    return ShopifyEngine(brand_key)
    
return VTEXEngine(brand_key)   # ← silently handles every unknown string
```

**Analog — existing marketplace guard pattern (lines 22-28):**
```python
brand_key_lower = brand_key.lower().replace(" ", "").replace("_", "")
if brand_key_lower == "mercadolivre":
    return MercadoLivreEngine()
elif brand_key_lower == "netshoes":
    return NetshoesEngine()
elif brand_key_lower == "amazon":
    return AmazonEngine()
```

**Pattern to copy for SFCC/Wake guard (insert between lines 43-44 and line 45):**
```python
if engine_type in ("sfcc", "wake"):
    # D-09: engine registrado mas ainda sem implementação (Phases 31/32).
    # Falha diagnosticável em vez de cair silenciosamente no VTEXEngine.
    raise NotImplementedError(
        f"Engine '{engine_type}' para '{brand_key}' ainda não disponível "
        f"(Phase 31/32 pendente). A marca está ativa mas será ignorada na busca."
    )

return VTEXEngine(brand_key)
```

**Why `NotImplementedError`:** it is a subclass of `Exception`, so it is captured by `_search_one`'s bare `except Exception as e` at lines 86-88 without any changes to that code. The error string becomes `BrandSearchResult.error`, giving a diagnosticable message in the API response (D-10).

**`_search_one` capture point (lines 75-88) — no change needed:**
```python
async def _search_one(brand_key: str) -> BrandSearchResult:
    try:
        engine = self.get_engine(brand_key)
        return await engine.search(...)
    except Exception as e:
        # Retorna um resultado vazio com erro para não quebrar o gather
        return BrandSearchResult(brand_key=brand_key, brand_name=brand_key, error=str(e))
```

The `NotImplementedError` raised inside `get_engine` propagates up through line 77 and is caught at line 86 — the gather continues unbroken.

---

### `backend/core/browser_manager.py` — REUSE ONLY

**No modification.** The SFCC probe calls `BrowserManager.fetch_html(url)` directly.

**API to reuse (lines 78-163):**
```python
@classmethod
async def fetch_html(
    cls,
    url: str,
    wait_selector: Optional[str] = None,
    timeout: int = 30000,
    wait_until: str = "domcontentloaded",
    extra_sleep: float = 1.0,
) -> str:
```

**Call signature for the SFCC probe:**
```python
rendered_html = await BrowserManager.fetch_html(f"https://{domain}")
```

Default `wait_until="domcontentloaded"` and `extra_sleep=1.0` are sufficient for asset-host detection (demandware markers are in `<link>`/`<script>` tags loaded at parse time). No `wait_selector` needed.

The method raises on navigation error (line 154 `raise`), which the probe's `except Exception` will catch and degrade to `"unknown"` (D-04).

---

### `backend/tests/test_engine_detection.py` — new test cases

**Existing mock infrastructure (lines 25-54) — reuse as-is:**

```python
def _make_mock_response(status: int, json_data=None, text_data=""):
    resp = MagicMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data or {})
    resp.text = AsyncMock(return_value=text_data)
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp

def _make_mock_session(responses: dict):
    session = MagicMock()
    def _get(url, **kwargs):
        for key, resp in responses.items():
            if key in url:
                return resp
        raise aiohttp.ClientError("no mock for " + url)
    session.get = _get
    session.post = MagicMock(side_effect=aiohttp.ClientError("blocked"))
    return session
```

**New mock seam needed for SFCC browser path (D-11):**

The SFCC probe calls `BrowserManager.fetch_html(url)` — an async classmethod. Mock it with `patch` + `AsyncMock`:

```python
# Pattern: mock BrowserManager.fetch_html to inject a fixture HTML
with patch(
    "api.routes_brands.BrowserManager.fetch_html",
    new=AsyncMock(return_value='<link href="https://www.demandware.static/...">'),
):
    result = asyncio.run(detect_engine("www.lacoste.com.br"))
assert result == "sfcc"
```

**Existing analog for patching a coroutine on the module under test (lines 68-74):**
```python
with patch(
    "api.routes_brands.SessionManager.get_session",
    new=AsyncMock(return_value=mock_session),
):
    from api.routes_brands import detect_engine
    result = asyncio.run(detect_engine("test.myshopify.com"))
```

Same `patch` target convention: `"api.routes_brands.<ClassName>.<method>"`.

**New test cases to add (4 scenarios from D-11):**

1. **Wake → `"wake"`** (was `"unknown"` — existing test `test_wake_commerce_returns_unknown` becomes GREEN, update its assert from `"unknown"` to `"wake"`)

2. **SFCC → `"sfcc"`** (new):
   - Mock session: all HTTP probes fail (404 / ClientError)
   - Mock `BrowserManager.fetch_html`: returns HTML with `demandware.static`
   - Assert `result == "sfcc"`

3. **All fail including browser → `"unknown"`** (new, extends existing `test_all_probes_fail_returns_unknown`):
   - Mock session: all fail
   - Mock `BrowserManager.fetch_html`: returns generic HTML without demandware markers
   - Assert `result == "unknown"`

4. **Anti-false-positive: 403 + no demandware → `"unknown"`** (new, Zara/SC-4):
   - Mock session: all HTTP probes return 403 or raise
   - Mock `BrowserManager.fetch_html`: returns HTML without `demandware.static`/`demandware.edgesuite.net`
   - Assert `result == "unknown"`

**Pattern for case 2 (SFCC):**
```python
def test_sfcc_detected_via_browser(self):
    """SFCC: HTTP probes falham; browser renderiza HTML com demandware.static → 'sfcc'."""
    no = _make_mock_response(404)
    mock_session = _make_mock_session({
        "collections.json": no,
        "category/tree/1": no,
        "lacoste.com.br": no,  # home HTML probe também falha (403 simulado)
    })
    sfcc_html = '<link rel="stylesheet" href="https://www.demandware.static/sites/...">'
    with patch(
        "api.routes_brands.SessionManager.get_session",
        new=AsyncMock(return_value=mock_session),
    ):
        with patch(
            "api.routes_brands.BrowserManager.fetch_html",
            new=AsyncMock(return_value=sfcc_html),
        ):
            from api.routes_brands import detect_engine
            result = asyncio.run(detect_engine("www.lacoste.com.br"))
    assert result == "sfcc"
```

---

## Shared Patterns

### try/except → degrade (never crash)
**Source:** `backend/api/routes_brands.py` lines 22-30, 32-38, 43-65
**Apply to:** SFCC browser probe (new Step 6)
```python
try:
    ...  # probe logic
except Exception as e:
    logger.debug("<probe name> falhou para %s: %s", domain, e)
# execution continues to next probe / return "unknown"
```

### Exclusive-marker check in lowercased HTML
**Source:** `backend/api/routes_brands.py` lines 46, 51, 58, 62
**Apply to:** SFCC marker check (`demandware.static`, `demandware.edgesuite.net`)
```python
html_lower = html.lower()
if "marker-string" in html_lower:
    return "engine_name"
```

### Patch target convention in tests
**Source:** `backend/tests/test_engine_detection.py` lines 68-70
**Apply to:** BrowserManager mock seam
```python
patch("api.routes_brands.<ClassName>.<method>", new=AsyncMock(return_value=...))
```

---

## No Analog Found

None. All four files have direct in-place analogs.

---

## Metadata

**Analog search scope:** `backend/api/`, `backend/services/engines/`, `backend/core/`, `backend/tests/`
**Files read:** 4 (routes_brands.py, factory.py, browser_manager.py, test_engine_detection.py)
**Pattern extraction date:** 2026-06-23
