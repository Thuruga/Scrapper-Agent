from typing import Optional, List
from services.engines.base_engine import BaseEngine
from services.engines.vtex_engine import VTEXEngine
from services.engines.shopify_engine import ShopifyEngine
from services.brand_service import brand_service
from core.models import BrandSearchResult

class EngineFactory:
    """
    Fábrica para instanciar a Engine correta baseada na marca.
    """

    @staticmethod
    def get_engine(brand_key: str) -> BaseEngine:
        """
        Resolve a engine para a marca. 
        """
        brand_data = brand_service.get_brand(brand_key.lower())
        
        # Lê o campo 'engine' do JSON (pode vir como dict ou objeto Pydantic)
        engine_type = "vtex"
        if brand_data:
            if isinstance(brand_data, dict):
                engine_type = brand_data.get("engine", "vtex")
            else:
                # O Pydantic model pode não ter o campo 'engine' ainda, mas o brand_service 
                # lê o JSON bruto que já contém a chave.
                engine_type = getattr(brand_data, "engine", "vtex")

        if engine_type == "shopify":
            return ShopifyEngine(brand_key)
            
        return VTEXEngine(brand_key)

    async def search_all_brands(
        self,
        query: str,
        brands: Optional[List[str]] = None,
        max_per_brand: int = 10,
        sort: Optional[str] = None,
        only_in_stock: bool = False
    ) -> List[BrandSearchResult]:
        """
        Busca `query` em todas as marcas em PARALELO usando engines.
        """
        import asyncio
        from core.models import BrandSearchResult
        
        if not query or not query.strip():
            return []

        target_brands = brands or [b.brand_key for b in brand_service.list_brands()]
        target_brands = [b.lower() for b in target_brands]

        async def _search_one(brand_key: str) -> BrandSearchResult:
            try:
                engine = self.get_engine(brand_key)
                return await engine.search(
                    query=query.strip(),
                    max_results=max_per_brand,
                    sort=sort,
                    only_in_stock=only_in_stock
                )
            except Exception as e:
                # Retorna um resultado vazio com erro para não quebrar o gather
                return BrandSearchResult(brand_key=brand_key, brand_name=brand_key, error=str(e))

        tasks = [_search_one(brand_key) for brand_key in target_brands]
        results = await asyncio.gather(*tasks)
        return list(results)

engine_factory = EngineFactory()
