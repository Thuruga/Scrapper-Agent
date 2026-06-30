import asyncio

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

    async def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.posts = []

    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        status, payload = self.responses.pop(0)
        return FakeResponse(status, payload)


def _brand():
    return DynamicBrand(
        brand_key="richards",
        brand_name="Richards",
        domain="www.richards.com.br",
        engine="wake",
        wake_access_token="tcs_test",
    )


def _product(**kwargs):
    data = {
        "brand": "Richards",
        "product_name": "Camisa",
        "url": "https://www.richards.com.br/produto/camisa-linho-196863",
        "price_full": 479.0,
        "shipping_variant_id": "548230",
    }
    data.update(kwargs)
    return SearchProductResult(**data)


def test_wake_shipping_uses_product_variant_id_and_parses_quotes():
    from services.shipping.base import ShippingState
    from services.shipping.wake import WakeShipping

    session = FakeSession([
        (200, {"data": {"shippingQuotes": [
            {"shippingQuoteId": "sedex", "name": "SEDEX", "value": 32.95, "deadline": 4},
            {"shippingQuoteId": "pac", "name": "PAC", "value": 24.32, "deadline": 8},
        ]}}),
    ])
    provider = WakeShipping(session_factory=lambda: session)

    result = asyncio.run(provider.calculate(_product(), "01415000", _brand()))

    assert result.state == ShippingState.AVAILABLE
    assert [opt.service_name for opt in result.shipping_options] == ["PAC", "SEDEX"]
    assert result.shipping_options[0].price == pytest.approx(24.32)
    payload = session.posts[0][1]["json"]
    assert payload["variables"]["productVariantId"] == 548230


def test_wake_shipping_fetches_variant_from_product_url_when_missing():
    from services.shipping.base import ShippingState
    from services.shipping.wake import WakeShipping

    session = FakeSession([
        (200, {"data": {"product": {"productVariantId": 548230}}}),
        (200, {"data": {"shippingQuotes": [
            {"shippingQuoteId": "pac", "name": "PAC", "value": 24.32, "deadline": 8},
        ]}}),
    ])
    provider = WakeShipping(session_factory=lambda: session)
    product = _product(shipping_variant_id=None)

    result = asyncio.run(provider.calculate(product, "01415000", _brand()))

    assert result.state == ShippingState.AVAILABLE
    assert session.posts[0][1]["json"]["variables"]["productId"] == 196863


def test_wake_shipping_rejects_wrong_host_before_requests():
    from services.shipping.base import ShippingState
    from services.shipping.wake import WakeShipping

    session = FakeSession([])
    provider = WakeShipping(session_factory=lambda: session)

    result = asyncio.run(
        provider.calculate(
            _product(url="https://evil.example/produto/camisa-196863"),
            "01415000",
            _brand(),
        )
    )

    assert result.state == ShippingState.UNSUPPORTED
    assert session.posts == []


def test_wake_shipping_empty_quotes_not_free():
    from services.shipping.base import ShippingState
    from services.shipping.wake import WakeShipping

    session = FakeSession([(200, {"data": {"shippingQuotes": []}})])
    provider = WakeShipping(session_factory=lambda: session)

    result = asyncio.run(provider.calculate(_product(), "01415000", _brand()))

    assert result.state == ShippingState.UNAVAILABLE_FOR_CEP
    assert result.shipping_options == []
