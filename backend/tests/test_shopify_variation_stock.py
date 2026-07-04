import asyncio
from types import SimpleNamespace

import services.shopify_api_client as shopify_module
from services.shopify_api_client import ShopifyApiClient


def _shopify_product(variants):
    return {
        "handle": "polo-regular",
        "title": "Polo Regular",
        "body_html": "Polo",
        "vendor": "Shopify Brand",
        "product_type": "Polo",
        "tags": ["masculino"],
        "images": [{"src": "https://example.com/polo.jpg"}],
        "variants": variants,
    }


def test_map_to_bronze_true_when_any_variant_is_available(monkeypatch):
    monkeypatch.setattr(
        shopify_module.brand_service,
        "get_brand",
        lambda brand_key: SimpleNamespace(domain="shop.example.com", brand_name="Shop"),
    )
    client = ShopifyApiClient("shop")

    product = client._map_to_bronze(
        _shopify_product(
            [
                {"title": "P", "price": "199.90", "available": False},
                {"title": "M", "price": "199.90", "available": True},
            ]
        ),
        "polos",
    )

    assert product is not None
    assert product.stock_availability is True
    assert product.available_sizes == ["M"]


def test_map_to_bronze_false_when_all_variants_are_unavailable(monkeypatch):
    monkeypatch.setattr(
        shopify_module.brand_service,
        "get_brand",
        lambda brand_key: SimpleNamespace(domain="shop.example.com", brand_name="Shop"),
    )
    client = ShopifyApiClient("shop")

    product = client._map_to_bronze(
        _shopify_product(
            [
                {"title": "P", "price": "199.90", "available": False},
                {"title": "M", "price": "199.90", "available": False},
            ]
        ),
        "polos",
    )

    assert product is not None
    assert product.stock_availability is False
    assert product.available_sizes == []


class _FakeResp:
    def __init__(self, status, payload=None, text_body=None):
        self.status = status
        self._payload = payload
        self._text_body = text_body or ""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def json(self, content_type=None):
        return self._payload

    async def text(self):
        return self._text_body


class _FakeSession:
    def __init__(self, responses):
        self._responses = list(responses)

    def get(self, url, timeout=None, headers=None):
        if not self._responses:
            raise AssertionError(f"Unexpected request: {url}")
        return self._responses.pop(0)


def _patch_search_dependencies(monkeypatch, responses):
    monkeypatch.setattr(
        shopify_module.brand_service,
        "get_brand",
        lambda brand_key: SimpleNamespace(domain="shop.example.com", brand_name="Shop"),
    )
    async def fake_get_session():
        return _FakeSession(responses)

    monkeypatch.setattr(shopify_module.SessionManager, "get_session", staticmethod(fake_get_session))

    from services.engines.base_engine import BaseEngine

    monkeypatch.setattr(BaseEngine, "filter_mens_fashion", staticmethod(lambda products: products))


def test_search_suggest_maps_available_from_variants(monkeypatch):
    _patch_search_dependencies(
        monkeypatch,
        [
            _FakeResp(
                200,
                {
                    "resources": {
                        "results": {
                            "products": [
                                {
                                    "title": "Polo indisponivel",
                                    "url": "/products/polo",
                                    "price": "199.90",
                                    "featured_image": {"url": "https://example.com/polo.jpg"},
                                    "variants": [
                                        {"available": False},
                                        {"available": False},
                                    ],
                                }
                            ]
                        }
                    }
                },
            )
        ],
    )

    result = asyncio.run(ShopifyApiClient("shop").search("polo"))

    assert len(result.products) == 1
    assert result.products[0].available is False


def test_search_json_maps_available_from_variants(monkeypatch):
    _patch_search_dependencies(
        monkeypatch,
        [
            _FakeResp(200, {"resources": {"results": {"products": []}}}),
            _FakeResp(
                200,
                {
                    "results": [
                        _shopify_product(
                            [
                                {"title": "P", "price": "199.90", "available": False},
                                {"title": "M", "price": "199.90", "available": True},
                            ]
                        )
                    ]
                },
            ),
        ],
    )

    result = asyncio.run(ShopifyApiClient("shop").search("polo"))

    assert len(result.products) == 1
    assert result.products[0].available is True


def test_get_product_by_url_enriches_availability_and_rating_from_json_ld(monkeypatch):
    monkeypatch.setattr(
        shopify_module.brand_service,
        "get_brand",
        lambda brand_key: SimpleNamespace(domain="shop.example.com", brand_name="Shop"),
    )
    session = _FakeSession(
        [
            _FakeResp(
                200,
                {
                    "product": _shopify_product(
                        [
                            {"title": "36", "price": "199.90"},
                            {"title": "40", "price": "199.90"},
                        ]
                    )
                },
            ),
            _FakeResp(
                200,
                text_body="""
                <html>
                  <head>
                    <script type="application/ld+json">
                    {
                      "@context": "https://schema.org",
                      "@type": "ProductGroup",
                      "aggregateRating": {
                        "ratingValue": "4,8",
                        "reviewCount": "1.234"
                      },
                      "hasVariant": [
                        {
                          "@type": "Product",
                          "name": "Polo Regular - 36",
                          "offers": {
                            "@type": "Offer",
                            "availability": "http://schema.org/OutOfStock"
                          }
                        },
                        {
                          "@type": "Product",
                          "name": "Polo Regular - 40",
                          "offers": {
                            "@type": "Offer",
                            "availability": "http://schema.org/InStock"
                          }
                        }
                      ]
                    }
                    </script>
                  </head>
                </html>
                """,
            ),
        ]
    )

    async def fake_get_session():
        return session

    monkeypatch.setattr(shopify_module.SessionManager, "get_session", staticmethod(fake_get_session))

    product = asyncio.run(
        ShopifyApiClient("shop").get_product_by_url("https://shop.example.com/products/polo-regular")
    )

    assert product is not None
    assert product.category == "Polo"
    assert product.stock_availability is True
    assert product.available_sizes == ["40"]
    assert product.rating == 4.8
    assert product.review_count == 1234


def test_get_product_by_url_leaves_category_blank_without_truthful_source_value(monkeypatch):
    monkeypatch.setattr(
        shopify_module.brand_service,
        "get_brand",
        lambda brand_key: SimpleNamespace(domain="shop.example.com", brand_name="Shop"),
    )
    session = _FakeSession(
        [
            _FakeResp(
                200,
                {
                    "product": {
                        **_shopify_product(
                            [
                                {"title": "U", "price": "199.90", "available": True},
                            ]
                        ),
                        "product_type": "",
                    }
                },
            ),
            _FakeResp(200, text_body="<html></html>"),
        ]
    )

    async def fake_get_session():
        return session

    monkeypatch.setattr(shopify_module.SessionManager, "get_session", staticmethod(fake_get_session))

    product = asyncio.run(
        ShopifyApiClient("shop").get_product_by_url("https://shop.example.com/products/polo-regular")
    )

    assert product is not None
    assert product.category is None
