"""Pure parsers for Zara/Inditex rendered pages.

Zara BR pages expose useful product data in two shapes:
  - category pages: JSON-LD ItemList with product name, image, URL and price.
  - search pages: rendered product tiles with title, URL, prices and image.

This module has no network or browser dependency so it can be tested with small
fixtures. The engine is responsible for fetching rendered HTML.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from services.promotion_parser import derive_discount_promotions

_BR_MONEY_RE = re.compile(
    r"R\$\s*([\d]{1,3}(?:\.[\d]{3})*,[\d]{2}|[\d]+,[\d]{2})"
)


def parse_price_br(value: Any) -> Optional[float]:
    """Parse Brazilian Real prices from Zara HTML/JSON-LD."""
    if isinstance(value, (int, float)):
        parsed = float(value)
        return parsed if parsed > 0 else None

    if not isinstance(value, str):
        return None

    stripped = value.strip()
    if not stripped:
        return None

    try:
        parsed = float(stripped)
        return parsed if parsed > 0 else None
    except ValueError:
        pass

    match = _BR_MONEY_RE.search(stripped)
    if not match:
        return None

    normalized = match.group(1).replace(".", "").replace(",", ".")
    try:
        parsed = float(normalized)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _absolute_url(url: str, base_url: str = "https://www.zara.com") -> str:
    if not url:
        return ""
    if url.startswith("//"):
        return f"https:{url}"
    return urljoin(base_url, url)


def _first_offer(product: Dict[str, Any]) -> Dict[str, Any]:
    offers = product.get("offers")
    if isinstance(offers, list):
        return offers[0] if offers else {}
    return offers if isinstance(offers, dict) else {}


def _aggregate_rating(product: Dict[str, Any]) -> tuple[Optional[float], Optional[int]]:
    raw = product.get("aggregateRating")
    if not isinstance(raw, dict):
        return None, None
    rating = None
    count = None
    try:
        if raw.get("ratingValue") is not None:
            rating = round(float(str(raw.get("ratingValue")).replace(",", ".")), 1)
    except (TypeError, ValueError):
        rating = None
    for key in ("reviewCount", "ratingCount"):
        try:
            if raw.get(key) is not None:
                count = int(str(raw.get(key)).replace(".", ""))
                break
        except (TypeError, ValueError):
            continue
    return rating, count


def _product_dict(
    *,
    name: str,
    url: str,
    image_url: Optional[str],
    price_full: Optional[float],
    brand: str,
    price_discount: Optional[float] = None,
    available: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    name = (name or "").strip()
    url = (url or "").strip()
    if not name or not url or not price_full or not image_url:
        return None

    return {
        "url": url,
        "brand": brand,
        "raw_title": name,
        "raw_description": name,
        "price_full": price_full,
        "price_discount": price_discount,
        "promotions": [
            promo.model_dump(mode="json")
            for promo in derive_discount_promotions(price_full, price_discount)
        ],
        "stock_availability": available,
        "image_url": image_url,
        "available_colors": [],
        "available_sizes": [],
        "specifications": {},
    }


def _jsonld_blocks(soup: BeautifulSoup) -> Iterable[Any]:
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            yield json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue


def parse_itemlist_products(
    html: str,
    *,
    brand: str = "Zara",
    base_url: str = "https://www.zara.com",
) -> List[Dict[str, Any]]:
    """Extract products from Zara category ItemList JSON-LD."""
    soup = BeautifulSoup(html, "html.parser")
    products: List[Dict[str, Any]] = []

    for block in _jsonld_blocks(soup):
        if not isinstance(block, dict) or block.get("@type") != "ItemList":
            continue

        for entry in block.get("itemListElement", []):
            if not isinstance(entry, dict):
                continue
            item = entry.get("item")
            if not isinstance(item, dict):
                continue

            offer = _first_offer(item)
            url = (
                offer.get("url")
                or item.get("url")
                or ""
            )
            image = item.get("image")
            if isinstance(image, list):
                image_url = str(image[0]).strip() if image else None
            else:
                image_url = str(image).strip() if image else None

            product = _product_dict(
                name=str(item.get("name") or ""),
                url=_absolute_url(str(url), base_url),
                image_url=_absolute_url(image_url or "", base_url),
                price_full=parse_price_br(offer.get("price")),
                brand=brand,
                available=None,
            )
            if product:
                rating, review_count = _aggregate_rating(item)
                product["rating"] = rating
                product["review_count"] = review_count
                products.append(product)

    return products


def _tile_prices(tile: Any) -> tuple[Optional[float], Optional[float]]:
    """Return (price_full, price_discount) from a rendered Zara tile."""
    current = None
    current_node = tile.select_one(".price-current__amount")
    if current_node:
        current = parse_price_br(current_node.get_text(" ", strip=True))

    prices: List[float] = []
    for node in tile.select(".money-amount__main"):
        parsed = parse_price_br(node.get_text(" ", strip=True))
        if parsed is not None:
            prices.append(parsed)

    if current is None and prices:
        current = prices[-1]

    unique_prices = []
    for price in prices:
        if price not in unique_prices:
            unique_prices.append(price)

    if len(unique_prices) >= 2 and current is not None:
        original = max(unique_prices)
        if original > current:
            return original, current

    return current, None


def parse_tile_products(
    html: str,
    *,
    brand: str = "Zara",
    base_url: str = "https://www.zara.com",
) -> List[Dict[str, Any]]:
    """Extract products from rendered Zara search/category tiles."""
    soup = BeautifulSoup(html, "html.parser")
    products: List[Dict[str, Any]] = []

    for tile in soup.select(".product-grid-product"):
        name_link = tile.select_one(".product-grid-product-info__name[href]")
        figure_link = tile.select_one(".product-grid-product__link[href]")
        link = name_link or figure_link
        if not link:
            continue

        title = name_link.get_text(" ", strip=True) if name_link else ""
        if not title:
            heading = tile.select_one("h3")
            title = heading.get_text(" ", strip=True) if heading else ""
        if not title:
            continue

        image_url = None
        img = tile.select_one("img[src]")
        if img and img.get("src"):
            image_url = _absolute_url(img["src"].strip(), base_url)

        price_full, price_discount = _tile_prices(tile)
        text = tile.get_text(" ", strip=True).lower()
        available = False if "esgotado" in text else True

        product = _product_dict(
            name=title,
            url=_absolute_url(link.get("href", ""), base_url),
            image_url=image_url,
            price_full=price_full,
            price_discount=price_discount,
            brand=brand,
            available=available,
        )
        if product:
            product_id = tile.get("data-productid")
            if product_id:
                product["shipping_product_id"] = product_id
            products.append(product)

    return products


def parse_product_detail(
    html: str,
    source_url: str,
    *,
    brand: str = "Zara",
    base_url: str = "https://www.zara.com",
) -> Optional[Dict[str, Any]]:
    """Extract a single product from a Zara PDP."""
    soup = BeautifulSoup(html, "html.parser")

    for block in _jsonld_blocks(soup):
        if not isinstance(block, dict) or block.get("@type") not in ("Product", "ProductGroup"):
            continue

        offer = _first_offer(block)
        image = block.get("image")
        if isinstance(image, list):
            image_url = str(image[0]).strip() if image else None
        else:
            image_url = str(image).strip() if image else None

        product = _product_dict(
            name=str(block.get("name") or ""),
            url=source_url,
            image_url=_absolute_url(image_url or "", base_url),
            price_full=parse_price_br(offer.get("price")),
            brand=brand,
            available=None,
        )
        if product:
            rating, review_count = _aggregate_rating(block)
            product["rating"] = rating
            product["review_count"] = review_count
        return product

    og_title = soup.find("meta", property="og:title")
    og_image = soup.find("meta", property="og:image")
    return _product_dict(
        name=og_title.get("content", "") if og_title else "",
        url=source_url,
        image_url=_absolute_url(og_image.get("content", "") if og_image else "", base_url),
        price_full=parse_price_br(soup.get_text(" ", strip=True)),
        brand=brand,
        available=None,
    )


def parse_products(
    html: str,
    *,
    brand: str = "Zara",
    base_url: str = "https://www.zara.com",
) -> List[Dict[str, Any]]:
    """Extract products from every known Zara listing shape, deduped by URL."""
    products = [
        *parse_tile_products(html, brand=brand, base_url=base_url),
        *parse_itemlist_products(html, brand=brand, base_url=base_url),
    ]

    seen: set[str] = set()
    deduped: List[Dict[str, Any]] = []
    for product in products:
        canonical = product["url"].split("?")[0].rstrip("/")
        if canonical in seen:
            continue
        seen.add(canonical)
        deduped.append(product)
    return deduped


def parse_nav_categories(html: str) -> List[Dict[str, Any]]:
    """Extract Zara category links from a rendered navigation/menu page."""
    soup = BeautifulSoup(html, "html.parser")
    noise = {
        "ver tudo",
        "the new",
        "nova colecao",
        "colecao",
        "saldo",
        "01 collection",
        "02 colecao",
        "02 sapatos | acessorios",
        "homem",
    }

    seen: set[str] = set()
    categories: List[Dict[str, Any]] = []
    for anchor in soup.select('a[href*="/br/pt/man-"]'):
        label = anchor.get_text(" ", strip=True)
        href = anchor.get("href", "")
        if not label or len(label) <= 2:
            continue
        label_key = label.lower().strip()
        if label_key in noise:
            continue

        path = _absolute_url(href).replace("https://www.zara.com", "")
        if not path.startswith("/br/pt/") or path in seen:
            continue
        seen.add(path)
        categories.append({"name": label, "path": path, "id": path})

    return categories
