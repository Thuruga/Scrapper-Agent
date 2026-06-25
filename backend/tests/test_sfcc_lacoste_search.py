"""
Hermetic tests for the SFCC Lacoste search path (spike 009 follow-up).

Proves — WITHOUT any live network / clean IP — that the engine extracts real
products from the Lacoste search page, using a fixture captured from the live
store (`tests/fixtures/lacoste_search_polo.html`, trimmed from spike 009).

Covers the three fixes that turned the Phase 36 NO-GO into a working engine:
  1. parse_search_tiles() extracts title+url+price+image straight from tiles.
  2. The canonical host (www.lacoste.com/br/) is used via brand.search_url_template
     — the stored lacoste.com.br redirects to home and drops the ?q=.
  3. brand.proxy_url is threaded to BrowserManager (clean-IP egress for prod).

Run from the backend/ dir:  python -m pytest tests/test_sfcc_lacoste_search.py
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from services.engines.sfcc_engine import SFCCEngine
from services.engines.sfcc_parser import parse_search_tiles

# Mock seam — same as test_sfcc_engine.py / test_engine_detection.py
_BROWSER_FETCH_TARGET = "core.browser_manager.BrowserManager.fetch_html"
_GET_BRAND_TARGET = "services.brand_service.brand_service.get_brand"

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "lacoste_search_polo.html"


def _fixture_html() -> str:
    return _FIXTURE.read_text(encoding="utf-8")


def _lacoste_brand(proxy_url=None):
    """Minimal brand stub matching the brands.json Lacoste config."""
    return SimpleNamespace(
        brand_key="lacoste",
        brand_name="Lacoste",
        domain="lacoste.com.br",
        search_url_template="https://www.lacoste.com/br/search?q={query}",
        proxy_url=proxy_url,
    )


# ---------------------------------------------------------------------------
# Parser-level: pure extraction from the captured tiles (no mocking)
# ---------------------------------------------------------------------------
class TestParseSearchTiles:
    def test_extracts_at_least_three_real_products(self):
        products = parse_search_tiles(_fixture_html(), "lacoste.com.br", brand="Lacoste")
        valid = [
            p for p in products
            if p["raw_title"]
            and p["url"].startswith("https://www.lacoste.com/br/")
            and (p["price_full"] or 0) > 0
            and p["image_url"]
            and p["image_url"].startswith("https://")
        ]
        assert len(valid) >= 3, f"esperava >=3 produtos completos, obtive {len(valid)}"

    def test_dicts_are_rawproductbronze_shaped(self):
        products = parse_search_tiles(_fixture_html(), "lacoste.com.br", brand="Lacoste")
        assert products, "fixture deveria render >=1 tile"
        required = {"url", "brand", "raw_title", "raw_description", "price_full", "image_url"}
        for p in products:
            assert required <= set(p), f"faltam chaves em {p.get('raw_title')!r}"
            assert p["brand"] == "Lacoste"

    def test_no_protocol_relative_url_leak(self):
        # Regressão do bug // : nenhuma URL/imagem pode ficar protocol-relative
        # nem conter // depois do host (era https://www.lacoste.com.br//www.lacoste.com/...).
        products = parse_search_tiles(_fixture_html(), "lacoste.com.br", brand="Lacoste")
        for p in products:
            assert not p["url"].startswith("//")
            assert "//" not in p["url"].split("://", 1)[1]
            if p["image_url"]:
                assert not p["image_url"].startswith("//")

    def test_prices_parsed_as_positive_floats(self):
        products = parse_search_tiles(_fixture_html(), "lacoste.com.br", brand="Lacoste")
        priced = [p for p in products if p["price_full"] is not None]
        assert priced, "esperava preços extraídos dos tiles"
        assert all(isinstance(p["price_full"], float) and p["price_full"] > 0 for p in priced)


# ---------------------------------------------------------------------------
# Engine-level: search() with BrowserManager + brand_service mocked
# ---------------------------------------------------------------------------
class TestEngineSearchTilesPath:
    def test_uses_canonical_url_and_returns_products(self):
        fetch_mock = AsyncMock(return_value=_fixture_html())
        with patch(_BROWSER_FETCH_TARGET, new=fetch_mock), \
             patch(_GET_BRAND_TARGET, return_value=_lacoste_brand()):
            result = asyncio.run(SFCCEngine("lacoste").search("polo", max_results=10))

        # 1) Host canônico foi usado (NÃO o lacoste.com.br que redireciona à home)
        called_url = (
            fetch_mock.call_args.args[0]
            if fetch_mock.call_args.args
            else fetch_mock.call_args.kwargs.get("url")
        )
        assert called_url == "https://www.lacoste.com/br/search?q=polo"

        # 2) Produtos reais extraídos e validados pelo Quality Gate
        assert len(result.products) >= 3
        assert all(p.price_full and p.price_full > 0 for p in result.products)
        assert all(p.url.startswith("https://www.lacoste.com/br/") for p in result.products)
        assert result.error is None

    def test_proxy_url_is_threaded_to_browser(self):
        brand = _lacoste_brand(proxy_url="http://user:pass@1.2.3.4:8080")
        fetch_mock = AsyncMock(return_value=_fixture_html())
        with patch(_BROWSER_FETCH_TARGET, new=fetch_mock), \
             patch(_GET_BRAND_TARGET, return_value=brand):
            asyncio.run(SFCCEngine("lacoste").search("polo"))

        assert fetch_mock.call_args.kwargs.get("proxy") == "http://user:pass@1.2.3.4:8080"

    def test_max_results_caps_output(self):
        fetch_mock = AsyncMock(return_value=_fixture_html())
        with patch(_BROWSER_FETCH_TARGET, new=fetch_mock), \
             patch(_GET_BRAND_TARGET, return_value=_lacoste_brand()):
            result = asyncio.run(SFCCEngine("lacoste").search("polo", max_results=2))
        assert len(result.products) <= 2
