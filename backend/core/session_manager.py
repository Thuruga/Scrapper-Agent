import aiohttp
import asyncio
import logging
from typing import Optional

logger = logging.getLogger("SessionManager")

class SessionManager:
    """
    Gerenciador de sessões HTTP para reaproveitamento de conexões.
    """
    _session: Optional[aiohttp.ClientSession] = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_session(cls) -> aiohttp.ClientSession:
        """Retorna uma sessão compartilhada, criando-a se necessário."""
        if cls._session is None or cls._session.closed:
            async with cls._lock:
                if cls._session is None or cls._session.closed:
                    # Limite de conexões simultâneas
                    connector = aiohttp.TCPConnector(limit=50, ttl_dns_cache=300)
                    cls._session = aiohttp.ClientSession(connector=connector)
                    logger.info("[SESSION] Nova sessão compartilhada criada.")
        return cls._session

    @classmethod
    async def close_session(cls):
        """Fecha a sessão compartilhada."""
        if cls._session and not cls._session.closed:
            async with cls._lock:
                if cls._session and not cls._session.closed:
                    await cls._session.close()
                    logger.info("[SESSION] Sessão compartilhada fechada.")

session_manager = SessionManager()
