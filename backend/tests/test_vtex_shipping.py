"""
Testes unitarios puros para o modulo vtex_shipping.

Cobrem as funcoes puras parse_estimate, filter_and_sort_slas, select_candidate e
classify_result sem nenhuma dependencia de rede ou sessao HTTP.

Requisito: FRET-05 — contrato centavos→reais, filtro de pickup, unidades de prazo,
ordenacao, entradas malformadas, guarda de regressao R$1.000.

Analogia de estilo: test_vtex_api_client.py (assertions diretas, sem fakes HTTP para
funcoes puras, sem pytest-asyncio).
"""
import pytest

from services.vtex_shipping import (
    classify_result,
    filter_and_sort_slas,
    parse_estimate,
    select_candidate,
)


# ---------------------------------------------------------------------------
# parse_estimate — quatro unidades VTEX (D-11)
# ---------------------------------------------------------------------------

class TestParseEstimate:
    def test_bd_display_text(self):
        value, unit, sort_seconds, display = parse_estimate("5bd")
        assert display == "Até 5 dias úteis"

    def test_d_display_text(self):
        value, unit, sort_seconds, display = parse_estimate("2d")
        assert display == "Até 2 dias"

    def test_h_display_text(self):
        value, unit, sort_seconds, display = parse_estimate("12h")
        assert display == "Até 12 horas"

    def test_m_display_text(self):
        value, unit, sort_seconds, display = parse_estimate("30m")
        assert display == "Até 30 minutos"

    def test_bd_unit_preserved(self):
        value, unit, sort_seconds, display = parse_estimate("5bd")
        assert unit == "bd"
        assert value == 5

    def test_d_unit_preserved(self):
        value, unit, sort_seconds, display = parse_estimate("2d")
        assert unit == "d"
        assert value == 2

    def test_h_unit_preserved(self):
        value, unit, sort_seconds, display = parse_estimate("12h")
        assert unit == "h"
        assert value == 12

    def test_m_unit_preserved(self):
        value, unit, sort_seconds, display = parse_estimate("30m")
        assert unit == "m"
        assert value == 30

    def test_sort_order_bd_longer_than_h(self):
        """bd dias uteis deve produzir duração sortavel maior que horas."""
        _, _, secs_bd, _ = parse_estimate("1bd")
        _, _, secs_h, _ = parse_estimate("1h")
        assert secs_bd > secs_h

    def test_sort_order_m_shorter_than_h(self):
        """minutos devem sortear antes de horas."""
        _, _, secs_m, _ = parse_estimate("60m")
        _, _, secs_h, _ = parse_estimate("1h")
        assert secs_m <= secs_h

    def test_invalid_estimate_returns_none(self):
        """Estimativa nao-parsavel retorna None."""
        result = parse_estimate("malformed")
        assert result is None

    def test_empty_estimate_returns_none(self):
        result = parse_estimate("")
        assert result is None


# ---------------------------------------------------------------------------
# filter_and_sort_slas — filtro de pickup, conversao centavos→reais, ordenacao
# ---------------------------------------------------------------------------

