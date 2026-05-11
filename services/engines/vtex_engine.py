import logging
import asyncio
from typing import List, Dict, Any, Optional, Callable
from services.engines.base_engine import BaseEngine
from services.vtex_api_scraper import VtexApiClient

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
        Descobre a árvore de categorias real da VTEX e retorna uma lista plana.
        """
        logger.info(f"[{self.brand_key}] Buscando categorias via API VTEX...")
        
        # 1. Busca do brand_service para obter o domínio
        from services.brand_service import brand_service
        brand_data = brand_service.get_brand(self.brand_key)
        if not brand_data:
            return []

        # 2. Busca via VtexApiClient
        raw_tree = await VtexApiClient.fetch_categories(brand_data.domain)
        if not raw_tree:
            return []

        # 3. Achata a árvore (usando o helper que estava no CategoryIntelligenceService)
        return self._flatten_vtex_tree(raw_tree)

    def _flatten_vtex_tree(self, tree: List[Dict[str, Any]], parent_path: str = "") -> List[Dict[str, Any]]:
        """Achata a árvore de categorias da VTEX para uma lista simples de paths."""
        flat = []
        for node in tree:
            name = node.get("name", "")
            url = node.get("url", "")
            
            if name and url:
                flat.append({"name": name, "path": url})
            
            children = node.get("children", [])
            if children:
                flat.extend(self._flatten_vtex_tree(children, url))
        return flat

    async def get_catalog(self) -> List[Dict[str, Any]]:
        """
        Retorna o catálogo de categorias da VTEX (com cache).
        """
        from services.vtex_catalog import vtex_catalog
        return await vtex_catalog.get_categories(self.brand_key)

    async def search(
        self,
        query: str,
        max_results: int = 10,
        sort: Optional[str] = None,
        only_in_stock: bool = False
    ) -> Any:
        """
        Executa a busca via VtexApiClient usando sessão compartilhada.
        """
        from core.session_manager import SessionManager
        session = await SessionManager.get_session()
        async with VtexApiClient(self.brand_key, session=session) as client:
            return await client.search(
                query=query,
                max_results=max_results,
                sort=sort,
                only_in_stock=only_in_stock
            )

    async def get_product_details(self, product_url: str) -> Optional[Dict[str, Any]]:
        """
        Extrai detalhes de um único produto via VtexApiClient usando sessão compartilhada.
        """
        from core.session_manager import SessionManager
        session = await SessionManager.get_session()
        async with VtexApiClient(self.brand_key, session=session) as client:
            prod = await client.get_product_by_url(product_url)
            return self.validate_single(prod) if prod else None

    async def run_bulk_scrape(
        self,
        category_url: str,
        log_callback: Optional[Callable] = None,
        cancel_event: Optional[asyncio.Event] = None
    ):
        """
        Implementa o pipeline de extração paginada da VTEX com streaming.
        """
        def emit(msg):
            self.emit_log(log_callback, msg)

        async with VtexApiClient(self.brand_key) as client:
            async for product in client.scrape_category_paged(
                category_url=category_url,
                log_callback=emit,
                cancel_event=cancel_event,
                chunk_size=50
            ):
                # Aplica os Quality Gates em cada produto individualmente (Streaming)
                validated = self.validate_single(product, log_callback=log_callback)
                if validated:
                    yield validated
