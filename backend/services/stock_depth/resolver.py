from __future__ import annotations

from typing import Any

from services.stock_depth.base import get_field


_AVAILABILITY_ENGINES = {
    "shopify",
    "wake",
    "sfcc",
    "mercadolivre",
    "mercado_livre",
    "netshoes",
    "amazon",
    "zara",
}


def resolve_stock_depth_provider(brand: Any):
    engine = str(get_field(brand, "engine", "") or "").lower()
    if engine == "vtex":
        from services.stock_depth.vtex import VtexStockDepthProvider

        return VtexStockDepthProvider()
    if engine in _AVAILABILITY_ENGINES:
        from services.stock_depth.availability import AvailabilityStockDepthProvider

        return AvailabilityStockDepthProvider()
    from services.stock_depth.unsupported import UnsupportedStockDepthProvider

    return UnsupportedStockDepthProvider(
        reason=f"Profundidade de estoque nao suportada para engine '{engine or 'unknown'}'"
    )
