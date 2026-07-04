from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from typing import Any

import pandas as pd


CANONICAL_PRODUCT_COLUMNS = [
    "brand",
    "url",
    "price_full",
    "price_discount",
    "product_name",
    "product_description",
    "composition",
    "available_colors",
    "available_sizes",
    "product_code",
    "category",
    "rating",
    "review_count",
]

PHASE43_PRODUCT_COLUMNS = [
    "promotions",
    "map_violation",
    "map_price_floor",
    "map_rule_scope",
    "map_rule_id",
    "map_infractor",
    "map_infractor_is_default",
]

CANONICAL_SPEC_ALIASES = {
    "composition": (
        "composition",
        "Composição",
        "Composicao",
        "Composição do produto",
        "Material",
    ),
    "product_code": (
        "product_code",
        "Código",
        "Codigo",
        "Código do produto",
        "Codigo do produto",
        "Referência",
        "Referencia",
        "Ref.",
        "REF",
    ),
    "category": (
        "category",
        "Categoria",
        "Department",
    ),
}

LIST_SPEC_ALIASES = {
    "available_colors": (
        "Cor",
        "Cores",
        "Color",
        "Colors",
    ),
    "available_sizes": (
        "Tamanho",
        "Tamanhos",
        "Size",
        "Sizes",
    ),
}


def _as_dict(product_like: Any) -> dict[str, Any]:
    if product_like is None:
        return {}
    if isinstance(product_like, Mapping):
        return dict(product_like)
    if hasattr(product_like, "model_dump"):
        return product_like.model_dump(mode="json")
    if hasattr(product_like, "dict"):
        return product_like.dict()
    return dict(vars(product_like))


def _clean_scalar(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned or cleaned.lower() == "none":
            return None
        return cleaned
    return value


def _clean_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned or cleaned.lower() == "none":
            return []
        for separator in ("|", ";", "/"):
            cleaned = cleaned.replace(separator, ",")
        return [part.strip() for part in cleaned.split(",") if part.strip()]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        items: list[str] = []
        for item in value:
            cleaned = _clean_scalar(item)
            if cleaned is not None:
                items.append(str(cleaned))
        return items
    cleaned = _clean_scalar(value)
    return [str(cleaned)] if cleaned is not None else []


def _coerce_float(value: Any) -> float | None:
    cleaned = _clean_scalar(value)
    if cleaned is None:
        return None
    try:
        return round(float(str(cleaned).replace(",", ".")), 2)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: Any) -> int | None:
    cleaned = _clean_scalar(value)
    if cleaned is None:
        return None
    digits = "".join(ch for ch in str(cleaned) if ch.isdigit())
    return int(digits) if digits else None


def _clean_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned in {"true", "1", "sim", "yes"}:
            return True
        if cleaned in {"false", "0", "nao", "não", "no"}:
            return False
    return bool(value)


def _serialize_promotions(value: Any) -> str | None:
    if not value:
        return None
    items = []
    for item in value:
        if hasattr(item, "model_dump"):
            items.append(item.model_dump(mode="json"))
        elif isinstance(item, Mapping):
            items.append(dict(item))
        else:
            items.append({"raw_text": str(item)})
    return json.dumps(items, ensure_ascii=False, sort_keys=True)


def _normalize_export_prices(payload: Mapping[str, Any]) -> tuple[float | None, float | None]:
    price_full = _coerce_float(payload.get("price_full"))
    price_discount = _coerce_float(payload.get("price_discount"))

    if payload.get("price_discount_is_delta") and price_full is not None and price_discount is not None:
        return round(price_full + price_discount, 2), round(price_full, 2)

    return price_full, price_discount


def normalize_specifications_aliases(specifications: Mapping[str, Any] | None) -> dict[str, Any]:
    normalized = dict(specifications or {})
    for canonical_key, aliases in CANONICAL_SPEC_ALIASES.items():
        if _clean_scalar(normalized.get(canonical_key)) is not None:
            continue
        for alias in aliases:
            candidate = _clean_scalar(normalized.get(alias))
            if candidate is not None:
                normalized[canonical_key] = candidate
                break
    return normalized


