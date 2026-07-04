"""Pure MAP verdict computation over product-like input."""

from __future__ import annotations

from typing import Any, Iterable

from core.models import MapRule, resolve_effective_price
from services.engines.seller_extraction import is_marketplace_default
from services.map_rules_service import find_applicable_rule


EMPTY_MAP_METADATA = {
    "map_violation": False,
    "map_price_floor": None,
    "map_rule_scope": None,
    "map_rule_id": None,
    "map_infractor": None,
    "map_infractor_is_default": False,
}


def _as_dict(product_like: Any) -> dict[str, Any]:
    if product_like is None:
        return {}
    if isinstance(product_like, dict):
        return dict(product_like)
    if hasattr(product_like, "model_dump"):
        return product_like.model_dump(mode="json")
    if hasattr(product_like, "dict"):
        return product_like.dict()
    return dict(vars(product_like))


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def resolve_effective_advertised_price(product_like: Any) -> float | None:
    product = _as_dict(product_like)

    if "price_full" in product or "price_discount" in product:
        return resolve_effective_price(
            _coerce_float(product.get("price_full")),
            _coerce_float(product.get("price_discount")),
            bool(product.get("price_discount_is_delta", False)),
        )

    return (
        _coerce_float(product.get("price"))
        or _coerce_float(product.get("preco"))
        or _coerce_float(product.get("landed_price"))
    )


def _resolve_infractor(
    product: dict[str, Any],
    brand_name: str | None = None,
    marketplace: str | None = None,
) -> tuple[str | None, bool]:
    seller = product.get("seller")
    if seller and not is_marketplace_default(str(seller), marketplace):
        return str(seller), False
    if seller:
        return str(seller), True

    fallback = brand_name or product.get("brand_name") or product.get("brand") or product.get("marketplace")
    return (str(fallback), False) if fallback else (None, False)


def evaluate_map_violation(
    product_like: Any,
    rules: Iterable[MapRule],
    *,
    brand_name: str | None = None,
    marketplace: str | None = None,
) -> dict[str, Any]:
    product = _as_dict(product_like)
    rule = find_applicable_rule(product, rules)
    effective_price = resolve_effective_advertised_price(product)

    if rule is None or effective_price is None:
        return dict(EMPTY_MAP_METADATA)

    infractor, is_default = _resolve_infractor(product, brand_name, marketplace)
    return {
        "map_violation": effective_price < rule.min_price,
        "map_price_floor": rule.min_price,
        "map_rule_scope": rule.scope,
        "map_rule_id": rule.id,
        "map_infractor": infractor,
        "map_infractor_is_default": is_default,
    }
