from __future__ import annotations

from typing import Any

from core.models import SearchProductResult
from services.shipping.base import BaseShipping, ShippingCalculation, ShippingState


class MercadoLivreShipping(BaseShipping):
    def __init__(self, engine: Any = None) -> None:
        self.engine = engine

    async def calculate(
        self,
        product: SearchProductResult | dict[str, Any],
        zipcode: str,
        brand: Any,
    ) -> ShippingCalculation:
        return ShippingCalculation(
            state=ShippingState.UNSUPPORTED,
            message="Frete Mercado Livre ainda nao implementado",
        )
