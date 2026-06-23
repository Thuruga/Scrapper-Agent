"""Rotas locais para monitoramento de categorias."""

import json
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

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

    background_tasks.add_task(run_category_scan, row)
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
        return json.loads(products_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
