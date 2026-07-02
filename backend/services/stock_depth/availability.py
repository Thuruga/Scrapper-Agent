from __future__ import annotations

import logging
from typing import Any

from core.models import StockDepthResult
from services.stock_depth.base import (
    BaseStockDepthProvider,
    StockDepthState,
    get_field,
    is_url_allowed_for_brand,
)

logger = logging.getLogger("StockDepthAvailability")


class AvailabilityStockDepthProvider(BaseStockDepthProvider):
    """Confirm availability for engines that do not expose exact stock depth."""

    def __init__(self, engine_factory: Any = None):
        self._engine_factory = engine_factory

    async def probe(
        self,
        product: dict[str, Any] | Any,
        brand: Any,
        quantity: int,  # noqa: ARG002 - non-VTEX sources do not expose quantity
    ) -> StockDepthResult:
        url = str(get_field(product, "url", "") or "")
        if not url or not is_url_allowed_for_brand(url, brand):
            return self._result(
                StockDepthState.TEMPORARY_FAILURE,
                "availability-provider",
                "Produto sem URL valida para a marca persistida.",
            )

        live_product = await self._fetch_live_product(product, brand)
        availability = self._extract_availability(live_product)
        if availability is None:
            availability = self._extract_availability(product)
            source = "persisted-availability"
            label = "Disponibilidade reaproveitada da ultima varredura; quantidade exata nao exposta."
        else:
            source = "pdp-availability"
            label = "Disponibilidade confirmada na PDP/API; quantidade exata nao exposta."

        if availability is True:
            return self._result(StockDepthState.AVAILABILITY_ONLY, source, label)
        if availability is False:
            return StockDepthResult(
                stock_depth_state=StockDepthState.UNAVAILABLE,
                stock_depth_estimate=0,
                stock_depth_source=source,
                stock_depth_label=label,
            )
        return self._result(
            StockDepthState.UNSUPPORTED,
            "availability-provider",
            "Engine nao expoe quantidade nem disponibilidade confiavel para este produto.",
        )

    async def _fetch_live_product(
        self,
        product: dict[str, Any] | Any,
        brand: Any,
    ) -> Any:
        brand_key = str(get_field(brand, "brand_key", "") or "").strip().lower()
        if not brand_key:
            return None
        try:
            engine = self._resolve_engine(brand_key)
            url = str(get_field(product, "url", "") or "")
            if hasattr(engine, "get_pdp_product"):
                result = await engine.get_pdp_product(url)
                if result:
                    return result
            if hasattr(engine, "get_product_details"):
                return await engine.get_product_details(url)
        except Exception as exc:
            logger.debug("[stock-depth:availability] live product fetch failed: %s", exc)
        return None

    def _resolve_engine(self, brand_key: str) -> Any:
        if self._engine_factory is not None:
            return self._engine_factory(brand_key)
        from services.engines.factory import engine_factory

        return engine_factory.get_engine(brand_key)

    @staticmethod
    def _extract_availability(product: Any) -> bool | None:
        for field in ("stock_availability", "available"):
            value = get_field(product, field)
            if isinstance(value, bool):
                return value
        return None

    @staticmethod
    def _result(state: str, source: str, label: str) -> StockDepthResult:
        return StockDepthResult(
            stock_depth_state=state,
            stock_depth_estimate=None,
            stock_depth_source=source,
            stock_depth_label=label,
        )
