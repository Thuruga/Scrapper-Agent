from core.models import MapRule, RawProductBronze, SearchProductResult
from services.map_evaluator_service import (
    evaluate_map_violation,
    resolve_effective_advertised_price,
)
from services.promotion_parser import parse_promotion_text, parse_promotions
from services.promotion_parser import derive_discount_promotions


def test_map_uses_effective_sale_price_not_full_price():
    product = SearchProductResult(
        brand="Aramis",
        product_name="Polo",
        url="https://www.aramis.com.br/p/polo",
        price_full=300,
        price_discount=250,
    )
    rule = MapRule(scope="brand", target="Aramis", min_price=275)

    result = evaluate_map_violation(product, [rule], brand_name="Aramis")

    assert resolve_effective_advertised_price(product) == 250
    assert result["map_violation"] is True
    assert result["map_price_floor"] == 275
    assert result["map_infractor"] == "Aramis"


def test_delta_style_discount_resolves_to_current_price():
    product = SearchProductResult(
        brand="Aramis",
        product_name="Polo",
        url="https://www.aramis.com.br/p/polo",
        price_full=250,
        price_discount=50,
        price_discount_is_delta=True,
    )
    rule = MapRule(scope="brand", target="Aramis", min_price=275)

    result = evaluate_map_violation(product, [rule], brand_name="Aramis")

    assert resolve_effective_advertised_price(product) == 250
    assert result["map_violation"] is True


def test_no_rule_or_no_price_never_violates():
    product = SearchProductResult(
        brand="Aramis",
        product_name="Polo",
        url="https://www.aramis.com.br/p/polo",
        price_full=None,
    )
    rule = MapRule(scope="brand", target="Aramis", min_price=275)

    assert evaluate_map_violation(product, [rule])["map_violation"] is False
    assert evaluate_map_violation({"brand": "Reserva", "price": 100}, [rule])["map_violation"] is False


def test_marketplace_default_seller_is_marked_as_default_infractor():
    product = {
        "marketplace": "Mercado Livre",
        "seller": "Mercado Livre",
        "price": 99.0,
    }
    rule = MapRule(scope="brand", target="Mercado Livre", min_price=120)

    result = evaluate_map_violation(product, [rule], marketplace="Mercado Livre")

    assert result["map_violation"] is True
    assert result["map_infractor"] == "Mercado Livre"
    assert result["map_infractor_is_default"] is True


def test_raw_product_bronze_accepts_promotion_and_map_defaults():
    product = RawProductBronze(
        url="https://www.aramis.com.br/p/camisa",
        brand="Aramis",
        raw_title="Camisa",
        raw_description="Descricao",
        price_full=199.9,
        image_url="https://example.com/camisa.jpg",
    )

    assert product.promotions == []
    assert product.map_violation is False


def test_promotion_parser_classifies_required_types():
    assert parse_promotion_text("15% OFF no Pix").type == "pix_discount"
    assert parse_promotion_text("30% de desconto").type == "percentage_discount"
    assert parse_promotion_text("Leve 3 pague 2").type == "bundle"

    installments = parse_promotion_text("10x de R$ 39,90 sem juros")
    assert installments.type == "installments"
    assert installments.installments_count == 10
    assert installments.installment_amount == 39.9

    generic = parse_promotion_text("Oferta exclusiva")
    assert generic.type == "generic_badge"
    assert generic.raw_text == "Oferta exclusiva"
    assert generic.parsed is False


def test_parse_promotions_dedupes_and_skips_empty_values():
    parsed = parse_promotions(["15% OFF", "15% off", "", "Pix especial"])

    assert [p.raw_text for p in parsed] == ["15% OFF", "Pix especial"]


def test_derive_discount_promotions_from_delta_price():
    parsed = derive_discount_promotions(250.0, 50.0, price_discount_is_delta=True)

    assert parsed[0].type == "percentage_discount"
    assert parsed[0].raw_text == "17% OFF"
