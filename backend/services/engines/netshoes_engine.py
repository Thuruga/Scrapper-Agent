import json
import logging
import urllib.parse
import re
from typing import List, Dict, Any, Optional, Callable
import asyncio
from curl_cffi.requests import AsyncSession

from config import relevance_settings
from services.engines.base_engine import BaseEngine

logger = logging.getLogger(__name__)


class NetshoesEngine(BaseEngine):
    def __init__(self, brand_key: str = "netshoes"):
        self.brand_key = brand_key
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
        }

    def get_engine_name(self) -> str:
        return "Netshoes"

    async def run_bulk_scrape(
        self,
        category_url: str,
        log_callback: Optional[Callable] = None,
        cancel_event: Optional[asyncio.Event] = None,
        zipcode: Optional[str] = None,
        include_shipping: bool = False
    ):
        raise NotImplementedError("Netshoes engine is for search only.")

    async def discover_categories(self) -> List[Dict[str, Any]]:
        return []

    async def get_catalog(self) -> List[Dict[str, Any]]:
        return []

    async def get_product_details(self, product_url: str) -> Optional[Dict[str, Any]]:
        try:
            async with AsyncSession(impersonate="chrome120", timeout=15) as session:
                response = await session.get(product_url, headers=self.headers)
                if response.status_code == 200:
                    state = self._extract_initial_state(response.text)
                    return self._extract_seller_price(state)
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes Netshoes {product_url}: {e}")
        return None

    def _extract_seller_price(self, state: Optional[dict]) -> Dict[str, Any]:
        """
        Extrai vendedor e preço autoritativo da PDP a partir do __INITIAL_STATE__.

        O preço da PDP (``price.saleInCents``) é a fonte da verdade da variante/
        vendedor específicos — diverge do preço da listagem de busca, que aponta
        para uma variante representativa do parentSku. Sempre em centavos.
        """
        seller = "Netshoes"
        price: Optional[float] = None

        product_state = (state or {}).get("Product", {}).get("currentProduct", {})
        price_obj = product_state.get("price") or (
            product_state.get("prices", [{}])[0] if product_state.get("prices") else {}
        )

        if isinstance(price_obj, dict):
            seller_obj = price_obj.get("seller", {})
            if isinstance(seller_obj, dict) and seller_obj.get("name"):
                seller = seller_obj.get("name")

            sale_in_cents = price_obj.get("saleInCents")
            if isinstance(sale_in_cents, (int, float)) and sale_in_cents > 0:
                price = float(sale_in_cents) / 100

        return {"seller": seller, "price": price}

    def _extract_initial_state(self, html: str) -> Optional[dict]:
        """
        Extrai o window.__INITIAL_STATE__ do HTML da Netshoes.
        A Netshoes injeta um JSON grande diretamente no HTML (SSR).
        """
        match = re.search(r"window\.__INITIAL_STATE__\s*=\s*", html)
        if not match:
            return None

        start = match.end()
        # Percorre o JSON manualmente para encontrar o fim do objeto raiz
        depth = 0
        in_string = False
        escape_next = False
        i = start

        for i, char in enumerate(html[start:], start=start):
            if escape_next:
                escape_next = False
                continue
            if char == "\\" and in_string:
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            if not in_string:
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        # Fim do JSON raiz
                        json_str = html[start : i + 1]
                        try:
                            return json.loads(json_str)
                        except Exception as e:
                            logger.warning(f"Falha ao parsear __INITIAL_STATE__: {e}")
                            return None

        return None

    def _parse_from_initial_state(self, state: dict, limit: int) -> List[Dict[str, Any]]:
        """Parse dos produtos a partir do __INITIAL_STATE__ da Netshoes."""
        produtos = []
        urls_vistas = set()

        search_page = state.get("SearchPage", {})
        items = search_page.get("parentSkus", [])

        if not items:
            # Tenta outras chaves possíveis
            for key in ["products", "items", "results"]:
                items = state.get(key, [])
                if items:
                    break

        for item in items[:limit]:
            try:
                title = item.get("name", "") or item.get("productName", "")
                url_slug = item.get("productSlug", "") or item.get("slug", "")

                # Desescapa unicode (ex: \u002F -> /)
                if url_slug:
                    url_slug = url_slug.encode().decode("unicode_escape") if "\\u" in url_slug else url_slug

                # Preço — a Netshoes SEMPRE armazena em centavos (ex: 9990 = R$ 99,90)
                sale_price_raw = item.get("salePrice", 0) or item.get("price", 0)
                list_price_raw = item.get("listPrice", 0) or sale_price_raw
                try:
                    sale_price = float(sale_price_raw) / 100
                    list_price = float(list_price_raw) / 100
                except (TypeError, ValueError):
                    sale_price = 0.0
                    list_price = 0.0

                if not url_slug or sale_price <= 0:
                    continue

                url = (
                    url_slug
                    if url_slug.startswith("http")
                    else f"https://www.netshoes.com.br{url_slug}"
                )

                image = item.get("image") or ""
                if image and not image.startswith("http"):
                    image = f"https:{image}" if image.startswith("//") else f"https://www.netshoes.com.br{image}"

                seller = item.get("seller") or item.get("sellerName") or item.get("shopName") or "Netshoes"

                if url not in urls_vistas:
                    produtos.append({
                        "plataforma": "Netshoes",
                        "titulo": title,
                        "preco": sale_price,
                        "preco_original": list_price,
                        "url": url,
                        "imagem": image,
                        "seller": seller,
                    })
                    urls_vistas.add(url)

            except Exception as e:
                logger.debug(f"Erro ao parsear item Netshoes: {e}")
                continue

        return produtos

    async def search(
        self,
        query: str,
        max_results: int = 10,
        sort: Optional[str] = None,
        only_in_stock: bool = False,
        zipcode: Optional[str] = None,
        include_shipping: bool = False
    ) -> Any:  # Returns BrandSearchResult
        from core.models import BrandSearchResult, SearchProductResult, ShippingInfo

        # Monta a URL dinamicamente — gender filter configurável via RelevanceSettings
        params: dict = {"q": query}
        gender_filter = relevance_settings.NETSHOES_GENDER_FILTER.strip()
        if gender_filter:
            params["gender"] = gender_filter
        
        if sort == "recent":
            params["sort"] = "new-release"
        elif sort == "price_asc":
            params["sort"] = "lowest-first"
        elif sort == "price_desc":
            params["sort"] = "highest-first"

        base_url = "https://www.netshoes.com.br/busca"
        url = f"{base_url}?{urllib.parse.urlencode(params)}"

        try:
            async with AsyncSession(impersonate="chrome120", timeout=25) as session:
                response = await session.get(url, headers=self.headers)

                if response.status_code != 200:
                    logger.error(f"Falha HTTP Netshoes: {response.status_code}")
                    return BrandSearchResult(brand_key=self.brand_key, brand_name="Netshoes", error=f"HTTP {response.status_code}")

                html = response.text
                state = self._extract_initial_state(html)

                if state is None:
                    logger.warning(f"Netshoes: __INITIAL_STATE__ não encontrado ou inválido para '{query}'")
                    return BrandSearchResult(brand_key=self.brand_key, brand_name="Netshoes", error="__INITIAL_STATE__ not found")

                produtos_dict = self._parse_from_initial_state(state, max_results * 2)
                produtos_dict = self.filter_mens_fashion(produtos_dict)[:max_results]
                logger.info(f"Netshoes: {len(produtos_dict)} produtos encontrados para '{query}'")
                
                products = []
                for p in produtos_dict:
                    shipping = ShippingInfo(status="Calculado no checkout", price=0.0 if False else None) if include_shipping else None
                    products.append(SearchProductResult(
                        brand="Netshoes",
                        product_name=p["titulo"],
                        url=p["url"],
                        price_full=p["preco"],
                        image_url=p["imagem"],
                        available=True,
                        seller=p.get("seller", "Netshoes"),
                        shipping=shipping,
                        is_free_shipping=False,
                        shipping_price=None
                    ))
                    
                return BrandSearchResult(
                    brand_key=self.brand_key,
                    brand_name="Netshoes",
                    products=products,
                    total_found=len(products)
                )

        except Exception as e:
            logger.error(f"Erro na Netshoes: {e}")
            return BrandSearchResult(brand_key=self.brand_key, brand_name="Netshoes", error=str(e))

    async def calculate_shipping(self, product: Any, zipcode: str) -> Optional[Dict[str, Any]]:
        return await self.calculate_shipping_advanced(product, zipcode)

    def _run_playwright_shipping(self, url: str, zipcode: str) -> Optional[Dict[str, Any]]:
        from playwright.sync_api import sync_playwright
        import time
        try:
            logger.info(f"Calculando frete Netshoes via Playwright para {url} com CEP {zipcode}")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
                page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
                time.sleep(2)
                
                # Clica no "Enviar para" no header
                enviar_btn = page.query_selector('.header__cep, button:has-text("Enviar para"), a:has-text("Enviar para")')
                if enviar_btn:
                    enviar_btn.click()
                    time.sleep(1)
                
                cep_input = page.query_selector('#cepModal')
                if not cep_input:
                    cep_input = page.query_selector('input[name="cep"], input[placeholder*="CEP"]')
                
                if not cep_input:
                    logger.warning("Netshoes: Input de CEP não encontrado na página.")
                    browser.close()
                    return None
                    
                cep_input.fill(zipcode)
                
                calc_btn = page.query_selector('#cepModal + button, button:has-text("Calcular"), .shipping-calculate__btn')
                if calc_btn:
                    calc_btn.click()
                else:
                    cep_input.press("Enter")
                    
                time.sleep(4)
                
                html = page.content()
                browser.close()
                
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, "html.parser")
                shipping_elements = soup.find_all(class_=re.compile(r'fulfillment|freight|shipping|cep'))
                
                prices = []
                for el in shipping_elements:
                    text = el.text.strip()
                    if not text:
                        continue
                    
                    if re.search(r'gr[aá]tis', text, re.IGNORECASE):
                        return {
                            "is_free_shipping": True,
                            "shipping_price": 0.0
                        }
                        
                    match = re.search(r'R\$\s*(\d+,\d{2})', text)
                    if match:
                        try:
                            val = float(match.group(1).replace(",", "."))
                            prices.append(val)
                        except Exception as e:
                            logger.debug("Netshoes: falha ao converter preço de frete '%s': %s", match.group(1), e)
                            
                if prices:
                    return {
                        "is_free_shipping": False,
                        "shipping_price": min(prices)
                    }
                    
                return None
        except Exception as e:
            logger.error(f"Erro no Playwright Netshoes: {e}")
            return None

    async def calculate_shipping_advanced(self, product_url: str, zipcode: str) -> Optional[Dict[str, Any]]:
        url = product_url if isinstance(product_url, str) else getattr(product_url, "url", "")
        if not url:
            return None
        return await asyncio.to_thread(self._run_playwright_shipping, url, zipcode)
