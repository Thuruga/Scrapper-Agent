---
phase: 31-engine-sfcc-browser-p-blico-lacoste-hugoboss
type: code-review
status: complete
reviewed_files:
  - backend/services/engines/sfcc_engine.py
  - backend/services/engines/sfcc_parser.py
  - backend/services/engines/factory.py
  - backend/tests/test_sfcc_engine.py
---

# Code Review — Phase 31 (SFCC Engine)

Inline review (subagent quota exhausted). Findings derived from reading live
source files after all three waves merged to `develop`.

---

## Findings

### [HIGH] Double `www.` in constructed URLs

**Files:** `sfcc_engine.py:149`, `sfcc_engine.py:379`

`DynamicBrand.clean_domain` strips the scheme (`https://`) and trailing `/`
but does **not** strip the `www.` prefix. Brands stored as
`"www.lacoste.com.br"` (the typical registered value) produce:

- `search()` line 149: `SEARCH_URL_TEMPLATE.format(domain="www.lacoste.com.br", ...)`
  → `"https://www.www.lacoste.com.br/search?q=polo"` — 404 for every live search.
- `discover_categories()` line 379: `home_url = f"https://www.{domain}"`
  → `"https://www.www.lacoste.com.br"` — category discovery silently returns `[]`.

`parse_search_results` correctly uses `base_domain.lstrip('www.')` at line 479
for building absolute URLs, so that path is fine — the bug is upstream in the
URL used to *fetch* the search page.

**Fix:** Strip `www.` before constructing URLs:

```python
clean = domain.lstrip("www.").lstrip(".")  # "www.lacoste.com.br" → "lacoste.com.br"
search_url = SEARCH_URL_TEMPLATE.format(domain=clean, query=encoded_query)
home_url   = f"https://www.{clean}"
```

Or, safer: use `re.sub(r"^www\.", "", domain)` (matches the literal prefix, not
a character set).

---

### [MEDIUM] `run_bulk_scrape` skips `filter_mens_fashion`

**File:** `sfcc_engine.py:311-319`

`_enrich_results` applies gender filtering at line 220:
`filtered = self.filter_mens_fashion(parsed)`.

`run_bulk_scrape` feeds results directly to `validate_single` (line 317) with no
gender filter. Feminine items pass through bulk scrape but are excluded from
search — inconsistent quality across the two access paths.

**Fix:** Add before the `for raw in await asyncio.gather(...)` loop:

```python
parsed_results = [r for r in await asyncio.gather(...) if r is not None]
filtered = self.filter_mens_fashion(parsed_results)
for raw in filtered:
    ...
```

---

### [MEDIUM] Empty `domain` causes malformed PDP URLs in `run_bulk_scrape`

**File:** `sfcc_engine.py:284-297`

Brand lookup happens **after** `fetch_html(category_url)` (lines 285-295).
If the brand is not registered, `domain = ""`. Then `parse_search_results(html, "")`
(line 297) invokes `_looks_like_pdp_url(href, "")` and — for relative hrefs — builds:

```python
absolute = f"https://www.{base_domain.lstrip('www.')}{href}"
# → "https://www./polo/p"  (malformed)
```

Callers of `run_bulk_scrape` pass a full `category_url`; extracting the host from
that URL would be more robust than relying on a post-fetch brand lookup.

**Fix:** Extract domain from `category_url` before the fetch, with brand as override:

```python
from urllib.parse import urlparse
_parsed = urlparse(category_url)
domain = re.sub(r"^www\.", "", _parsed.netloc) if _parsed.netloc else ""
```

---

### [LOW] `lstrip("www.")` strips characters, not the prefix

**File:** `sfcc_parser.py:424-425`, `sfcc_parser.py:479`

```python
link_host  = parsed.netloc.lstrip("www.")
canon_host = base_domain.lstrip("www.")
```

`str.lstrip(chars)` strips any leading character that appears in the argument
*set*, not the literal string `"www."`. For example:
- `"web.lacoste.com.br".lstrip("www.")` → `"eb.lacoste.com.br"` (false negative: host is rejected)
- `"ww.lacoste.com.br".lstrip("www.")` → `"lacoste.com.br"` (false positive: treated same as www.)

**Fix:** Use `re.sub(r"^www\.", "", host)` or Python 3.9+ `host.removeprefix("www.")`.

---

### [LOW] Dead code: defensive `isinstance(brand, dict)` branches

**File:** `sfcc_engine.py:130-135`, `sfcc_engine.py:288-295`, `sfcc_engine.py:364-368`

`brand_service.get_brand()` is typed `Optional[DynamicBrand]` (Pydantic model);
it never returns a dict. The `isinstance(brand, dict)` branches in all three
brand-resolution blocks are unreachable dead code that adds noise to three methods.

**Fix:** Replace the three-line defensive patterns with single-attribute lookups:

```python
domain     = getattr(brand, "domain", "") or ""
brand_name = getattr(brand, "brand_name", self.brand_key) or self.brand_key
```

---

### [LOW] Triple HTML parsing in `parse_pdp`

**File:** `sfcc_parser.py:251-253`

```python
soup      = BeautifulSoup(html, "html.parser")   # parse #1
og_meta   = extract_og_meta(html)                # parse #2 inside
products  = extract_jsonld_products(html)         # parse #3 inside
```

For PDP pages (often 200-500 KB of HTML), three sequential parse passes are
wasteful. `extract_og_meta` and `extract_jsonld_products` each accept a raw
`html: str` and construct their own `BeautifulSoup` instance internally.

**Fix:** Accept an optional `soup` parameter in both helpers, or pass the already-
parsed `soup` from `parse_pdp` and let them use it.

---

### [LOW] Duplicate `_enrich_one` inner function

**File:** `sfcc_engine.py:204-212` and `sfcc_engine.py:302-309`

`_enrich_results` and `run_bulk_scrape` each define a nearly identical
`async def _enrich_one(url)` closure. Only the log prefix differs. The
duplication means any change to the PDP-fetch logic must be made twice.

**Fix:** Extract to a private `async def _fetch_pdp(self, url, sem)` method
that both callers use.

---

## Summary

| Severity | Count | Action |
|----------|-------|--------|
| HIGH     | 1     | Fix before any live run — will 404 all searches for registered brands |
| MEDIUM   | 2     | Fix before category monitoring goes live |
| LOW      | 4     | Tech debt; fix in follow-up or alongside next engine work |

The HIGH finding (double `www.`) is the only one that would silently break an
otherwise complete integration test. The test suite mocks `fetch_html` and
therefore never exercises the constructed URL — tests are green while live
traffic would fail.
