"""Pure stock rupture summary helpers and local scan artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from core.models import StockRuptureSummary


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _field(product: Any, name: str, default: Any = None) -> Any:
    if isinstance(product, dict):
        return product.get(name, default)
    return getattr(product, name, default)


def _product_dict(product: Any) -> dict[str, Any]:
    if isinstance(product, dict):
        return dict(product)
    if hasattr(product, "model_dump"):
        return product.model_dump(mode="json")
    if hasattr(product, "dict"):
        return product.dict()
    return dict(vars(product))


def compute_stock_summary(
    products: Iterable[Any],
    brand: str,
    scan_id: str | None = None,
    monitor_id: str | None = None,
    scanned_at: str | None = None,
) -> StockRuptureSummary:
    product_list = list(products)
    in_stock_count = 0
    out_of_stock_count = 0
    unknown_stock_count = 0

    for product in product_list:
        stock = _field(product, "stock_availability")
        if stock is True:
            in_stock_count += 1
        elif stock is False:
            out_of_stock_count += 1
        else:
            unknown_stock_count += 1

    verified_stock_count = in_stock_count + out_of_stock_count
    rupture_pct = (
        out_of_stock_count / verified_stock_count
        if verified_stock_count > 0
        else None
    )

    return StockRuptureSummary(
        brand=brand,
        total_products=len(product_list),
        in_stock_count=in_stock_count,
        out_of_stock_count=out_of_stock_count,
        unknown_stock_count=unknown_stock_count,
        verified_stock_count=verified_stock_count,
        rupture_pct=rupture_pct,
        scan_id=scan_id,
        monitor_id=monitor_id,
        scanned_at=scanned_at or datetime.now(timezone.utc).isoformat(),
    )


def ensure_scan_product_ids(
    products: Iterable[Any],
    brand: str,
    scan_id: str,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for product in products:
        item = _product_dict(product)
        if not item.get("scan_product_id"):
            title = (
                item.get("raw_title")
                or item.get("product_name")
                or item.get("name")
                or item.get("title")
                or ""
            )
            raw_key = "|".join(
                str(part or "")
                for part in (scan_id, brand, item.get("url"), title)
            )
            digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]
            item["scan_product_id"] = f"{scan_id}:{digest}"
        result.append(item)
    return result


def _safe_artifact_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value))


def _write_json(path: Path, payload: Any) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def persist_monitor_stock_summary(
    monitor_id: str,
    summary: StockRuptureSummary,
) -> None:
    path = DATA_DIR / f"stock_summary_{_safe_artifact_id(monitor_id)}.json"
    _write_json(path, summary.model_dump(mode="json"))


def load_monitor_stock_summary(monitor_id: str) -> StockRuptureSummary | None:
    path = DATA_DIR / f"stock_summary_{_safe_artifact_id(monitor_id)}.json"
    data = _read_json(path)
    if data is None:
        return None
    return StockRuptureSummary.model_validate(data)


def persist_category_job_stock_summaries(
    job_id: str,
    summaries: Iterable[StockRuptureSummary],
) -> None:
    path = DATA_DIR / f"category_scan_summaries_{_safe_artifact_id(job_id)}.json"
    payload = [summary.model_dump(mode="json") for summary in summaries]
    _write_json(path, payload)


def load_category_job_stock_summaries(job_id: str) -> list[StockRuptureSummary]:
    path = DATA_DIR / f"category_scan_summaries_{_safe_artifact_id(job_id)}.json"
    data = _read_json(path)
    if not isinstance(data, list):
        return []
    return [StockRuptureSummary.model_validate(item) for item in data]
