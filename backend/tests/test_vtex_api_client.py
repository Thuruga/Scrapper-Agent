"""
Testes de caracterizacao de VtexApiClient (parse_product_dict + _fetch_shipping).

Travam o comportamento do _fetch_shipping reescrito em Wave 2 (33-02):
  - SKU pareado com seller resolvido (nao hardcoded "1") — D-01
  - Exatamente 1 retry em falha de transporte; sem retry em 200 vazio — D-15
  - Tres estados explícitos: available / unavailable_for_cep / temporary_failure — D-13/D-14
  - shipping_options populado; primary shipping/shipping_price/is_free_shipping derivados — FRET-05
  - Exceção por produto absorvida para nao cancelar asyncio.gather siblings — D-13

Estrategia (deterministico, zero rede):
  - parse_product_dict: fixture VtexProduct valido; as DUAS dependencias de I/O
    (get_single_review e _get_color_family) sao mockadas; o resto (extract_colors,
    extract_sizes, montagem do RawProductBronze) roda de verdade.
  - _fetch_shipping: self.session substituido por um fake async (post -> resposta
    async-context-manager). _FakeSession suporta sequencia de respostas/raises.
  - Sleep de retry patchado via monkeypatch para testes deterministicos.
  - metodos async dirigidos via asyncio.run (projeto sem pytest-asyncio configurado).
"""
import asyncio
import copy
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
        assert result.specifications["Cor"] == "Azul"
        assert result.specifications["Composição"] == "100% Algodão"
        assert result.specifications["composition"] == "100% Algodão"

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

    def test_stock_availability_true_when_later_sku_has_stock(self, monkeypatch):
        async def fake_review(brand_key, product_id):
            return (None, None)

        async def fake_color_family(domain, product_id):
            return []

        product = copy.deepcopy(_PRODUCT)
        product["items"][0]["sellers"][0]["commertialOffer"]["AvailableQuantity"] = 0
        product["items"].append(copy.deepcopy(product["items"][0]))
        product["items"][1]["itemId"] = "sku2"
        product["items"][1]["name"] = "Camisa Polo Aramis Piquet - G"
        product["items"][1]["sellers"][0]["commertialOffer"]["AvailableQuantity"] = 4

        monkeypatch.setattr(vtex_module, "get_single_review", fake_review)
        client = VtexApiClient(brand_name="Aramis")
        monkeypatch.setattr(client, "_get_color_family", fake_color_family)

        result = asyncio.run(client.parse_product_dict(product, product["link"], "www.aramis.com.br"))

        assert result is not None
        assert result.stock_availability is True

    def test_stock_availability_false_when_all_skus_are_unavailable(self, monkeypatch):
        async def fake_review(brand_key, product_id):
            return (None, None)

        async def fake_color_family(domain, product_id):
            return []

        product = copy.deepcopy(_PRODUCT)
        product["items"][0]["sellers"][0]["commertialOffer"]["AvailableQuantity"] = 0
        product["items"].append(copy.deepcopy(product["items"][0]))
        product["items"][1]["itemId"] = "sku2"
        product["items"][1]["name"] = "Camisa Polo Aramis Piquet - G"
        product["items"][1]["sellers"][0]["commertialOffer"]["AvailableQuantity"] = 0

        monkeypatch.setattr(vtex_module, "get_single_review", fake_review)
        client = VtexApiClient(brand_name="Aramis")
        monkeypatch.setattr(client, "_get_color_family", fake_color_family)

        result = asyncio.run(client.parse_product_dict(product, product["link"], "www.aramis.com.br"))

        assert result is not None
        assert result.stock_availability is False


