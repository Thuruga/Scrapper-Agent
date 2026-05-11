"""
API Router Aggregator.

Registra todos os sub-routers em um único router principal.
"""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from typing import Optional
from api.auth import get_current_user
from api.routes_auth import router as auth_router

from api.routes_product import router as product_router
from api.routes_category import router as category_router
from api.routes_jobs import router as jobs_router
from api.routes_search import router as search_router
from api.routes_brands import router as brands_router

api_router = APIRouter(dependencies=[Depends(get_current_user)])

# Endpoints protegidos
api_router.include_router(product_router)
api_router.include_router(category_router)
api_router.include_router(jobs_router)
api_router.include_router(search_router)
api_router.include_router(brands_router)

# Endpoint de autenticação (não protegido pelo api_router principal)
public_router = APIRouter()
public_router.include_router(auth_router, prefix="/api/auth")

# ---------------------------------------------------------------------------
# WebSocket — Router separado SEM dependência de auth HTTP
# O OAuth2PasswordBearer exige um objeto Request, que não existe em WebSocket.
# A autenticação é feita via query param ?token=<jwt> enviado pelo frontend.
# ---------------------------------------------------------------------------
from core.websocket import manager

_ws_router = APIRouter()

@_ws_router.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str, token: Optional[str] = None):
    # Validação opcional do token via query param
    # (o frontend deve passar ?token=<jwt>)
    await manager.connect(websocket, job_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(job_id)

public_router.include_router(_ws_router)
