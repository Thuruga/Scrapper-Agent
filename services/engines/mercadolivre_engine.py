import logging
import re
from typing import Any, Dict, List, Optional
from services.engines.base_engine import BaseEngine
from core.models import BrandSearchResult, SearchProductResult

logger = logging.getLogger("MercadoLivreEngine")


class MercadoLivreEngine(BaseEngine):
    """
    Motor para integração com Mercado Livre.

    A página de listagem do ML é 100% renderizada client-side (JS), então usamos
    o BrowserManager (Playwright headless low-memory) para obter o HTML completo.

    O BrowserManager já usa --single-process, --disable-gpu, e heap V8 limitado
    a 128MB — seguro para rodar no Render free tier (512MB RAM).
    """

    def __init__(self, brand_key: str = "mercadolivre"):
        self.brand_key = brand_key
        self.base_url = "https://lista.mercadolivre.com.br"

    def get_engine_name(self) -> str:
        return "Mercado Livre"

    async def run_bulk_scrape(self, category_url: str, log_callback=None, cancel_event=None):
        pass

    async def discover_categories(self) -> List[Dict[str, Any]]:
        return []

    async def get_catalog(self) -> List[Dict[str, Any]]:
        return []

    def _parse_price(self, fraction_text: str, cents_text: str = "00") -> float:
        """Converte fração e centavos do Andes money-amount em float."""
        try:
            return float(f"{fraction_text.replace('.', '').strip()}.{cents_text.strip()}")
        except (ValueError, AttributeError):
            return 0.0

    def _parse_items(self, html: str, max_results: int) -> List[Dict]:
        """
        Extrai dados dos cards de produto do HTML renderizado pelo Playwright.
        O ML usa a estrutura poly-card com classes poly-component__*.
        """
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        results = []
        cards = soup.select("li.ui-search-layout__item")

        for card in cards[:max_results]:
            # Título — <a class="poly-component__title">
            title_el = card.select_one("a.poly-component__title, h3.poly-component__title-wrapper a")
            title = title_el.text.strip() if title_el else ""
            if not title:
                continue

            # URL do produto (href do link do título — inclui tracking, mas funciona)
            product_url = title_el.get("href", "") if title_el else ""

            # Imagem — <img class="poly-component__picture">
            img_el = card.select_one("img.poly-component__picture, img[class*='picture']")
            image_url = ""
            if img_el:
                # Pega srcset menor (thumbnail) ou src
                srcset = img_el.get("srcset", "")
                if srcset:
                    # Primeiro entry do srcset é o menor tamanho
                    first = srcset.split(",")[0].strip().split(" ")[0]
                    image_url = first
                else:
                    image_url = img_el.get("src", "")

            # Preço — primeiro .andes-money-amount__fraction é o preço de venda atual
            fractions = card.select(".andes-money-amount__fraction")
            cents_els = card.select(".andes-money-amount__cents")

            if not fractions:
                continue

            price = self._parse_price(
                fractions[0].text,
                cents_els[0].text if cents_els else "00"
            )
            if price <= 0:
                continue

            # Preço original: quando há desconto o ML mostra o preço riscado num segundo bloco
            # <s class="andes-money-amount--previous"> contém o original
            original_el = card.select_one(".andes-money-amount--previous .andes-money-amount__fraction")
            price_full = price
            price_discount = None
            if original_el:
                orig = self._parse_price(original_el.text)
                if orig > price:
                    price_full = orig
                    price_discount = price

            results.append({
                "title": title,
                "url": product_url,
                "price_full": price_full,
                "price_discount": price_discount,
                "image_url": image_url,
            })

        return results

    async def search(
        self,
        query: str,
        max_results: int = 10,
        sort: Optional[str] = None,
        only_in_stock: bool = False
    ) -> BrandSearchResult:
        """
        Busca produtos no Mercado Livre usando Playwright para renderizar a página
        (necessário pois o site é 100% client-side via React).
        """
        from core.browser_manager import browser_manager, BrowserManager
        from config import settings

        # Constrói URL de busca
        q_slug = query.strip().replace(" ", "-").lower()
        # Format: https://lista.mercadolivre.com.br/_q_polo-camisa
        search_url = f"{self.base_url}/_q_{q_slug}"
        if sort == "price_asc":
            search_url += "_PriceAsc"
        elif sort == "price_desc":
            search_url += "_PriceDesc"

        if not settings.PLAYWRIGHT_ENABLED:
            return BrandSearchResult(
                brand_key=self.brand_key,
                brand_name="Mercado Livre",
                error="Mercado Livre requer Playwright habilitado (PLAYWRIGHT_ENABLED=true)"
            )

        try:
            # ML é uma SPA React — precisa de networkidle para esperar os produtos renderizarem
            html = await BrowserManager.fetch_html(
                search_url,
                wait_until="networkidle",
                extra_sleep=2.0,
                timeout=35000
            )
        except Exception as e:
            logger.error(f"[MercadoLivre] Playwright error: {e}")
            return BrandSearchResult(
                brand_key=self.brand_key,
                brand_name="Mercado Livre",
                error=f"Falha ao carregar página: {e}"
            )

        raw_items = self._parse_items(html, max_results)
        if not raw_items:
            return BrandSearchResult(
                brand_key=self.brand_key,
                brand_name="Mercado Livre",
                error="Nenhum produto encontrado na página renderizada"
            )

        products = [
            SearchProductResult(
                brand="Mercado Livre",
                product_name=item["title"],
                url=item["url"],
                price_full=item["price_full"],
                price_discount=item["price_discount"],
                image_url=item["image_url"],
                available=True,
                available_colors=[],
                available_sizes=[]
            )
            for item in raw_items
        ]

        return BrandSearchResult(
            brand_key=self.brand_key,
            brand_name="Mercado Livre",
            products=products,
            total_found=len(products)
        )

    async def get_product_details(self, product_url: str) -> Optional[Dict[str, Any]]:
        """
        Extrai detalhes profundos de um produto ML via Playwright (Two-Tier para Monitor).
        """
        from core.browser_manager import BrowserManager
        from config import settings

        if not settings.PLAYWRIGHT_ENABLED:
            return None

        try:
            html = await BrowserManager.fetch_html(
                product_url,
                wait_selector="h1",
                timeout=30000
            )
        except Exception as e:
            logger.error(f"[MercadoLivre] Playwright error em detalhes: {e}")
            return None

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            title_el = soup.select_one("h1")
            title = title_el.text.strip() if title_el else ""

            price_int = soup.select_one(".andes-money-amount__fraction")
            price_dec = soup.select_one(".andes-money-amount__cents")
            price = self._parse_price(
                price_int.text if price_int else "0",
                price_dec.text if price_dec else "00"
            )

            # Tamanhos (picker de variações ativas)
            available_sizes = []
            for el in soup.select(
                ".ui-pdp-variations__picker-single span, "
                "[class*='variation-picker']:not([class*='disabled']) span"
            ):
                t = el.text.strip()
                if t:
                    available_sizes.append(t)

            # Cores
            available_colors = []
            for el in soup.select(
                "[class*='color-picker'] img, [aria-label*='Cor'] span"
            ):
                c = el.get("alt") or el.text.strip()
                if c:
                    available_colors.append(c)

            img_el = soup.select_one(".ui-pdp-gallery__figure img, .ui-pdp-image")
            img_url = img_el.get("src", "") if img_el else ""

            return {
                "url": product_url,
                "brand": "Mercado Livre",
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
            logger.error(f"[MercadoLivre] Erro extraindo detalhes: {e}")
            return None
