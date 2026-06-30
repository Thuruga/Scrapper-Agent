from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from core.models import SearchProductResult, ShippingInfo
from services.shipping.base import (
    BaseShipping,
    ShippingCalculation,
    ShippingState,
    brand_domain,
    get_field,
    is_url_allowed_for_brand,
    normalize_zipcode,
    sorted_shipping_options,
)

logger = logging.getLogger(__name__)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


class ShopifyShipping(BaseShipping):
    def __init__(self, session_factory: Any = None, sleep: Any = None) -> None:
        self.session_factory = session_factory
        self.sleep = sleep or asyncio.sleep

    def _open_session(self):
        if self.session_factory:
            return self.session_factory()
        return aiohttp.ClientSession(headers=HEADERS)

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

        domain = brand_domain(brand)
        variant_id = get_field(product, "shipping_variant_id")
        try:
            async with self._open_session() as session:
                if not variant_id:
                    variant_id = await self._fetch_variant_id(session, product_url)
                if not variant_id:
                    return ShippingCalculation(
                        state=ShippingState.UNSUPPORTED,
                        message="Variante Shopify nao encontrada",
                    )
                options = await self._quote(session, domain, str(variant_id), cep)
        except Exception as exc:
            logger.warning(
                "[ShopifyShipping] quote failed brand=%s status=%s",
                get_field(brand, "brand_key", "unknown"),
                type(exc).__name__,
            )
            return ShippingCalculation(
                state=ShippingState.TEMPORARY_FAILURE,
                message="Frete temporariamente indisponivel",
            )

        if not options:
            return ShippingCalculation(
                state=ShippingState.UNAVAILABLE_FOR_CEP,
                message="Entrega indisponivel para este CEP",
            )

        return ShippingCalculation(
            state=ShippingState.AVAILABLE,
            shipping_options=sorted_shipping_options(options),
        )

    async def _json_request(
        self,
        session: aiohttp.ClientSession,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> tuple[int, Any]:
        async with session.request(
            method,
            url,
            timeout=aiohttp.ClientTimeout(total=15),
            **kwargs,
        ) as resp:
            try:
                data = await resp.json(content_type=None)
            except Exception:
                data = None
            return resp.status, data

    async def _fetch_variant_id(self, session: aiohttp.ClientSession, product_url: str) -> str | None:
        json_url = product_url.split("?", 1)[0].rstrip("/") + ".json"
        status, data = await self._json_request(session, "GET", json_url)
        if status != 200 or not isinstance(data, dict):
            return None
        product = data.get("product") or {}
        for variant in product.get("variants") or []:
            if variant.get("available", True) and variant.get("id"):
                return str(variant["id"])
        variants = product.get("variants") or []
        return str(variants[0]["id"]) if variants and variants[0].get("id") else None

    async def _quote(
        self,
        session: aiohttp.ClientSession,
        domain: str,
        variant_id: str,
        cep: str,
    ) -> list[ShippingInfo]:
        await self._json_request(session, "POST", f"https://{domain}/cart/clear.js", json={})
        add_status, _ = await self._json_request(
            session,
            "POST",
            f"https://{domain}/cart/add.js",
            json={"id": variant_id, "quantity": 1},
        )
        if add_status >= 400:
            return []

        params = {
            "shipping_address[zip]": cep,
            "shipping_address[country]": "Brazil",
            "shipping_address[country_code]": "BR",
            "shipping_address[province]": "SP",
            "shipping_address[city]": "Sao Paulo",
        }
        prepare_status, _ = await self._json_request(
            session,
            "POST",
            f"https://{domain}/cart/prepare_shipping_rates.json",
            params=params,
        )
        if prepare_status not in (200, 202):
            return []

        try:
            for _ in range(5):
                await self.sleep(1)
                status, data = await self._json_request(
                    session,
                    "GET",
                    f"https://{domain}/cart/async_shipping_rates.json",
                    params=params,
                )
                if status == 200 and isinstance(data, dict) and data.get("shipping_rates") is not None:
                    return self._parse_rates(data.get("shipping_rates") or [])
            return []
        finally:
            await self._json_request(session, "POST", f"https://{domain}/cart/clear.js", json={})

    def _parse_rates(self, rates: list[dict[str, Any]]) -> list[ShippingInfo]:
        options: list[ShippingInfo] = []
        for rate in rates:
            price = self._parse_price(rate.get("price"))
            days = self._parse_delivery_days(rate)
            service_name = rate.get("presentment_name") or rate.get("name") or "Entrega"
            estimate_display = f"Ate {days} dias uteis" if days is not None else None
            raw_text = rate.get("delivery_date") or service_name
            options.append(
                ShippingInfo(
                    price=price,
                    status="Gratis" if price == 0.0 else "Disponivel",
                    estimated_delivery_days=days,
                    raw_text=str(raw_text) if raw_text is not None else None,
                    service_name=service_name,
                    service_id=str(rate.get("code") or service_name),
                    estimate_display=estimate_display,
                    estimate_unit="d" if days is not None else None,
                    is_free_shipping=price == 0.0,
                )
            )
        return options

    @staticmethod
    def _parse_price(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return round(float(str(value).replace(",", ".").strip()), 2)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_delivery_days(rate: dict[str, Any]) -> int | None:
        days = rate.get("delivery_days")
        if isinstance(days, list) and days:
            try:
                return int(max(days))
            except (TypeError, ValueError):
                return None
        try:
            return int(days) if days is not None else None
        except (TypeError, ValueError):
            return None