def extract_canonical_spec_value(
    specifications: Mapping[str, Any] | None,
    canonical_key: str,
) -> Any:
    return normalize_specifications_aliases(specifications).get(canonical_key)


def _extract_list_from_specs(
    specifications: Mapping[str, Any] | None,
    canonical_key: str,
) -> list[str]:
    normalized = normalize_specifications_aliases(specifications)
    direct_value = normalized.get(canonical_key)
    if direct_value is not None:
        return _clean_list(direct_value)
    for alias in LIST_SPEC_ALIASES.get(canonical_key, ()):
        candidate = specifications.get(alias) if specifications else None
        values = _clean_list(candidate)
        if values:
            return values
    return []


def build_canonical_product_row(product_like: Any) -> dict[str, Any]:
    payload = _as_dict(product_like)
    specifications = normalize_specifications_aliases(payload.get("specifications"))
    price_full, price_discount = _normalize_export_prices(payload)

    row = {
        "brand": _clean_scalar(payload.get("brand")),
        "url": _clean_scalar(payload.get("url")),
        "price_full": price_full,
        "price_discount": price_discount,
        "product_name": (
            _clean_scalar(payload.get("product_name"))
            or _clean_scalar(payload.get("raw_title"))
            or _clean_scalar(payload.get("title"))
        ),
        "product_description": (
            _clean_scalar(payload.get("product_description"))
            or _clean_scalar(payload.get("raw_description"))
            or _clean_scalar(payload.get("description"))
        ),
        "composition": (
            _clean_scalar(payload.get("composition"))
            or _clean_scalar(specifications.get("composition"))
        ),
        "available_colors": (
            _clean_list(payload.get("available_colors"))
            or _extract_list_from_specs(specifications, "available_colors")
        ),
        "available_sizes": (
            _clean_list(payload.get("available_sizes"))
            or _extract_list_from_specs(specifications, "available_sizes")
        ),
        "product_code": (
            _clean_scalar(payload.get("product_code"))
            or _clean_scalar(specifications.get("product_code"))
        ),
        "category": (
            _clean_scalar(payload.get("category"))
            or _clean_scalar(specifications.get("category"))
        ),
        "rating": _coerce_float(payload.get("rating")),
        "review_count": _coerce_int(payload.get("review_count")),
        "promotions": _serialize_promotions(payload.get("promotions")),
        "map_violation": _clean_bool(payload.get("map_violation")),
        "map_price_floor": _coerce_float(payload.get("map_price_floor")),
        "map_rule_scope": _clean_scalar(payload.get("map_rule_scope")),
        "map_rule_id": _clean_scalar(payload.get("map_rule_id")),
        "map_infractor": _clean_scalar(payload.get("map_infractor")),
        "map_infractor_is_default": _clean_bool(payload.get("map_infractor_is_default")),
    }

    if row["rating"] is None:
        row["rating"] = _coerce_float(specifications.get("rating"))
    if row["review_count"] is None:
        row["review_count"] = _coerce_int(specifications.get("review_count"))

    result = {column: row.get(column) for column in CANONICAL_PRODUCT_COLUMNS}
    for column in PHASE43_PRODUCT_COLUMNS:
        value = row.get(column)
        if _has_phase43_value(value):
            result[column] = value
    return result


def build_canonical_export_dataframe(products: Sequence[Any]) -> pd.DataFrame:
    rows = [build_canonical_product_row(product) for product in products]
    if not rows:
        return pd.DataFrame(columns=CANONICAL_PRODUCT_COLUMNS)

    df = pd.DataFrame(rows)
    for column in ("available_colors", "available_sizes"):
        if column in df.columns:
            df[column] = df[column].apply(
                lambda value: ", ".join(value) if isinstance(value, list) else value
            )

    active_phase43_columns = [
        column
        for column in PHASE43_PRODUCT_COLUMNS
        if column in df.columns and df[column].apply(_has_phase43_value).any()
    ]
    return df[CANONICAL_PRODUCT_COLUMNS + active_phase43_columns]


def _has_phase43_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return bool(value.strip())
    return True
