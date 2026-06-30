from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from urllib.parse import urlparse

from core.models import StockDepthResult


class StockDepthState:
    ESTIMATED = "estimated"
    UNAVAILABLE = "unavailable"
    UNSUPPORTED = "unsupported"
    BLOCKED = "blocked"
    TEMPORARY_FAILURE = "temporary_failure"


class BaseStockDepthProvider(ABC):
    @abstractmethod
    async def probe(
        self,
        product: dict[str, Any] | Any,
        brand: Any,
        quantity: int,
    ) -> StockDepthResult:
        """Estimate stock depth for one persisted scan product."""


def get_field(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def brand_domain(brand: Any) -> str:
    return (
        str(get_field(brand, "domain", "") or "")
        .replace("https://", "")
        .replace("http://", "")
        .strip("/")
    )


def is_url_allowed_for_brand(url: str, brand: Any) -> bool:
    expected = brand_domain(brand).lower()
    if not expected:
        return False
    parsed = urlparse(str(url or ""))
    host = (parsed.netloc or "").lower()
    if not host:
        return False
    return host == expected or host.endswith("." + expected)
