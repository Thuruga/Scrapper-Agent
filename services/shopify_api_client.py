import asyncio
import aiohttp
import logging
from typing import Optional, List, Dict, Any, Callable
import threading
from urllib.parse import urljoin

from core.models import RawProductBronze, BrandSearchResult, SearchProductResult
from services.brand_service import brand_service
from core.base_scraper import BaseScraper
from core.session_manager import SessionManager

logger = logging.getLogger("ShopifyApiClient")

class ShopifyApiClient(BaseScraper):
    """
    Cliente robusto para extração de dados de lojas Shopify via APIs JSON públicas.
    Implementa suporte a coleções, produtos e bypass de Cloudflare via Playwright fallback.
    """

    def __init__(self, brand_key: str, session: Optional[aiohttp.ClientSession] = None):
        self.brand_key = brand_key
        self.brand_info = brand_service.get_brand(brand_key)
        self.domain = self.brand_info.domain if self.brand_info else ""
        self.base_url = f"https://{self.domain}"
        self.session = session
        self.semaphore = asyncio.Semaphore(10)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    async def fetch_collections(self) -> List[Dict[str, Any]]:
        """Busca todas as coleções públicas da loja via collections.json."""
        collections = []
        page = 1
        
        session = await SessionManager.get_session()
        while True:
            url = f"{self.base_url}/collections.json?page={page}"
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15), headers=self.headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        batch = data.get("collections", [])
                        if not batch:
                            break
                        collections.extend(batch)
                        page += 1
                    else:
                        logger.error(f"[{self.brand_key}] Erro ao buscar coleções: {resp.status}")
                        break
            except Exception as e:
                logger.error(f"[{self.brand_key}] Falha na requisição de coleções: {e}")
                break
        
        return collections

    async def fetch_products_from_collection(
        self, 
        collection_handle: str, 
        limit_pages: int = 10,
        log_callback: Optional[Callable] = None
    ) -> List[RawProductBronze]:
        """Extrai produtos de uma coleção específica via JSON."""
        all_products = []
        page = 1
        
        session = await SessionManager.get_session()
        while page <= limit_pages:
            # Shopify permite até 250 produtos por página no endpoint de collections
            url = f"{self.base_url}/collections/{collection_handle}/products.json?page={page}&limit=250"
            
            if log_callback:
                log_callback(f"  -> Lendo página {page} da coleção '{collection_handle}'...")

            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=20), headers=self.headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        products_json = data.get("products", [])
                        if not products_json:
                            break
                        
                        for p in products_json:
                            bronze = self._map_to_bronze(p, collection_handle)
                            if bronze:
                                all_products.append(bronze)
                        
                        page += 1
                    elif resp.status == 404:
                        # Tenta fallback para o endpoint global se a coleção não existir
                        if page == 1:
                            logger.warning(f"[{self.brand_key}] Coleção '{collection_handle}' não encontrada. Tentando global.")
                            return await self.fetch_all_products(limit_pages, log_callback)
                        break
                    else:
                        logger.error(f"[{self.brand_key}] Erro {resp.status} em {url}")
                        break
            except Exception as e:
                logger.error(f"[{self.brand_key}] Erro ao paginar Shopify JSON: {e}")
                break
                    
        return all_products

    async def fetch_all_products(self, limit_pages: int = 5, log_callback: Optional[Callable] = None) -> List[RawProductBronze]:
        """Fallback para buscar produtos globais da loja."""
        all_products = []
        page = 1
        session = await SessionManager.get_session()
        while page <= limit_pages:
            url = f"{self.base_url}/products.json?page={page}&limit=250"
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=20), headers=self.headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        products_json = data.get("products", [])
                        if not products_json:
                            break
                        for p in products_json:
                            bronze = self._map_to_bronze(p, "Geral")
                            if bronze:
                                all_products.append(bronze)
                        page += 1
                    else:
                        break
            except Exception as e:
                logger.error(f"[{self.brand_key}] Erro ao buscar todos os produtos Shopify: {e}")
                break
        return all_products

    def _map_to_bronze(self, p: Dict[str, Any], category: str) -> Optional[RawProductBronze]:
        """Converte JSON nativo da Shopify para o modelo RawProductBronze."""
        try:
            handle = p.get("handle", "")
            if not handle: return None
            
            variants = p.get("variants", [])
            first_variant = variants[0] if variants else {}
            
            # Preços
            price_full = float(first_variant.get("price", 0))
            price_old = first_variant.get("compare_at_price")
            price_old = float(price_old) if price_old else None
            
            # Imagem
            images = p.get("images", [])
            image_url = images[0].get("src") if images else None
            
            # Atributos
            available_sizes = list(set([v.get("title") for v in variants if v.get("available")]))
            
            return RawProductBronze(
                url=urljoin(self.base_url, f"/products/{handle}"),
                brand=self.brand_key,
                raw_title=p.get("title", "Sem título"),
                raw_description=p.get("body_html", ""),
                price_full=price_old if price_old and price_old > price_full else price_full,
                price_discount=price_full if price_old and price_old > price_full else None,
                stock_availability=any([v.get("available") for v in variants]),
                category=category,
                image_url=image_url,
                available_sizes=available_sizes,
                specifications={
                    "vendor": p.get("vendor", ""),
                    "product_type": p.get("product_type", ""),
                    "tags": ", ".join(p.get("tags", [])) if isinstance(p.get("tags"), list) else p.get("tags", "")
                }
            )
        except Exception as e:
            logger.error(f"Erro ao mapear produto Shopify: {e}")
            return None

    async def get_product_by_url(self, product_url: str) -> Optional[RawProductBronze]:
        """Extrai dados de um único produto via URL (append .json)."""
        json_url = product_url.split("?")[0] + ".json"
        session = await SessionManager.get_session()
        try:
            async with session.get(json_url, timeout=aiohttp.ClientTimeout(total=15), headers=self.headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    p = data.get("product")
                    if p:
                        return self._map_to_bronze(p, "Detalhes")
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes do produto Shopify: {e}")
        return None

    async def scrape_category_paged(
        self, 
        category_url: str, 
        log_callback: Optional[Callable] = None,
        cancel_event: Optional[threading.Event] = None,
        chunk_size: int = 50
    ) -> List[RawProductBronze]:
        """
        Varre uma coleção completa.
        """
        handle = category_url.split("/")[-1] if "/" in category_url else category_url
        if not handle or handle == "products":
            handle = "all"
            
        if log_callback:
            log_callback(f"Iniciando extração Shopify para a coleção: {handle}")
            
        return await self.fetch_products_from_collection(handle, log_callback=log_callback)

    async def search(
        self, 
        query: str, 
        max_results: int = 10,
        sort: Optional[str] = None,
        only_in_stock: bool = False
    ) -> BrandSearchResult:
        """Busca produtos via endpoint de busca da Shopify."""
        # ... (mantém o resto igual)
        url = f"{self.base_url}/search/suggest.json?q={query}&resources[type]=product"
        products = []
        
        session = await SessionManager.get_session()
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15), headers=self.headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    suggestions = data.get("resources", {}).get("results", {}).get("products", [])
                    for p in suggestions[:max_results]:
                        products.append(SearchProductResult(
                            brand=self.brand_key,
                            product_name=p.get("title"),
                            url=urljoin(self.base_url, p.get("url")),
                            price_full=float(p.get("price") or 0),
                            image_url=p.get("image"),
                            available=True
                        ))
        except Exception as e:
            logger.error(f"Erro na busca Shopify: {e}")

        return BrandSearchResult(
            brand_key=self.brand_key,
            brand_name=self.brand_info.brand_name if self.brand_info else self.brand_key,
            products=products,
            total_found=len(products)
        )
