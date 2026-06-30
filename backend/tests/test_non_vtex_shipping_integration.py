import asyncio

import pytest

from core.models import SearchProductResult, ShippingInfo
from services.shipping.base import (
    ShippingCalculation,
    ShippingState,
    apply_shipping_calculation,
)


def _product() -> SearchProductResult:
    return SearchProductResult(
        brand="bck",
        product_name="Camisa",
        url="https://buckmanbck.com.br/products/camisa",
        price_full=100.0,
    )


def test_apply_shipping_sorts_options_and_sets_primary_fields():
    product = _product()
    options = [
        ShippingInfo(price=30.0, status="Disponivel", service_name="Sedex", estimated_delivery_days=2),
        ShippingInfo(price=0.0, status="Gratis", service_name="PAC", estimated_delivery_days=7, is_free_shipping=True),
    ]

    apply_shipping_calculation(
        product,
        ShippingCalculation(state=ShippingState.AVAILABLE, shipping_options=options),
    )

    assert [opt.service_name for opt in product.shipping_options] == ["PAC", "Sedex"]
    assert product.shipping is product.shipping_options[0]
    assert product.shipping_price == pytest.approx(0.0)
    assert product.is_free_shipping is True
    assert product.landed_price == pytest.approx(100.0)


def test_apply_shipping_temporary_failure_does_not_mark_free():
    product = _product()

    apply_shipping_calculation(
        product,
        ShippingCalculation(
            state=ShippingState.TEMPORARY_FAILURE,
            message="Frete temporariamente indisponivel",
        ),
    )

    assert product.shipping_options == []
    assert product.shipping_price is None
    assert product.is_free_shipping is False
    assert product.shipping is not None
    assert "temporariamente" in product.shipping.status


def test_apply_shipping_unsupported_does_not_mark_free():
    product = _product()

    apply_shipping_calculation(
        product,
        ShippingCalculation(state=ShippingState.UNSUPPORTED),
    )

    assert product.shipping_price is None
    assert product.is_free_shipping is False


def test_shopify_inline_shipping_called_only_with_zipcode(monkeypatch):
    from core.models import BrandSearchResult
    from services.engines.shopify_engine import ShopifyEngine

    calls = []

    async def fake_calculate(self, product, zipcode):
        calls.append((product.url, zipcode))
        return ShippingCalculation(
            state=ShippingState.AVAILABLE,
            shipping_options=[
                ShippingInfo(price=12.0, status="Disponivel", service_name="PAC")
            ],
        )

    async def fake_search(self, query, max_results):
        return BrandSearchResult(
            brand_key="bck",
            brand_name="Buckman",
            products=[_product()],
            total_found=1,
        )

    monkeypatch.setattr(ShopifyEngine, "calculate_shipping", fake_calculate)
    monkeypatch.setattr("services.shopify_api_client.ShopifyApiClient.search", fake_search)
    async def fake_get_session():
        return object()

    monkeypatch.setattr("core.session_manager.SessionManager.get_session", fake_get_session)

    engine = ShopifyEngine("bck")
    no_zip = asyncio.run(engine.search("camisa", include_shipping=True, zipcode=None))
    assert calls == []
    assert no_zip.products[0].shipping_price is None

    with_zip = asyncio.run(engine.search("camisa", include_shipping=True, zipcode="01415000"))
    assert calls == [(with_zip.products[0].url, "01415000")]
    assert with_zip.products[0].shipping_price == pytest.approx(12.0)
