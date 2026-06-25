"""
Hermetic test suite for the SFCC engine (Phase 31).

Test classes:
  - TestSFCCParser       : Pure-Python parser tests — NO mocking, GREEN in Wave 0.
  - TestSFCCFactory      : EngineFactory wires SFCCEngine — RED until Wave 1 (sfcc_engine.py).
  - TestSFCCEngineSearch : SFCCEngine.search() with BrowserManager mocked — RED until Wave 1.
  - TestSFCCCategoryDiscovery : discover_categories() stub — RED until Wave 2.

The engine/factory/category tests are EXPECTED to fail (ImportError / AttributeError)
until sfcc_engine.py is implemented in Wave 1.  This is the intentional Nyquist RED
state: the contract is locked, the parser is green.

BrowserManager mock seam (matches test_engine_detection.py):
  _BROWSER_FETCH_TARGET = "core.browser_manager.BrowserManager.fetch_html"
"""

from __future__ import annotations

import asyncio
import textwrap
from unittest.mock import AsyncMock, patch

import pytest

# ---------------------------------------------------------------------------
# Mock seam — must match test_engine_detection.py pattern (31-PATTERNS.md)
# ---------------------------------------------------------------------------
_BROWSER_FETCH_TARGET = "core.browser_manager.BrowserManager.fetch_html"

# ---------------------------------------------------------------------------
# Inline HTML fixtures
# ---------------------------------------------------------------------------

# PDP fixture: Product JSON-LD + OpenGraph tags, BR price
_PDP_HTML = textwrap.dedent("""\
    <!DOCTYPE html>
    <html>
    <head>
      <meta property="og:title" content="Polo Petit Piqué Lacoste" />
      <meta property="og:image" content="https://www.lacoste.com.br/img/polo.jpg" />
      <meta property="og:url" content="https://www.lacoste.com.br/polo-petit-pique/L12120/p" />
      <meta property="og:description" content="Polo masculina de algodão." />
      <script type="application/ld+json">
      {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": "Polo Petit Piqué",
        "brand": {"@type": "Brand", "name": "Lacoste"},
        "description": "Polo masculina de algodão.",
        "image": ["https://www.lacoste.com.br/img/polo.jpg"],
        "offers": {
          "@type": "Offer",
          "price": 799.0,
          "priceCurrency": "BRL",
          "availability": "https://schema.org/InStock"
        }
      }
      </script>
    </head>
    <body>
      <span class="price">R$ 799,00</span>
    </body>
    </html>
""")

# Search page fixture: one product anchor pointing to a PDP URL
_SEARCH_HTML = textwrap.dedent("""\
    <!DOCTYPE html>
    <html>
    <head><title>Resultados para: polo</title></head>
    <body>
      <div class="product-tile">
        <a href="/polo-petit-pique/L12120/p">
          <span class="product-name">Polo Petit Piqué</span>
        </a>
      </div>
    </body>
    </html>
""")


# ---------------------------------------------------------------------------
# TestSFCCParser — pure Python, no mocking; GREEN in Wave 0
# ---------------------------------------------------------------------------