class TestVtexSearchStockAggregation:
    def test_only_in_stock_keeps_product_when_later_sku_has_stock(self, monkeypatch):
        product_with_later_stock = copy.deepcopy(_PRODUCT)
        product_with_later_stock["items"][0]["sellers"][0]["commertialOffer"]["AvailableQuantity"] = 0
        product_with_later_stock["items"].append(copy.deepcopy(product_with_later_stock["items"][0]))
        product_with_later_stock["items"][1]["itemId"] = "sku2"
        product_with_later_stock["items"][1]["sellers"][0]["commertialOffer"]["AvailableQuantity"] = 2

        product_without_stock = copy.deepcopy(_PRODUCT)
        product_without_stock["productId"] = "empty"
        product_without_stock["productName"] = "Camisa sem estoque"
        product_without_stock["items"][0]["sellers"][0]["commertialOffer"]["AvailableQuantity"] = 0

        class _Brand:
            brand_key = "aramis"
            brand_name = "Aramis"
            domain = "www.aramis.com.br"

        async def fake_request_json(self, url):
            if "_from=0" in url:
                return [product_with_later_stock, product_without_stock]
            return []

        async def fake_reviews(brand_key, product_ids):
            return {pid: (None, None) for pid in product_ids}

        monkeypatch.setattr(vtex_module.brand_service, "get_brand", lambda brand_key: _Brand())
        monkeypatch.setattr(vtex_module, "resolve_query_to_vtex_category_path", lambda query, brand_key: None)
        monkeypatch.setattr(vtex_module, "get_bulk_reviews", fake_reviews)
        monkeypatch.setattr(VtexApiClient, "_request_json", fake_request_json)

        from services.engines.base_engine import BaseEngine

        monkeypatch.setattr(BaseEngine, "filter_mens_fashion", staticmethod(lambda products: products))

        result = asyncio.run(VtexApiClient("Aramis").search("camisa", max_results=10, only_in_stock=True))

        assert [p.product_name for p in result.products] == ["Camisa Polo Aramis Piquet"]
        assert result.products[0].available is True

    def test_search_marks_product_unavailable_when_no_sku_has_stock(self, monkeypatch):
        product_without_stock = copy.deepcopy(_PRODUCT)
        product_without_stock["items"][0]["sellers"][0]["commertialOffer"]["AvailableQuantity"] = 0

        class _Brand:
            brand_key = "aramis"
            brand_name = "Aramis"
            domain = "www.aramis.com.br"

        async def fake_request_json(self, url):
            if "_from=0" in url:
                return [product_without_stock]
            return []

        async def fake_reviews(brand_key, product_ids):
            return {pid: (None, None) for pid in product_ids}

        monkeypatch.setattr(vtex_module.brand_service, "get_brand", lambda brand_key: _Brand())
        monkeypatch.setattr(vtex_module, "resolve_query_to_vtex_category_path", lambda query, brand_key: None)
        monkeypatch.setattr(vtex_module, "get_bulk_reviews", fake_reviews)
        monkeypatch.setattr(VtexApiClient, "_request_json", fake_request_json)

        from services.engines.base_engine import BaseEngine

        monkeypatch.setattr(BaseEngine, "filter_mens_fashion", staticmethod(lambda products: products))

        result = asyncio.run(VtexApiClient("Aramis").search("camisa", max_results=10, only_in_stock=False))

        assert len(result.products) == 1
        assert result.products[0].available is False


# ---------------------------------------------------------------------------
# Helpers para SLAs com deliveryChannel correto (obrigatório em filter_and_sort_slas)
# ---------------------------------------------------------------------------

def _delivery_sla(name: str, price_cents: int, estimate: str) -> dict:
    """Constrói um SLA de entrega domiciliar mínimo para testes."""
    return {
        "name": name,
        "id": name.lower(),
        "deliveryChannel": "delivery",
        "price": price_cents,
        "shippingEstimate": estimate,
    }


def _pickup_sla(name: str, price_cents: int, estimate: str) -> dict:
    """Constrói um SLA de pickup (deve ser filtrado)."""
    return {
        "name": name,
        "id": name.lower(),
        "deliveryChannel": "pickup-in-point",
        "price": price_cents,
        "shippingEstimate": estimate,
    }


def _make_prod():
    """Cria um namespace de produto com os campos que _fetch_shipping popula."""
    return types.SimpleNamespace(
        shipping=None,
        shipping_options=[],
        shipping_price=None,
        is_free_shipping=False,
    )


# ---------------------------------------------------------------------------
# Fakes para _fetch_shipping (substituem aiohttp.ClientSession)
# ---------------------------------------------------------------------------

