"""
API Router Aggregator.

Registra todos os sub-routers em um único router principal.
Autenticação: X-API-Key header em todos os endpoints protegidos.
"""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from typing import Optional
from api.auth import verify_api_key, verify_ws_api_key

from api.routes_product import router as product_router
from api.routes_category import router as category_router
from api.routes_jobs import router as jobs_router
from api.routes_search import router as search_router
from api.routes_brands import router as brands_router
from api.routes_monitor import router as monitor_router

from api.routes_history import router as history_router
from api.routes_banners import router as banners_router

# Todos os endpoints da API exigem X-API-Key
api_router = APIRouter(dependencies=[Depends(verify_api_key)])

api_router.include_router(product_router)
api_router.include_router(category_router)
api_router.include_router(jobs_router)
api_router.include_router(search_router)
api_router.include_router(brands_router)
api_router.include_router(monitor_router)
api_router.include_router(history_router)
api_router.include_router(banners_router)

# Router público (health-check, WebSocket, etc.)
public_router = APIRouter()
# ---------------------------------------------------------------------------
# WebSocket — autenticação via query param ?api_key=<chave>
# ---------------------------------------------------------------------------
from core.websocket import manager

_ws_router = APIRouter()

@_ws_router.websocket("/ws/{job_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    job_id: str,
    api_key: Optional[str] = None,
):
    from config import settings
    if not verify_ws_api_key(api_key):
        await websocket.close(code=4003, reason="API Key inválida")
        return

    await manager.connect(websocket, job_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(job_id)

public_router.include_router(_ws_router)
