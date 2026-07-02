from __future__ import annotations

import logging
from typing import Any

from core.models import SearchProductResult, ShippingInfo
from services.shipping.base import (
    BaseShipping,
    ShippingCalculation,
    ShippingState,
    get_field,
    is_url_allowed_for_brand,
    normalize_zipcode,
    sorted_shipping_options,
)

logger = logging.getLogger(__name__)


class AmazonShipping(BaseShipping):
    def __init__(self, engine: Any = None) -> None:
        self._engine = engine

    @property
    def engine(self) -> Any:
        if self._engine is None:
            from services.engines.amazon_engine import AmazonEngine

            self._engine = AmazonEngine()
        return self._engine

    async def calculate(
        self,
        product: SearchProductResult | dict[str, Any],
        zipcode: str,
        brand: Any,
    ) -> ShippingCalculation:
        try:
            cep = normalize_zipcode(zipcode)
        except ValueError:
            return ShippingCalculation(
                state=ShippingState.UNAVAILABLE_FOR_CEP,
                message="CEP invalido",
            )

        product_url = str(get_field(product, "url", "") or "")
        if not is_url_allowed_for_brand(product_url, brand):
            return ShippingCalculation(
                state=ShippingState.UNSUPPORTED,
                message="URL do produto nao pertence ao dominio da marca",
            )

        try:
            result = await self.engine.calculate_shipping_advanced(product_url, cep)
        except Exception as exc:
            logger.warning(
                "[AmazonShipping] quote failed brand=%s status=%s",
                get_field(brand, "brand_key", "unknown"),
                type(exc).__name__,
            )
            return ShippingCalculation(
                state=ShippingState.TEMPORARY_FAILURE,
                message="Frete temporariamente indisponivel",
            )

        if not result:
            return ShippingCalculation(
                state=ShippingState.TEMPORARY_FAILURE,
                message="Frete temporariamente indisponivel",
            )

        if "error" in result:
            # CAPTCHA/anti-bot e transitorio por sessao — NUNCA BLOCKED (D-02).
            return ShippingCalculation(
                state=ShippingState.TEMPORARY_FAILURE,
                message=result["error"],
            )

        price = result.get("shipping_price")
        is_free = bool(result.get("is_free_shipping"))
        days = result.get("estimated_delivery_days")
        raw_text = result.get("delivery_raw_text")

        info = ShippingInfo(
            price=price,
            status="Gratis" if is_free else "Disponivel",
            estimated_delivery_days=days,
            raw_text=raw_text,
            is_free_shipping=is_free or price == 0.0,
        )

        return ShippingCalculation(
            state=ShippingState.AVAILABLE,
            shipping_options=sorted_shipping_options([info]),
        )
