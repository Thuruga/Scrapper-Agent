import asyncio
import logging
from typing import List, Optional

from services.brand_service import brand_service
from core.models import BrandSearchResult
from services.scraper_factory import ScraperFactory

logger = logging.getLogger("SearchService")

async def search_all_brands(
    query: str,
    brands: Optional[List[str]] = None,
    max_per_brand: int = 10,
    sort: Optional[str] = None,
    only_in_stock: bool = False
) -> List[BrandSearchResult]:
    """
    Busca `query` em todas as marcas em PARALELO usando a ScraperFactory.
    """
    if not query or not query.strip():
        return []

    target_brands = brands or [b.brand_key for b in brand_service.list_brands()]
    target_brands = [b.lower() for b in target_brands]

    async def _search_one(brand_key: str):
        try:
            scraper = ScraperFactory.get_scraper_for_brand(brand_key)
            return await scraper.search(
                query=query.strip(),
                max_results=max_per_brand,
                sort=sort,
                only_in_stock=only_in_stock
            )
        except Exception as e:
            logger.error(f"Erro ao buscar na marca {brand_key}: {e}")
            return BrandSearchResult(brand_key=brand_key, brand_name=brand_key, error=str(e))

    tasks = [_search_one(brand_key) for brand_key in target_brands]
    results = await asyncio.gather(*tasks)

    return list(results)
