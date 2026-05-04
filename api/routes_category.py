"""
Rotas de Categoria: listagem dinâmica e varredura em lote.

GET  /brands/{brand}/categories      — Categorias dinâmicas via VTEX API
GET  /canonical-categories            — Categorias canônicas de/para
POST /category-preview                — Preview do mapeamento de/para
POST /scrape-category                 — Inicia job de varredura (marca única)
POST /scrape-category-multi           — Inicia job de varredura multi-marca
WS   /ws/{job_id}                     — WebSocket para logs em tempo real
"""

import asyncio
import threading
import uuid

from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import Optional, List, Dict

from config import BRAND_REGISTRY
from core.websocket import manager
from core.job_manager import JOB_CANCEL_FLAGS
from services.vtex_catalog import vtex_catalog
from services.category_mapping import (
    get_canonical_categories,
    resolve_category_for_brands,
    get_category_preview,
)

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


class ScrapeMultiBrandRequest(BaseModel):
    """Request para varredura multi-marca com mapeamento de/para."""
    brands: List[str] = Field(
        ..., min_length=1,
        description="Lista de brand_keys para varrer (ex: ['aramis', 'reserva'])"
    )
    category_slug: str = Field(
        ..., description="Slug canônico da categoria (ex: 'camisas', 'polos')"
    )


class CategoryPreviewRequest(BaseModel):
    """Request para preview do mapeamento de/para."""
    brands: List[str]
    category_slug: str


# ---------------------------------------------------------------------------
# Orchestrator runner — Marca Única (background thread)
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
# Endpoints — Existentes (retrocompatíveis)
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


# ---------------------------------------------------------------------------
# Endpoints — Multi-Marca (novos)
# ---------------------------------------------------------------------------
@router.get("/canonical-categories")
async def list_canonical_categories():
    """Retorna todas as categorias canônicas agrupadas para o frontend."""
    return {"categories": get_canonical_categories()}


@router.post("/category-preview")
async def preview_category_mapping(request: CategoryPreviewRequest):
    """Retorna o preview do mapeamento de/para antes de iniciar a varredura."""
    preview = get_category_preview(request.category_slug, request.brands)
    if not preview:
        raise HTTPException(
            status_code=404,
            detail=f"Categoria '{request.category_slug}' não encontrada."
        )
    return preview


@router.post("/scrape-category-multi")
async def scrape_category_multi(
    request: ScrapeMultiBrandRequest,
    background_tasks: BackgroundTasks,
):
    """
    Inicia job de varredura multi-marca em paralelo.

    Resolve automaticamente o mapeamento de/para usando o slug canônico,
    garantindo que cada marca use o path VTEX correto para a mesma categoria.
    """
    # Validar marcas
    invalid_brands = [b for b in request.brands if b.lower() not in BRAND_REGISTRY]
    if invalid_brands:
        raise HTTPException(
            status_code=400,
            detail=f"Marcas não suportadas: {invalid_brands}"
        )

    # Resolver mapeamento de/para
    try:
        brand_url_map = resolve_category_for_brands(
            request.category_slug, request.brands
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Extrair apenas as URLs finais
    url_map = {bk: info["url"] for bk, info in brand_url_map.items()}
    category_label = brand_url_map[request.brands[0].lower()]["label"]

    job_id = str(uuid.uuid4())
    main_loop = asyncio.get_running_loop()

    cancel_event = threading.Event()
    JOB_CANCEL_FLAGS[job_id] = cancel_event

    # Importar e lançar o orquestrador multi-marca
    from services.orchestrator_multi import run_multi_orchestrator_sync

    background_tasks.add_task(
        run_multi_orchestrator_sync,
        job_id,
        url_map,
        category_label,
        main_loop,
        cancel_event,
    )

    return {
        "job_id": job_id,
        "message": f"Varredura multi-marca iniciada para '{category_label}'.",
        "brands": list(url_map.keys()),
        "urls": url_map,
    }
