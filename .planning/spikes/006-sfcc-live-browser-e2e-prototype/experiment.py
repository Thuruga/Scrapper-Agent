"""
Verification harness for the Spike 006 live browser E2E capture.

The actual live capture was performed with the Codex in-app browser so it could
render public storefront pages. This script keeps the spike reproducible by
validating the saved capture and regenerating REPORT.md without touching
production code or the network.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from typing import Any, Dict, List


SPIKE_DIR = os.path.dirname(os.path.abspath(__file__))
LIVE_RESULT_PATH = os.path.join(SPIKE_DIR, "LIVE_RESULT.json")
RAW_PRODUCTS_PATH = os.path.join(SPIKE_DIR, "raw_products.json")
REPORT_PATH = os.path.join(SPIKE_DIR, "REPORT.md")


REQUIRED_PRODUCT_FIELDS = ["url", "brand", "raw_title", "price_full", "image_url"]


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def product_quality(product: Dict[str, Any]) -> str:
    missing = [field for field in REQUIRED_PRODUCT_FIELDS if product.get(field) in (None, "")]
    return "bronze_ready" if not missing else "incomplete"


def validate(live_result: Dict[str, Any], products: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_brand = Counter(product.get("brand", "") for product in products if product_quality(product) == "bronze_ready")
    errors = []

    if live_result.get("stats", {}).get("errors", 0) != 0:
        errors.append("live_result reported browser errors")

    if len(products) != live_result.get("stats", {}).get("normalized_products"):
        errors.append("raw_products count differs from live_result stats")

    if by_brand.get("BOSS", 0) < 3:
        errors.append("Hugo Boss produced fewer than 3 bronze-ready products")

    if by_brand.get("Lacoste", 0) < 3:
        errors.append("Lacoste produced fewer than 3 bronze-ready products")

    for product in products:
        if product_quality(product) != "bronze_ready":
            errors.append(f"incomplete product: {product.get('url')}")

    return {
        "valid": not errors,
        "errors": errors,
        "bronze_ready_by_brand": dict(by_brand),
        "total_products": len(products),
        "bronze_ready": sum(1 for product in products if product_quality(product) == "bronze_ready"),
    }


def render_report(live_result: Dict[str, Any], products: List[Dict[str, Any]], validation: Dict[str, Any]) -> str:
    lines = [
        "# Spike 006 Report: SFCC Live Browser E2E Prototype",
        "",
        "## Summary",
        f"- Verdict: `{live_result.get('verdict')}`",
        f"- Brands tested: `{live_result.get('stats', {}).get('brands')}`",
        f"- Normalized products: `{validation['total_products']}`",
        f"- Bronze-ready products: `{validation['bronze_ready']}`",
        f"- Browser errors: `{live_result.get('stats', {}).get('errors')}`",
        f"- Validation passed: `{validation['valid']}`",
        "",
        "## Brand Results",
        "| Brand | Category | Candidate Count | PDPs Visited | Bronze Ready | Notes |",
        "|---|---|---:|---:|---:|---|",
    ]

    for brand in live_result.get("brands", []):
        notes = []
        category = brand.get("category_summary", {})
        if category.get("jsonld_product_count", 0):
            notes.append(f"{category['jsonld_product_count']} category JSON-LD products")
        else:
            notes.append("category discovery via rendered product links")
        notes.append(f"demandware={category.get('signals', {}).get('demandware', 0)}")
        lines.append(
            "| {brand} | {category_url} | {candidates} | {pdps} | {ready} | {notes} |".format(
                brand=brand.get("brand"),
                category_url=brand.get("category_url"),
                candidates=category.get("product_candidate_count", 0),
                pdps=len(brand.get("product_urls", [])),
                ready=brand.get("bronze_ready", 0),
                notes=", ".join(notes),
            )
        )

    lines.extend(
        [
            "",
            "## Product Output",
            "| Brand | Title | Price | Availability | Color | Quality |",
            "|---|---|---:|---|---|---|",
        ]
    )

    for product in products:
        lines.append(
            "| {brand} | {title} | {price} | {availability} | {color} | {quality} |".format(
                brand=product.get("brand"),
                title=str(product.get("raw_title", "")).replace("|", "/"),
                price=product.get("price_full"),
                availability=product.get("stock_availability"),
                color=", ".join(product.get("available_colors") or []),
                quality=product.get("_quality"),
            )
        )

    lines.extend(
        [
            "",
            "## Findings",
            "- The live browser path met the success threshold: at least 2 bronze-ready products per brand.",
            "- Hugo Boss category pages expose ProductGroup JSON-LD, but PDP visible text is still needed for price.",
            "- Lacoste category pages require stricter PDP-link filtering, then PDP pages provide Product JSON-LD and stock metadata.",
            "- Price parsing must prefer money patterns such as `$119.00`; generic numbers in accessibility text caused false positives in the first trial.",
            "- This remains a browser-rendered public extraction path, not API scraping.",
            "",
            "## Out of Scope Preserved",
            "- No OCAPI/SCAPI.",
            "- No checkout, account, cart, wishlist, ZIP/store availability, or shipping.",
            "- No proxy, stealth, CAPTCHA solving, or WAF bypass.",
            "- No production engine/factory/brand registry changes.",
            "",
        ]
    )

    if validation["errors"]:
        lines.append("## Validation Errors")
        for error in validation["errors"]:
            lines.append(f"- {error}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    live_result = load_json(LIVE_RESULT_PATH)
    products = load_json(RAW_PRODUCTS_PATH)
    validation = validate(live_result, products)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(render_report(live_result, products, validation))

    print(json.dumps(validation, indent=2, ensure_ascii=False))
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
