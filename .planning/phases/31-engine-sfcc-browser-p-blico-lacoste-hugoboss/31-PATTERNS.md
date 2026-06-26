# Phase 31: Engine SFCC (Browser Público) — Lacoste & HugoBoss - Pattern Map

**Mapped:** 2026-06-24
**Files analyzed:** 4 new/modified files
**Analogs found:** 4 / 4

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/services/engines/sfcc_engine.py` | engine (service) | request-response + browser I/O | `backend/services/engines/shopify_engine.py` | exact |
| `backend/services/engines/sfcc_parser.py` | utility / parser | transform | `.planning/spikes/005-sfcc-public-parser-prototype/experiment.py` | role-match |
| `backend/services/engines/factory.py` | factory / config | request-response | `backend/services/engines/factory.py` (self — branch edit) | exact |
| `backend/tests/test_sfcc_engine.py` | test | — | `backend/tests/test_engine_detection.py` | exact |

---

## Pattern Assignments

### `backend/services/engines/sfcc_engine.py` (engine, request-response + browser I/O)

**Analog:** `backend/services/engines/shopify_engine.py`

**Imports pattern** (shopify_engine.py lines 1-6):
```python
import asyncio
from typing import List, Dict, Any, Optional, Callable
from services.engines.base_engine import BaseEngine
from core.models import BrandSearchResult, SearchProductResult, ShippingInfo
# SFCC-specific additions:
import logging
from core.browser_manager import BrowserManager
from services.engines.sfcc_parser import parse_search_results, parse_pdp

logger = logging.getLogger(__name__)
```

**Class declaration + `__init__` pattern** (shopify_engine.py lines 9-19):
```python
class SFCCEngine(BaseEngine):
    """
    Motor de e-commerce para a plataforma SFCC (Demandware).
    Extração via browser-rendered HTML (Playwright) — path público, sem OCAPI/SCAPI.
    """

    def __init__(self, brand_key: str):
        self.brand_key = brand_key

    def get_engine_name(self) -> str:
        return "SFCC"
```

**`calculate_shipping` pattern — returns None** (shopify_engine.py lines 121-123):
```python
async def calculate_shipping(self, product: Any, zipcode: str) -> Optional[Dict[str, Any]]:
    # D-09: path público sem checkout — sem cálculo de frete
    return None
```

**`search()` signature pattern** (shopify_engine.py lines 94-102):
```python
async def search(
    self,
    query: str,
    max_results: int = 10,
    sort: Optional[str] = None,
    only_in_stock: bool = False,
    zipcode: Optional[str] = None,
    include_shipping: bool = False
) -> Any:
```

**`search()` error guard + BrandSearchResult construction** (research code examples):
```python
# Source: RESEARCH.md §Pattern 1 + shopify_engine.py structure
async def search(self, query: str, max_results: int = 10, **kwargs) -> BrandSearchResult:
    from services.brand_service import brand_service
    brand = brand_service.get_brand(self.brand_key)
    if not brand or not brand.domain:
        return BrandSearchResult(
            brand_key=self.brand_key,
            brand_name=self.brand_key,
            error="Domain not found"
        )
    # ... fetch + parse + enrich ...
    return BrandSearchResult(
        brand_key=self.brand_key,
        brand_name=brand.brand_name,
        products=[
            SearchProductResult(
                brand=brand.brand_name,
                product_name=p["raw_title"],
                url=p["url"],
                price_full=p["price_full"],
                image_url=p.get("image_url"),
                available=p.get("stock_availability"),
            )
            for p in validated_products
        ],
        total_found=len(validated_products),
    )
```

**Concurrent PDP enrichment with semaphore** (RESEARCH.md §Pattern 3):
```python
async def _enrich_results(self, candidate_urls: list, max_results: int) -> list:
    sem = asyncio.Semaphore(3)  # max 3 concurrent PDPs (D-08)

    async def _enrich_one(url):
        async with sem:
            try:
                html = await BrowserManager.fetch_html(url)
                return parse_pdp(html, url)
            except Exception as e:
                logger.warning("SFCC PDP fetch failed for %s: %s", url, e)
                return None

    tasks = [_enrich_one(url) for url in candidate_urls[:max_results]]
    results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]
```

**`validate_single` usage** (shopify_engine.py lines 88-90):
```python
validated = self.validate_single(product, log_callback=log_callback)
if validated:
    yield validated
