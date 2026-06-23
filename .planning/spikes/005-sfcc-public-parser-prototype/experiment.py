"""
Standalone parser prototype for SFCC public browser observations.

This spike intentionally does not import the production application. It consumes
small offline fixtures derived from browser-rendered public pages and normalizes
them into a RawProductBronze-like dictionary so we can evaluate data quality
before creating any real engine.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


SPIKE_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURES_PATH = os.path.join(SPIKE_DIR, "fixtures.json")
RESULTS_PATH = os.path.join(SPIKE_DIR, "RESULTS.json")
REPORT_PATH = os.path.join(SPIKE_DIR, "REPORT.md")


@dataclass
class ParsedProduct:
    url: str
    brand: str
    raw_title: str
    raw_description: str
    price_full: Optional[float]
    price_discount: Optional[float] = None
    stock_availability: Optional[bool] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    composition: Optional[str] = None
    available_colors: List[str] = field(default_factory=list)
    available_sizes: List[str] = field(default_factory=list)
    rating: Optional[float] = None
    review_count: Optional[int] = None
    specifications: Dict[str, str] = field(default_factory=dict)
    image_url: Optional[str] = None
    source_id: str = ""
    source_type: str = ""
    quality: str = "unknown"
    missing_fields: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "brand": self.brand,
            "raw_title": self.raw_title,
            "raw_description": self.raw_description,
            "price_full": self.price_full,
            "price_discount": self.price_discount,
            "stock_availability": self.stock_availability,
            "category": self.category,
            "sub_category": self.sub_category,
            "composition": self.composition,
            "available_colors": self.available_colors,
            "available_sizes": self.available_sizes,
            "rating": self.rating,
            "review_count": self.review_count,
            "specifications": self.specifications,
            "image_url": self.image_url,
            "_source_id": self.source_id,
            "_source_type": self.source_type,
            "_quality": self.quality,
            "_missing_fields": self.missing_fields,
        }


def compact(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def first_present(*values: Any) -> Any:
    for value in values:
        if isinstance(value, str):
            if value.strip():
                return value.strip()
        elif value is not None:
            return value
    return None


def list_first(value: Any) -> Optional[str]:
    if isinstance(value, list):
        return compact(value[0]) if value else None
    return compact(value) if value else None


def brand_name(value: Any, fallback: str) -> str:
    if isinstance(value, dict):
        return compact(value.get("name")) or fallback
    return compact(value) or fallback


def parse_price(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value)
    match = re.search(r"(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)", text)
    if not match:
        return None
    number = match.group(1).replace(",", "")
    try:
        parsed = float(number)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def parse_discount_price(value: Any) -> Optional[float]:
    text = compact(value)
    if not text:
        return None
    lowered = text.lower()
    if "discount" not in lowered and "sale" not in lowered:
        return None
    return parse_price(text)


def parse_availability(value: Any) -> Optional[bool]:
    text = compact(value).lower()
    if not text:
        return None
    if "instock" in text or "in stock" in text:
        return True
    if "outofstock" in text or "out of stock" in text or "sold out" in text:
        return False
    return None


def offer_from(product: Dict[str, Any]) -> Dict[str, Any]:
    offers = product.get("offers")
    if isinstance(offers, list):
        return offers[0] if offers else {}
    return offers if isinstance(offers, dict) else {}


def clean_title(title: str, brand: str) -> str:
    title = compact(title)
    brand = compact(brand)
    if brand and title.lower().startswith(f"{brand.lower()} - "):
        return title[len(brand) + 3 :].strip()
    return title


def quality_for(product: ParsedProduct) -> str:
    required = {
        "url": product.url,
        "brand": product.brand,
        "raw_title": product.raw_title,
        "price_full": product.price_full,
        "image_url": product.image_url,
    }
    missing = [name for name, value in required.items() if value in (None, "")]
    product.missing_fields = missing
    if not missing:
        return "bronze_ready"
    if product.url and product.raw_title and product.price_full:
        return "needs_detail_page"
    return "insufficient"


def normalize_jsonld_product(
    observation: Dict[str, Any],
    product: Dict[str, Any],
) -> ParsedProduct:
    meta = observation.get("opengraph_meta") or {}
    offer = offer_from(product)
    brand = brand_name(product.get("brand"), observation.get("brand_hint", ""))
    raw_title = clean_title(first_present(product.get("name"), meta.get("og:title"), ""), brand)
    price_full = first_present(
        parse_price(offer.get("price")),
        parse_price(offer.get("lowPrice")),
        parse_price(meta.get("og:product:price:amount")),
        parse_price(observation.get("visible_price_text")),
    )
    price_discount = parse_discount_price(observation.get("visible_discount_price_text"))
    image_url = first_present(list_first(product.get("image")), meta.get("og:image"))
    color = first_present(product.get("color"), meta.get("og:product:color"))
    composition = first_present(product.get("material"), meta.get("og:product:material"))
    availability = first_present(offer.get("availability"), meta.get("og:product:availability"))

    parsed = ParsedProduct(
        url=first_present(product.get("url"), product.get("@id"), meta.get("og:url"), observation.get("source_url"), ""),
        brand=brand,
        raw_title=raw_title,
        raw_description=compact(first_present(product.get("description"), meta.get("og:description"), raw_title)),
        price_full=price_full,
        price_discount=price_discount,
        stock_availability=parse_availability(availability),
        category=observation.get("category_hint"),
        composition=composition,
        available_colors=[compact(color)] if color else [],
        specifications={k: v for k, v in {"schema_type": compact(product.get("@type"))}.items() if v},
        image_url=image_url,
        source_id=observation.get("id", ""),
        source_type=f"{observation.get('page_type', 'unknown')}:jsonld",
    )
    parsed.quality = quality_for(parsed)
    return parsed


def normalize_visible_card(observation: Dict[str, Any], card: Dict[str, Any]) -> ParsedProduct:
    price_full = parse_price(card.get("visible_price_text"))
    price_discount = parse_discount_price(card.get("visible_discount_price_text"))
    parsed = ParsedProduct(
        url=compact(card.get("url")),
        brand=compact(observation.get("brand_hint")),
        raw_title=compact(card.get("name")),
        raw_description=compact(card.get("name")),
        price_full=price_full,
        price_discount=price_discount,
        stock_availability=None,
        category=observation.get("category_hint"),
        image_url=list_first(card.get("image")),
        source_id=observation.get("id", ""),
        source_type=f"{observation.get('page_type', 'unknown')}:visible_card",
    )
    parsed.quality = quality_for(parsed)
    return parsed


def normalize_observation(observation: Dict[str, Any]) -> List[ParsedProduct]:
    normalized: List[ParsedProduct] = []
    for product in observation.get("jsonld_products") or []:
        normalized.append(normalize_jsonld_product(observation, product))
    for card in observation.get("visible_cards") or []:
        normalized.append(normalize_visible_card(observation, card))
    return normalized


def dedupe_products(products: Iterable[ParsedProduct]) -> List[ParsedProduct]:
    best: Dict[str, ParsedProduct] = {}
    rank = {"bronze_ready": 3, "needs_detail_page": 2, "insufficient": 1, "unknown": 0}
    for product in products:
        key = product.url or f"{product.source_id}:{product.raw_title}"
        current = best.get(key)
        if current is None or rank.get(product.quality, 0) > rank.get(current.quality, 0):
            best[key] = product
    return list(best.values())


def render_report(products: List[ParsedProduct]) -> str:
    total = len(products)
    bronze_ready = sum(1 for p in products if p.quality == "bronze_ready")
    needs_detail = sum(1 for p in products if p.quality == "needs_detail_page")
    insufficient = sum(1 for p in products if p.quality == "insufficient")

    lines = [
        "# Spike 005 Report: SFCC Public Parser Prototype",
        "",
        "## Summary",
        f"- Normalized products: `{total}`",
        f"- Bronze-ready products: `{bronze_ready}`",
        f"- Needs product detail page: `{needs_detail}`",
        f"- Insufficient: `{insufficient}`",
        "",
        "## Product Output",
        "| Source | Quality | Brand | Title | Full | Discount | Availability | Missing |",
        "|---|---|---|---|---:|---:|---|---|",
    ]

    for product in products:
        lines.append(
            "| {source} | {quality} | {brand} | {title} | {full} | {discount} | {availability} | {missing} |".format(
                source=product.source_id,
                quality=product.quality,
                brand=product.brand,
                title=product.raw_title.replace("|", "/"),
                full=f"{product.price_full:.2f}" if product.price_full is not None else "-",
                discount=f"{product.price_discount:.2f}" if product.price_discount is not None else "-",
                availability=product.stock_availability if product.stock_availability is not None else "-",
                missing=", ".join(product.missing_fields) if product.missing_fields else "-",
            )
        )

    lines.extend(
        [
            "",
            "## Verdict",
            "The parser prototype is viable for a future isolated `sfcc_public` engine design.",
            "",
            "Hugo Boss is strongest at category level because rendered category pages expose ProductGroup JSON-LD.",
            "Lacoste is strongest at product page level because PDP pages expose Product JSON-LD and OpenGraph product metadata.",
            "Lacoste category cards are useful for discovery but should be enriched by visiting the product detail page because image and stock are missing from the captured card fixture.",
            "",
            "## Production Implications",
            "- Use JSON-LD first.",
            "- Use OpenGraph product metadata as a supplement, especially for Lacoste price/material/color/availability.",
            "- Use visible card text for discovery and price hints, not as final product data when image or availability are missing.",
            "- Keep checkout, account, cart, wishlist, ZIP availability, private APIs, and bypass behavior out of scope.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
        fixtures = json.load(f)

    products: List[ParsedProduct] = []
    for observation in fixtures.get("observations", []):
        products.extend(normalize_observation(observation))

    result = {
        "spike": "005-sfcc-public-parser-prototype",
        "verdict": "VALIDATED_WITH_DETAIL_PAGE_ENRICHMENT",
        "products": [product.to_dict() for product in products],
        "stats": {
            "total": len(products),
            "bronze_ready": sum(1 for p in products if p.quality == "bronze_ready"),
            "needs_detail_page": sum(1 for p in products if p.quality == "needs_detail_page"),
            "insufficient": sum(1 for p in products if p.quality == "insufficient"),
        },
    }

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(render_report(products))

    print(json.dumps(result["stats"], indent=2))
    print(f"Wrote {RESULTS_PATH}")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
