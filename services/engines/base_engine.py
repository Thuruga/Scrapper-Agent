from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
import threading

class BaseEngine(ABC):
    """
    Interface abstrata para motores de e-commerce.
    Define o contrato para orquestração de scraping e inteligência.
    """

    @abstractmethod
    async def run_bulk_scrape(
        self,
        category_url: str,
        log_callback: Optional[Callable] = None,
        cancel_event: Optional[threading.Event] = None
    ) -> List[Dict[str, Any]]:
        """
        Executa uma varredura completa em uma categoria.
        """
        pass

    @abstractmethod
    async def discover_categories(self) -> List[Dict[str, Any]]:
        """
        Descobre a árvore de categorias real do motor.
        """
        pass

    @abstractmethod
    def get_engine_name(self) -> str:
        """Retorna o nome amigável do motor (ex: 'VTEX')."""
        pass
