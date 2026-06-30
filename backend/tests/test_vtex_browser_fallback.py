"""Hermetic tests for the VTEX browser-fallback product extraction (Phase 39 gap
closure). Covers the VTEX-IO Intelligent-Search DOM-tile parser used for Hugo Boss,
the BRL price parser (char-spaced render), the legacy ROOT_QUERY parser, and the
model-invariant guard (skip tiles missing price/image/title instead of crashing).

Zero network: parsers operate on canned HTML; the 2-render orchestration test mocks
browser_manager.fetch_html. No live VTEX calls.
"""
import asyncio
import json
from unittest.mock import AsyncMock, patch

from core.models import RawProductBronze
from services.vtex_api_scraper import VtexApiClient
import services.vtex_api_scraper as scraper_mod

DOMAIN = "www.hugoboss.com.br"

# Rendered VTEX-IO category page with two complete product-summary tiles (Hugo Boss
# shape). Price digits are char-spaced exactly as the live storefront renders them.
TILES_HTML = """
<html><body>
  <div class="vtex-product-summary-2-x-container">
    <a class="vtex-product-summary-2-x-clearLink" href="/camisa-slim-50550/p" aria-label="Camisa Slim">
      <span class="vtex-product-summary-2-x-productBrand">Camisa De Ajuste Slim Em Algodão</span>
      <img src="https://hb.img/camisa.jpg"/>
    </a>
    <span class="vtex-product-price-1-x-sellingPriceValue">R$ 1 . 460 , 00</span>
  </div>
  <div class="vtex-product-summary-2-x-container">
    <a href="/polo-paddy-50559/p">
      <span class="vtex-product-summary-2-x-productBrand">Polo Paddy Com Logo</span>
      <img src="https://hb.img/polo.jpg"/>
    </a>
    <span class="vtex-product-price-1-x-sellingPriceValue">R$ 920 , 00</span>
  </div>
</body></html>
"""

# An empty / "no products" category page (the real /masculino/roupas/polos shape):
# no product-summary tiles and no ROOT_QUERY blob.
EMPTY_HTML = "<html><body><h1>Polos</h1><p>nenhum resultado</p></body></html>"


def _make_client():
    # Sync parser methods need only brand_name; no session / no network.
    return VtexApiClient("hugoboss")


def _rootquery_html(name="Camisa Y", price=100.0):
    blob = {
        "ROOT_QUERY": {},
        "Product:1": {"productId": "1", "productName": name, "linkText": name.lower().replace(" ", "-"),
                      "items": [{"id": "Item:1"}]},
        "Item:1": {"images": [{"id": "Img:1"}], "sellers": [{"id": "Seller:1"}]},
        "Img:1": {"imageUrl": "https://hb.img/y.jpg"},
        "Seller:1": {"commertialOffer": {"id": "Offer:1"}},
        "Offer:1": {"Price": price},
    }
    return "<script>" + json.dumps(blob) + "</script>"


def test_parse_vtexio_tiles_extracts_real_products():
    client = _make_client()
    products = client._parse_vtexio_tiles(TILES_HTML, DOMAIN)
    assert len(products) == 2
    assert all(isinstance(p, RawProductBronze) for p in products)

    by_title = {p.raw_title: p for p in products}
    assert "Camisa De Ajuste Slim Em Algodão" in by_title
    assert "Polo Paddy Com Logo" in by_title

    camisa = by_title["Camisa De Ajuste Slim Em Algodão"]
    assert camisa.url.startswith("https://www.hugoboss.com.br/")
    assert "/camisa-slim-50550/p" in camisa.url
    assert camisa.price_full == 1460.0
    assert camisa.image_url == "https://hb.img/camisa.jpg"

    polo = by_title["Polo Paddy Com Logo"]
    assert polo.price_full == 920.0
    assert "/polo-paddy-50559/p" in polo.url