class _FakeResp:
    """Resposta fake que suporta uso como async context manager."""

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
    """Sessão fake com suporte a sequência de respostas e/ou raises.

    Se `responses` for uma lista, cada chamada a `post()` consome o próximo
    elemento. Elementos que são exceções são levantados; demais são retornados.
    Se a lista acabar, levanta IndexError (teste mal configurado).
    """

    def __init__(self, resp):
        if isinstance(resp, list):
            self._sequence = list(resp)
            self._single = None
        else:
            self._single = resp
            self._sequence = None

    def post(self, url, json=None, timeout=None):
        if self._sequence is not None:
            item = self._sequence.pop(0)
            if isinstance(item, BaseException):
                raise item
            return item
        return self._single


def _client_with_response(status, json_data):
    """Constrói um VtexApiClient com sessão fake de resposta única."""
    client = VtexApiClient(brand_name="Aramis")
    client.session = _FakeSession(_FakeResp(status, json_data))
    return client


def _client_with_sequence(items):
    """Constrói um VtexApiClient com sessão fake de sequência de respostas/raises."""
    client = VtexApiClient(brand_name="Aramis")
    client.session = _FakeSession(items)
    return client


# Atalho para chamar _fetch_shipping com argumentos padronizados
_DOMAIN = "www.aramis.com.br"
_ZIPCODE = "01001000"
_SKU = "sku1"
_SELLER = "2"  # seller não-"1" para validar que o caller usa o resolvido


def _run_fetch(client, prod=None, sku=_SKU, seller=_SELLER):
    if prod is None:
        prod = _make_prod()
    asyncio.run(client._fetch_shipping(sku, seller, _ZIPCODE, _DOMAIN, prod))
    return prod


# ---------------------------------------------------------------------------
# Testes de caracterização — baseline (3 pré-existentes, atualizados para Wave 2)
# ---------------------------------------------------------------------------

