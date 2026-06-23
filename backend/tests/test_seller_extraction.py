"""
Testes offline do módulo services/engines/seller_extraction.py.

Cobrem:
  - is_marketplace_default: helper de precedência (None, vazio, defaults conhecidos, seller real)
  - parse_ml_seller_from_html: extração de seller para Mercado Livre (seletores CSS + JSON state)
  - parse_amazon_seller_from_html: extração de seller para Amazon (seletores CSS)

Estilo: funções test_*, sem pytest-asyncio, sem rede (fixtures HTML inline mínimas).
"""
from services.engines.seller_extraction import (
    MARKETPLACE_DEFAULT_SELLER,
    ALL_DEFAULT_SELLERS,
    is_marketplace_default,
    parse_ml_seller_from_html,
    parse_amazon_seller_from_html,
)


# ---------------------------------------------------------------------------
# Constantes e estrutura
# ---------------------------------------------------------------------------

def test_marketplace_default_seller_has_expected_keys():
    assert "Mercado Livre" in MARKETPLACE_DEFAULT_SELLER
    assert "Amazon" in MARKETPLACE_DEFAULT_SELLER
    assert "Netshoes" in MARKETPLACE_DEFAULT_SELLER


def test_all_default_sellers_is_set_of_normalized_strings():
    assert isinstance(ALL_DEFAULT_SELLERS, set)
    # Todos os valores devem estar normalizados (lowercase, sem acentos, sem espaços extras)
    for s in ALL_DEFAULT_SELLERS:
        assert s == s.strip().lower(), f"Valor não normalizado em ALL_DEFAULT_SELLERS: {repr(s)}"


# ---------------------------------------------------------------------------
# is_marketplace_default
# ---------------------------------------------------------------------------

def test_none_is_default():
    assert is_marketplace_default(None) is True


def test_empty_string_is_default():
    assert is_marketplace_default("") is True


def test_whitespace_only_is_default():
    assert is_marketplace_default("   ") is True


def test_amazon_exact_is_default():
    assert is_marketplace_default("Amazon") is True


def test_amazon_lowercase_is_default():
    assert is_marketplace_default("amazon") is True


def test_mercado_livre_exact_is_default():
    assert is_marketplace_default("Mercado Livre") is True


def test_mercado_livre_with_spaces_is_default():
    assert is_marketplace_default(" Mercado Livre ") is True


def test_netshoes_is_default():
    assert is_marketplace_default("Netshoes") is True


def test_netshoes_lowercase_is_default():
    assert is_marketplace_default("netshoes") is True


def test_shoestime_is_not_default():
    assert is_marketplace_default("Shoestime") is False


def test_third_party_loja_is_not_default():
    assert is_marketplace_default("Loja XPTO") is False


def test_any_marketplace_default_is_flagged_regardless_of_marketplace_arg():
    # "Amazon" é default mesmo quando marketplace="Mercado Livre"
    assert is_marketplace_default("Amazon", "Mercado Livre") is True


def test_real_seller_with_marketplace_arg_is_not_default():
    assert is_marketplace_default("Shoestime", "Amazon") is False


def test_real_seller_with_accent_is_not_default():
    assert is_marketplace_default("Lojas Americanas") is False


# ---------------------------------------------------------------------------
# parse_ml_seller_from_html — Mercado Livre
# ---------------------------------------------------------------------------

def _ml_html_with_link_trigger_span(seller_name: str) -> str:
    return f"""
    <html><body>
      <div class="ui-pdp-seller">
        <span class="ui-pdp-seller__link-trigger">
          <span>{seller_name}</span>
        </span>
      </div>
    </body></html>
    """


def _ml_html_with_header_title(raw_text: str) -> str:
    return f"""
    <html><body>
      <div class="ui-pdp-seller__header__title">{raw_text}</div>
    </body></html>
    """


def _ml_html_with_official_store_name_json(store_name: str) -> str:
    return f"""
    <html><body>
      <script>
        window.__PRELOADED_STATE__ = {{"official_store_name":"{store_name}","other":"value"}};
      </script>
    </body></html>
    """


def _ml_html_direct_sale_no_seller() -> str:
    return """
    <html><body>
      <div class="ui-pdp-price">R$ 199,00</div>
      <p>Venda direta pelo marketplace sem lojista terceira.</p>
    </body></html>
    """


def test_ml_link_trigger_span_returns_seller_name():
    html = _ml_html_with_link_trigger_span("Loja Nike Oficial")
    result = parse_ml_seller_from_html(html)
    assert result == "Loja Nike Oficial"