class TestSFCCParser:
    """Unit tests for sfcc_parser module.  No browser mock needed — pure Python."""

    # -- parse_price_br -------------------------------------------------------

    def test_parse_price_br_standard(self):
        """parse_price_br('R$ 1.234,56') == 1234.56  (D-02 / SC-3)."""
        from services.engines.sfcc_parser import parse_price_br
        assert parse_price_br("R$ 1.234,56") == 1234.56

    def test_parse_price_br_simple(self):
        """parse_price_br('R$ 119,00') == 119.0  (D-02 / SC-3)."""
        from services.engines.sfcc_parser import parse_price_br
        assert parse_price_br("R$ 119,00") == 119.0

    def test_parse_price_br_rejects_usd(self):
        """parse_price_br('$119.00') is None  (Pitfall 1 — USD format rejected)."""
        from services.engines.sfcc_parser import parse_price_br
        assert parse_price_br("$119.00") is None

    def test_parse_price_br_rejects_accessibility_text(self):
        """parse_price_br('5 out of 5 stars') is None  (Pitfall 3 — accessibility numbers rejected)."""
        from services.engines.sfcc_parser import parse_price_br
        assert parse_price_br("5 out of 5 stars") is None

    def test_parse_price_br_rejects_review_count(self):
        """parse_price_br('208 reviews') is None  (Pitfall 3)."""
        from services.engines.sfcc_parser import parse_price_br
        assert parse_price_br("208 reviews") is None

    def test_parse_price_br_numeric_passthrough_float(self):
        """parse_price_br(1234.56) == 1234.56  (JSON-LD plain float passthrough)."""
        from services.engines.sfcc_parser import parse_price_br
        assert parse_price_br(1234.56) == 1234.56

    def test_parse_price_br_numeric_passthrough_int(self):
        """parse_price_br(119) == 119.0  (JSON-LD plain int passthrough)."""
        from services.engines.sfcc_parser import parse_price_br
        assert parse_price_br(119) == 119.0

    def test_parse_price_br_rejects_zero(self):
        """parse_price_br(0) is None  (zero is not a valid price)."""
        from services.engines.sfcc_parser import parse_price_br
        assert parse_price_br(0) is None

    # -- parse_pdp smoke ------------------------------------------------------

    def test_parse_pdp_extracts_title(self):
        """parse_pdp extracts title from JSON-LD name."""
        from services.engines.sfcc_parser import parse_pdp
        result = parse_pdp(_PDP_HTML, "https://www.lacoste.com.br/polo-petit-pique/L12120/p")
        assert result is not None
        assert result["raw_title"] == "Polo Petit Piqué"

    def test_parse_pdp_extracts_url(self):
        """parse_pdp sets url to source_url."""
        from services.engines.sfcc_parser import parse_pdp
        url = "https://www.lacoste.com.br/polo-petit-pique/L12120/p"
        result = parse_pdp(_PDP_HTML, url)
        assert result is not None
        assert result["url"] == url

    def test_parse_pdp_extracts_price(self):
        """parse_pdp extracts price_full from JSON-LD offers.price."""
        from services.engines.sfcc_parser import parse_pdp
        result = parse_pdp(_PDP_HTML, "https://www.lacoste.com.br/polo-petit-pique/L12120/p")
        assert result is not None
        assert result["price_full"] == 799.0

    def test_parse_pdp_extracts_image(self):
        """parse_pdp extracts image_url from JSON-LD image list."""
        from services.engines.sfcc_parser import parse_pdp
        result = parse_pdp(_PDP_HTML, "https://www.lacoste.com.br/polo-petit-pique/L12120/p")
        assert result is not None
        assert result["image_url"] == "https://www.lacoste.com.br/img/polo.jpg"

    def test_parse_pdp_returns_none_when_no_title(self):
        """parse_pdp returns None when both JSON-LD and OG title are absent."""
        from services.engines.sfcc_parser import parse_pdp
        empty_html = "<html><body><p>Nothing here</p></body></html>"
        result = parse_pdp(empty_html, "https://www.lacoste.com.br/some/path")
        assert result is None

    def test_parse_pdp_extracts_availability(self):
        """parse_pdp maps InStock to stock_availability=True."""
        from services.engines.sfcc_parser import parse_pdp
        result = parse_pdp(_PDP_HTML, "https://www.lacoste.com.br/polo-petit-pique/L12120/p")
        assert result is not None
        assert result["stock_availability"] is True

    # -- parse_search_results -------------------------------------------------

    def test_parse_search_results_returns_pdp_urls(self):
        """parse_search_results extracts absolute PDP URLs from the search fixture."""
        from services.engines.sfcc_parser import parse_search_results
        urls = parse_search_results(_SEARCH_HTML, "lacoste.com.br")
        assert len(urls) >= 1
        assert any("polo-petit-pique" in u for u in urls)

    def test_parse_search_results_returns_absolute_urls(self):
        """parse_search_results returns absolute (not relative) URLs."""
        from services.engines.sfcc_parser import parse_search_results
        urls = parse_search_results(_SEARCH_HTML, "lacoste.com.br")
        for url in urls:
            assert url.startswith("http"), f"Expected absolute URL, got: {url}"

    def test_parse_search_results_deduplicates(self):
        """parse_search_results returns deduplicated URLs."""
        from services.engines.sfcc_parser import parse_search_results
        # Same href appearing twice should yield one result
        html = textwrap.dedent("""\
            <html><body>
              <a href="/polo/L12120/p">Product 1</a>
              <a href="/polo/L12120/p">Product 1 (duplicate)</a>
            </body></html>
        """)
        urls = parse_search_results(html, "lacoste.com.br")
        assert urls.count(urls[0]) == 1 if urls else True


