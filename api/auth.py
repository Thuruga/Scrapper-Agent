from fastapi import Security, HTTPException, status, Request, WebSocket
from fastapi.security.api_key import APIKeyHeader
from config import settings
from typing import Optional

API_KEY_NAME = "X-API-Key"
api_key_header = API_KEY_NAME

async def get_api_key(
    request: Request = None,
    websocket: WebSocket = None
):
    """
    Valida a chave de API fornecida no header X-API-Key.
    Funciona tanto para rotas HTTP quanto para WebSockets.
    """
    api_key = None
    
    if request:
        api_key = request.headers.get(API_KEY_NAME)
    elif websocket:
        # No WebSocket, podemos receber via header no handshake ou via query param
        api_key = websocket.headers.get(API_KEY_NAME) or websocket.query_params.get("api_key")

    if api_key == settings.SCRAPER_API_KEY:
        return api_key
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Acesso negado: API Key inválida ou ausente."
    )

