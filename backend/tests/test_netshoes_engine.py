"""
Testes da extração de vendedor/preço da PDP da Netshoes.

Cobrem _extract_seller_price, que lê o preço autoritativo (price.saleInCents)
do __INITIAL_STATE__ da PDP — usado para corrigir a divergência com o preço da
listagem de busca (ex.: PDP R$ 538,55 vs busca R$ 429,99 para variantes/sellers
diferentes do mesmo modelo).
"""
from services.engines.netshoes_engine import NetshoesEngine


engine = NetshoesEngine()


def _state(price_obj=None, prices=None):
    cp = {}
    if price_obj is not None:
        cp["price"] = price_obj
    if prices is not None:
        cp["prices"] = prices
    return {"Product": {"currentProduct": cp}}


def test_extracts_seller_and_price_from_pdp():
    # Estrutura real observada na PDP (saleInCents em centavos)
    state = _state(price_obj={
        "saleInCents": 53855,
        "listInCents": 62390,
        "seller": {"name": "Shoestime"},
    })
    out = engine._extract_seller_price(state)
    assert out == {"seller": "Shoestime", "price": 538.55}


def test_falls_back_to_prices_list():
    state = _state(prices=[{"saleInCents": 19990, "seller": {"name": "Netshoes Oficial"}}])
    out = engine._extract_seller_price(state)
    assert out == {"seller": "Netshoes Oficial", "price": 199.9}


def test_missing_price_returns_none_price_default_seller():
    state = _state(price_obj={"seller": {"name": "Shoestime"}})
    out = engine._extract_seller_price(state)
    assert out["seller"] == "Shoestime"
    assert out["price"] is None


def test_zero_price_is_ignored():
    state = _state(price_obj={"saleInCents": 0, "seller": {"name": "X"}})
    assert engine._extract_seller_price(state)["price"] is None


def test_none_state_is_safe():
    out = engine._extract_seller_price(None)
    assert out == {"seller": "Netshoes", "price": None}


def test_no_seller_name_defaults_to_netshoes():
    state = _state(price_obj={"saleInCents": 10000})
    out = engine._extract_seller_price(state)
    assert out["seller"] == "Netshoes"
    assert out["price"] == 100.0
