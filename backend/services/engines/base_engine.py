from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
import asyncio
import logging

logger = logging.getLogger(__name__)

class BaseEngine(ABC):
    """
    Interface abstrata para motores de e-commerce.
    Define o contrato para orquestração de scraping e inteligência.
    """

    # Whether a None return from calculate_shipping() (Tier 2) means the engine
    # genuinely attempted and was blocked (anti-bot) vs. Tier 2 being an
    # unimplemented stub for this engine. Callers (e.g. cross_marketplace_service)
    # use this to avoid labeling an unimplemented engine as "blocked".
    SHIPPING_TIER2_BLOCKS_ON_NONE: bool = True

    @abstractmethod
    async def run_bulk_scrape(
        self,
        category_url: str,
        log_callback: Optional[Callable] = None,
        cancel_event: Optional[asyncio.Event] = None,
        zipcode: Optional[str] = None,
        include_shipping: bool = False
    ):
        """
        Executa uma varredura completa em uma categoria.
        Deve renderizar (yield) produtos um a um.
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
        only_in_stock: bool = False,
        zipcode: Optional[str] = None,
        include_shipping: bool = False
    ) -> Any:
        """
        Executa uma busca por termo na plataforma.
        """
        pass

    @abstractmethod
    async def get_product_details(self, product_url: str) -> Optional[Dict[str, Any]]:
        """
        Extrai detalhes de um único produto.

        IMPORTANTE: este método existe para o fluxo de enriquecimento de seller/preço
        do cross-marketplace. Os engines de marketplace (ML/Amazon/Netshoes) retornam
        aqui APENAS `{"seller": ...}` (ou `+price`), NÃO o produto completo. Para obter
        um produto completo compatível com `RawProductBronze` (price monitor), use
        `get_pdp_product`.
        """
        pass

    async def get_pdp_product(self, product_url: str) -> Optional[Dict[str, Any]]:
        """
        Extrai o produto COMPLETO de uma PDP (Product Detail Page), no formato
        compatível com `RawProductBronze` (campos url/brand/raw_title/
        raw_description/price_full/image_url/stock_availability/...).

        Usado pelo monitor de preço (`PriceMonitorService._monitor_loop`).

        Default: delega para `get_product_details`. Engines que JÁ retornam o
        produto completo lá (VTEX/Shopify/SFCC/Wake/Zara via `validate_single`)
        funcionam sem alteração. Engines de marketplace (ML/Amazon/Netshoes),
        cujo `get_product_details` retorna apenas `{"seller": ...}`,
        SOBRESCREVEM este método para parsear o produto completo da PDP.
        """
        return await self.get_product_details(product_url)

    @abstractmethod
    async def calculate_shipping(self, product: Any, zipcode: str) -> Optional[Dict[str, Any]]:
        """
        Calcula o frete para o produto e CEP fornecido.
        Retorna um dicionário com is_free_shipping e shipping_price, ou None em caso de falha.
        """
        pass

    async def calculate_shipping_advanced(self, url: str, zipcode: str) -> Optional[Dict[str, Any]]:
        """
        Calcula o frete usando métodos avançados (Playwright) na página do produto.
        Pode ser sobreposto pelas classes filhas (Netshoes, Amazon).
        """
        raise NotImplementedError()

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
                    except Exception as ex:
                        logger.debug("Não foi possível extrair detalhes do erro de validação: %s", ex)
                
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

    @staticmethod
    def filter_mens_fashion(products: List[Any]) -> List[Any]:
        """
        Filtra os produtos para remover itens fora da categoria de moda/acessórios masculinos.
        Usa uma blocklist de termos (ex: itens femininos, carros, etc).
        """
        import re
        
        blocklist = [
            r"feminina", r"feminino", r"femininas", r"femininos", r"mulher", r"mulheres", r"menina", r"meninas",
            r"saia", r"saias", r"vestido", r"vestidos", r"blusa", r"blusas", r"sutiã", r"sutiãs", r"calcinha", r"calcinhas", 
            r"maio", r"maios", r"biquini", r"biquinis",
            r"carro", r"pneu", r"automotivo", r"moto", r"roda", r"maçaneta", r"parachoque", r"retrovisor", r"farol", 
            r"escapamento", r"capa de banco", r"tapete", r"aro",
            r"volkswagen", r"fiat", r"chevrolet", r"ford", r"hyundai", r"toyota", r"honda", r"msi", r"flex", r"1\.0", r"1\.6", 
            r"tsi", r"comfortline", r"highline", r"trendline"
        ]
        
        # Compila os padrões com word boundaries para evitar over-filtering
        patterns = [re.compile(r'\b' + bw + r'\b', re.IGNORECASE) for bw in blocklist]
        
        filtered = []
        for p in products:
            title = ""
            if isinstance(p, dict):
                title = p.get('titulo') or p.get('product_name') or p.get('raw_title') or p.get('title') or ""
            else:
                title = getattr(p, 'titulo', getattr(p, 'product_name', getattr(p, 'raw_title', getattr(p, 'title', ""))))
            
            title_lower = title.lower()
            
            is_blocked = any(pattern.search(title_lower) for pattern in patterns)
            
            if not is_blocked:
                filtered.append(p)
                
        return filtered
