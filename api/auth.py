"""
Autenticação via API Key de ambiente.

Todos os endpoints da API protegida exigem o header:
    X-API-Key: <valor de INTERNAL_API_KEY>

O frontend envia a chave via variável VITE_API_KEY (injetada no build).
Não há tela de login — o dashboard é acessado diretamente.

Para WebSockets, a validação é feita via query param ?api_key=<chave>.
"""

from fastapi import Header, HTTPException, status
from config import settings


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Dependência FastAPI: valida o X-API-Key de cada requisição."""
    if x_api_key != settings.INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key inválida ou ausente.",
        )
    return x_api_key


def verify_ws_api_key(api_key: str | None) -> bool:
    """Valida a API Key passada via query param em WebSockets."""
    return api_key == settings.INTERNAL_API_KEY
