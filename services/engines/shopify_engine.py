import threading
from typing import List, Dict, Any, Optional, Callable
from services.engines.base_engine import BaseEngine
from services.shopify_api_client import ShopifyApiClient
from core.session_manager import SessionManager

class ShopifyEngine(BaseEngine):
    """
    Motor de e-commerce para a plataforma Shopify.
    Utiliza APIs JSON públicas para extração de coleções e produtos.
    """

    def __init__(self, brand_key: str):
        self.brand_key = brand_key

    def get_engine_name(self) -> str:
        return "Shopify"

    async def discover_categories(self) -> List[Dict[str, Any]]:
        """
        No Shopify, 'Collections' são tratadas como categorias.
        Retorna uma lista plana para o serviço de inteligência.
        """
        session = await SessionManager.get_session()
        client = ShopifyApiClient(self.brand_key, session=session)
        collections = await client.fetch_collections()
            
        # Transforma no formato esperado pelo CategoryIntelligenceService
        return [
            {
                "name": c.get("title"),
                "path": c.get("handle"), # Usamos o handle como path
                "id": str(c.get("id"))
            }
            for c in collections
        ]

    async def get_catalog(self) -> List[Dict[str, Any]]:
        """
        Retorna as coleções agrupadas para exibição no frontend.
        No Shopify, como não há árvore, agrupamos todas em 'Coleções'.
        """
        flat_cats = await self.discover_categories()
        return [
            {
                "group": "Coleções / Categorias",
                "items": [
                    {"label": c["name"], "path": c["path"]}
                    for c in flat_cats
                ]
            }
        ]

    async def run_bulk_scrape(
        self,
        category_url: str,
        log_callback: Optional[Callable] = None,
        cancel_event: Optional[threading.Event] = None
    ) -> List[Dict[str, Any]]:
        """Executa varredura via ShopifyApiClient com logs padronizados."""
        session = await SessionManager.get_session()
        client = ShopifyApiClient(self.brand_key, session=session)
        
        # Wrapper para garantir contrato de logs padronizado
        def emit(msg):
            self.emit_log(log_callback, msg)

        products = await client.scrape_category_paged(category_url, emit, cancel_event)
        return [p.model_dump() for p in products]

    async def search(
        self,
        query: str,
        max_results: int = 10,
        sort: Optional[str] = None,
        only_in_stock: bool = False
    ) -> Any:
        """Realiza busca via ShopifyApiClient."""
        session = await SessionManager.get_session()
        client = ShopifyApiClient(self.brand_key, session=session)
        return await client.search(query, max_results)

    async def get_product_details(self, product_url: str) -> Optional[Dict[str, Any]]:
        """
        TODO: Implementar extração de detalhes via .js ou .json do produto individual.
        Por enquanto, o bulk_scrape já traz dados suficientes.
        """
        return None
