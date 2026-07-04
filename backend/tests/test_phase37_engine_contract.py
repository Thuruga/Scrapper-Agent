from __future__ import annotations

import asyncio
import copy
import textwrap
from types import SimpleNamespace

import services.vtex_api_scraper as vtex_module
from services.engines.amazon_engine import AmazonEngine
from services.engines.sfcc_parser import parse_pdp
from services.engines.wake_engine import WakeEngine
from services.engines.zara_parser import parse_tile_products
from services.product_contract import build_canonical_product_row
from services.shopify_api_client import ShopifyApiClient
from services.vtex_api_scraper import VtexApiClient


VTEX_PRODUCT = {
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
    "allSpecifications": ["Cor", "Composição", "Código do produto"],
    "Cor": ["Azul"],
    "Composição": ["100% Algodão"],
    "Código do produto": ["REF-123"],
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


SFCC_PDP_HTML = textwrap.dedent(
    """\
    <!doctype html>
    <html>
    <head>
      <meta property="og:title" content="Polo Petit Pique" />
      <meta property="og:image" content="https://www.lacoste.com.br/img/polo.jpg" />
      <meta property="og:description" content="Polo masculina." />
      <script type="application/ld+json">
      {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": "Polo Petit Pique",
        "brand": {"@type": "Brand", "name": "Lacoste"},
        "description": "Polo masculina.",
        "image": ["https://www.lacoste.com.br/img/polo.jpg"],
        "aggregateRating": {
          "@type": "AggregateRating",
          "ratingValue": "4.8",
          "reviewCount": "208"
        },
        "offers": {
          "@type": "Offer",
          "price": 799.0,
          "priceCurrency": "BRL",
          "availability": "https://schema.org/InStock"
        }
      }
      </script>
    </head>
    <body></body>
    </html>
    """
)


ZARA_TILE_HTML = textwrap.dedent(
    """\
    <!doctype html>
    <html>
    <body>
      <li class="product-grid-product _product" data-productid="503417392">
        <div class="product-grid-product__figure">
          <a class="product-link product-grid-product__link link"
             href="https://www.zara.com/br/pt/camisa-de-linho-p01063407.html">
            <img
              class="media-image__image"
              src="https://static.zara.net/assets/camisa-linho.jpg?w=195"
              alt="Camisa branca de manga longa" />
          </a>
        </div>
        <div class="product-grid-product__data">
          <a class="product-link _item product-grid-product-info__name link"
             href="https://www.zara.com/br/pt/camisa-de-linho-p01063407.html">
            CAMISA DE LINHO
          </a>
          <div class="product-grid-product-info__product-price price">
            <span class="money-amount__main">R$ 279,00</span>
          </div>
        </div>
      </li>
    </body>
    </html>
    """
)


AMAZON_PDP_HTML = (
    "<html><body>"
    '<span id="productTitle">Tênis Aramis Runner</span>'
    '<div id="corePrice_feature_div">'
    '<span class="a-price"><span class="a-offscreen">R$ 249,00</span></span>'
    "</div>"
    '<img id="landingImage" src="https://m.media-amazon.com/img.jpg">'
    '<div id="availability"><span>Em estoque</span></div>'
    "</body></html>"
)


def test_vtex_maps_visible_product_code_and_additive_aliases(monkeypatch):
    async def fake_review(brand_key, product_id):
        return (4.5, 120)

    async def fake_color_family(domain, product_id):
        return ["PRETO", "AZUL"]

    monkeypatch.setattr(vtex_module, "get_single_review", fake_review)
    client = VtexApiClient(brand_name="Aramis")
    monkeypatch.setattr(client, "_get_color_family", fake_color_family)

    result = asyncio.run(
        client.parse_product_dict(
            copy.deepcopy(VTEX_PRODUCT),
            "https://www.aramis.com.br/camisa-polo-aramis-piquet/p",
            "www.aramis.com.br",
        )
    )

    assert result is not None
    row = build_canonical_product_row(result)
    assert row["composition"] == "100% Algodão"
    assert row["product_code"] == "REF-123"
    assert result.specifications["Código do produto"] == "REF-123"
    assert result.specifications["product_code"] == "REF-123"
    assert result.specifications["composition"] == "100% Algodão"


def test_shopify_promotes_available_colors_sizes_and_category(monkeypatch):
    monkeypatch.setattr(
        "services.shopify_api_client.brand_service.get_brand",
        lambda brand_key: SimpleNamespace(domain="www.aramis.com.br"),
    )
    client = ShopifyApiClient("aramis")

    bronze = client._map_to_bronze(
        {
            "handle": "camisa-linho",
            "title": "Camisa Linho",
            "body_html": "<p>Camisa em linho.</p>",
            "vendor": "Aramis",
            "product_type": "Camisas",
            "tags": ["linho", "casual"],
            "options": [
                {"name": "Cor", "position": 1, "values": ["Azul", "Branco"]},
                {"name": "Tamanho", "position": 2, "values": ["M", "G"]},
            ],
            "variants": [
                {
                    "available": True,
                    "price": "199.90",
                    "compare_at_price": "299.90",
                    "option1": "Azul",
                    "option2": "M",
                    "title": "Azul / M",
                },
                {
                    "available": True,
                    "price": "199.90",
                    "compare_at_price": "299.90",
                    "option1": "Branco",
                    "option2": "G",
                    "title": "Branco / G",
                },
            ],
            "images": [{"src": "https://www.aramis.com.br/img/camisa.jpg"}],
        },
        "Camisas",
    )

    assert bronze is not None
    row = build_canonical_product_row(bronze)
    assert sorted(row["available_colors"]) == ["Azul", "Branco"]
    assert sorted(row["available_sizes"]) == ["G", "M"]
    assert row["category"] == "Camisas"
    assert row["product_code"] is None


def test_wake_sparse_node_keeps_truthful_blanks():
    product = WakeEngine._node_to_dict(
        {
            "productName": "Camisa Slim Richards",
            "aliasComplete": "produto/camisa-slim-123",
            "prices": {"price": 799.0},
            "images": [{"url": "https://www.richards.com.br/img/camisa.jpg"}],
            "available": True,
        },
        "www.richards.com.br",
        "Richards",
    )

    assert product is not None
    row = build_canonical_product_row(product)
    assert row["product_name"] == "Camisa Slim Richards"
    assert row["product_code"] is None
    assert row["composition"] is None
    assert row["category"] is None


def test_sfcc_parser_surfaces_rating_and_review_count():
    parsed = parse_pdp(
        SFCC_PDP_HTML,
        "https://www.lacoste.com.br/polo-petit-pique/L12120/p",
    )

    assert parsed is not None
    row = build_canonical_product_row(parsed)
    assert row["product_name"] == "Polo Petit Pique"
    assert row["rating"] == 4.8
    assert row["review_count"] == 208


def test_zara_parser_keeps_sparse_fields_blank():
    products = parse_tile_products(ZARA_TILE_HTML)

    assert len(products) == 1
    row = build_canonical_product_row(products[0])
    assert row["product_name"] == "CAMISA DE LINHO"
    assert row["product_code"] is None
    assert row["composition"] is None


def test_marketplace_product_does_not_invent_product_code_or_composition():
    product = AmazonEngine()._parse_pdp_html(
        AMAZON_PDP_HTML,
        "https://www.amazon.com.br/dp/B0FZD1GZHN",
    )

    assert product is not None
    row = build_canonical_product_row(product)
    assert row["product_name"] == "Tênis Aramis Runner"
    assert row["product_code"] is None
    assert row["composition"] is None
