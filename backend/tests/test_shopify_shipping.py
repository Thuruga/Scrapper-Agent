import asyncio
from unittest.mock import AsyncMock

import pytest

from core.models import DynamicBrand, SearchProductResult


class FakeResponse:
    def __init__(self, status, payload):
        self.status = status
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def json(self, content_type=None):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def request(self, method, url, **kwargs):
        self.requests.append((method, url, kwargs))
        status, payload = self.responses.pop(0)
        return FakeResponse(status, payload)


def _brand():
    return DynamicBrand(
        brand_key="bck",
        brand_name="Buckman",
        domain="buckmanbck.com.br",
        engine="shopify",
    )


def _product(**kwargs):
    data = {
        "brand": "bck",
        "product_name": "Blazer",
        "url": "https://buckmanbck.com.br/products/blazer",
        "price_full": 100.0,
    }
    data.update(kwargs)
    return SearchProductResult(**data)


def test_shopify_shipping_parses_successful_rates():
    from services.shipping.base import ShippingState
    from services.shipping.shopify import ShopifyShipping

    responses = [
        (200, {"product": {"variants": [{"id": 123, "available": True}]}}),
        (200, {}),
        (200, {"id": 123}),
        (202, None),
        (200, {"shipping_rates": [
            {"name": "Sedex", "price": "28.85", "delivery_days": [3, 3], "code": "sedex"},
            {"name": "PAC", "price": "0.00", "delivery_days": [7, 7], "code": "pac"},
        ]}),
        (200, {}),
    ]
    session = FakeSession(responses)
    provider = ShopifyShipping(session_factory=lambda: session, sleep=AsyncMock())

    result = asyncio.run(provider.calculate(_product(), "01415-000", _brand()))

    assert result.state == ShippingState.AVAILABLE
    assert [opt.service_name for opt in result.shipping_options] == ["PAC", "Sedex"]
    assert result.shipping_options[0].price == pytest.approx(0.0)
    assert result.shipping_options[0].is_free_shipping is True


def test_shopify_shipping_null_then_success_poll():
    from services.shipping.base import ShippingState
    from services.shipping.shopify import ShopifyShipping

    responses = [
        (200, {"product": {"variants": [{"id": 123, "available": True}]}}),
        (200, {}),
        (200, {"id": 123}),
        (202, None),
        (200, {}),
        (200, {"shipping_rates": [{"name": "PAC", "price": "12.00", "delivery_days": [5, 5]}]}),
        (200, {}),
    ]
    session = FakeSession(responses)
    provider = ShopifyShipping(session_factory=lambda: session, sleep=AsyncMock())

    result = asyncio.run(provider.calculate(_product(), "01415000", _brand()))

    assert result.state == ShippingState.AVAILABLE
    assert result.shipping_options[0].price == pytest.approx(12.0)


def test_shopify_shipping_rejects_wrong_host_before_requests():
    from services.shipping.base import ShippingState
    from services.shipping.shopify import ShopifyShipping

    session = FakeSession([])
    provider = ShopifyShipping(session_factory=lambda: session, sleep=AsyncMock())

    result = asyncio.run(
        provider.calculate(
            _product(url="https://evil.example/products/blazer"),
            "01415000",
            _brand(),
        )
    )

    assert result.state == ShippingState.UNSUPPORTED
    assert session.requests == []


def test_shopify_shipping_empty_rates_not_free():
    from services.shipping.base import ShippingState
    from services.shipping.shopify import ShopifyShipping

    responses = [
        (200, {"product": {"variants": [{"id": 123, "available": True}]}}),
        (200, {}),
        (200, {"id": 123}),
        (202, None),
        (200, {"shipping_rates": []}),
        (200, {}),
    ]
    session = FakeSession(responses)
    provider = ShopifyShipping(session_factory=lambda: session, sleep=AsyncMock())

    result = asyncio.run(provider.calculate(_product(), "01415000", _brand()))

    assert result.state == ShippingState.UNAVAILABLE_FOR_CEP
    assert result.shipping_options == []