# ---------------------------------------------------------------------------
# TestSFCCFactory — RED until Wave 1 (sfcc_engine.py + factory.py edit)
# ---------------------------------------------------------------------------

class TestSFCCFactory:
    """Tests that EngineFactory.get_engine('sfcc') returns an SFCCEngine.

    These tests are RED until sfcc_engine.py is implemented and factory.py
    is updated in Wave 1 (Plan 31-02).
    """

    def test_factory_returns_sfcc_engine(self):
        """SC-2: EngineFactory.get_engine for an sfcc brand returns SFCCEngine, not NotImplementedError."""
        from services.engines.factory import EngineFactory
        from services.engines.sfcc_engine import SFCCEngine
        from unittest.mock import MagicMock

        # Simulate a brand with engine="sfcc"
        mock_brand = MagicMock()
        mock_brand.engine = "sfcc"

        with patch(
            "services.engines.factory.brand_service.get_brand",
            return_value=mock_brand,
        ):
            engine = EngineFactory.get_engine("lacoste")
        assert isinstance(engine, SFCCEngine)

# test_factory_wake_still_raises removed in Phase 32 plan 02 — WakeEngine is now live.
# The test test_factory_returns_wake_engine in test_wake_engine.py (plan 32-03) replaces it.


# ---------------------------------------------------------------------------
# TestSFCCEngineSearch — RED until Wave 1
# ---------------------------------------------------------------------------

class TestSFCCEngineSearch:
    """Tests for SFCCEngine.search() with BrowserManager mocked.

    These tests are RED until sfcc_engine.py is implemented in Wave 1.
    """

    def test_search_returns_products(self):
        """SC-1: search('polo', max_results=3) returns BrandSearchResult with ≥1 product."""
        from services.engines.sfcc_engine import SFCCEngine
        from core.models import BrandSearchResult

        with patch(
            _BROWSER_FETCH_TARGET,
            new=AsyncMock(side_effect=[_SEARCH_HTML, _PDP_HTML]),
        ):
            engine = SFCCEngine("lacoste")
            result = asyncio.run(engine.search("polo", max_results=3))

        assert isinstance(result, BrandSearchResult)
        assert len(result.products) >= 1
        assert result.products[0].product_name
        assert result.products[0].url
        assert result.products[0].price_full > 0

    def test_search_results_have_image(self):
        """D-07: PDP enrichment ran — each product has image_url."""
        from services.engines.sfcc_engine import SFCCEngine

        with patch(
            _BROWSER_FETCH_TARGET,
            new=AsyncMock(side_effect=[_SEARCH_HTML, _PDP_HTML]),
        ):
            engine = SFCCEngine("lacoste")
            result = asyncio.run(engine.search("polo", max_results=3))

        for product in result.products:
            assert product.image_url, f"Product {product.url} missing image_url"

    def test_calculate_shipping_returns_none(self):
        """SC-4 / D-09: calculate_shipping returns None (no false Frete Grátis badge)."""
        from services.engines.sfcc_engine import SFCCEngine
        from core.models import SearchProductResult

        engine = SFCCEngine("lacoste")
        product = SearchProductResult(
            brand="Lacoste",
            product_name="Polo Petit Piqué",
            url="https://www.lacoste.com.br/polo/L12120/p",
            price_full=799.0,
            image_url="https://www.lacoste.com.br/img/polo.jpg",
        )
        result = asyncio.run(engine.calculate_shipping(product, "01310-100"))
        assert result is None

    def test_sfcc_engine_implements_base_engine(self):
        """D-04: SFCCEngine can be instantiated without TypeError (all abstract methods)."""
        from services.engines.sfcc_engine import SFCCEngine
        from services.engines.base_engine import BaseEngine

        engine = SFCCEngine("lacoste")
        assert isinstance(engine, BaseEngine)
        assert engine.get_engine_name() == "SFCC"


