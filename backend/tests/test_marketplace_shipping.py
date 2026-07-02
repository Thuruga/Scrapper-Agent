from __future__ import annotations

import pytest

from config import settings
from core.models import DynamicBrand, SearchProductResult
from services.engines.amazon_engine import AmazonEngine
from services.shipping.amazon import AmazonShipping
from services.shipping.base import DEFAULT_MESSAGES, ShippingState
from services.shipping.mercado_livre import MercadoLivreShipping


def test_shipping_state_blocked_exists():
    assert ShippingState.BLOCKED == "blocked"
    assert DEFAULT_MESSAGES[ShippingState.BLOCKED] == "Bloqueado (anti-bot)"


def test_config_has_shipping_matrix_settings():
    assert isinstance(settings.SHIPPING_MATRIX_THROTTLE_SECONDS, (int, float))
    assert isinstance(settings.SHIPPING_MATRIX_CACHE_TTL_SECONDS, (int, float))


def _brand(engine: str, domain: str) -> DynamicBrand:
    return DynamicBrand(
        brand_key=f"{engine}_brand",
        brand_name=f"{engine} Brand",
        domain=domain,
        engine=engine,
    )


def _product(url: str) -> SearchProductResult:
    return SearchProductResult(
        brand=f"{url}_brand",
        product_name="Produto Teste",
        url=url,
        price_full=100.0,
    )


class _FakeEngine:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def calculate_shipping_advanced(self, product_url, cep):
        self.calls.append((product_url, cep))
        return self.result


# --- MercadoLivreShipping ---------------------------------------------------


@pytest.mark.asyncio
async def test_mercado_livre_provider_available_maps_cost_and_time():
    engine = _FakeEngine(
        {
            "is_free_shipping": False,
            "shipping_price": 24.9,
            "estimated_delivery_days": 5,
            "delivery_raw_text": "Chegara em ate 5 dias",
        }
    )
    provider = MercadoLivreShipping(engine=engine)
    brand = _brand("mercadolivre", "mercadolivre.com.br")
    product = _product("https://produto.mercadolivre.com.br/MLB-123-camisa")

    result = await provider.calculate(product, "01310100", brand)

    assert result.state == ShippingState.AVAILABLE
    assert len(result.shipping_options) == 1
    option = result.shipping_options[0]
    assert option.price == 24.9
    assert option.estimated_delivery_days == 5
    assert option.raw_text == "Chegara em ate 5 dias"


@pytest.mark.asyncio
async def test_mercado_livre_provider_free_shipping():
    engine = _FakeEngine({"is_free_shipping": True, "shipping_price": 0.0})
    provider = MercadoLivreShipping(engine=engine)
    brand = _brand("mercadolivre", "mercadolivre.com.br")
    product = _product("https://produto.mercadolivre.com.br/MLB-123-camisa")

    result = await provider.calculate(product, "01310100", brand)

    assert result.state == ShippingState.AVAILABLE
    option = result.shipping_options[0]
    assert option.price == 0.0
    assert option.is_free_shipping is True


@pytest.mark.asyncio
async def test_mercado_livre_provider_invalid_cep():
    engine = _FakeEngine({"is_free_shipping": False, "shipping_price": 10.0})
    provider = MercadoLivreShipping(engine=engine)
    brand = _brand("mercadolivre", "mercadolivre.com.br")
    product = _product("https://produto.mercadolivre.com.br/MLB-123-camisa")

    result = await provider.calculate(product, "123", brand)

    assert result.state == ShippingState.UNAVAILABLE_FOR_CEP
    assert engine.calls == []


@pytest.mark.asyncio
async def test_mercado_livre_provider_url_host_mismatch():
    engine = _FakeEngine({"is_free_shipping": False, "shipping_price": 10.0})
    provider = MercadoLivreShipping(engine=engine)
    brand = _brand("mercadolivre", "mercadolivre.com.br")
    product = _product("https://www.outrosite.com.br/produto-x")

    result = await provider.calculate(product, "01310100", brand)

    assert result.state == ShippingState.UNSUPPORTED
    assert engine.calls == []


@pytest.mark.asyncio
async def test_mercado_livre_provider_none_result():
    engine = _FakeEngine(None)
    provider = MercadoLivreShipping(engine=engine)
    brand = _brand("mercadolivre", "mercadolivre.com.br")
    product = _product("https://produto.mercadolivre.com.br/MLB-123-camisa")

    result = await provider.calculate(product, "01310100", brand)

    assert result.state == ShippingState.TEMPORARY_FAILURE


# --- AmazonShipping ----------------------------------------------------------


def test_amazon_provider_extracts_delivery_time():
    engine = AmazonEngine()

    parsed = engine._parse_shipping_text(
        "Receba em ate 3 dias uteis com frete de R$ 12,50"
    )

    assert parsed is not None
    assert parsed["is_free_shipping"] is False
    assert parsed["shipping_price"] == 12.50
    assert parsed.get("estimated_delivery_days") == 3 or parsed.get("delivery_raw_text")


@pytest.mark.asyncio
async def test_amazon_provider_captcha_is_temporary_not_blocked():
    engine = _FakeEngine({"error": "A Amazon bloqueou o calculo de frete com CAPTCHA/anti-bot nesta sessao."})
    provider = AmazonShipping(engine=engine)
    brand = _brand("amazon", "amazon.com.br")
    product = _product("https://www.amazon.com.br/dp/B012345")

    result = await provider.calculate(product, "01310100", brand)

    assert result.state == ShippingState.TEMPORARY_FAILURE