def test_ml_header_title_with_vendido_por_prefix():
    html = _ml_html_with_header_title("Vendido por Loja X")
    result = parse_ml_seller_from_html(html)
    assert result == "Loja X"


def test_ml_header_title_with_por_prefix():
    html = _ml_html_with_header_title("por Loja Exemplo")
    result = parse_ml_seller_from_html(html)
    assert result == "Loja Exemplo"


def test_ml_header_title_with_loja_oficial_prefix():
    html = _ml_html_with_header_title("Loja oficial Nike")
    result = parse_ml_seller_from_html(html)
    assert result == "Nike"


def test_ml_official_store_name_json_fallback():
    html = _ml_html_with_official_store_name_json("Loja Y")
    result = parse_ml_seller_from_html(html)
    assert result == "Loja Y"


def test_ml_direct_sale_returns_none():
    html = _ml_html_direct_sale_no_seller()
    result = parse_ml_seller_from_html(html)
    assert result is None


def test_ml_never_returns_marketplace_default():
    # HTML que só contém "Mercado Livre" como seller → deve retornar None
    html = _ml_html_with_link_trigger_span("Mercado Livre")
    result = parse_ml_seller_from_html(html)
    assert result is None


def test_ml_link_trigger_button_span():
    html = """
    <html><body>
      <button class="ui-pdp-seller__link-trigger-button">
        <span>Shoestime</span>
      </button>
    </body></html>
    """
    result = parse_ml_seller_from_html(html)
    assert result == "Shoestime"


def test_ml_action_modal_link():
    html = """
    <html><body>
      <a class="ui-pdp-action-modal__link">
        <span>Loja Parceira</span>
      </a>
    </body></html>
    """
    result = parse_ml_seller_from_html(html)
    assert result == "Loja Parceira"


def test_ml_loja_href_link():
    html = """
    <html><body>
      <a href="https://www.mercadolivre.com.br/loja/lojaexemplo">Loja Exemplo</a>
    </body></html>
    """
    result = parse_ml_seller_from_html(html)
    assert result == "Loja Exemplo"


def test_ml_empty_html_returns_none():
    result = parse_ml_seller_from_html("")
    assert result is None


# ---------------------------------------------------------------------------
# parse_amazon_seller_from_html — Amazon
# ---------------------------------------------------------------------------

def _amazon_html_with_seller_profile(seller_name: str) -> str:
    return f"""
    <html><body>
      <a id="sellerProfileTriggerId">{seller_name}</a>
    </body></html>
    """


def _amazon_html_with_merchant_info_link(seller_name: str) -> str:
    return f"""
    <html><body>
      <div id="merchant-info">
        Vendido por <a href="/sp?seller=123">{seller_name}</a>
      </div>
    </body></html>
    """


def _amazon_html_with_merchant_info_text(seller_name: str) -> str:
    return f"""
    <html><body>
      <div id="merchant-info">Vendido por {seller_name}</div>
    </body></html>
    """


def _amazon_html_no_seller() -> str:
    return """
    <html><body>
      <div class="a-section">Produto sem lojista terceira exposta.</div>
    </body></html>
    """


def test_amazon_seller_profile_trigger():
    html = _amazon_html_with_seller_profile("Loja Parceira BR")
    result = parse_amazon_seller_from_html(html)
    assert result == "Loja Parceira BR"


def test_amazon_merchant_info_link():
    html = _amazon_html_with_merchant_info_link("Loja Z")
    result = parse_amazon_seller_from_html(html)
    assert result == "Loja Z"


def test_amazon_merchant_info_text_vendido_por():
    html = _amazon_html_with_merchant_info_text("Loja Z")
    result = parse_amazon_seller_from_html(html)
    assert result == "Loja Z"


def test_amazon_no_seller_returns_none():
    html = _amazon_html_no_seller()
    result = parse_amazon_seller_from_html(html)
    assert result is None


def test_amazon_never_returns_marketplace_default():
    # sellerProfileTriggerId mostrando "Amazon" → deve retornar None
    html = _amazon_html_with_seller_profile("Amazon")
    result = parse_amazon_seller_from_html(html)
    assert result is None


def test_amazon_tabular_buybox_seller():
    html = """
    <html><body>
      <div id="tabular-buybox">
        <span>Vendido por</span><span>Loja Premium</span>
      </div>
    </body></html>
    """
    result = parse_amazon_seller_from_html(html)
    assert result == "Loja Premium"


def test_amazon_empty_html_returns_none():
    result = parse_amazon_seller_from_html("")
    assert result is None
