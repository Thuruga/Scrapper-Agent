"""
Testes da extração de PDP da Amazon (get_pdp_product / _parse_pdp_html).

REGRESSÃO (monitor-marketplace-pendente Round 2, hypothesis_C): a Amazon passava
pelo Playwright mas NÃO extraía preço e NÃO logava nada — o monitor ficava
"Pendente" silenciosamente. Estes testes cobrem:
  - o seletor de preço do layout ATUAL (#corePriceDisplay .a-price .a-offscreen)
  - o seletor de preço de layouts antigos (#priceblock_ourprice)
  - o WARNING explícito quando título/preço não são extraídos (diagnosticável)

Não há I/O de rede: _parse_pdp_html/_extract_pdp_price recebem HTML já obtido.
"""
import logging

from bs4 import BeautifulSoup

from services.engines.amazon_engine import AmazonEngine


engine = AmazonEngine()


def _pdp_html(title: str, price_block: str, image: bool = True) -> str:
    img = '<img id="landingImage" src="https://m.media-amazon.com/img.jpg">' if image else ""
    return (
        f"<html><body>"
        f'<span id="productTitle">{title}</span>'
        f"{price_block}"
        f"{img}"
        f'<div id="availability"><span>Em estoque</span></div>'
        f"</body></html>"
    )


# ---------------------------------------------------------------------------
# _extract_pdp_price — cobre os layouts de preço da PDP
# ---------------------------------------------------------------------------

def test_extract_price_modern_core_price_display():
    """Layout atual: #corePriceDisplay_desktop_feature_div .a-price .a-offscreen."""
    block = (
        '<div id="corePriceDisplay_desktop_feature_div">'
        '<span class="a-price" data-a-color="price">'
        '<span class="a-offscreen">R$ 1.299,90</span>'
        '<span aria-hidden="true">R$1.299,90</span>'
        "</span></div>"
    )
    soup = BeautifulSoup(_pdp_html("Camisa Aramis", block), "html.parser")
    assert engine._extract_pdp_price(soup) == 1299.90


def test_extract_price_legacy_priceblock_ourprice():
    """Layout antigo: #priceblock_ourprice."""
    block = '<span id="priceblock_ourprice">R$ 299,90</span>'
    soup = BeautifulSoup(_pdp_html("Camisa Aramis", block), "html.parser")
    assert engine._extract_pdp_price(soup) == 299.90


def test_extract_price_fallback_broad_a_offscreen():
    """Fallback amplo: span.a-price span.a-offscreen sem contêiner conhecido."""
    block = '<span class="a-price"><span class="a-offscreen">R$ 89,90</span></span>'
    soup = BeautifulSoup(_pdp_html("Meia Aramis", block), "html.parser")
    assert engine._extract_pdp_price(soup) == 89.90


def test_extract_price_absent_returns_none():
    """Sem nenhum contêiner de preço → None."""
    soup = BeautifulSoup(_pdp_html("Produto Sem Preço", "", image=False), "html.parser")
    assert engine._extract_pdp_price(soup) is None


# ---------------------------------------------------------------------------
# _parse_pdp_html — produto completo + logging quando extração falha
# ---------------------------------------------------------------------------

def test_parse_pdp_html_full_product():
    block = (
        '<div id="corePrice_feature_div">'
        '<span class="a-price"><span class="a-offscreen">R$ 249,00</span></span>'
        "</div>"
    )
    html = _pdp_html("Tênis Aramis Runner", block)
    product = engine._parse_pdp_html(html, "https://www.amazon.com.br/dp/B0FZD1GZHN")
    assert product is not None
    assert product["price_full"] == 249.00
    assert product["raw_title"] == "Tênis Aramis Runner"
    assert product["brand"] == "amazon"
    assert product["image_url"].startswith("https://")


def test_parse_pdp_html_no_price_returns_none_and_logs_warning(caplog):
    """REGRESSÃO hypothesis_C: título presente mas SEM preço → None + WARNING nomeando
    o engine/URL (antes era silencioso, deixando o monitor 'Pendente' sem pista)."""
    html = _pdp_html("Produto Sem Preço Visível", "", image=False)
    with caplog.at_level(logging.WARNING):
        product = engine._parse_pdp_html(html, "https://www.amazon.com.br/dp/XYZ")

    assert product is None
    assert any(
        "Amazon _parse_pdp_html" in rec.message and "XYZ" in rec.message
        for rec in caplog.records
    ), "deve logar um WARNING diagnosticável nomeando a extração incompleta da Amazon"
