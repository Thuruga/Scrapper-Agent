"""
Testes de contrato da API de busca — Wave 2 (33-02).

Cobre:
  1. GET /search/config → retorna {default_cep} de settings.DEFAULT_CEP, sem chaves secretas.
  2. SearchProductResult com shipping_options serializa corretamente via Pydantic:
       - shipping_options preservado como lista ordenada no model_dump(mode="json")
       - campos legados (shipping, shipping_price, is_free_shipping, landed_price) presentes
     Garante que o contrato de serialização para histórico e resposta da busca inclui as
     opções multi-modal sem hand-serialization (D-07).

Estratégia: determinística, zero rede.
  - config endpoint: chamado diretamente via FastAPI TestClient (sem servidor real).
  - contrato Pydantic: instancia SearchProductResult com shipping_options e valida model_dump.
  - metodos async (se usados) via asyncio.run (projeto sem pytest-asyncio configurado).
"""
import pytest
from fastapi.testclient import TestClient

from config import settings
from core.models import SearchProductResult, ShippingInfo


# ---------------------------------------------------------------------------
# TestClient para o router /search
# ---------------------------------------------------------------------------

def _make_test_app():
    """Cria um app FastAPI mínimo com apenas o router de search."""
    from fastapi import FastAPI
    from api.routes_search import router as search_router

    app = FastAPI()
    app.include_router(search_router)
    return app


@pytest.fixture(scope="module")
def client():
    app = _make_test_app()
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Testes do endpoint GET /config
# ---------------------------------------------------------------------------

class TestSearchConfigEndpoint:
    def test_returns_default_cep_from_settings(self, client):
        """D-04: GET /config retorna default_cep igual a settings.DEFAULT_CEP."""
        response = client.get("/search/config")
        assert response.status_code == 200
        data = response.json()
        assert data["default_cep"] == settings.DEFAULT_CEP

    def test_response_contains_only_default_cep_key(self, client):
        """Segurança (T-33-01): resposta contém somente 'default_cep', sem segredos."""
        response = client.get("/search/config")
        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) == {"default_cep"}, (
            f"Resposta contém chaves não esperadas: {set(data.keys()) - {'default_cep'}}"
        )

    def test_default_cep_is_nonempty_string(self, client):
        """DEFAULT_CEP deve ser uma string não-vazia."""
        response = client.get("/search/config")
        data = response.json()
        assert isinstance(data["default_cep"], str)
        assert len(data["default_cep"]) > 0

    def test_config_endpoint_requires_no_auth_body(self, client):
        """GET /config é read-only: sem body, sem parâmetros obrigatórios."""
        # Sem headers especiais, sem body — deve responder 200 normalmente
        response = client.get("/search/config")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Testes do contrato de serialização — SearchProductResult + shipping_options
# ---------------------------------------------------------------------------

def _make_shipping_option(name: str, price_reais: float, estimate_display: str, is_free: bool) -> ShippingInfo:
    return ShippingInfo(
        price=price_reais,
        status="Grátis" if is_free else "Disponível",
        estimated_delivery_days=5,
        raw_text=f"{name} - 5bd",
        service_name=name,
        service_id=name.lower(),
        estimate_display=estimate_display,
        estimate_unit="bd",
        is_free_shipping=is_free,
    )


class TestSearchProductResultSerializationContract:
    def test_shipping_options_serializes_as_list(self):
        """D-07: shipping_options serializa automaticamente via Pydantic (sem hand-serialization)."""
        options = [
            _make_shipping_option("Normal", 19.90, "Até 5 dias úteis", False),
            _make_shipping_option("Expressa", 39.90, "Até 2 dias úteis", False),
        ]
        result = SearchProductResult(
            brand="aramis",
            product_name="Camisa Polo",
            url="https://www.aramis.com.br/polo/p",
            price_full=199.90,
            shipping=options[0],
            shipping_options=options,
            shipping_price=options[0].price,
            is_free_shipping=False,
        )
        data = result.model_dump(mode="json")

        assert "shipping_options" in data, "shipping_options deve estar no model_dump"
        assert isinstance(data["shipping_options"], list)
        assert len(data["shipping_options"]) == 2

    def test_shipping_options_ordered_by_price(self):
        """Opções em shipping_options preservam a ordem (price asc) após serialização."""
        options = [
            _make_shipping_option("Normal", 19.90, "Até 5 dias úteis", False),
            _make_shipping_option("Expressa", 39.90, "Até 2 dias úteis", False),
        ]
        result = SearchProductResult(
            brand="aramis",
            product_name="Camisa Polo",
            url="https://www.aramis.com.br/polo/p",
            price_full=199.90,
            shipping=options[0],
            shipping_options=options,
            shipping_price=options[0].price,
        )
        data = result.model_dump(mode="json")

        prices = [opt["price"] for opt in data["shipping_options"]]
        assert prices == sorted(prices), f"Opções não estão ordenadas por preço: {prices}"
        assert prices[0] == pytest.approx(19.90)
        assert prices[1] == pytest.approx(39.90)

    def test_legacy_fields_still_present_alongside_shipping_options(self):
        """Evolução aditiva (D-08): campos legados coexistem com shipping_options."""
        option = _make_shipping_option("Normal", 19.90, "Até 5 dias úteis", False)
        result = SearchProductResult(
            brand="aramis",
            product_name="Camisa Polo",
            url="https://www.aramis.com.br/polo/p",
            price_full=199.90,
            shipping=option,
            shipping_options=[option],
            shipping_price=option.price,
            is_free_shipping=False,
        )
        data = result.model_dump(mode="json")

        # Campos legados obrigatoriamente presentes
        for field in ("shipping", "shipping_price", "is_free_shipping", "landed_price"):
            assert field in data, f"Campo legado ausente no model_dump: {field}"

    def test_free_shipping_option_serializes_correctly(self):
        """Frete grátis: price=0.0, is_free_shipping=True propagam na serialização."""
        free_option = _make_shipping_option("Gratis", 0.0, "Até 3 dias úteis", True)
        result = SearchProductResult(
            brand="aramis",
            product_name="Camisa Polo",
            url="https://www.aramis.com.br/polo/p",
            price_full=199.90,
            shipping=free_option,
            shipping_options=[free_option],
            shipping_price=0.0,
            is_free_shipping=True,
        )
        data = result.model_dump(mode="json")

        assert data["is_free_shipping"] is True
        assert data["shipping_price"] == pytest.approx(0.0)
        opt = data["shipping_options"][0]
        assert opt["price"] == pytest.approx(0.0)
        assert opt["is_free_shipping"] is True

    def test_empty_shipping_options_is_valid_for_legacy_results(self):
        """Registros antigos sem shipping_options ainda serializam (pitfall 6 / case 9)."""
        result = SearchProductResult(
            brand="aramis",
            product_name="Camisa Polo",
            url="https://www.aramis.com.br/polo/p",
            price_full=199.90,
        )
        data = result.model_dump(mode="json")

        assert data["shipping_options"] == [], (
            "shipping_options deve ser lista vazia (não None) em registros legados"
        )
