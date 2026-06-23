"""
Testes de caracterizacao de VtexApiClient (parse_product_dict + _fetch_shipping).

Travam o comportamento ANTES do refactor de Workstream 2 (decomposicao da
god-class VtexApiClient — em especial a extracao de um builder PURO a partir de
parse_product_dict, e a extracao do transporte/shipping). Hoje so as funcoes
puras de vtex_parsing tem teste; o metodo de montagem parse_product_dict e a
simulacao de frete nao tinham cobertura.

Estrategia (deterministico, zero rede):
  - parse_product_dict: fixture VtexProduct valido; as DUAS dependencias de I/O
    (get_single_review e _get_color_family) sao mockadas; o resto (extract_colors,
    extract_sizes, montagem do RawProductBronze) roda de verdade.
  - _fetch_shipping: self.session substituido por um fake async (post -> resposta
    async-context-manager), exercitando a selecao do SLA mais barato, o /100, o
    parse do prazo e os status Gratis/Disponivel/Indisponivel.
  - metodos async dirigidos via asyncio.run (projeto sem pytest-asyncio configurado).
"""
import asyncio
import types

import pytest

import services.vtex_api_scraper as vtex_module
from services.vtex_api_scraper import VtexApiClient


# Fixture de produto VTEX valido (schema core.vtex_schemas.VtexProduct).
_PRODUCT = {
    "productId": "12345",
    "productName": "Camisa Polo Aramis Piquet",
    "brand": "Aramis",
    "brandId": 1,
    "linkText": "camisa-polo-aramis-piquet",
    "categoryId": "12",
    "categories": ["/Masculino/Camisas/Polo/"],
    "categoriesIds": ["/10/11/12/"],
    "link": "https://www.aramis.com.br/camisa-polo-aramis-piquet/p",
    "description": "Camisa polo em piquet de algodao.",
    "allSpecifications": ["Cor", "Composição"],
    "Cor": ["Azul"],
    "Composição": ["100% Algodão"],
    "items": [
        {
            "itemId": "sku1",
            "name": "Camisa Polo Aramis Piquet - M",
            "nameComplete": "Camisa Polo Aramis Piquet Azul M",
            "images": [{"imageUrl": "http://img/aramis-polo.jpg"}],
            "sellers": [
                {
                    "sellerId": "1",
                    "sellerName": "Aramis",
                    "sellerDefault": True,
                    "commertialOffer": {
                        "Price": 199.90,
                        "ListPrice": 299.90,
                        "PriceWithoutDiscount": 299.90,
                        "RewardValue": 0.0,
                        "AvailableQuantity": 5,
                        "Installments": [],
                    },
                }
            ],
        }
    ],
}


class TestParseProductDictCharacterization:
    def test_full_parse_in_stock_with_discount(self, monkeypatch):
        # Mocka as 2 dependencias de I/O (rede) de parse_product_dict
        async def fake_review(brand_key, product_id):
            return (4.5, 120)

        async def fake_color_family(domain, product_id):
            return ["PRETO", "AZUL"]  # overlap com a cor atual -> dedupe via set

        monkeypatch.setattr(vtex_module, "get_single_review", fake_review)

        client = VtexApiClient(brand_name="Aramis")
        monkeypatch.setattr(client, "_get_color_family", fake_color_family)

        product_url = "https://www.aramis.com.br/camisa-polo-aramis-piquet/p"
        result = asyncio.run(client.parse_product_dict(_PRODUCT, product_url, "www.aramis.com.br"))

        assert result is not None, "fixture deveria validar e produzir um RawProductBronze"
        assert result.url == product_url
        assert result.brand == "Aramis"
        assert result.raw_title == "Camisa Polo Aramis Piquet"
        assert result.raw_description == "Camisa polo em piquet de algodao."

        # Precos: usa a 1a variacao com estoque; price_discount = ListPrice - Price
        assert result.price_full == pytest.approx(199.90)
        assert result.price_discount == pytest.approx(100.0)
        assert result.stock_availability is True

        # Categoria: split de "/Masculino/Camisas/Polo/"
        assert result.category == "Masculino"
        assert result.sub_category == "Camisas"

        # Composicao via specs dinamicas
        assert result.composition == "100% Algodão"
        assert result.specifications == {"Cor": "Azul", "Composição": "100% Algodão"}

        # Cores: extract_colors (AZUL) + _get_color_family (PRETO/AZUL), dedup
        assert sorted(result.available_colors) == ["AZUL", "PRETO"]

        # Tamanhos: item com estoque, nome apos " - "
        assert result.available_sizes == ["M"]

        # Reviews (mockadas)
        assert result.rating == 4.5
        assert result.review_count == 120

        # Imagem
        assert result.image_url == "http://img/aramis-polo.jpg"

    def test_invalid_payload_returns_none(self, monkeypatch):
        # Payload que nao valida no VtexProduct (faltam campos obrigatorios) -> None
        client = VtexApiClient(brand_name="Aramis")
        result = asyncio.run(client.parse_product_dict({"foo": "bar"}, "http://x/p", "x"))
        assert result is None


# ---------------------------------------------------------------------------
# Fakes para _fetch_shipping (substituem aiohttp.ClientSession)
# ---------------------------------------------------------------------------
class _FakeResp:
    def __init__(self, status, json_data):
        self.status = status
        self._json = json_data

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def json(self):
        return self._json


class _FakeSession:
    def __init__(self, resp):
        self._resp = resp

    def post(self, url, json=None, timeout=None):
        return self._resp


def _client_with_response(status, json_data):
    client = VtexApiClient(brand_name="Aramis")
    client.session = _FakeSession(_FakeResp(status, json_data))
    return client


class TestFetchShippingCharacterization:
    def test_picks_cheapest_sla_and_parses_estimate(self):
        body = {
            "logisticsInfo": [
                {
                    "slas": [
                        {"name": "Expressa", "price": 3990, "shippingEstimate": "2bd"},
                        {"name": "Normal", "price": 1990, "shippingEstimate": "5bd"},
                    ]
                }
            ]
        }
        client = _client_with_response(200, body)
        prod = types.SimpleNamespace(shipping=None)
        asyncio.run(client._fetch_shipping("sku1", "01001000", "www.aramis.com.br", prod))

        assert prod.shipping is not None
        assert prod.shipping.price == pytest.approx(19.90)  # 1990 / 100
        assert prod.shipping.status == "Disponível"
        assert prod.shipping.estimated_delivery_days == 5
        assert prod.shipping.raw_text == "Normal - 5bd"

    def test_free_shipping_status(self):
        body = {"logisticsInfo": [{"slas": [{"name": "Gratis", "price": 0, "shippingEstimate": "3bd"}]}]}
        client = _client_with_response(200, body)
        prod = types.SimpleNamespace(shipping=None)
        asyncio.run(client._fetch_shipping("sku1", "01001000", "www.aramis.com.br", prod))

        assert prod.shipping.price == 0.0
        assert prod.shipping.status == "Grátis"
        assert prod.shipping.estimated_delivery_days == 3

    def test_no_logistics_info_is_unavailable(self):
        client = _client_with_response(200, {"logisticsInfo": []})
        prod = types.SimpleNamespace(shipping=None)
        asyncio.run(client._fetch_shipping("sku1", "01001000", "www.aramis.com.br", prod))

        assert prod.shipping.status == "Indisponível"
