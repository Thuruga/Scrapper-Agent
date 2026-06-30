import asyncio
from typing import List, Dict, Any, Optional, Callable
from services.engines.base_engine import BaseEngine
from services.shopify_api_client import ShopifyApiClient
from core.session_manager import SessionManager
from services.brand_service import brand_service
from services.shipping.base import ShippingCalculation, apply_shipping_calculation
from services.shipping.resolver import resolve_shipping_provider


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

        noise_handles = ["all", "frontpage", "test", "teste"]
        noise_keywords = [
            "estoque", "hidden", "policy", "terms", "quem-somos", "quem somos",
            "ate-", "até", "desconto", "off", "giftcard", "reclame", 
            "aumento-", "unt", "teste", "promo"
        ]

        filtered = []
        for c in collections:
            handle = c.get("handle", "").lower()
            title = c.get("title", "").lower()

            is_noise = (
                handle in noise_handles
                or any(k in handle for k in noise_keywords)
                or any(k in title for k in noise_keywords)
            )

            if not is_noise:
                filtered.append(
                    {
                        "name": c.get("title"),
                        "path": f"/collections/{handle}",  # Usamos o caminho relativo completo
                        "id": str(c.get("id")),
                    }
                )

        return filtered

    async def get_catalog(self) -> List[Dict[str, Any]]:
        """
        Retorna as coleções agrupadas para exibição no frontend.
        No Shopify, como não há árvore, agrupamos todas em 'Coleções'.
        """
        flat_cats = await self.discover_categories()
        return [
            {
                "group": "Coleções / Categorias",
                "items": [{"label": c["name"], "path": c["path"]} for c in flat_cats],
            }
        ]

    async def run_bulk_scrape(
        self,
        category_url: str,
        log_callback: Optional[Callable] = None,
        cancel_event: Optional[asyncio.Event] = None,
        zipcode: Optional[str] = None,
        include_shipping: bool = False
    ):
        """Executa varredura via ShopifyApiClient com streaming e logs padronizados."""
        session = await SessionManager.get_session()
        client = ShopifyApiClient(self.brand_key, session=session)

        # Wrapper para garantir contrato de logs padronizado
        def emit(msg):
            self.emit_log(log_callback, msg)

        async for product in client.scrape_category_paged(category_url, emit, cancel_event):
            # Aplica os Quality Gates antes de dar yield
            validated = self.validate_single(product, log_callback=log_callback)
            if validated:
                yield validated

    async def search(
        self,
        query: str,
        max_results: int = 10,
        sort: Optional[str] = None,
        only_in_stock: bool = False,
        zipcode: Optional[str] = None,
        include_shipping: bool = False
    ) -> Any:
        """Realiza busca via ShopifyApiClient."""
        session = await SessionManager.get_session()
        client = ShopifyApiClient(self.brand_key, session=session)
        result = await client.search(query, max_results)
        
        if include_shipping and zipcode and result and hasattr(result, 'products'):
            await self._populate_shipping(result.products, zipcode)
                
        return result

    async def get_product_details(self, product_url: str) -> Optional[Dict[str, Any]]:
        """Extrai detalhes de um único produto Shopify."""
        session = await SessionManager.get_session()
        client = ShopifyApiClient(self.brand_key, session=session)
        prod = await client.get_product_by_url(product_url)
        return self.validate_single(prod) if prod else None

    async def calculate_shipping(self, product: Any, zipcode: str) -> Optional[ShippingCalculation]:
        brand = brand_service.get_brand(self.brand_key)
        if not brand:
            return None
        provider = resolve_shipping_provider(brand)
        return await provider.calculate(product, zipcode, brand)

    async def _populate_shipping(self, products: List[Any], zipcode: str) -> None:
        semaphore = asyncio.Semaphore(3)

        async def _one(product: Any) -> None:
            async with semaphore:
                try:
                    calculation = await self.calculate_shipping(product, zipcode)
                    if calculation is not None:
                        apply_shipping_calculation(product, calculation)
                except Exception:
                    # Frete nunca deve derrubar o produto ou a busca da marca.
                    return

        await asyncio.gather(*(_one(product) for product in products))
