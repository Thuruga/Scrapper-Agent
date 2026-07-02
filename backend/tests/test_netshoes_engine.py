"""
Testes da extração de vendedor/preço da PDP da Netshoes.

Cobrem _extract_seller_price, que lê o preço autoritativo (price.saleInCents)
do __INITIAL_STATE__ da PDP — usado para corrigir a divergência com o preço da
listagem de busca (ex.: PDP R$ 538,55 vs busca R$ 429,99 para variantes/sellers
diferentes do mesmo modelo).
"""
import asyncio
from unittest.mock import patch, MagicMock

from services.engines.netshoes_engine import NetshoesEngine


engine = NetshoesEngine()


# ---------------------------------------------------------------------------
# Helpers para mockar o curl_cffi AsyncSession em get_pdp_product
# ---------------------------------------------------------------------------

def _pdp_html_with_state(sale_in_cents: int, name: str = "Tênis Aramis Icon") -> str:
    """HTML mínimo com window.__INITIAL_STATE__ contendo um currentProduct válido."""
    import json as _json

    state = {
        "Product": {
            "currentProduct": {
                "name": name,
                "description": name,
                "price": {"saleInCents": sale_in_cents, "seller": {"name": "Netshoes"}},
                "image": "https://static.netshoes.com.br/img.jpg",
                "available": True,
            }
        }
    }
    return f"<html><body><script>window.__INITIAL_STATE__ = {_json.dumps(state)};</script></body></html>"


def _mock_curl_session(status_code: int, text: str = ""):
    """Constrói um AsyncSession mockado (context manager) para o curl_cffi."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text

    session = MagicMock()
    session.get = _AsyncReturn(resp)
    session.__aenter__ = _AsyncReturn(session)
    session.__aexit__ = _AsyncReturn(False)
    return session


class _AsyncReturn:
    """Callable que retorna um valor via coroutine (para mockar métodos async)."""

    def __init__(self, value):
        self._value = value

    async def __call__(self, *args, **kwargs):
        return self._value


# ---------------------------------------------------------------------------
# REGRESSÃO (monitor-marketplace-pendente Round 2, hypothesis_B):
# get_pdp_product deve fazer fallback p/ Playwright quando o curl_cffi tomar 403.
# Antes: 403 → None → "Pendente" eterno, sem fallback.
# ---------------------------------------------------------------------------

def test_get_pdp_product_403_falls_back_to_playwright():
    """curl_cffi 403 → renderiza via Playwright → extrai o produto do __INITIAL_STATE__."""
    rendered = _pdp_html_with_state(53855, name="Tênis Aramis Icon Light")
    url = "https://www.netshoes.com.br/p/tenis-aramis-icon-light-G06-75I1-006"

    with patch(
        "services.engines.netshoes_engine.AsyncSession",
        return_value=_mock_curl_session(403),
    ), patch.object(engine, "_render_pdp_html", return_value=rendered) as mock_render:
        product = asyncio.run(engine.get_pdp_product(url))

    mock_render.assert_called_once_with(url)
    assert product is not None, "403 deve cair no fallback Playwright, não em None"
    assert product["price_full"] == 538.55
    assert product["raw_title"] == "Tênis Aramis Icon Light"
    assert product["brand"] == "netshoes"


def test_get_pdp_product_403_and_playwright_blocked_returns_none_with_warning(caplog):
    """403 no curl_cffi + Playwright também bloqueado (None) → retorna None e loga WARNING
    nomeando o engine (anti-bot persistente exige iteração ao vivo)."""
    url = "https://www.netshoes.com.br/p/tenis-x"

    with patch(
        "services.engines.netshoes_engine.AsyncSession",
        return_value=_mock_curl_session(403),
    ), patch.object(engine, "_render_pdp_html", return_value=None):
        import logging
        with caplog.at_level(logging.WARNING):
            product = asyncio.run(engine.get_pdp_product(url))

    assert product is None
    assert any("Netshoes PDP" in rec.message for rec in caplog.records), (
        "deve logar um WARNING nomeando a Netshoes PDP"
    )


def test_get_pdp_product_200_success_no_playwright():
    """200 OK com __INITIAL_STATE__ válido → NÃO aciona Playwright (caminho feliz)."""
    html = _pdp_html_with_state(19990)
    with patch(
        "services.engines.netshoes_engine.AsyncSession",
        return_value=_mock_curl_session(200, html),
    ), patch.object(engine, "_render_pdp_html") as mock_render:
        product = asyncio.run(engine.get_pdp_product("https://www.netshoes.com.br/p/x"))

    mock_render.assert_not_called()
    assert product["price_full"] == 199.9


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
