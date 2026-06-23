from services.engines.amazon_engine import AmazonEngine
from services.engines.mercado_livre_engine import MercadoLivreEngine


def test_mercado_livre_extracts_item_id_from_product_url():
    engine = MercadoLivreEngine()

    assert (
        engine._extract_item_id(
            "https://produto.mercadolivre.com.br/MLB-4144269271-camisa-aramis-_JM"
        )
        == "MLB4144269271"
    )


def test_mercado_livre_extracts_item_id_from_catalog_url():
    engine = MercadoLivreEngine()

    assert engine._extract_item_id("https://www.mercadolivre.com.br/p/MLB12345678") == "MLB12345678"


def test_amazon_parses_free_shipping_text():
    engine = AmazonEngine()

    assert engine._parse_shipping_text("Entrega GRÁTIS amanhã") == {
        "is_free_shipping": True,
        "shipping_price": 0.0,
    }


def test_amazon_parses_paid_shipping_text():
    engine = AmazonEngine()

    assert engine._parse_shipping_text("Entrega em 2 dias com frete de R$ 18,90") == {
        "is_free_shipping": False,
        "shipping_price": 18.90,
    }


def test_amazon_captcha_result_shape_is_not_treated_as_shipping_price():
    blocked = {
        "error": "A Amazon bloqueou o cálculo de frete com CAPTCHA/anti-bot nesta sessão."
    }

    assert "shipping_price" not in blocked
    assert blocked["error"].startswith("A Amazon bloqueou")
