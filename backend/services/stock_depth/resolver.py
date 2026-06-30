from __future__ import annotations

from typing import Any

from services.stock_depth.base import get_field
from services.stock_depth.unsupported import UnsupportedStockDepthProvider


def resolve_stock_depth_provider(brand: Any):
    engine = str(get_field(brand, "engine", "") or "").lower()
    if engine == "vtex":
        from services.stock_depth.vtex import VtexStockDepthProvider

        return VtexStockDepthProvider()
    return UnsupportedStockDepthProvider(
        reason=f"Profundidade de estoque nao suportada para engine '{engine or 'unknown'}'"
    )