# ---------------------------------------------------------------------------
# HTML fixtures for category discovery tests
# ---------------------------------------------------------------------------

# Nav HTML fixture: two category anchors in a <nav> element
_NAV_HTML = textwrap.dedent("""\
    <!DOCTYPE html>
    <html>
    <head><title>Lacoste</title></head>
    <body>
      <nav>
        <a href="/masculino/polo">Polo Masculina</a>
        <a href="/masculino/camisetas">Camisetas</a>
        <a href="/login">Entrar</a>
        <a href="https://external.com/offers">Ofertas Externas</a>
        <a href="/polo">Polo Masculina</a>
      </nav>
      <main><p>Conteúdo da página</p></main>
    </body>
    </html>
""")

# Nav HTML via role=navigation attribute (alternative pattern)
_ROLE_NAV_HTML = textwrap.dedent("""\
    <!DOCTYPE html>
    <html>
    <head><title>HugoBoss</title></head>
    <body>
      <div role="navigation">
        <a href="/colecoes/ternos">Ternos</a>
        <a href="/colecoes/camisas">Camisas</a>
        <a href="/account">Minha Conta</a>
      </div>
    </body>
    </html>
""")

# ---------------------------------------------------------------------------
# TestSFCCCategoryDiscovery — RED until Wave 2
# ---------------------------------------------------------------------------