```

**`run_bulk_scrape` signature + emit_log pattern** (shopify_engine.py lines 72-92):
```python
async def run_bulk_scrape(
    self,
    category_url: str,
    log_callback: Optional[Callable] = None,
    cancel_event: Optional[asyncio.Event] = None,
    zipcode: Optional[str] = None,
    include_shipping: bool = False
):
    def emit(msg):
        self.emit_log(log_callback, msg)
    # ... fetch html, parse cards, validate_single, yield ...
```

**`discover_categories()` + graceful stub** (RESEARCH.md §CRQ-2 implementation approach):
```python
async def discover_categories(self) -> List[Dict[str, Any]]:
    from services.brand_service import brand_service
    brand = brand_service.get_brand(self.brand_key)
    if not brand:
        return []
    try:
        html = await BrowserManager.fetch_html(
            f"https://www.{brand.domain}",
            wait_selector="nav",
            extra_sleep=2.0
        )
        # ... BeautifulSoup nav extraction ...
    except Exception as e:
        logger.warning("SFCC discover_categories failed for %s: %s", self.brand_key, e)
        return []  # D-06 graceful stub
```

**`get_catalog()` pattern** (shopify_engine.py lines 59-70):
```python
async def get_catalog(self) -> List[Dict[str, Any]]:
    flat_cats = await self.discover_categories()
    return [
        {
            "group": "Coleções / Categorias",
            "items": [{"label": c["name"], "path": c["path"]} for c in flat_cats],
        }
    ]
