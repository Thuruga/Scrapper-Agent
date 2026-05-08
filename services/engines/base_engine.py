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

    def validate_and_filter(
        self, 
        products: List[Any], 
        log_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Aplica os Quality Gates nos produtos extraídos.
        Filtra itens inválidos e emite logs de aviso.
        """
        from core.models import RawProductBronze
        from pydantic import ValidationError

        valid_products = []
        rejected_count = 0
        
        for p in products:
            try:
                # Garante que os validadores do Pydantic rodem
                if isinstance(p, dict):
                    validated = RawProductBronze.model_validate(p)
                else:
                    # Se já for um objeto, converte para dict e valida para garantir que os validators rodem
                    validated = RawProductBronze.model_validate(p if isinstance(p, dict) else p.model_dump())
                
                valid_products.append(validated.model_dump())
            except (ValidationError, ValueError) as e:
                rejected_count += 1
                title = "Produto Desconhecido"
                if isinstance(p, dict):
                    title = p.get('raw_title') or p.get('product_name') or "Sem título"
                else:
                    title = getattr(p, 'raw_title', None) or getattr(p, 'product_name', 'Sem título')
                
                # Simplifica a mensagem de erro do Pydantic
                reason = str(e)
                if hasattr(e, 'errors') and callable(getattr(e, 'errors', None)):
                    try:
                        errs = e.errors()
                        if errs:
                            reason = errs[0].get('msg', 'Erro desconhecido')
                    except:
                        pass
                
                self.emit_log(
                    log_callback, 
                    f"⚠️ [Quality Gate] '{title}' descartado. Motivo: {reason}",
                    type="brand_warning" # Usando warning para não assustar o usuário, mas informar o descarte
                )
        
        if rejected_count > 0:
            self.emit_log(log_callback, f"📊 Quality Gate finalizado: {rejected_count} itens descartados por baixa qualidade.")
            
        return valid_products

    def validate_single(self, product: Any, log_callback: Optional[Callable] = None) -> Optional[Dict[str, Any]]:
        """Valida um único produto."""
        results = self.validate_and_filter([product], log_callback)
        return results[0] if results else None
