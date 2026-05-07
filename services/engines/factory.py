from typing import Optional
from services.engines.base_engine import BaseEngine
from services.engines.vtex_engine import VTEXEngine
from services.brand_service import brand_service

class EngineFactory:
    """
    Fábrica para instanciar a Engine correta baseada na marca.
    """

    @staticmethod
    def get_engine(brand_key: str) -> BaseEngine:
        """
        Resolve a engine para a marca. 
        Atualmente todas as marcas são tratadas como VTEX.
        """
        brand_data = brand_service.get_brand(brand_key.lower())
        
        # Futuramente, poderíamos ter brand_data.engine_type (vtex, shopify, etc)
        # Por enquanto, fallback para VTEX
        return VTEXEngine(brand_key)

engine_factory = EngineFactory()
