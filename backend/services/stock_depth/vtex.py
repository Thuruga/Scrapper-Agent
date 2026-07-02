from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable
from urllib.parse import quote
from urllib.request import Request, urlopen

from config import settings
from core.browser_manager import BrowserManager
from core.models import StockDepthResult
from services.stock_depth.base import (
    BaseStockDepthProvider,
    StockDepthState,
    brand_domain,
    get_field,
    is_url_allowed_for_brand,
)

logger = logging.getLogger("StockDepthVTEX")


class VtexStockDepthProvider(BaseStockDepthProvider):
    def __init__(self, playwright_factory: Callable[[], Any] | None = None):
        self._playwright_factory = playwright_factory

    async def probe(
        self,
        product: dict[str, Any] | Any,
        brand: Any,
        quantity: int,
    ) -> StockDepthResult:
        return await asyncio.to_thread(self._probe_sync, product, brand, quantity)

    def _probe_sync(
        self,
        product: dict[str, Any] | Any,
        brand: Any,
        quantity: int,
    ) -> StockDepthResult:
        url = str(get_field(product, "url", "") or "")
        if not url or not is_url_allowed_for_brand(url, brand):
            return self._result(
                StockDepthState.TEMPORARY_FAILURE,
                source="vtex-cart-probe",
                message="Produto sem URL valida para a marca persistida.",
            )

        api_result = self._probe_product_api(product, brand, quantity)
        if api_result is not None:
            return api_result

        page = None
        context = None
        browser = None

        try:
            with self._sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=BrowserManager.CHROMIUM_ARGS,
                )
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/125.0.0.0 Safari/537.36"
                    ),
                    java_script_enabled=True,
                    viewport={"width": 1366, "height": 768},
                    locale="pt-BR",
                    timezone_id="America/Sao_Paulo",
                    extra_http_headers={"Accept-Language": "pt-BR,pt;q=0.9"},
                )
                page = context.new_page()
                page.add_init_script(
                    """
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    window.chrome = { runtime: {} };
                    """
                )
                page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=settings.STOCK_PROBE_TIMEOUT_SECONDS * 1000,
                )
                evidence = page.evaluate(_VTEX_STOCK_DEPTH_SCRIPT, quantity)
                return self._result_from_evidence(evidence)
        except Exception as exc:
            state = self._state_from_exception(exc)
            logger.info("[stock-depth:vtex] provider ended with state=%s", state)
            return self._result(state, source="vtex-cart-probe", message=str(exc))
        finally:
            for resource in (page, context, browser):
                if resource is None:
                    continue
                try:
                    resource.close()
                except Exception:
                    logger.debug("[stock-depth:vtex] cleanup failed", exc_info=True)

    def _probe_product_api(
        self,
        product: dict[str, Any] | Any,
        brand: Any,
        quantity: int,
    ) -> StockDepthResult | None:
        product_id = str(
            get_field(product, "review_product_id")
            or get_field(product, "product_id")
            or ""
        ).strip()
        domain = brand_domain(brand)
        if not product_id or not domain:
            return None

        url = (
            f"https://{domain}/api/catalog_system/pub/products/search"
            f"?fq=productId:{quote(product_id)}"
        )
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
            },
        )
        try:
            with urlopen(
                request,
                timeout=settings.STOCK_PROBE_TIMEOUT_SECONDS,
            ) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            logger.debug("[stock-depth:vtex] product API probe failed: %s", exc)
            return None

        if not isinstance(data, list) or not data:
            return None

        quantities = self._extract_available_quantities(data[0])
        if not quantities:
            return None

        max_quantity = max(quantities)
        if max_quantity <= 0:
            return self._result(
                StockDepthState.UNAVAILABLE,
                estimate=0,
                source="vtex-product-api",
                message="VTEX API retornou estoque indisponivel.",
            )

        return self._result(
            StockDepthState.ESTIMATED,
            estimate=min(max_quantity, quantity),
            source="vtex-product-api",
            message="Estimativa pelo AvailableQuantity da VTEX API publica.",
        )

    @staticmethod
    def _extract_available_quantities(product_data: Any) -> list[int]:
        quantities: list[int] = []
        if not isinstance(product_data, dict):
            return quantities

        for item in product_data.get("items") or []:
            if not isinstance(item, dict):
                continue
            for seller in item.get("sellers") or []:
                if not isinstance(seller, dict):
                    continue
                offer = seller.get("commertialOffer") or {}
                if not isinstance(offer, dict):
                    continue
                try:
                    quantities.append(int(offer.get("AvailableQuantity") or 0))
                except (TypeError, ValueError):
                    continue
        return quantities

    def _sync_playwright(self):
        if self._playwright_factory is not None:
            return self._playwright_factory()
        from playwright.sync_api import sync_playwright

        return sync_playwright()

    @staticmethod
    def _state_from_exception(exc: Exception) -> str:
        text = str(exc).lower()
        if any(marker in text for marker in ("403", "blocked", "access denied", "captcha")):
            return StockDepthState.BLOCKED
        if "timeout" in text or isinstance(exc, TimeoutError):
            return StockDepthState.TEMPORARY_FAILURE
        return StockDepthState.TEMPORARY_FAILURE

    @staticmethod
    def _result_from_evidence(evidence: Any) -> StockDepthResult:
        if not isinstance(evidence, dict):
            return VtexStockDepthProvider._result(
                StockDepthState.TEMPORARY_FAILURE,
                source="vtex-cart-probe",
                message="Sem evidencia estruturada de estoque.",
            )

        state = str(evidence.get("state") or "").lower()
        raw_estimate = evidence.get("estimate")
        if raw_estimate is None:
            raw_estimate = evidence.get("availableQuantity")

        estimate = None
        try:
            if raw_estimate is not None:
                estimate = int(raw_estimate)
        except (TypeError, ValueError):
            estimate = None

        if state == StockDepthState.ESTIMATED and estimate is not None:
            if estimate <= 0:
                return VtexStockDepthProvider._result(
                    StockDepthState.UNAVAILABLE,
                    estimate=0,
                    source="vtex-cart-probe",
                    message="Provider retornou indisponibilidade confiavel.",
                )
            return VtexStockDepthProvider._result(
                StockDepthState.ESTIMATED,
                estimate=estimate,
                source="vtex-cart-probe",
                message="Estimativa via cart-probe VTEX.",
            )

        if state == StockDepthState.UNAVAILABLE:
            return VtexStockDepthProvider._result(
                StockDepthState.UNAVAILABLE,
                estimate=0 if estimate == 0 else None,
                source="vtex-cart-probe",
                message="Provider retornou indisponibilidade confiavel.",
            )

        if state == StockDepthState.BLOCKED:
            return VtexStockDepthProvider._result(
                StockDepthState.BLOCKED,
                source="vtex-cart-probe",
                message="Provider bloqueou o probe.",
            )

        return VtexStockDepthProvider._result(
            StockDepthState.TEMPORARY_FAILURE,
            source="vtex-cart-probe",
            message="Sem evidencia confiavel de profundidade.",
        )

    @staticmethod
    def _result(
        state: str,
        estimate: int | None = None,
        source: str | None = None,
        message: str | None = None,
    ) -> StockDepthResult:
        if state not in (StockDepthState.ESTIMATED, StockDepthState.UNAVAILABLE):
            estimate = None
        return StockDepthResult(
            stock_depth_state=state,
            stock_depth_estimate=estimate,
            stock_depth_source=source,
            stock_depth_label=message,
        )


_VTEX_STOCK_DEPTH_SCRIPT = """
(quantity) => {
  const scripts = Array.from(document.scripts || []).map((node) => node.textContent || "");
  const joined = scripts.join("\\n");
  const match = joined.match(/"AvailableQuantity"\\s*:\\s*(\\d+)/i);
  if (match) {
    const availableQuantity = Number(match[1]);
    return {
      state: availableQuantity > 0 ? "estimated" : "unavailable",
      estimate: Math.min(availableQuantity, quantity),
    };
  }
  const bodyText = (document.body && document.body.innerText || "").toLowerCase();
  if (bodyText.includes("access denied") || bodyText.includes("captcha")) {
    return { state: "blocked" };
  }
  return { state: "temporary_failure" };
}
"""
