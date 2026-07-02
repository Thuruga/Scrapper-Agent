"""Hermetic tests for the Zara/Inditex engine.

The live Zara storefront is rendered and Akamai-protected, so these tests avoid
network entirely. BrowserManager is mocked and the parser is exercised with
small HTML fixtures that mirror the two useful page shapes:
  - category ItemList JSON-LD
  - search result product tiles
"""

from __future__ import annotations

import asyncio
import textwrap
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from core.models import CategoryMapping


_BROWSER_FETCH_TARGET = "core.browser_manager.BrowserManager.fetch_html"
_GET_BRAND_TARGET = "services.brand_service.brand_service.get_brand"


_CATEGORY_HTML = textwrap.dedent(
    """\
    <!doctype html>
    <html>
    <head>
      <title>Camisas masculinas | ZARA Brasil</title>
    </head>
    <body>
      <script type="application/ld+json">
      {
        "@context": "https://schema.org/",
        "@type": "ItemList",
        "numberOfItems": 1,
        "itemListElement": [
          {
            "@type": "ListItem",
            "position": 0,
            "item": {
              "@type": "Product",
              "name": "CAMISA VOILE XADREZ",
              "image": "https://static.zara.net/assets/camisa.jpg?w=352",
              "offers": {
                "@type": "Offer",
                "price": 319,
                "priceCurrency": "BRL",
                "url": "https://www.zara.com/br/pt/camisa-voile-xadrez-p07545101.html"
              }
            }
          }
        ]
      }
      </script>
    </body>
    </html>
    """
)


_SEARCH_HTML = textwrap.dedent(
    """\
    <!doctype html>
    <html>
    <body>
      <li class="product-grid-product _product" data-productid="503417392">
        <div class="product-grid-product__figure">
          <a class="product-link product-grid-product__link link"
             href="https://www.zara.com/br/pt/camisa-de-linho---algodao-p01063407.html">
            <img
              class="media-image__image"
              src="https://static.zara.net/assets/camisa-linho.jpg?w=195"
              alt="Camisa branca de manga longa" />
          </a>
        </div>
        <div class="product-grid-product__data">
          <a class="product-link _item product-grid-product-info__name link"
             href="https://www.zara.com/br/pt/camisa-de-linho---algodao-p01063407.html">
            CAMISA DE LINHO - ALGODAO
          </a>
          <div class="product-grid-product-info__product-price price">
            <span class="money-amount__main">R$ 279,00</span>
            <span class="price-current__amount">
              <span class="money-amount__main">R$ 167,40</span>
            </span>
          </div>
        </div>
      </li>
    </body>
    </html>
    """
)


_PDP_HTML = textwrap.dedent(
    """\
    <!doctype html>
    <html>
    <head>
      <script type="application/ld+json">
      {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": "CAMISA VOILE XADREZ",
        "image": ["https://static.zara.net/assets/camisa-pdp.jpg"],
        "offers": {
          "@type": "Offer",
          "price": "319.00",
          "priceCurrency": "BRL"
        }
      }
      </script>
    </head>
    <body></body>
    </html>
    """
)


def _zara_brand(*, proxy_url=None, mappings=None):
    return SimpleNamespace(
        brand_key="zara",
        brand_name="Zara",
        domain="www.zara.com",
        engine="zara",
        search_url_template="https://www.zara.com/br/pt/search?searchTerm={query}&section=MAN",
        proxy_url=proxy_url,
        mappings=mappings or [],
    )


class TestZaraParser:
    def test_itemlist_products_extract_catalog_shape(self):
        from services.engines.zara_parser import parse_itemlist_products

        products = parse_itemlist_products(_CATEGORY_HTML)

        assert len(products) == 1
        first = products[0]
        assert first["raw_title"] == "CAMISA VOILE XADREZ"
        assert first["url"].startswith("https://www.zara.com/br/pt/")
        assert first["price_full"] == 319.0
        assert first["image_url"].startswith("https://static.zara.net/")

    def test_tile_products_extract_discount_price(self):
        from services.engines.zara_parser import parse_tile_products

        products = parse_tile_products(_SEARCH_HTML)

        assert len(products) == 1
        first = products[0]
        assert first["raw_title"] == "CAMISA DE LINHO - ALGODAO"
        assert first["price_full"] == 279.0
        assert first["price_discount"] == 167.4
        assert first["shipping_product_id"] == "503417392"


