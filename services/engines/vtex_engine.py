import logging
import asyncio
import threading
from typing import List, Dict, Any, Optional, Callable
from services.engines.base_engine import BaseEngine
from services.vtex_api_scraper import VtexApiClient
from services.category_intelligence import category_intelligence

logger = logging.getLogger("VTEXEngine")

class VTEXEngine(BaseEngine):
    """
    Motor especializado em plataformas VTEX.
    """

    def __init__(self, brand_key: str):
        self.brand_key = brand_key

    def get_engine_name(self) -> str:
        return "VTEX"

    async def discover_categories(self) -> List[Dict[str, Any]]:
        """
        Usa o serviço de inteligência para descobrir categorias VTEX.
        """
        logger.info(f"[{self.brand_key}] Iniciando descoberta de categorias VTEX...")
        return await category_intelligence.discover_and_map(self.brand_key)

    async def run_bulk_scrape(
        self,
        category_url: str,
        log_callback: Optional[Callable] = None,
        cancel_event: Optional[threading.Event] = None
    ) -> List[Dict[str, Any]]:
        """
        Implementa o pipeline de extração paginada da VTEX.
        """
        def emit_log(msg):
            if log_callback:
                if isinstance(msg, dict):
                    log_callback(msg)
                else:
                    log_callback({"type": "info", "message": str(msg)})

        async with VtexApiClient(self.brand_key) as client:
            resultados = await client.scrape_category_paged(
                category_url=category_url,
                log_callback=emit_log,
                cancel_event=cancel_event,
                chunk_size=50
            )
            
            return [res.model_dump() for res in resultados if res]