class TestFilterAndSortSlas:
    def _sla(self, name, price, estimate, channel="delivery",
             is_pickup=False, pickup_point_id=""):
        return {
            "name": name,
            "price": price,
            "shippingEstimate": estimate,
            "deliveryChannel": channel,
            "pickupStoreInfo": {"isPickupStore": is_pickup},
            "pickupPointId": pickup_point_id,
        }

    # --- Filtro de pickup (D-09) ---

    def test_pickup_by_channel_excluded(self):
        """SLA com deliveryChannel pickup-in-point deve ser excluido."""
        slas = [
            self._sla("Normal", 1990, "5bd"),
            self._sla("Expressa", 3990, "2bd"),
            self._sla("Retirada", 0, "0bd", channel="pickup-in-point"),
        ]
        result = filter_and_sort_slas(slas)
        channels = [o["deliveryChannel"] for o in result]
        assert "pickup-in-point" not in channels
        assert len(result) == 2

    def test_pickup_by_is_pickup_store_excluded(self):
        """Pickup defensivo por pickupStoreInfo.isPickupStore deve ser excluido."""
        slas = [
            self._sla("Normal", 1990, "5bd"),
            self._sla("Store", 0, "0bd", is_pickup=True),
        ]
        result = filter_and_sort_slas(slas)
        assert len(result) == 1
        assert result[0]["name"] == "Normal"

    def test_pickup_by_pickup_point_id_excluded(self):
        """Pickup defensivo por pickupPointId nao-vazio deve ser excluido."""
        slas = [
            self._sla("Normal", 1990, "5bd"),
            self._sla("Loja", 0, "0bd", pickup_point_id="STORE-001"),
        ]
        result = filter_and_sort_slas(slas)
        assert len(result) == 1
        assert result[0]["name"] == "Normal"

    def test_free_pickup_does_not_become_free_shipping(self):
        """Um pickup gratuito nao pode virar 'Frete Gratis' (D-09)."""
        slas = [
            self._sla("Normal", 1990, "5bd"),
            self._sla("Retirada Gratis", 0, "0bd", channel="pickup-in-point"),
        ]
        result = filter_and_sort_slas(slas)
        assert len(result) == 1
        # O unico resultado nao e gratis
        assert result[0]["price"] != 0 or result[0]["name"] != "Retirada Gratis"

    # --- Conversao centavos→reais e guarda de regressao R$1.000 (FRET-05, D-02) ---

    def test_cents_to_reais_conversion(self):
        """Preco 1990 centavos deve resultar em 19.90 reais."""
        slas = [self._sla("Normal", 1990, "5bd")]
        result = filter_and_sort_slas(slas)
        assert result[0]["price_reais"] == pytest.approx(19.90)

    def test_unit_regression_guard_below_1000(self):
        """Nenhuma opcao de entrega deve ter preco >= R$1.000 (guarda de regressao FRET-05)."""
        slas = [
            self._sla("Normal", 1990, "5bd"),
            self._sla("Expressa", 3990, "2bd"),
        ]
        result = filter_and_sort_slas(slas)
        assert all(o["price_reais"] < 1000 for o in result), (
            "Precos acima de R$1.000 indicam erro de unidade (centavos nao convertidos)"
        )

    # --- Ordenacao (D-10) ---

    def test_ordering_price_asc(self):
        """Opcoes devem ser ordenadas por preco crescente."""
        slas = [
            self._sla("Expressa", 3990, "2bd"),
            self._sla("Normal", 1990, "5bd"),
        ]
        result = filter_and_sort_slas(slas)
        assert result[0]["price_reais"] == pytest.approx(19.90)
        assert result[1]["price_reais"] == pytest.approx(39.90)

    def test_ordering_duration_asc_on_price_tie(self):
        """Em empate de preco, opcao com menor prazo deve vir primeiro."""
        slas = [
            self._sla("Lenta", 1990, "10bd"),
            self._sla("Rapida", 1990, "2bd"),
        ]
        result = filter_and_sort_slas(slas)
        assert result[0]["name"] == "Rapida"

    # --- Frete gratis + pago coexistindo (D-12) ---

    def test_free_and_paid_both_present(self):
        """Opcao gratuita e opcao paga devem coexistir no resultado."""
        slas = [
            self._sla("Gratis", 0, "5bd"),
            self._sla("Expressa", 3990, "1bd"),
        ]
        result = filter_and_sort_slas(slas)
        assert len(result) == 2

    def test_free_option_comes_first(self):
        """Opcao gratuita deve aparecer primeira (menor preco)."""
        slas = [
            self._sla("Expressa", 3990, "1bd"),
            self._sla("Gratis", 0, "5bd"),
        ]
        result = filter_and_sort_slas(slas)
        assert result[0]["price_reais"] == 0.0

    def test_free_option_flagged_is_free_shipping(self):
        """Opcao com price 0 deve ter is_free_shipping=True."""
        slas = [
            self._sla("Gratis", 0, "5bd"),
            self._sla("Expressa", 3990, "1bd"),
        ]
        result = filter_and_sort_slas(slas)
        free = next(o for o in result if o["price_reais"] == 0.0)
        assert free["is_free_shipping"] is True

    def test_paid_option_not_flagged_as_free(self):
        """Opcao paga nao deve ter is_free_shipping=True."""
        slas = [self._sla("Normal", 1990, "5bd")]
        result = filter_and_sort_slas(slas)
        assert result[0]["is_free_shipping"] is False

    # --- Contrato None != 0.0 (D-02) ---

    def test_price_zero_is_free_not_none(self):
        """Preco 0 (gratis) deve ser 0.0, nao None — os dois estados sao distintos."""
        slas = [self._sla("Gratis", 0, "3bd")]
        result = filter_and_sort_slas(slas)
        assert result[0]["price_reais"] == 0.0
        assert result[0]["price_reais"] is not None

    # --- Entradas malformadas (D-16) ---

    def test_malformed_missing_price_discarded(self):
        """Entrada sem campo price deve ser descartada."""
        slas = [
            {"name": "Sem preco", "shippingEstimate": "5bd", "deliveryChannel": "delivery",
             "pickupStoreInfo": {"isPickupStore": False}, "pickupPointId": ""},
            self._sla("Normal", 1990, "5bd"),
        ]
        result = filter_and_sort_slas(slas)
        assert len(result) == 1
        assert result[0]["name"] == "Normal"

    def test_malformed_negative_price_discarded(self):
        """Entrada com preco negativo deve ser descartada."""
        slas = [
            self._sla("Negativo", -100, "5bd"),
            self._sla("Normal", 1990, "5bd"),
        ]
        result = filter_and_sort_slas(slas)
        assert len(result) == 1
        assert result[0]["name"] == "Normal"

    def test_malformed_unparseable_estimate_discarded(self):
        """Entrada com shippingEstimate nao parseavel deve ser descartada."""
        slas = [
            self._sla("Malformed", 1990, "INVALIDO"),
            self._sla("Normal", 1990, "5bd"),
        ]
        result = filter_and_sort_slas(slas)
        assert len(result) == 1
        assert result[0]["name"] == "Normal"

    def test_all_malformed_returns_empty(self):
        """Lista totalmente malformada retorna lista vazia."""
        slas = [
            self._sla("M1", -1, "5bd"),
            self._sla("M2", 1990, "XPTO"),
        ]
        result = filter_and_sort_slas(slas)
        assert result == []

    def test_valid_survives_alongside_malformed(self):
        """Entrada valida sobrevive quando ha entradas malformadas na lista."""
        slas = [
            self._sla("Malformed", -100, "5bd"),
            self._sla("Valida", 1990, "5bd"),
        ]
        result = filter_and_sort_slas(slas)
        assert len(result) == 1
        assert result[0]["name"] == "Valida"


