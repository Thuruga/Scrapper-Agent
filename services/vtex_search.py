"""
Serviço de Busca Full-Text VTEX.

Usa a API pública /api/catalog_system/pub/products/search para buscar produtos
por nome em tempo real, sem necessidade de browser (Playwright).

Vantagens vs. scraping de categoria:
  - HTTP puro: ~1s por marca vs. 30s+ com Playwright
  - Busca semântica por relevância (ScoreDESC)
  - Executado em paralelo para as 3 marcas via asyncio.gather
  - Fault-isolated: falha de uma marca não impede as demais
"""

import asyncio
import logging
import urllib.parse
from typing import List, Optional

import aiohttp
import re
from curl_cffi.requests import AsyncSession

from services.brand_service import brand_service
from core.models import BrandSearchResult, SearchProductResult
from services.vtex_catalog import _should_keep
from services.category_resolver import resolve_query_to_vtex_category_path
from services.review_service import get_bulk_reviews

logger = logging.getLogger("VTEXSearch")


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
_DEFAULT_MAX_RESULTS = 10
_SEARCH_TIMEOUT_SECONDS = 15
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# Mapeamento interno VTEX → nosso modelo
# ---------------------------------------------------------------------------

def _extract_best_price(items: list) -> tuple[Optional[float], Optional[float]]:
    """
    Extrai preço cheio e com desconto do array de SKUs da VTEX.
    Retorna (price_full, price_discount). discount=None se não houver desconto.
    """
    best_full: Optional[float] = None
    best_discount: Optional[float] = None

    for item in items:
        for seller in item.get("sellers", []):
            offer = seller.get("commertialOffer", {})
            list_price = offer.get("ListPrice") or offer.get("Price")
            sale_price = offer.get("Price")
            availability = offer.get("IsAvailable", False)

            if not sale_price or not availability:
                continue

            # Mantém o menor preço com disponibilidade
            if best_full is None or list_price < best_full:
                best_full = float(list_price) if list_price else None
                if sale_price and sale_price < (list_price or sale_price):
                    best_discount = float(sale_price)
                else:
                    best_discount = None  # Sem desconto real

    return best_full, best_discount


def _extract_image(items: list) -> Optional[str]:
    """Extrai a primeira imagem disponível dos SKUs."""
    for item in items:
        images = item.get("images", [])
        if images:
            return images[0].get("imageUrl")
    return None


def _is_available(items: list) -> bool:
    """Verifica se pelo menos um SKU está disponível."""
    for item in items:
        for seller in item.get("sellers", []):
            if seller.get("commertialOffer", {}).get("IsAvailable", False):
                return True
    return False


def _map_vtex_product(raw: dict, brand_key: str, rating: Optional[float] = None, review_count: Optional[int] = None) -> SearchProductResult:
    """Converte um produto bruto da VTEX Search API → SearchProductResult."""
    items = raw.get("items", [])
    price_full, price_discount = _extract_best_price(items)
    image_url = _extract_image(items)
    available = _is_available(items)

    # Categoria: pega o nome do departamento (primeiro nível da hierarquia)
    categories = raw.get("categories", [])
    category = None
    if categories:
        # A VTEX retorna caminhos como "/Roupas/Polos" — pega a parte mais específica
        deepest = max(categories, key=lambda c: c.count("/"))
        parts = [p for p in deepest.split("/") if p]
        
        # Filtra níveis genéricos indesejados no display
        ignore_levels = {"promoção", "promocao", "coleção", "colecao", "novidades", "geral", "todos"}
        valid_parts = [p for p in parts if p.lower() not in ignore_levels]
        category = valid_parts[-1] if valid_parts else (parts[-1] if parts else None)

    # URL do produto: Forçamos o uso do domínio público registrado na marca,
    # mesmo que a API retorne um link absoluto (ex: vtexcommercestable)
    product_url = raw.get("link", "")
    if product_url:
        brand_info = brand_service.get_brand(brand_key)
        public_domain = brand_info.domain.replace("https://", "").replace("http://", "").strip("/") if brand_info else ""
        
        # Extrai apenas o path (ex: /produto-xyz/p) caso venha absoluto
        path_match = re.search(r"https?://[^/]+(/.+)$", product_url)
        path = path_match.group(1) if path_match else product_url
        if not path.startswith("/"): path = "/" + path
        
        product_url = f"https://{public_domain}{path}"

    return SearchProductResult(
        brand=brand_key,
        product_name=raw.get("productName", ""),
        url=product_url,
        price_full=price_full,
        price_discount=price_discount,
        image_url=image_url,
        category=category,
        available=available,
        rating=rating,
        review_count=review_count,
    )


