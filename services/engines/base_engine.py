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
    async def get_catalog(self) -> List[Dict[str, Any]]:
        """
        Retorna o catálogo de categorias formatado para o frontend.
        """
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int = 10,
        sort: Optional[str] = None,
        only_in_stock: bool = False
    ) -> Any:
        """
        Executa uma busca por termo na plataforma.
        """
        pass

    @abstractmethod
    async def get_product_details(self, product_url: str) -> Optional[Dict[str, Any]]:
        """
        Extrai detalhes de um único produto.
        """
        pass

    @abstractmethod
    def get_engine_name(self) -> str:
        """Retorna o nome amigável do motor (ex: 'VTEX')."""
        pass

    def emit_log(self, callback: Optional[Callable], message: Any, type: str = "info", **kwargs):
        """
        Padroniza a emissão de logs para o frontend.
        Garante que a mensagem seja sempre um dicionário estruturado.
        """
        if not callback:
            return
            
        if isinstance(message, dict):
            # Se já for um dict, apenas garante que os campos extras sejam mesclados
            payload = message.copy()
            if kwargs:
                payload.update(kwargs)
            callback(payload)
        else:
            # Se for string ou outro tipo, encapsula no formato padrão
            payload = {"type": type, "message": str(message)}
            if kwargs:
                payload.update(kwargs)
            callback(payload)
