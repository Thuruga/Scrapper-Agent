"""Rotas da analise de sortimento."""

from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.models import SortimentCategoryRow, SortimentDashboardResponse
from services.sortiment_registry_service import (
    load_sortiment_categories,
    sync_sortiment_categories_from_monitor,
    update_sortiment_category,
)
from services.sortiment_snapshot_service import (
    get_sortiment_dashboard,
    try_run_sortiment_category,
)


router = APIRouter(prefix="/sortiment", tags=["Sortimento"])


class SortimentCategoryUpdate(BaseModel):
    enabled: bool

    model_config = {"extra": "forbid"}


class SortimentManualRunResponse(BaseModel):
    status: Literal["completed", "busy"]
    category_id: str
    snapshot_id: Optional[str] = None
    captured_at: Optional[str] = None


@router.get("/categories", response_model=list[SortimentCategoryRow])
async def list_sortiment_categories():
    return load_sortiment_categories()


@router.post("/categories/sync", response_model=list[SortimentCategoryRow])
async def sync_sortiment_categories():
    return sync_sortiment_categories_from_monitor()


@router.patch("/categories/{category_id}", response_model=SortimentCategoryRow)
async def patch_sortiment_category(
    category_id: str,
    data: SortimentCategoryUpdate,
):
    try:
        return update_sortiment_category(category_id, enabled=data.enabled)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/categories/{category_id}/run",
    response_model=SortimentManualRunResponse,
)
async def run_sortiment_category(category_id: str):
    try:
        status, snapshot = await try_run_sortiment_category(category_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return SortimentManualRunResponse(
        status=status,
        category_id=category_id,
        snapshot_id=snapshot.snapshot_id if snapshot else None,
        captured_at=snapshot.captured_at if snapshot else None,
    )


@router.get(
    "/categories/{category_id}/dashboard",
    response_model=SortimentDashboardResponse,
)
async def read_sortiment_dashboard(category_id: str):
    try:
        return get_sortiment_dashboard(category_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
