import asyncio
import aiohttp
import logging
from typing import Optional, List, Dict, Any, Callable
from urllib.parse import urljoin
import yarl
from bs4 import BeautifulSoup

from core.models import RawProductBronze, BrandSearchResult, SearchProductResult
from services.brand_service import brand_service
from core.base_scraper import BaseScraper
from core.session_manager import SessionManager
from core.browser_manager import browser_manager
import json
import re

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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # Explicitamente sem 'br' (Brotli) pois aiohttp nao suporta por padrao
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
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

    async def fetch_collection_count(self, collection_handle: str) -> int:
        """Busca o total de produtos em uma colecao via endpoint JSON da colecao."""
        # O Shopify retorna metadados da colecao em /{handle}.json
        url = f"{self.base_url}/collections/{collection_handle}.json"
            
        session = await SessionManager.get_session()
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10), headers=self.headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # O campo products_count fica dentro do objeto 'collection'
                    return data.get("collection", {}).get("products_count", 0)
        except Exception as e:
            logger.warning(f"[{self.brand_key}] Nao foi possivel obter contagem para '{collection_handle}': {e}")
        return 0

    async def fetch_products_from_collection(
        self, 
        collection_handle: str, 
        limit_pages: int = 10,
        log_callback: Optional[Callable] = None
    ):
        """Extrai produtos de uma coleção específica via JSON (Streaming). Mercadão da Roupa e similares."""
        page = 1
        
        session = await SessionManager.get_session()
        while page <= limit_pages:
            # Shopify permite até 250 produtos por página no endpoint de collections
            url = f"{self.base_url}/collections/{collection_handle}/products.json?page={page}&limit=250"
            
            if log_callback:
                log_callback(f"Buscando pagina {page} da colecao '{collection_handle}'...")
                log_callback(f"🔗 URL acessada: {url}")

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
                                if log_callback:
                                    log_callback({"type": "brand_success", "message": f"Sucesso: {bronze.raw_title}"})
                                yield bronze
                        
                        page += 1
                    elif resp.status == 404:
                        # Tenta fallback para o endpoint global se a coleção não existir
                        if page == 1:
                            logger.warning(f"[{self.brand_key}] Coleção '{collection_handle}' não encontrada. Tentando global.")
                            async for prod in self.fetch_all_products(limit_pages, log_callback):
                                yield prod
                            return
                        break
                    elif resp.status == 403:
                        logger.warning(f"[{self.brand_key}] Bloqueio Shopify (403). Acionando Playwright Fallback...")
                        try:
                            html_content = await browser_manager.fetch_html(url)
                            # Extrai JSON de produtos do HTML
                            clean_json = html_content
                            if "<pre" in html_content:
                                match = re.search(r"<pre[^>]*>(.*?)</pre>", html_content, re.DOTALL)
                                if match: clean_json = match.group(1)
                            
                            data = json.loads(clean_json)
                            products_json = data.get("products", [])
                            if not products_json: break
                            for p in products_json:
                                bronze = self._map_to_bronze(p, collection_handle)
                                if bronze:
                                    if log_callback: log_callback({"type": "brand_success", "message": f"Sucesso: {bronze.raw_title}"})
                                    yield bronze
                            page += 1
                            continue 
                        except Exception as e:
                            logger.error(f"Fallback Playwright falhou: {e}")
                            break
                    else:
                        if log_callback:
                            log_callback({"type": "brand_error", "message": f"Erro {resp.status} em {url}"})
                        break
            except Exception as e:
                if log_callback:
                    log_callback({"type": "brand_error", "message": f"Erro ao paginar Shopify JSON: {e}"})
                break
                    
        return

    async def fetch_all_products(self, limit_pages: int = 5, log_callback: Optional[Callable] = None):
        """Fallback para buscar produtos globais da loja (Streaming)."""
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
                                yield bronze
                        page += 1
                    else:
                        break
            except Exception as e:
                logger.error(f"[{self.brand_key}] Erro ao buscar todos os produtos Shopify: {e}")
                break

    def _map_to_bronze(self, p: Dict[str, Any], category: str) -> Optional[RawProductBronze]:
        """Converte JSON nativo da Shopify para o modelo RawProductBronze."""
        try:
            handle = p.get("handle", "")
            if not handle:
                return None
            
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
            stock_availability = self._variants_available(variants, default=False)
            
            return RawProductBronze(
                url=urljoin(self.base_url, f"/products/{handle}"),
                brand=self.brand_key,
                raw_title=p.get("title", "Sem título"),
                raw_description=p.get("body_html", ""),
                price_full=price_old if price_old and price_old > price_full else price_full,
                price_discount=price_full if price_old and price_old > price_full else None,
                stock_availability=stock_availability,
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

    @staticmethod
    def _variants_available(variants: List[Dict[str, Any]], default: bool) -> bool:
        if not variants:
            return default
        return any(variant.get("available") is True for variant in variants)

    async def get_product_by_url(self, product_url: str) -> Optional[RawProductBronze]:
        """Extrai dados de um único produto via URL (append .json)."""
        json_url = product_url.split("?")[0] + ".json"
        session = await SessionManager.get_session()
        product_data = None
        try:
            async with session.get(json_url, timeout=aiohttp.ClientTimeout(total=15), headers=self.headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    product_data = data.get("product")
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes do produto Shopify: {e}")
        mapped = self._map_to_bronze(product_data, "Detalhes") if product_data else None
        if not mapped:
            return None

        if self._should_enrich_product_details(product_data, mapped):
            enrichment = await self._fetch_product_page_enrichment(product_url, mapped.raw_title)
            if enrichment:
                mapped = self._merge_product_enrichment(mapped, enrichment)

        return mapped

    @staticmethod
    def _should_enrich_product_details(
        product_data: Dict[str, Any],
        mapped: RawProductBronze,
    ) -> bool:
        variants = product_data.get("variants", []) if isinstance(product_data, dict) else []
        has_explicit_variant_availability = any(
            isinstance(variant.get("available"), bool)
            for variant in variants
            if isinstance(variant, dict)
        )
        return (
            not has_explicit_variant_availability
            or mapped.rating is None
            or mapped.review_count is None
        )

    async def _fetch_product_page_enrichment(
        self,
        product_url: str,
        raw_title: str,
    ) -> Dict[str, Any]:
        session = await SessionManager.get_session()
        try:
            async with session.get(
                product_url,
                timeout=aiohttp.ClientTimeout(total=15),
                headers=self.headers,
            ) as resp:
                if resp.status != 200:
                    return {}
                html = await resp.text()
        except Exception as e:
            logger.debug(f"[{self.brand_key}] Falha ao enriquecer PDP Shopify via HTML: {e}")
            return {}
        return self._extract_product_page_enrichment(html, raw_title)

    @classmethod
    def _extract_product_page_enrichment(
        cls,
        html: str,
        raw_title: str,
    ) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        enrichment: Dict[str, Any] = {}

        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            content = script.string or script.get_text(" ", strip=True)
            if not content:
                continue
            try:
                payload = json.loads(content)
            except json.JSONDecodeError:
                continue
            for node in cls._iter_json_ld_nodes(payload):
                cls._merge_json_ld_node_into_enrichment(node, enrichment, raw_title)

        return enrichment

    @staticmethod
    def _iter_json_ld_nodes(payload: Any) -> List[Dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            nodes = []
            graph = payload.get("@graph")
            if isinstance(graph, list):
                nodes.extend(item for item in graph if isinstance(item, dict))
            nodes.append(payload)
            return nodes
        return []

    @classmethod
    def _merge_json_ld_node_into_enrichment(
        cls,
        node: Dict[str, Any],
        enrichment: Dict[str, Any],
        raw_title: str,
    ) -> None:
        node_type = node.get("@type")
        if isinstance(node_type, list):
            node_types = {str(item).lower() for item in node_type}
        else:
            node_types = {str(node_type).lower()}
        if "product" not in node_types and "productgroup" not in node_types:
            return

        aggregate = node.get("aggregateRating")
        if isinstance(aggregate, dict):
            rating = cls._parse_rating_value(aggregate.get("ratingValue"))
            review_count = cls._parse_review_count_value(
                aggregate.get("reviewCount") or aggregate.get("ratingCount")
            )
            if rating is not None:
                enrichment["rating"] = rating
            if review_count is not None:
                enrichment["review_count"] = review_count

        variants = node.get("hasVariant")
        if isinstance(variants, list):
            available_sizes: List[str] = list(enrichment.get("available_sizes") or [])
            any_in_stock = False
            found_availability = False
            for variant in variants:
                if not isinstance(variant, dict):
                    continue
                in_stock = cls._offers_in_stock(variant.get("offers"))
                if in_stock is None:
                    continue
                found_availability = True
                if in_stock:
                    any_in_stock = True
                    display_name = cls._variant_display_name(variant, raw_title)
                    if display_name and display_name not in available_sizes:
                        available_sizes.append(display_name)
            if found_availability:
                enrichment["stock_availability"] = any_in_stock
            if available_sizes:
                enrichment["available_sizes"] = available_sizes
            return

        offer_state = cls._offers_in_stock(node.get("offers"))
        if offer_state is not None:
            enrichment["stock_availability"] = offer_state

    @staticmethod
    def _offers_in_stock(offers: Any) -> Optional[bool]:
        if isinstance(offers, list):
            states = [ShopifyApiClient._offers_in_stock(item) for item in offers]
            states = [state for state in states if state is not None]
            if not states:
                return None
            return any(states)
        if not isinstance(offers, dict):
            return None
        availability = str(offers.get("availability") or "").lower()
        if availability.endswith("/instock"):
            return True
        if availability.endswith("/outofstock"):
            return False
        return None

    @staticmethod
    def _variant_display_name(variant: Dict[str, Any], raw_title: str) -> Optional[str]:
        name = str(variant.get("name") or "").strip()
        if not name:
            return None
        prefix = f"{raw_title.strip()} - "
        if raw_title and name.lower().startswith(prefix.lower()):
            return name[len(prefix):].strip() or None
        return name

    @staticmethod
    def _parse_rating_value(value: Any) -> Optional[float]:
        if value in (None, ""):
            return None
        try:
            return round(float(str(value).replace(",", ".")), 1)
        except Exception:
            return None

    @staticmethod
    def _parse_review_count_value(value: Any) -> Optional[int]:
        if value in (None, ""):
            return None
        digits = re.sub(r"[^\d]", "", str(value))
        if not digits:
            return None
        try:
            return int(digits)
        except Exception:
            return None

    @staticmethod
    def _merge_product_enrichment(
        product: RawProductBronze,
        enrichment: Dict[str, Any],
    ) -> RawProductBronze:
        payload = product.model_dump()
        for key in ("stock_availability", "rating", "review_count"):
            if enrichment.get(key) is not None:
                payload[key] = enrichment[key]
        if enrichment.get("available_sizes"):
            payload["available_sizes"] = enrichment["available_sizes"]
        return RawProductBronze.model_validate(payload)

    async def scrape_category_paged(
        self, 
        category_url: str, 
        log_callback: Optional[Callable] = None,
        cancel_event: Optional[asyncio.Event] = None,
        chunk_size: int = 50
    ):
        """
        Varre uma coleção completa (Streaming).
        """
        handle = category_url.split("/")[-1] if "/" in category_url else category_url
        if not handle or handle == "products":
            handle = "all"
            
        if log_callback:
            log_callback(f"[START] Iniciando extracao Shopify para a colecao: {handle}")
            
        async for prod in self.fetch_products_from_collection(handle, log_callback=log_callback):
            if cancel_event and cancel_event.is_set():
                break
            yield prod

    async def search(
        self, 
        query: str, 
        max_results: int = 10,
        sort: Optional[str] = None,
        only_in_stock: bool = False
    ) -> BrandSearchResult:
        """Busca produtos via endpoint de busca da Shopify."""
        products = []
        session = await SessionManager.get_session()

        def _parse_shopify_price(raw) -> float:
            try:
                val = str(raw).replace(",", ".").strip()
                numeric = float(val)
                if "." not in str(raw) and numeric > 1000:
                    return round(numeric / 100, 2)
                return round(numeric, 2)
            except Exception:
                return 0.0

        import urllib.parse
        encoded_query = urllib.parse.quote(query)
        suggest_url_str = f"{self.base_url}/search/suggest.json?q={encoded_query}&resources[type]=product"
        suggest_url = yarl.URL(suggest_url_str, encoded=True)
        try:
            async with session.get(suggest_url, timeout=aiohttp.ClientTimeout(total=15), headers=self.headers) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    suggestions = data.get("resources", {}).get("results", {}).get("products", [])
                    for p in suggestions[:max_results]:
                        img = p.get("featured_image") or {}
                        image_url = img.get("url") if isinstance(img, dict) else img
                        if not image_url:
                            image_url = p.get("image")

                        available = self._variants_available(p.get("variants", []), default=True)
                        if only_in_stock and not available:
                            continue
                        
                        products.append(SearchProductResult(
                            brand=self.brand_key,
                            product_name=p.get("title") or "Sem titulo",
                            url=urljoin(self.base_url, p.get("url", "/")),
                            price_full=_parse_shopify_price(p.get("price") or 0),
                            image_url=image_url,
                            available=available
                        ))
        except Exception as e:
            logger.debug(f"[{self.brand_key}] Falha na busca via suggest.json: {e}")

        if not products:
            search_url_str = f"{self.base_url}/search.json?type=product&q={encoded_query}"
            search_url = yarl.URL(search_url_str, encoded=True)
            try:
                async with session.get(search_url, timeout=aiohttp.ClientTimeout(total=15), headers=self.headers) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        results = data.get("results", [])
                        for p in results[:max_results]:
                            variants = p.get("variants", [])
                            first_variant = variants[0] if variants else {}
                            images = p.get("images", [])
                            image_url = images[0].get("src") if images else None
                            available = self._variants_available(variants, default=False)
                            if only_in_stock and not available:
                                continue
                            products.append(SearchProductResult(
                                brand=self.brand_key,
                                product_name=p.get("title") or "Sem titulo",
                                url=urljoin(self.base_url, f"/products/{p.get('handle', '')}"),
                                price_full=_parse_shopify_price(first_variant.get("price") or 0),
                                image_url=image_url,
                                available=available,
                            ))
            except Exception as e:
                logger.debug(f"[{self.brand_key}] Falha na busca via search.json: {e}")

        from services.engines.base_engine import BaseEngine
        filtered_products = BaseEngine.filter_mens_fashion(products)

        return BrandSearchResult(
            brand_key=self.brand_key,
            brand_name=self.brand_info.brand_name if self.brand_info else self.brand_key,
            products=filtered_products,
            total_found=len(filtered_products)
        )
