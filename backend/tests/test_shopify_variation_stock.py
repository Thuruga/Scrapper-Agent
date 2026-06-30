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
    def __init__(self, status, payload):
        self.status = status
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def json(self, content_type=None):
        return self._payload


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
