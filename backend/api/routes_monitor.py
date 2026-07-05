"""Rotas locais para monitoramento de categorias."""

import json
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from config import settings
from services.review_service import fetch_scan_product_review_comments
from services.stock_depth_service import probe_scan_product_stock_depth
from services.stock_summary_service import load_monitor_stock_summary

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
MONITORS_FILE = DATA_DIR / "monitored_categories.json"

router = APIRouter(prefix="/monitor", tags=["Monitoramento de Categorias"])


class CategoryMonitorCreate(BaseModel):
    url: str
    brand: str


class CategoryMonitorResponse(BaseModel):
    id: str
    url: str
    brand: str
    status: str
    last_scraped_at: Optional[str] = None
    last_map_violation_count: Optional[int] = None


class ReviewCommentsRequest(BaseModel):
    max_pages: Optional[int] = None

    model_config = {"extra": "forbid"}


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


@router.post("/category", response_model=CategoryMonitorResponse)
async def create_category_monitor(
    data: CategoryMonitorCreate, background_tasks: BackgroundTasks
):
    row = {
        "id": str(uuid.uuid4()),
        "url": data.url,
        "brand": data.brand,
        "status": "active",
    }
    local_data = _load_local()
    local_data.append(row)
    _save_local(local_data)

    from services.category_monitor_service import run_category_scan

    background_tasks.add_task(run_category_scan, row, notify_completion=True)
    return CategoryMonitorResponse(**row)


@router.get("/categories", response_model=List[CategoryMonitorResponse])
async def list_monitored_categories():
    return _load_local()


@router.delete("/category/{monitor_id}")
async def delete_category_monitor(monitor_id: str):
    _save_local([item for item in _load_local() if item.get("id") != monitor_id])
    products_file = DATA_DIR / f"monitored_products_{monitor_id}.json"
    products_file.unlink(missing_ok=True)
    return {"status": "ok", "message": "Monitor deletado com sucesso."}


@router.get("/category/{monitor_id}/products")
async def get_monitored_products(monitor_id: str):
    products_file = DATA_DIR / f"monitored_products_{monitor_id}.json"
    if not products_file.exists():
        return []
    try:
        products = json.loads(products_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    monitor = next((item for item in _load_local() if item.get("id") == monitor_id), None)
    from services.category_monitor_service import apply_map_metadata_to_products

    return apply_map_metadata_to_products(products, monitor.get("brand") if monitor else None)


@router.post("/category/{monitor_id}/products/{scan_product_id}/stock-depth")
async def probe_monitored_product_stock_depth(
    monitor_id: str,
    scan_product_id: str,
):
    try:
        result = await probe_scan_product_stock_depth(monitor_id, scan_product_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result.model_dump(mode="json")


@router.post("/category/{monitor_id}/products/{scan_product_id}/reviews")
async def fetch_monitored_product_reviews(
    monitor_id: str,
    scan_product_id: str,
    data: ReviewCommentsRequest = ReviewCommentsRequest(),
):
    max_pages = _cap_review_pages(data.max_pages)
    try:
        result = await fetch_scan_product_review_comments(
            monitor_id,
            scan_product_id,
            max_pages=max_pages,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result.model_dump(mode="json")


@router.get("/category/{monitor_id}/stock-summary")
async def get_monitor_stock_summary(monitor_id: str):
    summary = load_monitor_stock_summary(monitor_id)
    if summary is None:
        raise HTTPException(
            status_code=404,
            detail="Resumo de estoque nao encontrado.",
        )
    return summary.model_dump(mode="json")


def _cap_review_pages(max_pages: Optional[int]) -> int:
    configured_max = max(1, int(settings.MAX_REVIEW_PAGES))
    if max_pages is None:
        return configured_max
    return min(max(1, int(max_pages)), configured_max)
