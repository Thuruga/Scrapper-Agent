import logging
import json
import re
from typing import Any, Dict, List, Optional
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
from services.engines.base_engine import BaseEngine
from core.models import BrandSearchResult, SearchProductResult

logger = logging.getLogger("NetshoesEngine")


class NetshoesEngine(BaseEngine):
    """
    Motor para integração com Netshoes.
    Extrai dados do dataLayer GTM (ecommerce.impressions) via curl_cffi.
    Playwright usado somente como fallback final para pagar RAM mínima no Render.
    """

    def __init__(self, brand_key: str = "netshoes"):
        self.brand_key = brand_key
        self.base_url = "https://www.netshoes.com.br"

    def get_engine_name(self) -> str:
        return "Netshoes"

    async def run_bulk_scrape(self, category_url: str, log_callback=None, cancel_event=None):
        pass

    async def discover_categories(self) -> List[Dict[str, Any]]:
        return []

    async def get_catalog(self) -> List[Dict[str, Any]]:
        return []

    def _fetch_sync(self, url: str) -> Optional[str]:
        """Faz a requisição sync via curl_cffi (com TLS fingerprinting)."""
        try:
            resp = cffi_requests.get(
                url,
                impersonate="chrome120",
                timeout=15
            )
            if resp.status_code == 200:
                return resp.text
            logger.warning(f"[Netshoes] HTTP {resp.status_code} em {url}")
        except Exception as e:
            logger.warning(f"[Netshoes] curl_cffi error: {e}")
        return None

    def _parse_impressions(self, html: str, max_results: int = 10) -> List[Dict]:
        """
        Extrai produtos do bloco GTM ecommerce.impressions embutido na página.
        Retorna lista de dicts com os dados brutos de cada produto.
        """
        matches = re.findall(r'"impressions":\[(.*?)\]', html, re.DOTALL)
        if not matches:
            return []
        try:
            items = json.loads("[" + matches[0] + "]")
            return items[:max_results]
        except json.JSONDecodeError as e:
            logger.warning(f"[Netshoes] JSON decode error in impressions: {e}")
            return []

    def _build_product_url(self, item: Dict) -> str:
        """
        Constrói a URL do produto a partir do id do item GTM.
        Formato: https://www.netshoes.com.br/{slug}/{id}
        """
        item_id = item.get("id", "")
        if not item_id:
            return self.base_url
        slug = item.get("name", item_id).lower()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"\s+", "-", slug.strip())
        slug = slug[:60]
        return f"{self.base_url}/{slug}/{item_id}"

    def _get_image_url(self, html: str, item_id: str) -> str:
        """Extrai a URL de imagem para o item_id a partir do HTML."""
        # Os itens têm o skuFather (ex: OB2-0052-804). Tentamos qualquer imagem do produto.
        # Padrão: https://static.netshoes.com.br/produtos/{slug}/{sku}/{sku_detail}.jpg
        img_matches = re.findall(
            r"(https://static\.netshoes\.com\.br/produtos/[^\"']+/" + re.escape(item_id.split("-")[0]) + r"[^\"']+\.jpg)[^\"']*",
            html
        )
        if img_matches:
            return img_matches[0]
        return ""

    async def search(
        self,
        query: str,
        max_results: int = 10,
        sort: Optional[str] = None,
        only_in_stock: bool = False
    ) -> BrandSearchResult:
        """
        Busca produtos na Netshoes extraindo dados do GTM dataLayer.
        """
        sort_param = ""
        if sort == "price_asc":
            sort_param = "&sort=lowest-price"
        elif sort == "price_desc":
            sort_param = "&sort=highest-price"

        search_url = f"{self.base_url}/busca?q={query}{sort_param}"

        html = self._fetch_sync(search_url)
        if not html:
            return BrandSearchResult(
                brand_key=self.brand_key,
                brand_name="Netshoes",
                error="Falha ao obter HTML da página de busca"
            )

        raw_items = self._parse_impressions(html, max_results)
        if not raw_items:
            # Checamos se a página foi carregada mas sem resultados (searchResults:0)
            dl_match = re.search(r'"searchResults":(\d+)', html)
            sr_count = int(dl_match.group(1)) if dl_match else -1
            msg = f"Sem resultados (searchResults={sr_count})" if sr_count == 0 else "impressions não encontrados no HTML"
            return BrandSearchResult(brand_key=self.brand_key, brand_name="Netshoes", error=msg)

        products = []
        for item in raw_items:
            price_raw = item.get("price")
            discount_raw = item.get("discount")

            try:
                price = float(price_raw) if price_raw is not None else None
            except (ValueError, TypeError):
                price = None

            if not price or price <= 0:
                continue

            # discount é a porcentagem de desconto (ex: 6000 = 60%). Não é o preço com desc.
            # Usamos price como preço de venda. Para preço original, calculamos:
            discount_pct_str = item.get("discountPercent", "")
            price_full = price
            price_discount = None
            if discount_pct_str:
                try:
                    pct = float(discount_pct_str.replace("%", "").strip()) / 100
                    if pct > 0:
                        price_full = round(price / (1 - pct), 2)
                        price_discount = price
                except (ValueError, TypeError):
                    pass

            item_id = item.get("id", "")
            image_url = self._get_image_url(html, item_id)
            product_url = self._build_product_url(item)

            products.append(
                SearchProductResult(
                    brand="Netshoes",
                    product_name=item.get("name", "Produto"),
                    url=product_url,
                    price_full=price_full,
                    price_discount=price_discount,
                    image_url=image_url,
                    available=True,  # Se apareceu na busca, está disponível
                    available_colors=[],
                    available_sizes=[]
                )
            )

        return BrandSearchResult(
            brand_key=self.brand_key,
            brand_name="Netshoes",
            products=products,
            total_found=len(products)
        )

    async def get_product_details(self, product_url: str) -> Optional[Dict[str, Any]]:
        """
        Extrai detalhes profundos de um produto Netshoes (Two-Tier para Monitor).
        """
        html = self._fetch_sync(product_url)
        if not html:
            return None

        try:
            soup = BeautifulSoup(html, "html.parser")

            title_el = soup.select_one("h1") or soup.select_one(".product-name")
            title = title_el.text.strip() if title_el else ""

            # Preço: busca spans de preço
            price_el = (
                soup.select_one('[class*="sale-price"]') or
                soup.select_one('[class*="default-price"]') or
                soup.select_one('[itemprop="price"]')
            )
            price = 0.0
            if price_el:
                pt = price_el.get("content") or price_el.text
                pt = pt.replace("R$", "").replace(".", "").replace(",", ".").strip()
                try:
                    price = float(pt)
                except ValueError:
                    pass

            # Tamanhos disponíveis
            available_sizes = []
            for el in soup.select('[class*="sku"][data-available="true"], [class*="size-item"]:not([class*="unavailable"])'):
                t = el.text.strip()
                if t:
                    available_sizes.append(t)

            # Cores disponíveis
            available_colors = []
            for el in soup.select('[class*="color-list"] a, [class*="color-item"]'):
                c = el.get("title") or el.text.strip()
                if c:
                    available_colors.append(c)

            img_el = soup.select_one('[class*="photo"] img, .product-image img')
            img_url = img_el.get("src", "") if img_el else ""

            return {
                "url": product_url,
                "brand": "Netshoes",
                "raw_title": title,
                "raw_description": "",
                "price_full": price,
                "price_discount": None,
                "stock_availability": price > 0,
                "available_colors": available_colors,
                "available_sizes": available_sizes,
                "image_url": img_url
            }
        except Exception as e:
            logger.error(f"[Netshoes] Erro extraindo detalhes de {product_url}: {e}")
            return None