# ---------------------------------------------------------------------------
# Core: Busca em uma marca
# ---------------------------------------------------------------------------

async def _search_brand(
    session: aiohttp.ClientSession,
    brand_key: str,
    query: str,
    max_results: int,
) -> BrandSearchResult:
    """
    Executa a busca full-text na VTEX de uma única marca.
    Usa paginação segura (chunk=10) para evitar crash 500 na VTEX em queries muito amplas,
    mas continua até encontrar a quantidade pedida (limitado a 5 páginas para segurança).
    """
    brand_info = brand_service.get_brand(brand_key)
    brand_name = brand_info.brand_name if brand_info else brand_key.capitalize()

    if not brand_info:
        return BrandSearchResult(
            brand_key=brand_key,
            brand_name=brand_name,
            error=f"Marca '{brand_key}' não registrada no brand_service.",
        )

    domain = brand_info.domain.replace("https://", "").replace("http://", "").strip("/")
    
    # Sanitize query for VTEX Search API: remove hyphens and other special chars 
    # that cause internal 500 Object Reference errors
    sanitized_query = query.replace("-", " ")
    encoded_query = urllib.parse.quote(sanitized_query)

    headers = {
        "User-Agent": _USER_AGENT,
        "Accept": "application/json",
    }

    products = []
    chunk_size = 10
    max_pages = 5
    last_error = None
    
    category_path = resolve_query_to_vtex_category_path(query, brand_key)

    for page in range(max_pages):
        if len(products) >= max_results:
            break

        _from = page * chunk_size
        _to = _from + chunk_size - 1

        if category_path:
            # Modo Categoria Exata (Banana com Banana)
            # Removemos a ordenação forçada por Score para respeitar a ordem natural
            # da vitrine (ex: Lançamentos ou Mais Vendidos configurados pela marca)
            url = (
                f"https://{domain}/api/catalog_system/pub/products/search"
                f"?fq={category_path}"
                f"&_from={_from}&_to={_to}"
            )
        else:
            # Modo Full-Text (Fallback)
            url = (
                f"https://{domain}/api/catalog_system/pub/products/search"
                f"?ft={encoded_query}"
                f"&_from={_from}&_to={_to}"
                f"&O=OrderByScoreDESC"
            )

        logger.info(f"[{brand_key}] Buscando pag {page}: {url}")

        try:
            raw_products = []
            
            # Usamos AsyncSession do curl_cffi para emular um browser real e bypassar WAF (ex: Foxton)
            async with AsyncSession(impersonate="chrome", timeout=15) as curl_session:
                response = await curl_session.get(url, headers=headers)
                
                # Se retornar HTML (Headless/NextJS) ou Erro, tentamos o fallback estável
                should_retry = (
                    response.status_code == 500 or 
                    response.status_code == 404 or
                    "text/html" in response.headers.get("Content-Type", "").lower()
                )

                if should_retry:
                    logger.warning(f"[{brand_key}] Domínio principal falhou (Status {response.status_code}). Tentando Fallback Estável...")
                    
                    # Prioriza conta explícita se houver no brand_info
                    if brand_info.vtex_account:
                        account_name = brand_info.vtex_account
                    else:
                        # Inferir conta VTEX do domínio (legado/auto-discovery)
                        account_match = re.search(r"^(?:www\.)?([^.]+)", domain)
                        account_name = account_match.group(1) if account_match else domain.split(".")[0]
                    
                    stable_domain = f"{account_name}.vtexcommercestable.com.br"
                    url_fallback = url.replace(domain, stable_domain)
                    
                    # No fallback, se for 500, também limpamos o sorting
                    if response.status_code == 500:
                        url_fallback = url_fallback.replace(f"ft={encoded_query}", f"ft={encoded_query}%2A")
                        url_fallback = url_fallback.replace("&O=OrderByScoreDESC", "")
                    
                    response = await curl_session.get(url_fallback, headers=headers)
                
                if response.status_code in (200, 206):
                    try:
                        raw_products = response.json()
                    except:
                        logger.error(f"[{brand_key}] Falha ao decodificar JSON após todas as tentativas.")
                        break
                else:
                    last_error = f"HTTP {response.status_code} na busca de '{brand_key}'"
                    logger.warning(f"[{brand_key}] {last_error}")
                    break

            if not raw_products:
                # Acabaram os resultados da API
                break

            # Pre-filtrar os produtos que passam nas regras
            valid_raw_products = []
            for p in raw_products:
                if not isinstance(p, dict):
                    continue
                name = p.get("productName", "")
                link = p.get("link", "")
                categories = p.get("categories", [])
                
                if not name:
                    continue
                    
                cat_string = " ".join(categories) if categories else ""
                check_url = f"{link} {cat_string}"
                
                if not _should_keep(check_url, name, brand_key):
                    continue
                valid_raw_products.append(p)
                
            # Busca em lote as avaliacoes dos produtos que sobraram
            product_ids = [str(p.get("productId")) for p in valid_raw_products if p.get("productId")]
            reviews_dict = await get_bulk_reviews(brand_key, product_ids)
            
            for p in valid_raw_products:
                pid = str(p.get("productId"))
                rating, count = reviews_dict.get(pid, (None, None))
                mapped = _map_vtex_product(p, brand_key, rating, count)
                products.append(mapped)
                
                # Early exit assim que atingir a meta
                if len(products) >= max_results:
                    break

        except asyncio.TimeoutError:
            last_error = f"Timeout ao buscar '{brand_key}'"
            logger.error(f"[{brand_key}] {last_error}")
            break
        except Exception as e:
            last_error = f"Erro inesperado ao buscar '{brand_key}': {e}"
            logger.error(f"[{brand_key}] {last_error}")
            break

    # Retorna erro apenas se falhou completamente E não achou nenhum produto em páginas anteriores
    if last_error and not products:
        return BrandSearchResult(brand_key=brand_key, brand_name=brand_name, error=last_error)

    logger.info(f"[{brand_key}] {len(products)} produtos válidos (após filtros).")
    return BrandSearchResult(
        brand_key=brand_key,
        brand_name=brand_name,
        products=products,
        total_found=len(products),
    )


