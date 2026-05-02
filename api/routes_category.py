"""
Rotas de Categoria: listagem dinâmica e varredura em lote.

GET  /brands/{brand}/categories  — Categorias dinâmicas via VTEX API
POST /scrape-category            — Inicia job de varredura em lote
WS   /ws/{job_id}                — WebSocket para logs em tempo real
"""

import asyncio
import threading
import uuid

from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional

from config import BRAND_REGISTRY
from core.websocket import manager
from core.job_manager import JOB_CANCEL_FLAGS
from services.vtex_catalog import vtex_catalog

router = APIRouter()


# ---------------------------------------------------------------------------
# Utils
# ---------------------------------------------------------------------------
def clean_url(url: str) -> str:
    """Corrige caso a URL venha duplicada (ex: http...http...) ou com espaços."""
    url = url.strip()
    if url.count("http") > 1:
        idx = url.rfind("http")
        url = url[idx:]
    return url


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class ScrapeCategoryRequest(BaseModel):
    brand: str
    category_path: Optional[str] = None   # e.g. "/roupas/polos"
    custom_url: Optional[str] = None      # raw URL override

    def resolved_url(self) -> str:
        if self.custom_url:
            return clean_url(self.custom_url)
        brand_info = BRAND_REGISTRY.get(self.brand.lower(), {})
        base = brand_info.get("base_url", "")
        return f"{base}{self.category_path}"


# ---------------------------------------------------------------------------
# Orchestrator runner (background thread)
# ---------------------------------------------------------------------------
def run_orchestrator_sync(
    job_id: str,
    url: str,
    brand: str,
    main_loop: asyncio.AbstractEventLoop,
    cancel_event: threading.Event,
):
    """Runs in a background thread. Passes cancel_event to the orchestrator."""
    import asyncio as _asyncio
    from services.orchestrator import run_orchestrator

    def log_callback(msg):
        _asyncio.run_coroutine_threadsafe(manager.send_message(msg, job_id), main_loop)

    _asyncio.run(
        run_orchestrator(
            marca=brand,
            url_categoria=url,
            log_callback=log_callback,
            cancel_event=cancel_event,
        )
    )

    # Cleanup cancellation flag
    JOB_CANCEL_FLAGS.pop(job_id, None)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/brands/{brand}/categories")
async def get_categories(brand: str):
    """Retorna categorias agrupadas da marca, buscando dinamicamente da VTEX API."""
    brand_key = brand.lower()
    if brand_key not in BRAND_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Marca '{brand}' não suportada.")

    categories = await vtex_catalog.get_categories(brand_key)
    return {"brand": brand, "categories": categories}


@router.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    await manager.connect(websocket, job_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(job_id)


@router.post("/scrape-category")
async def scrape_category(request: ScrapeCategoryRequest, background_tasks: BackgroundTasks):
    url = request.resolved_url()
    if not url:
        raise HTTPException(status_code=400, detail="Forneça category_path ou custom_url.")

    job_id = str(uuid.uuid4())
    main_loop = asyncio.get_running_loop()

    cancel_event = threading.Event()
    JOB_CANCEL_FLAGS[job_id] = cancel_event

    background_tasks.add_task(
        run_orchestrator_sync, job_id, url, request.brand, main_loop, cancel_event
    )
    return {"job_id": job_id, "message": "Orquestração iniciada.", "url": url}