# ---------------------------------------------------------------------------
# select_candidate — seleciona (sku_id, seller_id) de itens disponiveis
# ---------------------------------------------------------------------------

class TestSelectCandidate:
    def _item(self, item_id, seller_id, price, available_qty=5):
        return {
            "itemId": item_id,
            "sellers": [
                {
                    "sellerId": seller_id,
                    "commertialOffer": {
                        "Price": price,
                        "AvailableQuantity": available_qty,
                    },
                }
            ],
        }

    def test_returns_sku_and_seller(self):
        items = [self._item("sku1", "seller-A", 199.90)]
        sku_id, seller_id = select_candidate(items)
        assert sku_id == "sku1"
        assert seller_id == "seller-A"

    def test_skips_out_of_stock_seller(self):
        """Vendedor sem estoque nao deve ser selecionado."""
        items = [
            self._item("sku1", "seller-out", 150.0, available_qty=0),
            self._item("sku2", "seller-in", 199.90, available_qty=5),
        ]
        sku_id, seller_id = select_candidate(items)
        assert sku_id == "sku2"
        assert seller_id == "seller-in"

    def test_empty_items_returns_none(self):
        result = select_candidate([])
        assert result is None


# ---------------------------------------------------------------------------
# classify_result — estado do resultado de simulacao
# ---------------------------------------------------------------------------

class TestClassifyResult:
    def test_available_when_options_present(self):
        options = [{"price_reais": 19.90, "is_free_shipping": False}]
        assert classify_result(options, transport_error=False) == "available"

    def test_unavailable_for_cep_when_no_options_and_no_error(self):
        """200 com zero opcoes de entrega = indisponivel para o CEP (nao falha tecnica)."""
        assert classify_result([], transport_error=False) == "unavailable_for_cep"

    def test_temporary_failure_on_transport_error(self):
        """Erro de transporte/timeout = falha temporaria."""
        assert classify_result([], transport_error=True) == "temporary_failure"

    def test_available_takes_precedence_over_transport_error(self):
        """Se ha opcoes validas, o resultado e available mesmo que houve erro parcial."""
        options = [{"price_reais": 19.90, "is_free_shipping": False}]
        assert classify_result(options, transport_error=True) == "available"
