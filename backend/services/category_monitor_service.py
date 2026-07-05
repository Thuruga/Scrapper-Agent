"""Monitoramento agendado de categorias com persistencia local."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from core.models import resolve_effective_price
from services.stock_summary_service import (
    compute_stock_summary,
    ensure_scan_product_ids,
    persist_monitor_stock_summary,
)
from services.map_evaluator_service import evaluate_map_violation
from services.map_rules_service import map_rules_service
from services.notification_service import notification_service
from services.url_utils import normalize_url

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


def _load_previous_snapshot(monitor_id: str) -> list[dict]:
    products_file = DATA_DIR / f"monitored_products_{monitor_id}.json"
    if not products_file.exists():
        return []
    try:
        data = json.loads(products_file.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _effective_price(product: dict) -> float | None:
    return resolve_effective_price(
        product.get("price_full"),
        product.get("price_discount"),
        bool(product.get("price_discount_is_delta")),
    )


def _detect_price_changes(previous: list[dict], current: list[dict]) -> list[dict]:
    """Compara preço efetivo produto a produto (chave: URL normalizada).

    Produtos que entraram ou saíram do snapshot são ignorados — só interessa
    quem estava nos dois scans com preço resolvido e valor diferente.
    """
    old_map = {
        normalize_url(p["url"]): p for p in previous if p.get("url")
    }
    changes: list[dict] = []
    for product in current:
        url = product.get("url")
        if not url:
            continue
        old_product = old_map.get(normalize_url(url))
        if old_product is None:
            continue
        old_price = _effective_price(old_product)
        new_price = _effective_price(product)
        if old_price is None or new_price is None:
            continue
        if round(old_price, 2) != round(new_price, 2):
            changes.append({
                "url": url,
                "title": product.get("raw_title"),
                "old_price": old_price,
                "new_price": new_price,
                "image_url": product.get("image_url"),
            })
    return changes


async def run_category_scan(monitor: dict, notify_completion: bool = False) -> None:
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

    # Snapshot anterior precisa ser lido ANTES de sobrescrever o arquivo,
    # senão o diff de preços compararia o novo scan com ele mesmo.
    previous_products = _load_previous_snapshot(monitor_id)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    products_file = DATA_DIR / f"monitored_products_{monitor_id}.json"
    products_file.write_text(
        json.dumps(scraped_products, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Alerta agregado de mudança de preço (1 notificação por scan, nunca por
    # produto). Primeiro scan (sem snapshot) e scrape vazio não notificam.
    if previous_products and scraped_products:
        changes = _detect_price_changes(previous_products, scraped_products)
        if changes:
            notification_service.add(
                type="category_price_change",
                title=f"Mudanças de preço — {brand}",
                message=(
                    f"{len(changes)} produto(s) mudaram de preço "
                    "na categoria monitorada."
                ),
                metadata={
                    "monitor_id": monitor_id,
                    "url": url,
                    "brand": brand,
                    "change_count": len(changes),
                    "changes": changes[:50],
                },
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

    # Término do scan inicial disparado pelo usuário. Scans agendados do
    # APScheduler não notificam término (seriam ~144 notificações/dia).
    if notify_completion:
        notification_service.add(
            type="scan_finished",
            title=f"Varredura concluída — {brand}",
            message=f"{len(scraped_products)} produto(s) coletados.",
            metadata={
                "monitor_id": monitor_id,
                "url": url,
                "brand": brand,
                "status": "success" if scraped_products else "error",
                "total_products": len(scraped_products),
            },
        )


async def category_monitor_job() -> None:
    categories = load_monitored_categories()
    for category in categories:
        try:
            await run_category_scan(category)
        except Exception as exc:
            logger.error("Falha no monitor %s: %s", category.get("id"), exc)
