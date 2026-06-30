from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.models import StockDepthResult
from services.stock_depth.base import BaseStockDepthProvider, StockDepthState


@dataclass
class UnsupportedStockDepthProvider(BaseStockDepthProvider):
    reason: str = "Profundidade de estoque nao suportada para este engine"

    async def probe(
        self,
        product: dict[str, Any] | Any,
        brand: Any,
        quantity: int,
    ) -> StockDepthResult:
        return StockDepthResult(
            stock_depth_state=StockDepthState.UNSUPPORTED,
            stock_depth_estimate=None,
            stock_depth_source="unsupported",
            stock_depth_label=self.reason,
        )
