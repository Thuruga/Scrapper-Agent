"""Monitoramento agendado de categorias com persistencia local."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from services.stock_summary_service import (
    compute_stock_summary,
    ensure_scan_product_ids,
    persist_monitor_stock_summary,
)
from services.map_evaluator_service import evaluate_map_violation
from services.map_rules_service import map_rules_service

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
MONITORS_FILE = DATA_DIR / "monitored_categories.json"

logger = logging.getLogger("CategoryMonitor")


def _load_local() -> list[dict]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not MONITORS_FILE.exists():
        return []
    try:
        return json.loads(MONITORS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_local(data: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MONITORS_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_monitored_categories() -> List[Dict[str, Any]]:
    return [item for item in _load_local() if item.get("status") == "active"]


def apply_map_metadata_to_products(
    products: List[Dict[str, Any]],
    brand: str | None,
) -> List[Dict[str, Any]]:
    rules = map_rules_service.list_rules(active_only=True)
    enriched: List[Dict[str, Any]] = []
    for product in products:
        item = dict(product)
        if brand and not item.get("brand"):
            item["brand"] = brand
        item.update(
            evaluate_map_violation(
                item,
                rules,
                brand_name=brand or item.get("brand"),
                marketplace=brand or item.get("brand"),
            )
        )
        enriched.append(item)
    return enriched


async def run_category_scan(monitor: dict) -> None:
    from services.engines.factory import engine_factory

    url = monitor.get("url")
    brand = monitor.get("brand")
    monitor_id = monitor.get("id")
    if not url or not brand or not monitor_id:
        logger.warning("Categoria monitorada invalida: %s", monitor)
        return

    engine = engine_factory.get_engine(brand)
    scraped_products = []
    try:
        async for product in engine.run_bulk_scrape(category_url=url):
            scraped_products.append(product)
            if len(scraped_products) >= 1000:
                logger.warning("Limite de 1000 produtos atingido para %s.", brand)
                break
    except Exception as exc:
        logger.error("Erro ao extrair %s: %s", url, exc)

    scraped_products = ensure_scan_product_ids(scraped_products, brand, monitor_id)
    scraped_products = apply_map_metadata_to_products(scraped_products, brand)
    map_violation_count = sum(1 for product in scraped_products if product.get("map_violation") is True)
    summary = compute_stock_summary(
        scraped_products,
        brand=brand,
        monitor_id=monitor_id,
    )
    persist_monitor_stock_summary(monitor_id, summary)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    products_file = DATA_DIR / f"monitored_products_{monitor_id}.json"
    products_file.write_text(
        json.dumps(scraped_products, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    last_scraped_at = datetime.now(timezone.utc).isoformat()
    local_data = _load_local()
    for item in local_data:
        if item.get("id") == monitor_id:
            item["last_scraped_at"] = last_scraped_at
            item["last_stock_summary"] = {
                "total_products": summary.total_products,
                "verified_stock_count": summary.verified_stock_count,
                "in_stock_count": summary.in_stock_count,
                "out_of_stock_count": summary.out_of_stock_count,
                "unknown_stock_count": summary.unknown_stock_count,
                "rupture_pct": summary.rupture_pct,
            }
            item["last_map_violation_count"] = map_violation_count
            break
    _save_local(local_data)


async def category_monitor_job() -> None:
    categories = load_monitored_categories()
    for category in categories:
        try:
            await run_category_scan(category)
        except Exception as exc:
            logger.error("Falha no monitor %s: %s", category.get("id"), exc)