class TestZaraEngine:
    def test_search_uses_template_proxy_and_returns_products(self):
        from services.engines.zara_engine import ZaraEngine

        fetch_mock = AsyncMock(return_value=_SEARCH_HTML)
        brand = _zara_brand(proxy_url="http://user:pass@1.2.3.4:8080")
        with patch(_BROWSER_FETCH_TARGET, new=fetch_mock), patch(
            _GET_BRAND_TARGET, return_value=brand
        ):
            result = asyncio.run(ZaraEngine("zara").search("camisa", max_results=3))

        called_url = fetch_mock.call_args.args[0]
        assert called_url == "https://www.zara.com/br/pt/search?searchTerm=camisa&section=MAN"
        assert fetch_mock.call_args.kwargs["proxy"] == "http://user:pass@1.2.3.4:8080"
        assert result.error is None
        assert len(result.products) == 1
        assert result.products[0].product_name == "CAMISA DE LINHO - ALGODAO"
        assert result.products[0].price_full == 279.0
        assert result.products[0].price_discount == 167.4

    def test_run_bulk_scrape_yields_valid_raw_products(self):
        from services.engines.zara_engine import ZaraEngine

        async def _collect():
            out = []
            async for product in ZaraEngine("zara").run_bulk_scrape(
                "/br/pt/man-shirts-l737.html"
            ):
                out.append(product)
            return out

        with patch(_BROWSER_FETCH_TARGET, new=AsyncMock(return_value=_CATEGORY_HTML)), patch(
            _GET_BRAND_TARGET, return_value=_zara_brand()
        ):
            products = asyncio.run(_collect())

        assert len(products) == 1
        assert products[0]["raw_title"] == "CAMISA VOILE XADREZ"
        assert products[0]["price_full"] == 319.0

    def test_get_product_details_uses_pdp_jsonld(self):
        from services.engines.zara_engine import ZaraEngine

        with patch(_BROWSER_FETCH_TARGET, new=AsyncMock(return_value=_PDP_HTML)), patch(
            _GET_BRAND_TARGET, return_value=_zara_brand()
        ):
            product = asyncio.run(
                ZaraEngine("zara").get_product_details(
                    "https://www.zara.com/br/pt/camisa-voile-xadrez-p07545101.html"
                )
            )

        assert product is not None
        assert product["raw_title"] == "CAMISA VOILE XADREZ"
        assert product["price_full"] == 319.0

    def test_get_catalog_from_mappings(self):
        from services.engines.zara_engine import ZaraEngine

        mappings = [
            CategoryMapping(
                canonical_slug="camisas",
                vtex_fq_path="/br/pt/man-shirts-l737.html",
                label="Camisas",
            )
        ]
        with patch(_GET_BRAND_TARGET, return_value=_zara_brand(mappings=mappings)):
            catalog = asyncio.run(ZaraEngine("zara").get_catalog())

        assert catalog == [
            {
                "group": "Categorias",
                "items": [{"label": "Camisas", "path": "/br/pt/man-shirts-l737.html"}],
            }
        ]

    def test_calculate_shipping_returns_none(self):
        from services.engines.zara_engine import ZaraEngine

        result = asyncio.run(ZaraEngine("zara").calculate_shipping({}, "01310000"))

        assert result is None


class TestZaraFactory:
    def test_factory_returns_zara_engine(self):
        from services.engines.factory import EngineFactory
        from services.engines.zara_engine import ZaraEngine

        with patch(
            "services.engines.factory.brand_service.get_brand",
            return_value=_zara_brand(),
        ):
            engine = EngineFactory.get_engine("zara")

        assert isinstance(engine, ZaraEngine)
