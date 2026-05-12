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

import uuid

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict

from services.brand_service import brand_service
from core.websocket import manager
from core.job_manager import JOB_CANCEL_FLAGS
from services.engines.factory import engine_factory
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
        
        # Tenta resolver o path real usando o mapeamento de/para
        try:
            mapping = resolve_category_for_brands(self.category_path, [self.brand])
            return mapping[self.brand.lower()]["url"]
        except Exception:
            # Fallback para comportamento antigo se não encontrar mapeamento
            brand_info = brand_service.get_brand(self.brand.lower())
            domain = brand_info.domain if brand_info else ""
            path = self.category_path if self.category_path.startswith("/") else f"/{self.category_path}"
            return f"https://{domain}{path}"



class ScrapeMultiBrandRequest(BaseModel):
    """Request para varredura multi-marca com mapeamento de/para ou manual."""
    brands: List[str] = Field(
        ..., min_length=1,
        description="Lista de brand_keys para varrer (ex: ['aramis', 'reserva'])"
    )
    category_slug: Optional[str] = Field(
        None, description="Slug canônico da categoria (ex: 'camisas', 'polos')"
    )
    brand_category_map: Optional[Dict[str, str]] = Field(
        None, description="Mapeamento manual {brand: path/url}"
    )


class CategoryPreviewRequest(BaseModel):
    """Request para preview do mapeamento de/para."""
    brands: List[str]
    category_slug: str


# ---------------------------------------------------------------------------
# Endpoints — Existentes (retrocompatíveis)
# ---------------------------------------------------------------------------
@router.get("/brands/{brand}/categories")
async def get_categories(brand: str):
    """Retorna categorias agrupadas da marca, buscando via Engine (ex: VTEX API)."""
    brand_key = brand.lower()
    if not brand_service.get_brand(brand_key):
        raise HTTPException(status_code=404, detail=f"Marca '{brand}' não suportada.")

    engine = engine_factory.get_engine(brand_key)
    categories = await engine.get_catalog()
    return {"brand": brand, "categories": categories}


# O WebSocket foi movido para api/__init__.py (ws_router) para evitar
# o conflito com OAuth2PasswordBearer, que exige Request HTTP e não WebSocket.


@router.post("/scrape-category")
async def scrape_category(request: ScrapeCategoryRequest, background_tasks: BackgroundTasks):
    url = request.resolved_url()
    if not url:
        raise HTTPException(status_code=400, detail="Forneça category_path ou custom_url.")

    job_id = str(uuid.uuid4())
    
    cancel_event = asyncio.Event()
    JOB_CANCEL_FLAGS[job_id] = cancel_event

    from services.orchestrator import run_orchestrator
    
    async def task_wrapper():
        def log_wrapper(msg):
            asyncio.create_task(manager.send_message(msg, job_id))
            
        try:
            await run_orchestrator(
                marca=request.brand, 
                url_categoria=url, 
                log_callback=log_wrapper, 
                cancel_event=cancel_event
            )
        finally:
            JOB_CANCEL_FLAGS.pop(job_id, None)

    background_tasks.add_task(task_wrapper)
    
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
    OU usa o mapeamento manual enviado pelo frontend.
    """
    # Validar marcas
    all_brands = {b.brand_key: b for b in brand_service.list_brands()}
    invalid_brands = [b for b in request.brands if b.lower() not in all_brands]
    if invalid_brands:
        raise HTTPException(
            status_code=400,
            detail=f"Marcas não suportadas: {invalid_brands}"
        )

    url_map = {}
    category_label = "Múltiplas"

    if request.brand_category_map:
        # Modo Manual (Novo fluxo)
        for bk, path_or_url in request.brand_category_map.items():
            bk_lower = bk.lower()
            if path_or_url.startswith("http"):
                url_map[bk_lower] = clean_url(path_or_url)
            else:
                brand_info = all_brands.get(bk_lower)
                domain = brand_info.domain if brand_info else ""
                clean_path = path_or_url if path_or_url.startswith("/") else f"/{path_or_url}"
                url_map[bk_lower] = f"https://{domain}{clean_path}"
        
        if request.category_slug:
            category_label = request.category_slug.title()
    elif request.category_slug:
        # Modo Canônico (Antigo fluxo)
        try:
            brand_url_map = resolve_category_for_brands(
                request.category_slug, request.brands
            )
            url_map = {bk: info["url"] for bk, info in brand_url_map.items()}
            category_label = brand_url_map[request.brands[0].lower()]["label"]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        raise HTTPException(status_code=400, detail="Forneça category_slug ou brand_category_map.")

    job_id = str(uuid.uuid4())
    
    cancel_event = asyncio.Event()
    JOB_CANCEL_FLAGS[job_id] = cancel_event

    # Importar e lançar o orquestrador multi-marca
    from services.orchestrator_multi import run_multi_orchestrator

    background_tasks.add_task(
        run_multi_orchestrator,
        job_id=job_id,
        brand_url_map=url_map,
        category_label=category_label,
        cancel_event=cancel_event,
    )

    return {
        "job_id": job_id,
        "message": f"Varredura multi-marca iniciada para '{category_label}'.",
        "brands": list(url_map.keys()),
        "urls": url_map,
    }



