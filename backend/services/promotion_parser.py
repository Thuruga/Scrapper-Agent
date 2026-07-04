"""Pure helpers for normalizing promotional badge text."""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable

from core.models import PromotionInfo


_PERCENT_RE = re.compile(r"(\d+(?:[,.]\d+)?)\s*%")
_INSTALLMENT_RE = re.compile(
    r"(\d{1,2})\s*x\s*(?:de\s*)?R?\$?\s*(\d+(?:[.,]\d{2})?)",
    re.IGNORECASE,
)
_BUNDLE_RE = re.compile(
    r"\b(?:leve|compre)\s+\d+\b|\bpague\s+\d+\b",
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    return (
        unicodedata.normalize("NFD", text)
        .encode("ascii", "ignore")
        .decode("utf-8")
        .lower()
        .strip()
    )


def _to_float(value: str) -> float:
    return float(value.replace(".", "").replace(",", "."))


def parse_promotion_text(text: str) -> PromotionInfo | None:
    raw_text = (text or "").strip()
    if not raw_text:
        return None

    normalized = _normalize(raw_text)

    installment = _INSTALLMENT_RE.search(raw_text)
    if installment:
        return PromotionInfo(
            type="installments",
            raw_text=raw_text,
            installments_count=int(installment.group(1)),
            installment_amount=round(_to_float(installment.group(2)), 2),
        )

    percent = _PERCENT_RE.search(raw_text)
    if "pix" in normalized and percent:
        return PromotionInfo(
            type="pix_discount",
            raw_text=raw_text,
            value=_to_float(percent.group(1)),
            unit="percent",
            payment_method="pix",
        )

    if percent and ("off" in normalized or "desconto" in normalized):
        return PromotionInfo(
            type="percentage_discount",
            raw_text=raw_text,
            value=_to_float(percent.group(1)),
            unit="percent",
        )

    if _BUNDLE_RE.search(normalized):
        return PromotionInfo(type="bundle", raw_text=raw_text)

    return PromotionInfo(type="generic_badge", raw_text=raw_text, parsed=False)


def parse_promotions(raw_values: str | Iterable[str] | None) -> list[PromotionInfo]:
    if raw_values is None:
        return []
    if isinstance(raw_values, str):
        values = [raw_values]
    else:
        values = list(raw_values)

    parsed: list[PromotionInfo] = []
    seen: set[str] = set()
    for value in values:
        item = parse_promotion_text(str(value))
        if item is None:
            continue
        key = _normalize(item.raw_text)
        if key in seen:
            continue
        seen.add(key)
        parsed.append(item)
    return parsed


def derive_discount_promotions(
    price_full: float | None,
    price_discount: float | None,
    price_discount_is_delta: bool = False,
) -> list[PromotionInfo]:
    if price_full is None or price_discount is None:
        return []
    original = price_full + price_discount if price_discount_is_delta else price_full
    current = price_full if price_discount_is_delta else price_discount
    if original <= 0 or current <= 0 or current >= original:
        return []
    percentage = round(((original - current) / original) * 100)
    return parse_promotions([f"{percentage}% OFF"])