# ---------------------------------------------------------------------------
# Ponto de Entrada Público
# ---------------------------------------------------------------------------

async def search_all_brands(
    query: str,
    brands: Optional[List[str]] = None,
    max_per_brand: int = _DEFAULT_MAX_RESULTS,
) -> List[BrandSearchResult]:
    """
    Busca `query` em todas as marcas em PARALELO via asyncio.gather.

    Args:
        query: Termo de busca livre (ex: "Polo Piquet").
        brands: Lista de chaves de marca. Se None, usa todas do BRAND_REGISTRY.
        max_per_brand: Número máximo de produtos por marca (default: 10).

    Returns:
        Lista de BrandSearchResult, uma por marca, na mesma ordem de `brands`.
        Nunca lança exceção — erros ficam encapsulados em BrandSearchResult.error.
    """
    if not query or not query.strip():
        return []

    target_brands = brands or [b.brand_key for b in brand_service.list_brands()]
    # Garante chaves em lowercase
    target_brands = [b.lower() for b in target_brands]

    timeout = aiohttp.ClientTimeout(total=_SEARCH_TIMEOUT_SECONDS)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = [
            _search_brand(session, brand_key, query.strip(), max_per_brand)
            for brand_key in target_brands
        ]
        # return_exceptions=False porque cada _search_brand já captura internamente
        results: List[BrandSearchResult] = await asyncio.gather(*tasks)

    return list(results)
    return list(results)
