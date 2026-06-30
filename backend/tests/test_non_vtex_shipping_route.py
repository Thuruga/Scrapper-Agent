from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.models import DynamicBrand, ShippingInfo
from services.shipping.base import ShippingCalculation, ShippingState


def _client(monkeypatch, brand=None, provider=None):
    import api.routes_search as routes_search

    app = FastAPI()
    app.include_router(routes_search.router)

    monkeypatch.setattr(routes_search.brand_service, "get_brand", lambda key: brand)
    if provider is not None:
        monkeypatch.setattr(routes_search, "resolve_shipping_provider", lambda _brand: provider)

    return TestClient(app)


def _brand(engine="shopify"):
    return DynamicBrand(
        brand_key="bck" if engine == "shopify" else "lacoste",
        brand_name="Buckman" if engine == "shopify" else "Lacoste",
        domain="buckmanbck.com.br" if engine == "shopify" else "www.lacoste.com.br",
        engine=engine,
    )


class FakeProvider:
    def __init__(self, calculation):
        self.calculation = calculation
        self.calls = []

    async def calculate(self, product, zipcode, brand):
        self.calls.append((product, zipcode, brand))
        return self.calculation


def test_calculate_shipping_brand_available(monkeypatch):
    provider = FakeProvider(
        ShippingCalculation(
            state=ShippingState.AVAILABLE,
            shipping_options=[
                ShippingInfo(price=0.0, status="Gratis", service_name="PAC", is_free_shipping=True)
            ],
        )
    )
    client = _client(monkeypatch, brand=_brand("shopify"), provider=provider)

    response = client.post(
        "/search/calculate-shipping-brand",
        json={
            "brand_key": "bck",
            "product_url": "https://buckmanbck.com.br/products/blazer",
            "zipcode": "01415-000",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "available"
    assert data["shipping_options"][0]["price"] == 0.0
    assert data["shipping_price"] == 0.0
    assert data["is_free_shipping"] is True
    assert len(provider.calls) == 1


def test_calculate_shipping_brand_rejects_host_mismatch_before_provider(monkeypatch):
    provider = FakeProvider(ShippingCalculation(state=ShippingState.AVAILABLE))
    client = _client(monkeypatch, brand=_brand("shopify"), provider=provider)

    response = client.post(
        "/search/calculate-shipping-brand",
        json={
            "brand_key": "bck",
            "product_url": "https://evil.example/products/blazer",
            "zipcode": "01415000",
        },
    )

    assert response.status_code == 400
    assert provider.calls == []


def test_calculate_shipping_brand_unknown_brand(monkeypatch):
    client = _client(monkeypatch, brand=None, provider=FakeProvider(ShippingCalculation("available")))

    response = client.post(
        "/search/calculate-shipping-brand",
        json={
            "brand_key": "missing",
            "product_url": "https://missing.example/products/a",
            "zipcode": "01415000",
        },
    )

    assert response.status_code == 404


def test_calculate_shipping_brand_rejects_vtex(monkeypatch):
    client = _client(monkeypatch, brand=_brand("vtex"), provider=FakeProvider(ShippingCalculation("available")))

    response = client.post(
        "/search/calculate-shipping-brand",
        json={
            "brand_key": "aramis",
            "product_url": "https://buckmanbck.com.br/products/a",
            "zipcode": "01415000",
        },
    )

    assert response.status_code == 400


def test_calculate_shipping_brand_unsupported_not_free(monkeypatch):
    provider = FakeProvider(
        ShippingCalculation(
            state=ShippingState.UNSUPPORTED,
            message="Frete nao suportado para este engine",
        )
    )
    client = _client(monkeypatch, brand=_brand("sfcc"), provider=provider)

    response = client.post(
        "/search/calculate-shipping-brand",
        json={
            "brand_key": "lacoste",
            "product_url": "https://www.lacoste.com.br/produto/a",
            "zipcode": "01415000",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "unsupported"
    assert data["shipping_options"] == []
    assert data["shipping_price"] is None
    assert data["is_free_shipping"] is False


def test_existing_vtex_endpoint_still_registered(monkeypatch):
    client = _client(monkeypatch, brand=_brand("shopify"), provider=FakeProvider(ShippingCalculation("available")))

    paths = {route.path for route in client.app.routes}
    assert "/search/calculate-shipping-vtex" in paths