class TestFetchShippingCharacterization:
    def test_picks_cheapest_sla_and_parses_estimate(self):
        """Baseline 1: SLA mais barato selecionado como primary; deliveryChannel exigido."""
        body = {
            "logisticsInfo": [
                {
                    "slas": [
                        _delivery_sla("Expressa", 3990, "2bd"),
                        _delivery_sla("Normal", 1990, "5bd"),
                    ]
                }
            ]
        }
        client = _client_with_response(200, body)
        prod = _run_fetch(client)

        assert prod.shipping is not None
        assert prod.shipping.price == pytest.approx(19.90)  # 1990 / 100 (mais barato)
        assert prod.shipping.status == "Disponível"
        assert prod.shipping.estimated_delivery_days == 5
        assert prod.shipping.raw_text == "Normal - 5bd"
        # Wave 2: shipping_options deve conter ambas as opções
        assert len(prod.shipping_options) == 2
        prices = [o.price for o in prod.shipping_options]
        assert prices == pytest.approx([19.90, 39.90])  # ordenadas por preço

    def test_free_shipping_status(self):
        """Baseline 2: SLA grátis → status 'Grátis' e is_free_shipping=True."""
        body = {
            "logisticsInfo": [
                {"slas": [_delivery_sla("Gratis", 0, "3bd")]}
            ]
        }
        client = _client_with_response(200, body)
        prod = _run_fetch(client)

        assert prod.shipping.price == 0.0
        assert prod.shipping.status == "Grátis"
        assert prod.shipping.estimated_delivery_days == 3
        assert prod.is_free_shipping is True
        assert prod.shipping_price == pytest.approx(0.0)

    def test_no_logistics_info_yields_unavailable_for_cep(self):
        """Baseline 3: logisticsInfo vazia → 'Entrega indisponível para este CEP' (D-14).

        NOTA: o status mudou de 'Indisponível' (legado) para o texto explícito D-14
        pois um 200 com zero opções é um resultado de negócio, não falha técnica.
        """
        client = _client_with_response(200, {"logisticsInfo": []})
        prod = _run_fetch(client)

        assert "indisponível" in prod.shipping.status.lower()
        assert prod.shipping_options == []

    # ---------------------------------------------------------------------------
    # Novos casos: Wave 2 (retry, estados, SKU+seller, isolamento de siblings)
    # ---------------------------------------------------------------------------

    def test_payload_carries_resolved_seller_not_hardcoded_1(self):
        """D-01: seller enviado no payload é o resolvido, não '1' hardcoded."""
        captured = {}

        class _CapturingSession:
            def post(self, url, json=None, timeout=None):
                captured["payload"] = json
                # Retorna resposta válida para não entrar em retry
                return _FakeResp(200, {
                    "logisticsInfo": [
                        {"slas": [_delivery_sla("Normal", 1990, "5bd")]}
                    ]
                })

        client = VtexApiClient(brand_name="Aramis")
        client.session = _CapturingSession()
        prod = _make_prod()
        asyncio.run(client._fetch_shipping(_SKU, "42", _ZIPCODE, _DOMAIN, prod))

        assert captured["payload"] is not None
        items = captured["payload"]["items"]
        assert len(items) == 1
        assert items[0]["id"] == _SKU
        assert items[0]["seller"] == "42"  # seller resolvido, não "1"

    def test_timeout_then_success_makes_exactly_2_calls(self, monkeypatch):
        """D-15: timeout → retry → sucesso = exatamente 2 chamadas, sem estado de erro."""
        monkeypatch.setattr(
            "services.vtex_api_scraper.VtexApiClient._SHIPPING_RETRY_SLEEP", 0
        )
        call_count = [0]
        success_body = {
            "logisticsInfo": [
                {"slas": [_delivery_sla("Normal", 1990, "5bd")]}
            ]
        }

        import asyncio as _asyncio

        class _CountingSession:
            def post(self, url, json=None, timeout=None):
                call_count[0] += 1
                if call_count[0] == 1:
                    raise _asyncio.TimeoutError()
                return _FakeResp(200, success_body)

        client = VtexApiClient(brand_name="Aramis")
        client.session = _CountingSession()
        prod = _make_prod()
        asyncio.run(client._fetch_shipping(_SKU, _SELLER, _ZIPCODE, _DOMAIN, prod))

        assert call_count[0] == 2, f"Esperado exatamente 2 chamadas, fez {call_count[0]}"
        assert prod.shipping is not None
        assert "indisponível" not in prod.shipping.status.lower(), (
            f"Não deveria ser estado de erro, mas foi: {prod.shipping.status}"
        )
        assert prod.shipping.price == pytest.approx(19.90)

    def test_timeout_twice_yields_temporary_failure(self, monkeypatch):
        """D-13: 2 timeouts → produto mantido com 'Frete temporariamente indisponível'."""
        monkeypatch.setattr(
            "services.vtex_api_scraper.VtexApiClient._SHIPPING_RETRY_SLEEP", 0
        )
        import asyncio as _asyncio

        class _AlwaysTimeoutSession:
            def post(self, url, json=None, timeout=None):
                raise _asyncio.TimeoutError()

        client = VtexApiClient(brand_name="Aramis")
        client.session = _AlwaysTimeoutSession()
        prod = _make_prod()
        asyncio.run(client._fetch_shipping(_SKU, _SELLER, _ZIPCODE, _DOMAIN, prod))

        assert prod.shipping is not None
        assert "temporariamente" in prod.shipping.status.lower(), (
            f"Status inesperado: {prod.shipping.status}"
        )

    def test_200_pickup_only_yields_unavailable_for_cep_with_exactly_1_call(self):
        """D-14 + pitfall 5: 200 com apenas pickup → unavailable_for_cep; sem retry."""
        call_count = [0]

        class _CountingSession:
            def post(self, url, json=None, timeout=None):
                call_count[0] += 1
                return _FakeResp(200, {
                    "logisticsInfo": [
                        {"slas": [_pickup_sla("Retirada", 0, "1bd")]}
                    ]
                })

        client = VtexApiClient(brand_name="Aramis")
        client.session = _CountingSession()
        prod = _make_prod()
        asyncio.run(client._fetch_shipping(_SKU, _SELLER, _ZIPCODE, _DOMAIN, prod))

        assert call_count[0] == 1, f"Não deve fazer retry em 200 vazio; fez {call_count[0]} chamadas"
        assert prod.shipping is not None
        assert "indisponível" in prod.shipping.status.lower()
        assert prod.shipping_options == []

    def test_sibling_isolation_one_raises_others_survive(self, monkeypatch):
        """D-13: exceção em um produto não cancela os siblings no asyncio.gather."""
        monkeypatch.setattr(
            "services.vtex_api_scraper.VtexApiClient._SHIPPING_RETRY_SLEEP", 0
        )

        success_body = {
            "logisticsInfo": [
                {"slas": [_delivery_sla("Normal", 1990, "5bd")]}
            ]
        }

        async def _run_siblings():
            import asyncio as _asyncio

            # prod_a: vai levantar exceção na session
            client_a = VtexApiClient(brand_name="Aramis")

            class _RaisingSession:
                def post(self, url, json=None, timeout=None):
                    raise RuntimeError("store offline")

            client_a.session = _RaisingSession()
            prod_a = _make_prod()

            # prod_b: vai responder com sucesso
            client_b = _client_with_response(200, success_body)
            prod_b = _make_prod()

            # Simula o gather — cada cliente tem seu próprio semaphore (como seria em produção
            # onde um único VtexApiClient orquestra vários produtos via gather)
            await _asyncio.gather(
                client_a._fetch_shipping(_SKU, _SELLER, _ZIPCODE, _DOMAIN, prod_a),
                client_b._fetch_shipping(_SKU, _SELLER, _ZIPCODE, _DOMAIN, prod_b),
            )
            return prod_a, prod_b

        prod_a, prod_b = asyncio.run(_run_siblings())

        # prod_a deve continuar existindo (não propagou exceção) com estado de falha
        assert prod_a.shipping is not None
        # prod_b não deve ter sido afetado
        assert prod_b.shipping is not None
        assert prod_b.shipping.price == pytest.approx(19.90)

    def test_flatten_slas_across_all_logistics_entries(self):
        """CR-02: SLAs são achatados de TODAS as entradas de logisticsInfo, não só [0].

        Quando a 1ª entrada não tem SLA de entrega mas uma entrada posterior tem,
        o frete NÃO pode ser descartado (regressão do hard-index logisticsInfo[0]).
        """
        body = {
            "logisticsInfo": [
                {"slas": []},  # 1ª entrada vazia — o bug antigo pararia aqui
                {"slas": [_delivery_sla("Normal", 1990, "5bd")]},
            ]
        }
        client = _client_with_response(200, body)
        prod = _run_fetch(client)

        assert prod.shipping is not None
        assert prod.shipping.price == pytest.approx(19.90)
        assert len(prod.shipping_options) == 1

    def test_malformed_logistics_entry_is_skipped(self):
        """Robustez: entradas não-dict em logisticsInfo são ignoradas sem AttributeError."""
        body = {
            "logisticsInfo": [
                None,  # entrada malformada
                {"slas": [_delivery_sla("Normal", 1990, "5bd")]},
            ]
        }
        client = _client_with_response(200, body)
        prod = _run_fetch(client)

        assert prod.shipping is not None
        assert prod.shipping.price == pytest.approx(19.90)