def test_parse_vtexio_tiles_distinct_per_category_no_crossbleed():
    """Different tile sets must yield disjoint product URLs (regression guard against
    the map=c,c,c failure that returned identical generic products for every category)."""
    client = _make_client()
    camisas = client._parse_vtexio_tiles(TILES_HTML, DOMAIN)
    polos_html = TILES_HTML.replace("camisa-slim-50550", "polo-x-111").replace("polo-paddy-50559", "polo-y-222")
    polos = client._parse_vtexio_tiles(polos_html, DOMAIN)
    assert {p.url for p in camisas}.isdisjoint({p.url for p in polos})


def test_parse_vtexio_tiles_empty_page_returns_nothing():
    client = _make_client()
    assert client._parse_vtexio_tiles(EMPTY_HTML, DOMAIN) == []


def test_parse_vtexio_tiles_skips_incomplete_tiles_without_crashing():
    """A tile missing price OR image must be skipped (model invariants), not crash the scan."""
    client = _make_client()
    html = """
    <div class="vtex-product-summary-2-x-container">
      <a href="/no-image-1/p"><span class="vtex-product-summary-2-x-productBrand">Sem Imagem</span></a>
      <span class="vtex-product-price-1-x-sellingPriceValue">R$ 100 , 00</span>
    </div>
    <div class="vtex-product-summary-2-x-container">
      <a href="/no-price-2/p"><span class="vtex-product-summary-2-x-productBrand">Sem Preço</span><img src="https://hb.img/x.jpg"/></a>
    </div>
    """
    assert client._parse_vtexio_tiles(html, DOMAIN) == []


def test_parse_brl_price_handles_char_spaced_render():
    f = VtexApiClient._parse_brl_price
    assert f("R$ 1 . 460 , 00") == 1460.0
    assert f("R$ 920 , 00") == 920.0
    assert f("R$1.460,00") == 1460.0
    assert f("R$ 99,90") == 99.90
    assert f("") == 0.0
    assert f("Indisponível") == 0.0


def test_parse_root_query_still_parses_legacy_blob():
    """Legacy ROOT_QUERY Apollo-blob parsing must keep working (no regression)."""
    client = _make_client()
    products = client._parse_root_query(_rootquery_html("Camisa Y", 100.0), DOMAIN, f"https://{DOMAIN}/cat")
    assert len(products) == 1
    assert products[0].raw_title == "Camisa Y"
    assert products[0].price_full == 100.0
    assert "/camisa-y/p" in products[0].url


def test_browser_fallback_prefers_dom_tiles_when_rootquery_empty():
    """The 2-render orchestration: render 1 (no ROOT_QUERY) -> render 2 (DOM tiles)."""
    client = _make_client()
    fake_fetch = AsyncMock(side_effect=[EMPTY_HTML, TILES_HTML])
    with patch.object(scraper_mod.browser_manager, "fetch_html", new=fake_fetch):
        products = asyncio.run(
            client._browser_fallback_products(f"https://{DOMAIN}/masculino/roupas/camisas", DOMAIN)
        )
    assert fake_fetch.await_count == 2  # ROOT_QUERY render then networkidle DOM render
    assert len(products) == 2
    assert {p.price_full for p in products} == {1460.0, 920.0}


def test_browser_fallback_uses_rootquery_without_second_render():
    """If ROOT_QUERY yields products, the DOM render is skipped entirely (no waste/regression)."""
    client = _make_client()
    fake_fetch = AsyncMock(side_effect=[_rootquery_html("Camisa Z", 150.0), TILES_HTML])
    with patch.object(scraper_mod.browser_manager, "fetch_html", new=fake_fetch):
        products = asyncio.run(client._browser_fallback_products(f"https://{DOMAIN}/cat", DOMAIN))
    assert fake_fetch.await_count == 1  # only the first render happened
    assert len(products) == 1
    assert products[0].raw_title == "Camisa Z"
