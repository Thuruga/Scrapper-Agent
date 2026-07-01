"""Orchestration for explicit stock-depth probes on persisted scan products."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import settings
from core.models import StockDepthResult
from services.brand_service import brand_service
from services.category_monitor_service import DATA_DIR
from services.stock_depth.base import StockDepthState, is_url_allowed_for_brand
from services.stock_depth.resolver import resolve_stock_depth_provider

logger = logging.getLogger("StockDepthService")

_PROBE_GUARDS: dict[tuple[str, str], dict[str, float | int]] = {}
_STOCK_DEPTH_LABEL = "maximo observado/estimativa via cart-probe"


async def probe_scan_product_stock_depth(
    monitor_id: str,
    scan_product_id: str,
) -> StockDepthResult:
    monitor = _find_monitor(monitor_id)
    brand_key = str(monitor.get("brand") or "").lower().strip()
    if not brand_key:
        raise ValueError("Monitor nao possui marca persistida.")

    brand = brand_service.get_brand(brand_key)
    if not brand:
        raise ValueError(f"Marca '{brand_key}' nao encontrada.")

    products = _load_products(monitor_id)
    product_index, product = _find_scan_product(products, scan_product_id)
    product_url = str(product.get("url") or "")
    if not is_url_allowed_for_brand(product_url, brand):
        raise ValueError("URL do produto nao pertence ao dominio da marca.")

    guard_result = _enforce_probe_guard(brand_key, monitor_id)
    if guard_result is not None:
        provider_result = guard_result
    else:
        provider = resolve_stock_depth_provider(brand)
        try:
            provider_result = await provider.probe(
                product,
                brand,
                settings.STOCK_PROBE_QUANTITY,
            )
        except Exception as exc:
            logger.info("[stock-depth] provider exception state=temporary_failure")
            provider_result = StockDepthResult(
                stock_depth_state=StockDepthState.TEMPORARY_FAILURE,
                stock_depth_estimate=None,
                stock_depth_source="provider-exception",
                stock_depth_label=str(exc),
            )

    checked_at = _utc_now_iso()
    normalized = _normalize_result(provider_result, checked_at)
    updated_product = _apply_result(product, normalized)
    products[product_index] = updated_product
    _write_products(monitor_id, products)
    return normalized


def _find_monitor(monitor_id: str) -> dict[str, Any]:
    monitors_file = DATA_DIR / "monitored_categories.json"
    if not monitors_file.exists():
        raise ValueError("Monitor de categoria nao encontrado.")
    try:
        monitors = json.loads(monitors_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError("Arquivo de monitores invalido.") from exc
    for monitor in monitors if isinstance(monitors, list) else []:
        if monitor.get("id") == monitor_id:
            return monitor
    raise ValueError("Monitor de categoria nao encontrado.")


def _load_products(monitor_id: str) -> list[dict[str, Any]]:
    products_file = _products_file(monitor_id)
    if not products_file.exists():
        raise ValueError("Produtos monitorados nao encontrados.")
    try:
        products = json.loads(products_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError("Arquivo de produtos monitorados invalido.") from exc
    if not isinstance(products, list):
        raise ValueError("Arquivo de produtos monitorados invalido.")
    return [dict(product) for product in products if isinstance(product, dict)]


def _find_scan_product(
    products: list[dict[str, Any]],
    scan_product_id: str,
) -> tuple[int, dict[str, Any]]:
    matches = [
        (index, product)
        for index, product in enumerate(products)
        if product.get("scan_product_id") == scan_product_id
    ]
    if not matches:
        raise ValueError("Produto do scan nao encontrado.")
    if len(matches) > 1:
        raise ValueError("Produto do scan duplicado.")
    return matches[0]


def _enforce_probe_guard(
    brand_key: str,
    monitor_id: str,
) -> StockDepthResult | None:
    key = (brand_key, monitor_id)
    now = _now_monotonic()
    guard = _PROBE_GUARDS.get(key)
    if guard is None:
        _PROBE_GUARDS[key] = {"last_probe_at": now, "count": 1}
        return None

    count = int(guard.get("count", 0))
    max_count = int(settings.MAX_STOCK_DEPTH_PROBES_PER_BRAND)
    if count >= max_count:
        return StockDepthResult(
            stock_depth_state=StockDepthState.BLOCKED,
            stock_depth_estimate=None,
            stock_depth_source="probe-limit",
        )

    last_probe_at = float(guard.get("last_probe_at", 0.0))
    elapsed = now - last_probe_at
    if elapsed < float(settings.STOCK_PROBE_THROTTLE_SECONDS):
        return StockDepthResult(
            stock_depth_state=StockDepthState.BLOCKED,
            stock_depth_estimate=None,
            stock_depth_source="probe-throttle",
        )

    guard["last_probe_at"] = now
    guard["count"] = count + 1
    return None


def _normalize_result(
    result: StockDepthResult,
    checked_at: str,
) -> StockDepthResult:
    state = result.stock_depth_state
    estimate = result.stock_depth_estimate
    if state not in (StockDepthState.ESTIMATED, StockDepthState.UNAVAILABLE):
        estimate = None
    if state == StockDepthState.UNAVAILABLE and estimate not in (0, None):
        estimate = None
    return StockDepthResult(
        stock_depth_estimate=estimate,
        stock_depth_state=state,
        stock_depth_checked_at=checked_at,
        stock_depth_source=result.stock_depth_source or "stock-depth-provider",
        stock_depth_label=_STOCK_DEPTH_LABEL,
    )


def _apply_result(
    product: dict[str, Any],
    result: StockDepthResult,
) -> dict[str, Any]:
    updated = dict(product)
    updated.update(
        {
            "stock_depth_estimate": result.stock_depth_estimate,
            "stock_depth_state": result.stock_depth_state,
            "stock_depth_checked_at": result.stock_depth_checked_at,
            "stock_depth_source": result.stock_depth_source,
            "stock_depth_label": result.stock_depth_label,
        }
    )
    return updated


def _write_products(monitor_id: str, products: list[dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _products_file(monitor_id).write_text(
        json.dumps(products, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _products_file(monitor_id: str) -> Path:
    return DATA_DIR / f"monitored_products_{monitor_id}.json"


def _now_monotonic() -> float:
    return time.monotonic()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
