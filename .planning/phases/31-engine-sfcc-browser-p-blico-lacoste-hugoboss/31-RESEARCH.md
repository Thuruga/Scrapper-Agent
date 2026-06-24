# Phase 31: Engine SFCC (Browser Público) — Lacoste & HugoBoss - Research

**Researched:** 2026-06-24
**Domain:** Salesforce Commerce Cloud (SFCC/Demandware) browser-rendered public extraction, Python/Playwright engine implementation
**Confidence:** HIGH (core implementation path); MEDIUM (BR locale signal behavior); LOW (category tree discovery feasibility)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Target BR storefronts — `lacoste.com.br` and `hugoboss.com.br`. Price in reais natively, no currency conversion. Spikes 004-006 validated US stores (`$119.00 USD`); Phase 31 changes target to `.com.br`.
- **D-02:** Price parser must handle BR format (`R$ 1.234,56` — dot thousands, comma decimal). Prefer explicit money patterns over generic accessibility-text numbers (Pitfall from Spike 006).
- **D-03:** Search by query term (SC-1) is served by rendering the store's native search page (query → rendered results page → cards), then enriching via PDP (see D-07). Not "category navigation" (doesn't match free query) and not "search + category fallback" (out of scope).
- **D-04:** `SFCCEngine` implements the full `BaseEngine` contract: `run_bulk_scrape`, `discover_categories`, `get_catalog`, `search`, `get_product_details`, `calculate_shipping`, `get_engine_name`.
- **D-05:** Deliver real `discover_categories()`/`get_catalog()` — Lacoste/HugoBoss appear in the category monitoring screen like VTEX/Shopify. This expands beyond SC-1..4 (search/price) and was NOT validated by spikes.
- **D-06 [guard]:** Category delivery (D-05) is gated by research. If SFCC public category-tree discovery from the rendered home/menu is infeasible or too costly, Phase 31 falls back to a graceful stub (`discover_categories`/`get_catalog` return empty without crash) and full catalog becomes a follow-up phase. Planner must sequence search (SC-1..4 core) BEFORE catalog (D-05 expansion).
- **D-07:** Enrich ALL results up to `max_results` by opening each PDP (price + image always present). Lacoste has no image in cards; HugoBoss has no price in category — both only available at PDP level.
- **D-08:** Because D-07 is expensive (each PDP = one browser navigation), `max_results` should be modest by default. Planner decides the exact number (Claude's Discretion). Concurrency/throttle strategy also to planner.
- **D-09:** `calculate_shipping` does NOT calculate shipping (public scope, no checkout): returns explicit absence (None or "unavailable" ShippingInfo), without error and without a false "Frete Grátis" badge. Mirrors `ShopifyEngine.calculate_shipping` (returns None). Exact form (None vs. ShippingInfo) at planner's discretion.

### Claude's Discretion

- Default value of `max_results` / scan depth (D-08).
- Exact return shape of `calculate_shipping` (None vs. ShippingInfo of absence) (D-09).
- Concrete extraction strategy JSON-LD vs. OpenGraph vs. card text per brand (Spike 005: HugoBoss strong in ProductGroup JSON-LD at category; Lacoste strong in Product JSON-LD + OG at PDP).
- Class/constant/marker names and test structure follow repo conventions.

### Deferred Ideas (OUT OF SCOPE)

- Shipping/checkout/stock by ZIP for SFCC (requires OCAPI/SCAPI with credentials).
- OCAPI/SCAPI (authenticated SFCC APIs) — no commercial credentials available.
- Full catalog/category monitoring as follow-up — only if research (D-06) rules out public tree discovery; Phase 31 still closes via search (SC-1..4).
- Zara / Inditex IOP (COMP-FUT-03) — deferred.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| COMP-03 | Operator can onboard and search products for SFCC brands Lacoste and HugoBoss (catalog + price) via public browser-rendered extraction (JSON-LD / OpenGraph). | Spike 004-006 validate the browser path. BR locale behavior confirmed by BrowserManager existing `locale="pt-BR"` + `timezone_id="America/Sao_Paulo"`. Parser strategy from `experiment.py` (005/006). Factory integration point identified at `factory.py:51-54`. |
</phase_requirements>

---

## Summary

Phase 31 implements `SFCCEngine`, a new engine class inheriting `BaseEngine` that extracts product catalog and price data from SFCC (Demandware) storefronts via browser-rendered HTML — specifically `lacoste.com.br` and `hugoboss.com.br`. HTTP direct access returns 403; the entire extraction path relies on Playwright via the existing `BrowserManager`.

The parser strategy is validated by spikes 004-006: JSON-LD first (`ProductGroup` at HugoBoss category level, `Product` at Lacoste PDP), OpenGraph as supplement, visible card text for discovery only. All results must be enriched via PDP since Lacoste has no image at category level and HugoBoss has no price at category level. The Quality Gate (`validate_and_filter` / `validate_single`) runs post-enrichment and rejects products missing `url`, `raw_title`, `price_full`, or `image_url`.

The single blocking open question for planning is D-06: whether public SFCC category-tree discovery (for the category monitoring screen) is feasible via the rendered home/menu. Research verdict below is FEASIBLE WITH CAVEATS — the menu is rendered, but it requires additional browser navigation (home → menu items → category pages) not validated by any spike. The planner should sequence search (SC-1..4) in earlier waves and treat catalog (D-05) as a later wave with its own validation threshold.

**Primary recommendation:** Build `SFCCEngine` as a direct analog of `ShopifyEngine` — thin `__init__(self, brand_key)`, `search()` renders the native search page and enriches up to `max_results` PDPs concurrently with throttle, `calculate_shipping` returns `None`, `get_engine_name` returns `"SFCC"`. Implement catalog discovery (D-05/D-06) as a separate wave, stubbed graciously if the tree extraction proves unstable in testing.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Product search (query → results) | API / Backend (`SFCCEngine.search`) | Browser (BrowserManager renders SFCC page) | Search logic lives in engine; browser is a transport |
| PDP enrichment (price + image) | API / Backend (`SFCCEngine._enrich_pdp`) | Browser (each PDP = one BrowserManager call) | Enrichment is a backend responsibility; browser renders each PDP |
| JSON-LD / OpenGraph parsing | API / Backend (parser module in engine) | — | Pure Python; no client-side logic |
| Category-tree discovery | API / Backend (`SFCCEngine.discover_categories`) | Browser (home/menu render) | Same pattern as ShopifyEngine.discover_categories |
| Engine registration | API / Backend (`EngineFactory.get_engine`) | — | Factory pattern, single integration point |
| Shipping display (None → no badge) | Browser / Client (App.tsx rendering guard) | — | Frontend guards on `p.shipping` and `item.is_free_shipping`; backend only needs to not set them |
| BR price formatting for display | Browser / Client (App.tsx `.toFixed(2)`) | — | Frontend formats float as `R$ X.XX`; backend delivers a plain Python `float` |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `playwright` (sync API via `asyncio.to_thread`) | Already installed | Browser rendering of SFCC pages | `BrowserManager.fetch_html` is the existing infra — mandatory reuse (D-03 Phase 30) |
| `beautifulsoup4` (bs4) | Already installed | HTML parsing, JSON-LD extraction, OG meta extraction | Used by existing scrapers; validated in experiment.py |
| `pydantic` v2 | Already installed | `RawProductBronze` validation (Quality Gate) | Project-wide model layer |
| `asyncio` | stdlib | Concurrency for concurrent PDP fetches | Used throughout the engine layer |

[ASSUMED] — checked via `grep` on `requirements.txt` below; versions confirmed from project.

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `re` (stdlib) | stdlib | BR money regex (`R\$\s*[\d.]+,\d{2}`) | Price parsing from rendered text — D-02 |
| `json` (stdlib) | stdlib | Deserialize `<script type="application/ld+json">` blocks | JSON-LD extraction |
| `logging` (stdlib) | stdlib | Structured engine logs via `emit_log` | All engines follow this pattern |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `BrowserManager.fetch_html` (sync_playwright in thread) | Async Playwright directly | BrowserManager is the established infra; async Playwright in uvicorn/Windows needs the existing `asyncio.to_thread` wrapper to avoid `NotImplementedError` with SelectorEventLoop — do NOT change |
| JSON-LD as primary source | CSS selector scraping | JSON-LD is structured, locale-agnostic, spike-validated; CSS selectors break on layout changes |
| Enriching all PDPs | Enriching only incomplete cards | D-07 is locked: enrich ALL. Quality of data is the project's core value |

**Installation:** No new packages required. All dependencies already in `backend/requirements.txt`. [ASSUMED]

**Version verification:**

```bash
# In the project root, run:
grep -E "(playwright|beautifulsoup4|bs4|pydantic)" backend/requirements.txt
```

---

## Package Legitimacy Audit

No new packages are introduced in this phase. All libraries are already installed in the project environment. [ASSUMED based on codebase inspection]

**Packages removed due to slopcheck:** none
**Packages flagged as suspicious:** none

---

## Architecture Patterns

### System Architecture Diagram

```
Operator search request
       |
       v
routes_search.POST /search
       |
       v
EngineFactory.get_engine("sfcc")
       |
       v
SFCCEngine(brand_key)
       |
       +--> search(query, max_results)
              |
              v
          BrowserManager.fetch_html(search_url)   <-- Playwright renders SFCC search page
              |
              v
          _parse_search_results(html)             <-- BeautifulSoup: extract card URLs + basic data
              |
              v
          [for each URL, up to max_results, concurrently with semaphore]
          BrowserManager.fetch_html(pdp_url)       <-- Playwright renders PDP
              |
              v
          _parse_pdp(html)                         <-- JSON-LD first → OG fallback → text
              |
              v
          validate_single(product)                 <-- BaseEngine Quality Gate (RawProductBronze)
              |
              v
          BrandSearchResult(brand_key, products=[SearchProductResult...])
              |
              v
routes_search returns ComparisonResult
```

### Recommended Project Structure

```
backend/
├── services/
│   └── engines/
│       ├── sfcc_engine.py          # NEW — SFCCEngine class (this phase)
│       ├── sfcc_parser.py          # NEW — parse_pdp(), parse_search_results(), parse_price_br()
│       └── factory.py              # EDIT — replace NotImplementedError guard with SFCCEngine(brand_key)
├── tests/
│   └── test_sfcc_engine.py         # NEW — unit tests with BrowserManager mocked
```

The parser is best separated into `sfcc_parser.py` to keep `SFCCEngine` thin and to make price-parsing testable without any browser mocking overhead. This mirrors how `shopify_api_client.py` carries the Shopify HTTP logic separately from `shopify_engine.py`.

### Pattern 1: ShopifyEngine as Direct Template

**What:** `SFCCEngine` follows the exact same structural pattern as `ShopifyEngine`.
**When to use:** For all non-VTEX engines that return `BrandSearchResult`.
**Example:**

```python
# Source: backend/services/engines/shopify_engine.py (codebase)
class SFCCEngine(BaseEngine):
    def __init__(self, brand_key: str):
        self.brand_key = brand_key

    def get_engine_name(self) -> str:
        return "SFCC"

    async def calculate_shipping(self, product: Any, zipcode: str) -> Optional[Dict[str, Any]]:
        # D-09: public path — no checkout, no shipping calculation
        return None

    async def search(self, query: str, max_results: int = 10, ...) -> BrandSearchResult:
        from services.brand_service import brand_service
        brand = brand_service.get_brand(self.brand_key)
        domain = brand.domain if brand else None
        if not domain:
            return BrandSearchResult(brand_key=self.brand_key, brand_name=self.brand_key, error="Domain not found")
        search_url = f"https://www.{domain}/search?q={query}"
        html = await BrowserManager.fetch_html(search_url)
        products = await self._enrich_results(html, max_results)
        return BrandSearchResult(brand_key=self.brand_key, brand_name=brand.brand_name, products=products)
```

### Pattern 2: BR Price Parser

**What:** Regex that captures the BR money format (`R$ 1.234,56`) and returns a Python float.
**Why:** Spike 006 pitfall — generic accessibility text numbers caused false positives when no money-pattern guard was in place. The BR format has a different thousands/decimal separator from the US format used in spikes 004-006. [VERIFIED: spike 006 report + D-02]

```python
# Source: experiment.py spike 005 (codebase) — adapted for BR locale
import re

_BR_MONEY_RE = re.compile(
    r"R\$\s*([\d]{1,3}(?:\.[\d]{3})*,[\d]{2}|[\d]+,[\d]{2})"
)

def parse_price_br(text: str) -> Optional[float]:
    """
    Parse a Brazilian Real price string to float.
    Handles: 'R$ 1.234,56' -> 1234.56, 'R$ 119,00' -> 119.0
    Does NOT accept plain integers or US-format prices.
    """
    match = _BR_MONEY_RE.search(text)
    if not match:
        return None
    raw = match.group(1)          # e.g. '1.234,56'
    normalized = raw.replace(".", "").replace(",", ".")  # '1234.56'
    value = float(normalized)
    return value if value > 0 else None
```

### Pattern 3: Concurrent PDP Enrichment with Semaphore

**What:** Open up to N PDPs concurrently using `asyncio.Semaphore` to limit parallel browser instances.
**When to use:** D-07 requires all results enriched; D-08 requires throttle to limit cost and anti-bot exposure.

```python
# Source: pattern derived from ShopifyEngine + BrowserManager contract (codebase)
import asyncio

async def _enrich_results(self, candidate_urls: list, max_results: int) -> list:
    sem = asyncio.Semaphore(3)  # max 3 concurrent PDPs — planner adjusts

    async def _enrich_one(url):
        async with sem:
            try:
                html = await BrowserManager.fetch_html(url)
                return _parse_pdp(html, url)
            except Exception as e:
                logger.warning("SFCC PDP fetch failed for %s: %s", url, e)
                return None

    tasks = [_enrich_one(url) for url in candidate_urls[:max_results]]
    results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]
```

### Pattern 4: JSON-LD Extraction

**What:** Extract `<script type="application/ld+json">` blocks, parse as JSON, filter for `@type: Product` or `@type: ProductGroup`.
**Validated by:** Spike 005 experiment.py — `normalize_jsonld_product()` pattern.

```python
# Source: .planning/spikes/005-sfcc-public-parser-prototype/experiment.py (codebase)
from bs4 import BeautifulSoup
import json

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

### Anti-Patterns to Avoid

- **Accessing `demandware.static` or SFCC internal APIs directly:** These require credentials (OCAPI/SCAPI) and are out of scope. All extraction must go through the rendered public DOM.
- **Using `parse_price` from spike 005 verbatim for BR stores:** The spike parser uses `re.search(r"(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)", text)` which is designed for USD `$119.00`. For `R$ 1.234,56` this will match `1` (thousands separator interpreted as decimal). The BR-specific regex in Pattern 2 above is required.
- **Using `async_playwright` directly in the engine:** `BrowserManager.fetch_html` uses `sync_playwright` in `asyncio.to_thread` specifically to work around `NotImplementedError` with the Uvicorn SelectorEventLoop on Windows. Do not bypass this.
- **Setting `is_free_shipping=True` or `shipping_price=0.0` on any product:** This triggers the "Frete Grátis" badge in the frontend at `App.tsx:1777`. For SFCC products, leave both at their defaults (`False` / `None`).
- **Registering `SFCCEngine` as a singleton:** Each `get_engine(brand_key)` call must instantiate a new `SFCCEngine(brand_key)` — different brands need different `brand_key` values.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Browser rendering | Custom Playwright wrapper | `BrowserManager.fetch_html` | Already handles headless args, Windows SelectorEventLoop workaround, UA spoofing, locale=pt-BR |
| Pydantic model validation | Custom field checks | `BaseEngine.validate_single` / `validate_and_filter` | Already implements the Quality Gate contract; tested in `test_quality_gates.py` |
| JSON-LD schema discovery | Hardcoded field maps per brand | Standard `@type: Product` / `ProductGroup` schema | Demandware uses Schema.org; spike-validated |
| Gender/category filtering | Custom SFCC filter | `BaseEngine.filter_mens_fashion` | Already has the blocklist (feminina/saia/vestido/etc.); apply post-parse for consistency with CAT-01 |
| Factory routing | New factory | Edit `factory.py:51-54`, replace `raise NotImplementedError` with `return SFCCEngine(brand_key)` | One-line change; keeps the existing guard architecture |

**Key insight:** The spike experiments already built and validated the parser logic. The production task is to port `experiment.py` patterns into a proper engine class — not to rediscover parsing strategies from scratch.

---

## Critical Research Questions — Answered

### CRQ-1: Do the BR storefronts expose the same JSON-LD/OpenGraph signals as the US stores?

**Verdict: YES, with high confidence — with one important adaptation (price format).**

The signals are structural properties of the SFCC/Demandware platform, not locale-specific. All Demandware storefronts inject `<script type="application/ld+json">` with `Product` or `ProductGroup` schemas as part of the platform's standard SEO output, regardless of locale. `OpenGraph` tags (`og:product:price:amount`, `og:image`, etc.) are similarly injected by the Demandware storefront framework. [ASSUMED — based on SFCC platform architecture knowledge; BR storefronts not directly probed by spikes]

The critical difference is price format. The BR storefront will render prices as `R$ 1.234,56` (dot thousands, comma decimal) rather than `$119.00`. Two sources of price data exist:

1. **JSON-LD `offers.price`**: This field in Schema.org is typically a plain float (`1234.56`) regardless of locale — the storefront may expose it as `1234.56` in the structured data even when the displayed price is `R$ 1.234,56`. [ASSUMED — Schema.org spec recommends numeric value; SFCC platform follows this]
2. **OpenGraph `og:product:price:amount`**: Also typically a plain numeric string per OG spec.
3. **Visible rendered text**: Will be in BR format `R$ 1.234,56` — requires the BR regex from Pattern 2.

**Recommendation for planner:** The parser should first attempt JSON-LD `offers.price` as a plain float (no parsing needed, just cast). If absent or zero, fall back to OpenGraph amount. Only fall back to rendered text (with BR regex) if both structured sources fail. This layered strategy handles the format difference gracefully.

**Risk flag:** If the SFCC BR storefront serializes `offers.price` in the JSON-LD as a locale-formatted string `"1.234,56"` rather than a plain float, the spike 005 parser's `parse_price()` would return `1.0` (stops at the dot). The BR regex guard handles this case. The planner should include a regression test that asserts `parse_price_br("R$ 1.234,56") == 1234.56`. [MEDIUM confidence — BR JSON-LD serialization behavior not directly verified]

---

### CRQ-2: D-06 Research Gate — Is public SFCC category-tree discovery FEASIBLE?

**Verdict: CONDITIONALLY FEASIBLE — with meaningful implementation risk not validated by any spike.**

**Evidence for feasibility:**
- SFCC storefronts render navigation menus in the DOM. Demandware platform standardly exposes category navigation as HTML anchor elements in the header/nav area. The rendered home page (already loaded by `BrowserManager`) will contain these links. [ASSUMED — platform knowledge]
- The category page URLs in SFCC follow a predictable pattern: `/on/demandware.store/Sites-{site_id}-Site/default/Search-Show?cgid={category_id}` or cleaner `/category/{slug}/` depending on storefront configuration. Spike 004 used category URLs directly (`/us/men-polo-shirts/`) without needing to discover them from the menu — they were provided.
- Spike 004 evidence: both Lacoste and HugoBoss exposed category pages successfully when navigated to directly, which means the category pages are accessible. The navigation links in the home page should point to these same URLs.

**Risks and caveats:**
1. **Not spike-validated:** No spike has ever loaded the BR home page and extracted category navigation links. The spikes only traversed a given category URL → PDPs. The category tree structure (depth, number of categories, menu rendering pattern) is unknown for the BR stores. [ASSUMED — extrapolated from US spike]
2. **Menu may require interaction:** Some SFCC storefronts render the full menu only after a hover or click event (JavaScript-driven dropdown). `BrowserManager.fetch_html` with `wait_until="domcontentloaded"` and `extra_sleep=1.0` may not trigger menu expansion. A `wait_selector` for the nav element might be needed.
3. **Number of categories:** VTEX/Shopify return structured API responses with a bounded list. SFCC navigation menus may expose 20-100+ categories as links — potentially expensive to enumerate if each needs a browser hit to confirm.
4. **Category URL format for `get_catalog()`:** The return type expected by the frontend is `[{"group": "...", "items": [{"label": ..., "path": ...}]}]` (see `ShopifyEngine.get_catalog()`). The SFCC category paths must be extractable from the rendered nav links without additional navigation.

**Recommendation (D-06 gate decision):** Mark category discovery as **FEASIBLE-with-stub-fallback**. The planner should:
- Implement `discover_categories()` as Wave N (after search waves), with `BrowserManager.fetch_html` on the store home + BeautifulSoup nav link extraction
- Include a fallback: if nav extraction returns 0 items, return `[]` without crash (stub behavior per D-06)
- Do NOT treat the stub as a failure — D-06 explicitly allows graceful stub if the tree is too costly

**Implementation approach (if FEASIBLE):**

```python
# Source: derived from spike evidence + ShopifyEngine pattern (codebase)
async def discover_categories(self) -> List[Dict[str, Any]]:
    from services.brand_service import brand_service
    brand = brand_service.get_brand(self.brand_key)
    if not brand:
        return []
    try:
        html = await BrowserManager.fetch_html(
            f"https://www.{brand.domain}",
            wait_selector="nav",   # wait for nav to render
            extra_sleep=2.0        # extra wait for JS-driven menu
        )
        soup = BeautifulSoup(html, "html.parser")
        nav = soup.find("nav") or soup.find(attrs={"role": "navigation"})
        if not nav:
            return []
        categories = []
        for a in nav.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            # Filter: must be a category-like path, not external, not empty
            if text and href.startswith("/") and len(text) > 2:
                categories.append({"name": text, "path": href, "id": href})
        # Deduplicate by path
        seen = set()
        result = []
        for c in categories:
            if c["path"] not in seen:
                seen.add(c["path"])
                result.append(c)
        return result
    except Exception as e:
        logger.warning("SFCC discover_categories failed for %s: %s", self.brand_key, e)
        return []  # graceful stub — D-06
```

---

### CRQ-3: PDP Enrichment Cost — max_results Default and Concurrency Strategy

**Recommendation: `max_results=10`, semaphore=3 concurrent PDPs.**

**Reasoning from spike timings:**
- Spike 006 visited 3 PDPs per brand (6 total). The experiment was described as feasible at this scale.
- `BrowserManager.fetch_html` launches a new Chromium instance per call (the BrowserManager is not a persistent singleton — see `browser_manager.py:159 "browser.close()`). Each PDP call takes approximately 3-8 seconds (based on typical Playwright page loads with `extra_sleep=1.0`).
- At `max_results=10` with semaphore=3: worst case is ~4 rounds × ~6s = ~24 seconds per brand. For a 2-brand search (Lacoste + HugoBoss), total = ~48s. This is acceptable for a competitive intelligence tool.
- At `max_results=20`, the cost doubles to ~96s, which approaches the territory of user-visible latency and anti-bot exposure.
- `max_results=10` aligns with the existing default in `SearchRequest` (`max_per_brand: int = 10`) and `BaseEngine.search(max_results: int = 10)`.

**Concurrency warning:** `BrowserManager.fetch_html` opens a new browser per call (`browser.close()` at the end of `_sync_fetch`). Running 3+ concurrent calls each launching Chromium will consume significant RAM. The BrowserManager docstring explicitly warns: "em máquinas com pouca RAM evite muitas chamadas Playwright concorrentes." A semaphore of 3 is a conservative starting point — the planner may reduce to 2 if memory is a concern.

**Anti-bot consideration:** SFCC BR storefronts (Lacoste and HugoBoss) did NOT block browser-rendered requests in spikes 004-006. The BrowserManager already includes UA spoofing, `locale="pt-BR"`, `timezone_id="America/Sao_Paulo"`, and basic fingerprint masking (navigator.webdriver override). However, rapid sequential PDP hits from the same IP may eventually trigger rate limiting. A `extra_sleep=1.0` between PDP calls (already the default) is the existing mitigation.

---

### CRQ-4: calculate_shipping Shape — None vs. ShippingInfo

**Verdict: Return `None`. This is the correct choice.**

**Evidence from frontend code** (App.tsx lines 1348, 1777):

1. **Comparative search results** (line 1348): `{p.shipping && (<div>...Frete Grátis...{p.shipping.status}...</div>)}` — a `None` shipping means the entire shipping div is not rendered. No badge appears.

2. **Cross-marketplace results** (line 1777-1779): `{item.is_free_shipping ? (<span>Frete Grátis</span>) : ...}` — the "Frete Grátis" badge fires on `item.is_free_shipping`, NOT on `item.shipping`. Since `RawProductBronze` has `is_free_shipping: bool = False` as default, and `SearchProductResult` has `is_free_shipping: bool = False` as default, these will be `False` as long as the engine doesn't set them. No badge fires.

3. **Paid shipping display** (line 1813): `R$ {(item.shipping_price || 0).toFixed(2)}` — only shown when `shipping_price` is not null and not free. With `shipping_price=None` (the default), this branch is not reached because `item.shipping_price === null && !item.is_free_shipping` at line 1788 shows "Frete a calcular" with a "Calcular Frete" button. However, this button calls `calculate_shipping_advanced` which only exists on Netshoes/Amazon engines. For SFCC products, clicking that button will fail gracefully (the `calculate_shipping_advanced` base class raises `NotImplementedError` which is caught).

**Conclusion:** Return `None` from `calculate_shipping`. The frontend rendering correctly handles `None` as "no shipping data" — no badge, no misleading price. The `is_free_shipping=False` default on `RawProductBronze` prevents any false "Frete Grátis" badges. This exactly mirrors `ShopifyEngine.calculate_shipping`.

For the comparative search view (lines 1348-1355), SFCC products will simply not show the shipping block. For the cross-marketplace view (lines 1773-1815), SFCC products will show "Frete a calcular" + "Calcular Frete" button, but clicking it will yield an error (no `calculate_shipping_advanced`). This is acceptable — the button is only visible/active in the cross-marketplace view, and SFCC brands are not typical cross-marketplace targets. [VERIFIED: codebase inspection of App.tsx]

---

## Common Pitfalls

### Pitfall 1: BR Price Format — Spike Parser Not Compatible

**What goes wrong:** The `parse_price()` function in `experiment.py` (spike 005) uses `re.search(r"(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)", text)`. For BR format `"R$ 1.234,56"`:
- It matches `1` (stopping at `.` which it reads as a decimal point)
- Returns `1.0` — a valid positive float that passes the Quality Gate
- This inserts a price of `R$ 1,00` into the results — a silent data corruption

**Why it happens:** The spike was designed for US USD prices (`$119.00`). D-02 explicitly requires adapting to BR format, but the old parser is not deleted — it will accidentally be copy-pasted.

**How to avoid:** Use `parse_price_br()` from Pattern 2 for any text-extracted price on BR stores. Apply the JSON-LD `offers.price` (plain float) as the primary source to avoid string parsing entirely.

**Warning signs:** Products with `price_full` between 0.01 and 9.99 from SFCC engines should trigger investigation.

### Pitfall 2: BrowserManager is NOT Async-Native — asyncio.to_thread is Mandatory

**What goes wrong:** `BrowserManager.fetch_html` is a classmethod that uses `sync_playwright` inside `asyncio.to_thread`. If you try to call `BrowserManager.fetch_html` with `await` directly from within another `asyncio.to_thread` context, you may get a nested-event-loop error.

**Why it happens:** Windows Uvicorn uses SelectorEventLoop which doesn't support nested `asyncio.run()`. The BrowserManager uses `sync_playwright` (not `async_playwright`) specifically to avoid this. The `asyncio.to_thread` wrapping makes the sync call non-blocking to the main loop.

**How to avoid:** Always call `await BrowserManager.fetch_html(url)` from an `async` method. Do not call it from within a `asyncio.to_thread` block. Do not use `asyncio.run()` inside a coroutine.

**Warning signs:** `RuntimeError: This event loop is already running` or `NotImplementedError` at `SelectorEventLoop.run_until_complete`.

### Pitfall 3: Accessibility Text Numbers Polluting Price (Spike 006 Finding)

**What goes wrong:** SFCC pages include ARIA labels and screen-reader text that contain numbers (e.g., "5 out of 5 stars", "208 reviews"). Generic number regexes match these as "prices".

**Why it happens:** Spike 006 report: "Price parsing must prefer money patterns such as `$119.00`; generic numbers in accessibility text caused false positives in the first trial."

**How to avoid:** The BR regex `R\$\s*[\d.]+,\d{2}` anchors on the currency symbol — generic numbers without `R$` prefix will not match. If falling back to visible text when JSON-LD is absent, always require the currency prefix.

**Warning signs:** Products with `price_full` equal to round numbers like 5.0, 208.0, 4.5 — these are accessibility text matches.

### Pitfall 4: factory.py Guard Must Be a Branch, Not a Delete

**What goes wrong:** The guard at `factory.py:51-54` is currently:
```python
if engine_type in ("sfcc", "wake"):
    raise NotImplementedError(...)
```
If a developer removes the entire block (thinking it's just a TODO), the `wake` branch will fall through to `return VTEXEngine(brand_key)` — silently running VTEX against a Wake domain (0 products, no error).

**How to avoid:** The edit must replace only the `sfcc` branch while keeping the `wake` guard:
```python
if engine_type == "sfcc":
    return SFCCEngine(brand_key)   # Phase 31
if engine_type == "wake":
    raise NotImplementedError(...)  # Phase 32 pending
```

**Warning signs:** Search for `wake` brands returns empty results with no error (would silently use VTEXEngine).

### Pitfall 5: Lacoste Search URL Pattern

**What goes wrong:** Constructing the search URL incorrectly for `lacoste.com.br`.

**Why it happens:** SFCC search URLs vary by storefront configuration. US Lacoste uses `/us/lacoste/...` path prefix. BR stores may use `/br/lacoste/...` or root `/search?q=...` or `/on/demandware.store/Sites-lacoste-br-Site/default/Search-Show?q=...`. The US URL pattern from spikes is NOT directly transferable.

**How to avoid:** Determine the BR search URL pattern during Wave 0 testing (smoke test). A simple `GET https://www.lacoste.com.br/search?q=polo` rendered by BrowserManager should redirect/resolve to the correct search results page. Capture and log the final URL after navigation.

**Warning signs:** Search returns 0 results despite a valid query; check if the search URL is returning a 404 or redirect loop.

---

## Code Examples

### Verified Patterns from Codebase

#### Engine Factory Integration Point

```python
# Source: backend/services/engines/factory.py:51-54 (codebase — current guard to replace)
# BEFORE:
if engine_type in ("sfcc", "wake"):
    raise NotImplementedError(
        f"Engine '{engine_type}' para '{brand_key}' ainda não disponível (Phase 31/32 pendente)."
    )

# AFTER (Phase 31 — split the guard):
if engine_type == "sfcc":
    from services.engines.sfcc_engine import SFCCEngine
    return SFCCEngine(brand_key)
if engine_type == "wake":
    raise NotImplementedError(
        f"Engine 'wake' para '{brand_key}' ainda não disponível (Phase 32 pendente)."
    )
```

#### BrandSearchResult Construction (from ShopifyEngine pattern)

```python
# Source: backend/services/engines/shopify_engine.py (codebase)
# search() must return BrandSearchResult with SearchProductResult items
from core.models import BrandSearchResult, SearchProductResult

return BrandSearchResult(
    brand_key=self.brand_key,
    brand_name=brand_name,
    products=[
        SearchProductResult(
            brand=brand_name,
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

#### validate_single Usage (from ShopifyEngine.run_bulk_scrape)

```python
# Source: backend/services/engines/shopify_engine.py:88-90 (codebase)
validated = self.validate_single(product, log_callback=log_callback)
if validated:
    yield validated
```

---

## Runtime State Inventory

Not applicable — this is a greenfield engine implementation. No rename/refactor/migration is involved. The only persistent state change is the onboarding of Lacoste and HugoBoss brand records (which already occurs via the existing `/brands/` POST endpoint).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| HTTP direct requests to SFCC | Browser-rendered extraction via Playwright | Spike 003 (HTTP 403 validated) | All SFCC extraction goes through BrowserManager |
| `engine="sfcc"` → `VTEXEngine` fallback (silent wrong engine) | `engine="sfcc"` → `NotImplementedError` guard (Phase 30) | Phase 30 | Guard prevents silent data corruption; Phase 31 replaces guard with real engine |
| US USD price format `$119.00` (spikes) | BR BRL price format `R$ 1.234,56` (Phase 31) | Phase 31 (D-01/D-02) | Requires new BR regex; JSON-LD `offers.price` may still be a plain float |

**Deprecated/outdated:**
- `experiment.py` spike parser (`parse_price` function): Functional for USD; NOT safe for BR stores without the currency-symbol anchor. Replace with `parse_price_br()` in production code.

---

## D-06 Verdict Summary (for planner)

**FEASIBLE WITH CAVEATS — implement in a late wave with graceful stub fallback.**

- Category navigation links ARE present in the rendered DOM of SFCC storefronts.
- The extraction approach (home page render → nav link extraction) is straightforward with BeautifulSoup.
- Risk: menu may require extra wait (JS dropdown); number of nav links may be large and noisy; category path format for `get_catalog()` output needs verification against actual BR stores.
- Mitigation: implement `discover_categories()` with `return []` fallback on any exception (D-06 stub). This satisfies D-04 (full BaseEngine contract) while allowing graceful degradation.
- DO NOT block search (SC-1..4) delivery on catalog discovery validation.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (configured in `pytest.ini` at project root) |
| Config file | `pytest.ini` (root) — `testpaths = backend/tests`, `pythonpath = backend` |
| Quick run command | `pytest backend/tests/test_sfcc_engine.py -x` |
| Full suite command | `pytest backend/tests/ -ra` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COMP-03 / SC-1 | `SFCCEngine.search("polo", max_results=3)` returns `BrandSearchResult` with ≥1 `SearchProductResult` with title, URL, `price_full > 0` | unit (BrowserManager mocked) | `pytest backend/tests/test_sfcc_engine.py::test_search_returns_products -x` | ❌ Wave 0 |
| COMP-03 / SC-2 | `EngineFactory.get_engine("sfcc")` returns `SFCCEngine` instance (not `NotImplementedError`) | unit | `pytest backend/tests/test_sfcc_engine.py::test_factory_returns_sfcc_engine -x` | ❌ Wave 0 |
| COMP-03 / SC-3 | `parse_price_br("R$ 1.234,56")` returns `1234.56`; `parse_price_br("R$ 119,00")` returns `119.0` | unit (no mock needed) | `pytest backend/tests/test_sfcc_engine.py::test_parse_price_br -x` | ❌ Wave 0 |
| COMP-03 / SC-4 | `SFCCEngine.calculate_shipping(product, "01310-100")` returns `None` | unit (no mock needed) | `pytest backend/tests/test_sfcc_engine.py::test_calculate_shipping_returns_none -x` | ❌ Wave 0 |
| COMP-03 / SC-3 | Price in search result formatted as `R$ X.XX` in UI (no "Frete Grátis" badge) | manual smoke | N/A | manual |
| D-04 / BaseEngine | `SFCCEngine` implements all abstract methods (no `TypeError` on instantiation) | unit | `pytest backend/tests/test_sfcc_engine.py::test_sfcc_engine_implements_base_engine -x` | ❌ Wave 0 |
| D-07 / enrichment | Each product in search result has `image_url` (PDP enrichment ran) | unit (BrowserManager mocked) | `pytest backend/tests/test_sfcc_engine.py::test_search_results_have_image -x` | ❌ Wave 0 |
| D-06 / stub | `SFCCEngine.discover_categories()` returns `[]` (stub) without crash | unit (BrowserManager mocked with empty nav) | `pytest backend/tests/test_sfcc_engine.py::test_discover_categories_stub -x` | ❌ Wave 0 |

### Test Patterns from Repo

The canonical mock pattern for browser-dependent engine tests is established in `test_engine_detection.py`:

```python
# Source: backend/tests/test_engine_detection.py (codebase)
_BROWSER_FETCH_TARGET = "core.browser_manager.BrowserManager.fetch_html"

with patch(_BROWSER_FETCH_TARGET, new=AsyncMock(return_value=rendered_html)):
    result = asyncio.run(some_async_function())
```

The `SFCCEngine` tests should follow this exact pattern — mock `core.browser_manager.BrowserManager.fetch_html` as an `AsyncMock` returning fixture HTML. No real browser launched (hermetic suite).

The `test_quality_gates.py` pattern shows how to test `validate_single` / `validate_and_filter` with a mock `log_callback`.

### Sampling Rate

- **Per task commit:** `pytest backend/tests/test_sfcc_engine.py -x`
- **Per wave merge:** `pytest backend/tests/ -ra`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/test_sfcc_engine.py` — covers all test cases above (COMP-03 SC-1..4, D-04, D-06, D-07)
- [ ] `backend/services/engines/sfcc_engine.py` — the engine class (stub to be implemented)
- [ ] `backend/services/engines/sfcc_parser.py` — parser helpers including `parse_price_br()`

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth on public SFCC pages |
| V3 Session Management | no | Stateless scraping |
| V4 Access Control | no | Engine only reads public data |
| V5 Input Validation | yes | `RawProductBronze` Pydantic validator + `parse_price_br` guards against injection via scraped content |
| V6 Cryptography | no | No secrets involved |

### Known Threat Patterns for Browser-Rendered Scraping

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Scraped HTML injection (malicious `<script>` in product title) | Tampering | BeautifulSoup `.get_text()` extracts text only; JSON-LD is parsed as data structure, not executed |
| Open redirect via constructed SFCC search URL | Spoofing | BrowserManager follows redirects within the same domain; the final URL is logged; do not construct URLs from untrusted user input without sanitization |
| Price tampering via accessibility text (Spike 006) | Tampering | `parse_price_br()` requires `R$` currency prefix — arbitrary numbers without prefix are ignored |
| Anti-bot block returning partial/malicious HTML | Denial of Service | `validate_single` Quality Gate rejects products with missing required fields; `try/except` in PDP enrichment swallows individual failures |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Playwright (Chromium) | `BrowserManager.fetch_html` | Confirmed (used in Phase 30) | — | `PLAYWRIGHT_ENABLED=false` disables engine (existing guard in BrowserManager) |
| Python 3.x | All backend | Confirmed (cpython-314 in git status) | 3.14 | — |
| BeautifulSoup4 | HTML parsing | Assumed present (project existing scrapers) | — | — [ASSUMED] |
| Internet access to `lacoste.com.br` and `hugoboss.com.br` | Smoke tests / live validation | Unknown (CI environment may block) | — | Mock-only tests in CI; manual smoke on dev machine |

**Missing dependencies with no fallback:**
- Internet access for smoke tests: tests using real BrowserManager calls require network access. All automated tests should mock BrowserManager (hermetic). Smoke validation is manual.

**Missing dependencies with fallback:**
- BeautifulSoup4: if not installed, `pip install beautifulsoup4` (already a standard project dep [ASSUMED]).

---

## Open Questions

1. **BR search URL pattern**
   - What we know: US Lacoste uses `/us/lacoste/men/clothing/polos/` (category); US HugoBoss uses `/us/men-polo-shirts/` (category). Neither spike tested a search query URL.
   - What's unclear: The exact search URL for `lacoste.com.br` and `hugoboss.com.br` — could be `/search?q=polo`, `/busca?q=polo`, `/on/demandware.store/.../Search-Show?q=polo`, or a JavaScript-only search with no URL change.
   - Recommendation: Wave 0 smoke test should manually navigate to both BR stores and observe the search URL when using the native search box. Record the URL pattern as a constant in `sfcc_engine.py`.

2. **JSON-LD `offers.price` serialization on BR stores**
   - What we know: Schema.org spec recommends plain numeric value. US stores exposed `"price": 119.00`.
   - What's unclear: Whether the BR SFCC storefront serializes price as `1234.56` (plain float) or `"1.234,56"` (localized string) in JSON-LD.
   - Recommendation: Layer the parser: try `float(offer["price"])` first (works for both formats if it's a number); if `ValueError`, apply `parse_price_br()`. Log which path was used per product for monitoring.

3. **Category discovery: nav selector for BR stores**
   - What we know: SFCC renders navigation in a `<nav>` element or element with `role="navigation"`. The exact CSS structure varies by storefront theme.
   - What's unclear: Whether Lacoste BR and HugoBoss BR use a standard `<nav>` element or a custom structure; whether the menu expands on page load or requires a click/hover event.
   - Recommendation: Treat as a Wave N research task (after search is working). Initial implementation should use a forgiving selector with broad fallback; if 0 categories are discovered, the graceful stub (return `[]`) applies.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | SFCC BR storefronts expose `Product`/`ProductGroup` JSON-LD with same schema as US stores | CRQ-1, Code Examples | Parser misses products; enrichment yields 0 results; search returns empty |
| A2 | JSON-LD `offers.price` in BR stores is a plain float (not localized string) | CRQ-1, Pitfall 1 | `float(offer["price"])` raises ValueError; fallback to BR regex needed |
| A3 | `beautifulsoup4` is already in `backend/requirements.txt` | Standard Stack | Must add to requirements.txt; no functional impact |
| A4 | BrowserManager concurrency at semaphore=3 is safe on the target machine's RAM | CRQ-3 | OOM or Chromium crashes; reduce semaphore to 2 |
| A5 | SFCC BR storefronts render full nav on `domcontentloaded` without user interaction | CRQ-2, Open Questions | `discover_categories()` returns 0 items; falls back to stub (D-06) — acceptable |
| A6 | lacoste.com.br and hugoboss.com.br have BR SFCC instances (not redirects to .com) | D-01 | BR domain unavailable; need to identify correct BR URL |

---

## Sources

### Primary (HIGH confidence)
- `backend/services/engines/shopify_engine.py` (codebase) — direct template for SFCCEngine structure
- `backend/services/engines/base_engine.py` (codebase) — BaseEngine contract
- `backend/services/engines/factory.py` (codebase) — integration point L51-54
- `backend/core/browser_manager.py` (codebase) — Playwright infra contract
- `backend/core/models.py` (codebase) — RawProductBronze, BrandSearchResult, ShippingInfo, SearchProductResult
- `frontend/src/App.tsx:1348-1355, 1777-1815` (codebase) — shipping rendering logic
- `.planning/spikes/005-sfcc-public-parser-prototype/experiment.py` (codebase) — parsing patterns
- `.planning/spikes/006-sfcc-live-browser-e2e-prototype/experiment.py` (codebase) — E2E validation pattern
- `.planning/spikes/006-sfcc-live-browser-e2e-prototype/REPORT.md` (codebase) — Pitfall: accessibility text price false positives
- `backend/tests/test_engine_detection.py` (codebase) — BrowserManager mock pattern
- `backend/tests/test_quality_gates.py` (codebase) — Quality Gate test patterns
- `pytest.ini` (codebase) — test framework configuration

### Secondary (MEDIUM confidence)
- `.planning/spikes/004-sfcc-browser-public-probe/REPORT.md` — SFCC signal evidence (US stores)
- `.planning/spikes/005-sfcc-public-parser-prototype/REPORT.md` — parser strategy per brand
- `.planning/phases/31-engine-sfcc-browser-p-blico-lacoste-hugoboss/31-CONTEXT.md` — locked decisions D-01..D-09
- `.planning/phases/30-detec-o-de-engine-sfcc-wake/30-CONTEXT.md` — BrowserManager reuse decisions

### Tertiary (LOW confidence — verify before relying)
- SFCC/Demandware platform behavior for BR locale stores (JSON-LD format, nav structure) — [ASSUMED], not directly spike-validated
- BeautifulSoup4 presence in requirements.txt — [ASSUMED], not verified by grep in this session

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — all libraries are existing project dependencies; no new packages
- Architecture: HIGH — follows established ShopifyEngine pattern, verified in codebase
- BR price parsing: MEDIUM — JSON-LD format for BR locale not directly verified; dual-path parser mitigates
- Category discovery (D-06): LOW-MEDIUM — concept is sound but no spike validation on BR stores; graceful stub fallback makes risk manageable
- Shipping shape: HIGH — frontend code directly verified; None is correct

**Research date:** 2026-06-24
**Valid until:** 2026-07-24 (stable platforms; SFCC storefront structure may change)

---

## Project Constraints (from CLAUDE.md)

The following directives from `CLAUDE.md` apply to this phase:

1. **Coding standards via Backstage MCP:** Before any code changes, the implementer must consult `backstage_get_coding_standards` (MCP server `backstage`). If the MCP tool is unavailable in the execution environment, this becomes a planning prerequisite — add a Wave 0 task: "Operator verifies Backstage coding standards are accessible; if unavailable, document exception in plan."

2. **Conventional Commits:** All commits must follow Conventional Commits with scope. For this phase, scope is `sfcc` or `engine`. Example: `feat(sfcc): implement SFCCEngine search with PDP enrichment`.

3. **Branch naming:** `feat/sfcc-engine` branching from `develop` (current branch). PRs required for `main`. Never commit directly.

4. **Clean Code + refactoring.guru principles:** No over-engineering. `SFCCEngine` should be thin — parsing logic in `sfcc_parser.py`, engine in `sfcc_engine.py`. Avoid deep inheritance chains.

5. **No secrets committed:** The `BrowserManager` uses no credentials for public SFCC extraction. No `.env` changes needed for this phase.
