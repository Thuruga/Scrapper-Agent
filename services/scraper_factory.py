from typing import Dict, Type
from core.base_scraper import BaseScraper
from services.vtex_api_scraper import VtexApiClient
from services.brand_service import brand_service

class ScraperFactory:
    """
    Fábrica para instanciar o scraper correto baseado na plataforma da marca.
    """
    
    _registry: Dict[str, Type[BaseScraper]] = {
        "vtex": VtexApiClient,
        # "shopify": ShopifyScraper,  # Exemplo de expansão futura
        # "magento": MagentoScraper,
    }

    @classmethod
    def get_scraper_for_brand(cls, brand_key: str) -> BaseScraper:
        """
        Retorna uma instância do scraper adequado para a marca.
        """
        brand_info = brand_service.get_brand(brand_key)
        
        # Atualmente assume VTEX se não especificado, mas permite expansão
        platform = "vtex"
        if brand_info and hasattr(brand_info, "platform"):
            platform = brand_info.platform.lower()
            
        scraper_cls = cls._registry.get(platform)
        if not scraper_cls:
            raise ValueError(f"Plataforma '{platform}' não suportada para a marca '{brand_key}'.")
            
        return scraper_cls(brand_key)
