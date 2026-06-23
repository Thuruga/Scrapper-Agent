"""Authenticated API for desktop banner extraction, review and history."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from core.banner_models import BannerRun, BannerRunStatus
from services.banner_job_service import banner_job_service
from services.banner_report_service import BannerReportService
from services.banner_storage_service import banner_storage_service


router = APIRouter(prefix="/banners", tags=["Banners"])
banner_report_service = BannerReportService(banner_storage_service)


class StartBannerJobRequest(BaseModel):
    brands: list[str] = Field(min_length=1)


class ApproveBannerRunRequest(BaseModel):
    banner_ids: list[str] = Field(min_length=1)


def _run_or_404(run_id: str) -> BannerRun:
    try:
        run = banner_storage_service.get_run(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not run:
        raise HTTPException(status_code=404, detail="Extração não encontrada")
    return run


@router.post("/jobs", status_code=202)
async def start_banner_job(request: StartBannerJobRequest, background_tasks: BackgroundTasks):
    try:
        run = banner_job_service.create_job(request.brands)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    background_tasks.add_task(banner_job_service.run_job, run.run_id)
    return {"job_id": run.run_id, "status": run.status, "run": run}


@router.get("/jobs/{run_id}", response_model=BannerRun)
async def get_banner_job(run_id: str):
    return _run_or_404(run_id)


@router.post("/jobs/{run_id}/stop", status_code=202)
async def stop_banner_job(run_id: str):
    run = _run_or_404(run_id)
    if run.status != BannerRunStatus.RUNNING or not banner_job_service.stop_job(run_id):
        raise HTTPException(status_code=409, detail="A extração não está em andamento")
    return {"job_id": run_id, "message": "Parada solicitada"}


@router.post("/jobs/{run_id}/approve", response_model=BannerRun)
async def approve_banner_job(run_id: str, request: ApproveBannerRunRequest):
    _run_or_404(run_id)
    try:
        run = banner_storage_service.approve_run(run_id, request.banner_ids)
        banner_report_service.generate(run)
        return run
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/history")
async def list_banner_history():
    return banner_storage_service.list_history()


@router.get("/history/{run_id}", response_model=BannerRun)
async def get_banner_history(run_id: str):
    run = _run_or_404(run_id)
    if run.status != BannerRunStatus.COMPLETED:
        raise HTTPException(status_code=404, detail="Histórico não encontrado")
    return run


@router.delete("/history/{run_id}", status_code=204)
async def delete_banner_history(run_id: str):
    try:
        deleted = banner_storage_service.delete_history(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Histórico não encontrado")


@router.get("/assets/{run_id}/{banner_id}")
async def get_banner_asset(run_id: str, banner_id: str):
    run = _run_or_404(run_id)
    banner = next((item for item in run.banners if item.banner_id == banner_id), None)
    if not banner:
        raise HTTPException(status_code=404, detail="Banner não encontrado")
    try:
        path = banner_storage_service.resolve_asset(banner.asset)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado") from exc
    return FileResponse(
        path, media_type=banner.asset.content_type,
        headers={"Content-Disposition": f'inline; filename="{banner.friendly_filename}"'},
    )


@router.get("/screenshots/{run_id}/{brand_key}")
async def get_banner_screenshot(run_id: str, brand_key: str):
    run = _run_or_404(run_id)
    progress = run.brand_progress.get(brand_key)
    if not progress or not progress.screenshot_asset:
        raise HTTPException(status_code=404, detail="Captura não encontrada")
    try:
        path = banner_storage_service.resolve_asset(progress.screenshot_asset)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Captura não encontrada") from exc
    return FileResponse(path, media_type=progress.screenshot_asset.content_type)


@router.get("/runs/{run_id}/reports/{report_format}")
async def get_banner_report(run_id: str, report_format: str):
    _run_or_404(run_id)
    try:
        path = banner_report_service.resolve(run_id, report_format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Relatório não encontrado") from exc
    media = {"json": "application/json", "csv": "text/csv", "html": "text/html"}[report_format]
    return FileResponse(path, media_type=media, filename=path.name)