```

**`BrowserManager.fetch_html` call signature** (browser_manager.py lines 78-85):
```python
# Signature to use — all params optional except url:
await BrowserManager.fetch_html(
    url,
    wait_selector=None,   # CSS selector to wait for (e.g. "nav", ".product-card")
    timeout=30000,
    wait_until="domcontentloaded",
    extra_sleep=1.0,      # extra pause after page load
)
# Returns: str (full rendered HTML)
# Internally: runs sync_playwright in asyncio.to_thread — NEVER nest inside another to_thread
```

---

### `backend/services/engines/sfcc_parser.py` (utility / parser, transform)

**Analog:** `.planning/spikes/005-sfcc-public-parser-prototype/experiment.py`

**Imports pattern** (experiment.py lines 1-17):
```python
from __future__ import annotations
import json
import re
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
```

**JSON-LD extraction** (experiment.py lines — derive from normalize_observation + RESEARCH.md §Pattern 4):
```python
def extract_jsonld_products(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(data, list):
            for item in data:
                if item.get("@type") in ("Product", "ProductGroup"):
                    results.append(item)
        elif data.get("@type") in ("Product", "ProductGroup"):
            results.append(data)
    return results
```

**OpenGraph extraction** (experiment.py `normalize_jsonld_product` lines 176-208 — meta dict pattern):
```python
def extract_og_meta(html: str) -> Dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    meta = {}
    for tag in soup.find_all("meta", property=True):
        prop = tag.get("property", "")
        if prop.startswith("og:"):
            meta[prop] = tag.get("content", "")
    return meta
```

**`offer_from` helper** (experiment.py lines 140-144):
```python
def offer_from(product: Dict[str, Any]) -> Dict[str, Any]:
    offers = product.get("offers")
    if isinstance(offers, list):
        return offers[0] if offers else {}
    return offers if isinstance(offers, dict) else {}
```

**BR price parser** (RESEARCH.md §Pattern 2 — D-02 critical):
```python
_BR_MONEY_RE = re.compile(
    r"R\$\s*([\d]{1,3}(?:\.[\d]{3})*,[\d]{2}|[\d]+,[\d]{2})"
)

def parse_price_br(text: str) -> Optional[float]:
    """
    Parse a Brazilian Real price string to float.
    'R$ 1.234,56' -> 1234.56,  'R$ 119,00' -> 119.0
    Does NOT match USD format or bare numbers without R$ prefix.
    """
    if isinstance(text, (int, float)):
        return float(text) if float(text) > 0 else None
    match = _BR_MONEY_RE.search(str(text))
    if not match:
        return None
    raw = match.group(1)             # e.g. '1.234,56'
    normalized = raw.replace(".", "").replace(",", ".")  # '1234.56'
    value = float(normalized)
    return value if value > 0 else None
```

**Price extraction priority** (RESEARCH.md §CRQ-1 recommendation):
```python
def extract_price(offer: Dict, og_meta: Dict, visible_text: str) -> Optional[float]:
    # Layer 1: JSON-LD offers.price — typically a plain float even on BR stores
    raw_price = offer.get("price") or offer.get("lowPrice")
    if raw_price is not None:
        try:
            value = float(raw_price)
            if value > 0:
                return value
        except (ValueError, TypeError):
            pass  # Falls through to Layer 2

    # Layer 2: OpenGraph og:product:price:amount
    og_price = og_meta.get("og:product:price:amount")
    if og_price:
        try:
            value = float(og_price)
            if value > 0:
                return value
        except (ValueError, TypeError):
            pass

    # Layer 3: BR regex on visible rendered text (anchored on R$ to avoid
    # accessibility-text false positives — Spike 006 Pitfall)
    return parse_price_br(visible_text or "")
```

**`parse_availability` helper** (experiment.py lines 129-137):
```python
def parse_availability(value: Any) -> Optional[bool]:
    text = str(value or "").lower().strip()
    if not text:
        return None
    if "instock" in text or "in stock" in text:
        return True
    if "outofstock" in text or "out of stock" in text or "sold out" in text:
        return False
    return None
```

**`parse_pdp` public function** (derived from experiment.py `normalize_jsonld_product` lines 172-209):
```python
def parse_pdp(html: str, source_url: str) -> Optional[Dict[str, Any]]:
    """
    Parse a rendered SFCC PDP page.
    Returns a dict compatible with RawProductBronze fields, or None if extraction fails.
    JSON-LD first -> OpenGraph fallback -> None.
    """
    soup = BeautifulSoup(html, "html.parser")
    jsonld_products = extract_jsonld_products(html)
    og_meta = extract_og_meta(html)

    if not jsonld_products and not og_meta:
        return None

    product_ld = jsonld_products[0] if jsonld_products else {}
    offer = offer_from(product_ld)

    # Title: JSON-LD name -> og:title
    raw_title = (product_ld.get("name") or og_meta.get("og:title") or "").strip()
    if not raw_title:
        return None

    # Image: JSON-LD image -> og:image
    image_raw = product_ld.get("image")
    image_url = (
        image_raw[0] if isinstance(image_raw, list) and image_raw
        else image_raw if isinstance(image_raw, str)
        else og_meta.get("og:image")
    )

    # Price with layered strategy
    price_full = extract_price(offer, og_meta, "")

    return {
        "url": source_url,
        "brand": _extract_brand(product_ld, og_meta),
        "raw_title": raw_title,
        "raw_description": (product_ld.get("description") or og_meta.get("og:description") or raw_title).strip(),
        "price_full": price_full,
        "image_url": image_url,
        "stock_availability": parse_availability(offer.get("availability") or og_meta.get("og:product:availability")),
        "available_colors": [],
        "available_sizes": [],
        "specifications": {},
    }
```

**`parse_search_results` public function** (derived from experiment.py `normalize_visible_card` lines 212-229):
```python
def parse_search_results(html: str, base_domain: str) -> List[str]:
    """
    Extract product page URLs from a rendered SFCC search/category page.
    Returns a list of absolute URLs for PDP enrichment (D-07).
    Does NOT extract product data — enrichment happens in the engine via parse_pdp.
    """
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Normalize to absolute URL
        if href.startswith("/"):
            href = f"https://www.{base_domain}{href}"
        if not href.startswith("http"):
            continue
        # Heuristic: product links on SFCC typically contain /p/ or a product ID segment
        if href not in seen and _looks_like_pdp_url(href, base_domain):
            seen.add(href)
            urls.append(href)
    return urls
```

---

### `backend/services/engines/factory.py` (factory, config edit)

**Analog:** `backend/services/engines/factory.py` (self — surgical edit at lines 51-54)

**Current guard to replace** (factory.py lines 51-54):
```python
# BEFORE (Phase 30 guard — to be split):
if engine_type in ("sfcc", "wake"):
    raise NotImplementedError(
        f"Engine '{engine_type}' para '{brand_key}' ainda não disponível (Phase 31/32 pendente)."
    )
```

**Replacement pattern** (RESEARCH.md §Code Examples + Pitfall 4):
```python
# AFTER (Phase 31 — lazy import preserves circular-import safety):
if engine_type == "sfcc":
    from services.engines.sfcc_engine import SFCCEngine
    return SFCCEngine(brand_key)
if engine_type == "wake":
    raise NotImplementedError(
        f"Engine 'wake' para '{brand_key}' ainda não disponível (Phase 32 pendente)."
    )
```

**Import placement pattern** (factory.py lines 1-9 — lazy import avoids circular deps; keep top imports intact):
```python
# Existing top-of-file imports are NOT changed. SFCCEngine is imported lazily
# inside get_engine() to match the pattern already used by detect_engine in routes_brands.py.
# Do NOT add `from services.engines.sfcc_engine import SFCCEngine` at the top level.
```

---

### `backend/tests/test_sfcc_engine.py` (test)

**Analog:** `backend/tests/test_engine_detection.py`

**File-level mock seam constant** (test_engine_detection.py line 33):
```python
_BROWSER_FETCH_TARGET = "core.browser_manager.BrowserManager.fetch_html"
```

**AsyncMock + patch pattern for browser-dependent tests** (test_engine_detection.py lines 151-160):
```python
from unittest.mock import AsyncMock, patch
import asyncio

with patch(
    _BROWSER_FETCH_TARGET,
    new=AsyncMock(return_value=rendered_html_fixture),
):
    result = asyncio.run(some_async_function())
assert ...
```

**Test class organization pattern** (test_engine_detection.py lines 75-358 — class per concern):
```python
class TestSFCCParser:
    """Pure-Python parser tests — no mock needed."""

    def test_parse_price_br_standard(self):
        from services.engines.sfcc_parser import parse_price_br
        assert parse_price_br("R$ 1.234,56") == 1234.56

    def test_parse_price_br_simple(self):
        from services.engines.sfcc_parser import parse_price_br
        assert parse_price_br("R$ 119,00") == 119.0

    def test_parse_price_br_rejects_usd(self):
        from services.engines.sfcc_parser import parse_price_br
        assert parse_price_br("$119.00") is None

    def test_parse_price_br_rejects_accessibility_number(self):
        from services.engines.sfcc_parser import parse_price_br
        assert parse_price_br("5 out of 5 stars") is None


class TestSFCCFactory:
    """Factory integration — SFCCEngine returned for engine='sfcc'."""

    def test_factory_returns_sfcc_engine(self):
        from services.engines.factory import EngineFactory
        from services.engines.sfcc_engine import SFCCEngine
        from unittest.mock import patch, MagicMock
        fake_brand = MagicMock()
        fake_brand.engine = "sfcc"
        with patch("services.engines.factory.brand_service.get_brand", return_value=fake_brand):
            engine = EngineFactory.get_engine("lacoste")
        assert isinstance(engine, SFCCEngine)

    def test_factory_wake_still_raises(self):
        from services.engines.factory import EngineFactory
        from unittest.mock import patch, MagicMock
        import pytest
        fake_brand = MagicMock()
        fake_brand.engine = "wake"
        with patch("services.engines.factory.brand_service.get_brand", return_value=fake_brand):
            with pytest.raises(NotImplementedError):
                EngineFactory.get_engine("some_wake_brand")


class TestSFCCEngineSearch:
    """search() + enrichment — BrowserManager mocked (hermetic, no real browser)."""

    def test_search_returns_brand_search_result(self):
        from services.engines.sfcc_engine import SFCCEngine
        # Provide fixture HTML for search page + PDP
        search_html = "<html>...</html>"   # fixture with product links
        pdp_html = "<html>...</html>"      # fixture with JSON-LD Product
        with patch(_BROWSER_FETCH_TARGET, new=AsyncMock(side_effect=[search_html, pdp_html])):
            engine = SFCCEngine("lacoste")
            result = asyncio.run(engine.search("polo", max_results=1))
        from core.models import BrandSearchResult
        assert isinstance(result, BrandSearchResult)

    def test_search_results_have_image(self):
        # Products from search() must have image_url (D-07: PDP enrichment ran)
        ...

    def test_calculate_shipping_returns_none(self):
        from services.engines.sfcc_engine import SFCCEngine
        engine = SFCCEngine("lacoste")
        result = asyncio.run(engine.calculate_shipping({}, "01310-100"))
        assert result is None

    def test_sfcc_engine_implements_base_engine(self):
        from services.engines.sfcc_engine import SFCCEngine
        from services.engines.base_engine import BaseEngine
        # Instantiation should not raise TypeError (all abstract methods implemented)
        engine = SFCCEngine("lacoste")
        assert isinstance(engine, BaseEngine)


class TestSFCCCategoryDiscovery:
    """discover_categories() graceful stub — D-06."""

    def test_discover_categories_stub_on_empty_nav(self):
        # When BrowserManager returns HTML without <nav>, return [] without crash
        from services.engines.sfcc_engine import SFCCEngine
        no_nav_html = "<html><body><div>no nav here</div></body></html>"
        with patch(_BROWSER_FETCH_TARGET, new=AsyncMock(return_value=no_nav_html)):
            engine = SFCCEngine("lacoste")
            result = asyncio.run(engine.discover_categories())
        assert result == []
```

**Pytest configuration** (pytest.ini at project root — `testpaths = backend/tests`, `pythonpath = backend`):
- Run single file: `pytest backend/tests/test_sfcc_engine.py -x`
- Run full suite: `pytest backend/tests/ -ra`

---

## Shared Patterns

### `BrowserManager.fetch_html` — async call contract
**Source:** `backend/core/browser_manager.py` lines 78-163
**Apply to:** `sfcc_engine.py` (all browser calls), `test_sfcc_engine.py` (mock target)

```python
# Correct call pattern (from async method in engine):
html = await BrowserManager.fetch_html(url, extra_sleep=1.0)

# With nav wait (for discover_categories):
html = await BrowserManager.fetch_html(url, wait_selector="nav", extra_sleep=2.0)

# Mock seam (hermetic tests):
_BROWSER_FETCH_TARGET = "core.browser_manager.BrowserManager.fetch_html"
with patch(_BROWSER_FETCH_TARGET, new=AsyncMock(return_value=fixture_html)):
    ...
```

### Quality Gate — `validate_single` / `validate_and_filter`
**Source:** `backend/services/engines/base_engine.py` lines 160-163
**Apply to:** `sfcc_engine.py` — call `self.validate_single(product)` on every parsed product dict before adding to results

```python
# validate_single: returns validated dict or None (single item)
validated = self.validate_single(product, log_callback=log_callback)
if validated:
    results.append(validated)

# validate_and_filter: batch variant
valid_products = self.validate_and_filter(raw_products, log_callback=log_callback)
```

Required fields that trigger rejection (models.py lines 28-88):
- `url` — must be non-empty string
- `raw_title` — must be non-empty string
- `price_full` — must be a positive float (`> 0`)
- `image_url` — must be non-empty and not `"None"` string

### `emit_log` — structured log emission
**Source:** `backend/services/engines/base_engine.py` lines 85-104
**Apply to:** `sfcc_engine.py`

```python
def emit(msg):
    self.emit_log(log_callback, msg)
# Accepts dict (with "type" key) or plain string; wraps string as {"type": "info", "message": str}
```

### `BrandSearchResult` construction
**Source:** `backend/core/models.py` lines 136-144
**Apply to:** `sfcc_engine.py` — every `search()` exit path must return a `BrandSearchResult`

```python
# Error path:
return BrandSearchResult(brand_key=self.brand_key, brand_name=self.brand_key, error="reason")

# Success path:
return BrandSearchResult(
    brand_key=self.brand_key,
    brand_name=brand_name,
    products=[SearchProductResult(...)],
    total_found=len(products),
)
```

### `filter_mens_fashion` — gender blocklist
**Source:** `backend/services/engines/base_engine.py` lines 165-201
**Apply to:** `sfcc_engine.py` — call `self.filter_mens_fashion(products)` after parsing, before validate_and_filter, for consistency with CAT-01

```python
filtered = self.filter_mens_fashion(raw_products)
validated = self.validate_and_filter(filtered, log_callback=log_callback)
```

---

## No Analog Found

No files in this phase lack an analog. All four files have direct codebase analogs.

---

## Anti-Pattern Notes for Planner

1. **Do NOT use `parse_price` from experiment.py spike 005** (lines 101-116) — designed for USD `$119.00`; returns `1.0` for `"R$ 1.234,56"`. Use `parse_price_br()` from `sfcc_parser.py`.
2. **Do NOT use `async_playwright` directly** — use `await BrowserManager.fetch_html(url)` which wraps `sync_playwright` in `asyncio.to_thread`.
3. **Do NOT delete the `wake` guard** in `factory.py` line 51 — split it, keep `wake` raising `NotImplementedError`.
4. **Do NOT register `SFCCEngine` as singleton** — `get_engine(brand_key)` must return `SFCCEngine(brand_key)` (new instance per call).
5. **Do NOT set `is_free_shipping=True` or `shipping_price=0.0`** — triggers "Frete Grátis" badge in App.tsx line 1777; leave defaults (`False` / `None`).

---

## Metadata

**Analog search scope:** `backend/services/engines/`, `backend/tests/`, `backend/core/`, `.planning/spikes/005*/`, `.planning/spikes/006*/`
**Files read:** 8 (shopify_engine.py, base_engine.py, factory.py, browser_manager.py, models.py, test_engine_detection.py, experiment.py×2)
**Pattern extraction date:** 2026-06-24