class TestSFCCCategoryDiscovery:
    """Tests for extract_nav_categories (sfcc_parser) and SFCCEngine.discover_categories.

    Tasks 1 and 2 of Plan 03 (Wave 2).
    """

    # -- extract_nav_categories (Task 1) ----------------------------------------

    def test_extract_nav_categories_no_nav_returns_empty(self):
        """extract_nav_categories returns [] when no <nav> or role=navigation is present."""
        from services.engines.sfcc_parser import extract_nav_categories
        html = "<html><body><div>no nav here</div></body></html>"
        result = extract_nav_categories(html, "lacoste.com.br")
        assert result == []

    def test_extract_nav_categories_returns_dicts(self):
        """extract_nav_categories returns list of {name, path, id} dicts for nav anchors."""
        from services.engines.sfcc_parser import extract_nav_categories
        result = extract_nav_categories(_NAV_HTML, "lacoste.com.br")
        assert isinstance(result, list)
        assert len(result) >= 1
        for item in result:
            assert "name" in item
            assert "path" in item
            assert "id" in item

    def test_extract_nav_categories_deduplicates_by_path(self):
        """extract_nav_categories deduplicates anchors with the same href by path."""
        from services.engines.sfcc_parser import extract_nav_categories
        # _NAV_HTML contains /polo twice (as /masculino/polo and /polo — different paths)
        # and also /masculino/polo appears once; test dedup with explicit duplicate HTML
        html = textwrap.dedent("""\
            <html><body><nav>
              <a href="/masculino/polo">Polo</a>
              <a href="/masculino/polo">Polo (duplicate)</a>
              <a href="/masculino/camisetas">Camisetas</a>
            </nav></body></html>
        """)
        result = extract_nav_categories(html, "lacoste.com.br")
        paths = [c["path"] for c in result]
        assert len(paths) == len(set(paths)), "Paths must be unique (deduplication required)"

    def test_extract_nav_categories_filters_noise_labels(self):
        """extract_nav_categories filters out login/account/cart/help noise labels."""
        from services.engines.sfcc_parser import extract_nav_categories
        result = extract_nav_categories(_NAV_HTML, "lacoste.com.br")
        paths = [c["path"] for c in result]
        assert "/login" not in paths, "login path should be filtered as noise"

    def test_extract_nav_categories_filters_external_hrefs(self):
        """extract_nav_categories keeps only same-domain relative hrefs (startswith '/')."""
        from services.engines.sfcc_parser import extract_nav_categories
        result = extract_nav_categories(_NAV_HTML, "lacoste.com.br")
        paths = [c["path"] for c in result]
        for path in paths:
            assert path.startswith("/"), f"All paths must be relative, got: {path}"

    def test_extract_nav_categories_role_navigation(self):
        """extract_nav_categories works on elements with role=navigation (not just <nav>)."""
        from services.engines.sfcc_parser import extract_nav_categories
        result = extract_nav_categories(_ROLE_NAV_HTML, "hugoboss.com.br")
        assert isinstance(result, list)
        assert len(result) >= 1
        # /colecoes/ternos and /colecoes/camisas should be returned; /account filtered
        paths = [c["path"] for c in result]
        assert "/colecoes/ternos" in paths or "/colecoes/camisas" in paths

    def test_extract_nav_categories_is_pure(self):
        """extract_nav_categories is importable as a pure function (no browser dep)."""
        # This will ImportError if extract_nav_categories doesn't exist
        import importlib
        mod = importlib.import_module("services.engines.sfcc_parser")
        fn = getattr(mod, "extract_nav_categories", None)
        assert fn is not None, "extract_nav_categories must be defined in sfcc_parser"
        assert callable(fn)

    # -- discover_categories stub (D-06, Wave 1 — already GREEN) ----------------

    def test_discover_categories_stub(self):
        """D-06: discover_categories() returns [] when nav is absent (no crash)."""
        from services.engines.sfcc_engine import SFCCEngine

        empty_nav_html = "<html><head></head><body><p>No nav here</p></body></html>"
        with patch(
            _BROWSER_FETCH_TARGET,
            new=AsyncMock(return_value=empty_nav_html),
        ):
            engine = SFCCEngine("lacoste")
            result = asyncio.run(engine.discover_categories())

        assert result == []

    # -- discover_categories real impl (Task 2 — RED until Wave 2) ---------------

    def test_discover_categories_populated_nav_returns_dicts(self):
        """D-05: discover_categories() returns category dicts from rendered nav HTML."""
        from services.engines.sfcc_engine import SFCCEngine

        with patch(
            _BROWSER_FETCH_TARGET,
            new=AsyncMock(return_value=_NAV_HTML),
        ):
            engine = SFCCEngine("lacoste")
            result = asyncio.run(engine.discover_categories())

        assert isinstance(result, list)
        assert len(result) >= 1
        for item in result:
            assert "name" in item
            assert "path" in item
            assert "id" in item

    def test_discover_categories_exception_returns_empty(self):
        """D-06: discover_categories() returns [] (no crash) when BrowserManager raises."""
        from services.engines.sfcc_engine import SFCCEngine

        with patch(
            _BROWSER_FETCH_TARGET,
            new=AsyncMock(side_effect=RuntimeError("anti-bot block")),
        ):
            engine = SFCCEngine("lacoste")
            result = asyncio.run(engine.discover_categories())

        assert result == []

    # -- get_catalog group-shape (Task 2 — RED until Wave 2) --------------------

    def test_get_catalog_returns_group_shape(self):
        """get_catalog() wraps discover_categories into [{group, items:[{label,path}]}]."""
        from services.engines.sfcc_engine import SFCCEngine, CATALOG_GROUP_LABEL

        with patch(
            _BROWSER_FETCH_TARGET,
            new=AsyncMock(return_value=_NAV_HTML),
        ):
            engine = SFCCEngine("lacoste")
            catalog = asyncio.run(engine.get_catalog())

        assert isinstance(catalog, list)
        assert len(catalog) == 1
        group = catalog[0]
        assert group["group"] == CATALOG_GROUP_LABEL
        assert isinstance(group["items"], list)
        assert len(group["items"]) >= 1
        for item in group["items"]:
            assert "label" in item
            assert "path" in item

    def test_get_catalog_empty_nav_returns_single_empty_group(self):
        """get_catalog() with empty nav returns [{group: CATALOG_GROUP_LABEL, items: []}]."""
        from services.engines.sfcc_engine import SFCCEngine, CATALOG_GROUP_LABEL

        empty_nav_html = "<html><head></head><body><p>No nav here</p></body></html>"
        with patch(
            _BROWSER_FETCH_TARGET,
            new=AsyncMock(return_value=empty_nav_html),
        ):
            engine = SFCCEngine("lacoste")
            catalog = asyncio.run(engine.get_catalog())

        assert isinstance(catalog, list)
        assert len(catalog) == 1
        assert catalog[0]["group"] == CATALOG_GROUP_LABEL
        assert catalog[0]["items"] == []