class TestSimulateShippingReturnsState:
    """simulate_shipping retorna estado + opções sem mutar nenhum produto."""

    def test_available_returns_options_list(self):
        body = {"logisticsInfo": [{"slas": [_delivery_sla("Normal", 1990, "5bd")]}]}
        client = _client_with_response(200, body)
        result = asyncio.run(client.simulate_shipping(_SKU, _SELLER, _ZIPCODE, _DOMAIN))

        assert result["state"] == "available"
        assert len(result["shipping_options"]) == 1
        assert result["shipping_options"][0].price == pytest.approx(19.90)

    def test_unavailable_for_cep_returns_empty(self):
        client = _client_with_response(200, {"logisticsInfo": []})
        result = asyncio.run(client.simulate_shipping(_SKU, _SELLER, _ZIPCODE, _DOMAIN))

        assert result["state"] == "unavailable_for_cep"
        assert result["shipping_options"] == []

    def test_temporary_failure_on_persistent_error(self, monkeypatch):
        monkeypatch.setattr(
            "services.vtex_api_scraper.VtexApiClient._SHIPPING_RETRY_SLEEP", 0
        )
        import asyncio as _asyncio

        class _AlwaysTimeoutSession:
            def post(self, url, json=None, timeout=None):
                raise _asyncio.TimeoutError()

        client = VtexApiClient(brand_name="Aramis")
        client.session = _AlwaysTimeoutSession()
        result = asyncio.run(client.simulate_shipping(_SKU, _SELLER, _ZIPCODE, _DOMAIN))

        assert result["state"] == "temporary_failure"
        assert result["shipping_options"] == []
