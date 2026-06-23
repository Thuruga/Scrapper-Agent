"""
Amazon Search Engine.

Estratégia de busca:
  1. curl_cffi (rápido, impersonation de Chrome)
  2. Playwright (fallback quando Amazon retorna 503/CAPTCHA)

A Amazon bloqueia bots com frequência via CAPTCHA (503). O Playwright com
stealth mitiga parcialmente esse problema em ambiente local/dev.

Em produção com alto volume, considere usar um proxy residencial
(BRIGHTDATA_PROXY_URL ou SCRAPERAPI_KEY em config.py).
"""

import logging
import urllib.parse
import re
from typing import List, Dict, Any, Optional, Callable
import asyncio
from curl_cffi.requests import AsyncSession
from bs4 import BeautifulSoup

from core.models import BrandSearchResult, SearchProductResult, ShippingInfo
from config import relevance_settings
from services.engines.base_engine import BaseEngine
from services.engines.seller_extraction import parse_amazon_seller_from_html, MARKETPLACE_DEFAULT_SELLER

logger = logging.getLogger(__name__)


class AmazonEngine(BaseEngine):
    def __init__(self, brand_key: str = "amazon"):
        self.brand_key = brand_key
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Upgrade-Insecure-Requests": "1",
        }

    def get_engine_name(self) -> str:
        return "Amazon"

    async def run_bulk_scrape(
        self,
        category_url: str,
        log_callback: Optional[Callable] = None,
        cancel_event: Optional[asyncio.Event] = None,
        zipcode: Optional[str] = None,
        include_shipping: bool = False
    ):
        raise NotImplementedError("Amazon engine is for search only.")

    async def discover_categories(self) -> List[Dict[str, Any]]:
        return []

    async def get_catalog(self) -> List[Dict[str, Any]]:
        return []

    async def get_product_details(self, product_url: str) -> Optional[Dict[str, Any]]:
        try:
            async with AsyncSession(impersonate="chrome120", timeout=15) as session:
                response = await session.get(product_url, headers=self.headers)
                if response.status_code == 200:
                    seller = parse_amazon_seller_from_html(response.text) or MARKETPLACE_DEFAULT_SELLER["Amazon"]
                    return {"seller": seller}
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes Amazon {product_url}: {e}")
        return None

    def _parse_html(self, html: str, limit: int) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        produtos = []
        urls_vistas = set()
        for item in soup.find_all(
            "div", attrs={"data-component-type": "s-search-result"}
        ):
            if len(produtos) >= limit:
                break
            try:
                a_tag = (
                    item.find_all("a", class_=re.compile(r"a-text-normal")) or [None]
                )[0]
                if not a_tag:
                    for h2 in item.find_all("h2"):
                        a_cand = h2.find_parent("a") or h2.find("a")
                        if a_cand:
                            a_tag = a_cand
                            break
                if not a_tag:
                    continue
                title = a_tag.text.replace("Anúncio patrocinado –", "").strip()
                url = a_tag["href"]
                if "/sspa/click" in url and "url=" in url:
                    url = urllib.parse.unquote(url.split("url=")[1].split("&")[0])
                if url.startswith("/"):
                    url = f"https://www.amazon.com.br{url}"
                url = url.split("?")[0].split("/ref=")[0]
                price_txt = (
                    item.find("span", class_="a-offscreen")
                    .text.replace("R$", "")
                    .replace(".", "")
                    .replace(",", ".")
                    .strip()
                )
                price = float(re.search(r"\d+\.\d+", price_txt).group())

                img_tag = item.find("img", class_="s-image")
                image_url = img_tag["src"] if img_tag else None

                seller = "Amazon"

                if url not in urls_vistas and price > 0:
                    produtos.append(
                        {
                            "plataforma": "Amazon",
                            "titulo": title,
                            "preco": price,
                            "url": url,
                            "imagem": image_url,
                            "seller": seller,
                        }
                    )
                    urls_vistas.add(url)
            except Exception:
                continue
        return produtos

    def _check_captcha(self, html: str) -> bool:
        """
        Detecta se a Amazon retornou uma página de CAPTCHA/bot challenge.

        Sinais usados APENAS os inequívocos da página de CAPTCHA real da Amazon.
        Evita 'robot' que é muito genérico (aparece em <meta name='robots'> em páginas normais).
        """
        captcha_signals = [
            "captcha" in html.lower(),
            "api-services-support@amazon.com" in html,
            '<form method="get" action="/errors/validateCaptcha"' in html,
            "Digitar os caracteres que você vê na imagem" in html,
            "Enter the characters you see below" in html,
        ]
        return any(captcha_signals)

    async def _search_with_playwright(self, query: str, max_results: int, sort: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Usa BrowserManager (Playwright) para contornar o CAPTCHA da Amazon.
        """
        from core.browser_manager import BrowserManager

        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://www.amazon.com.br/s?k={encoded_query}"
        if sort == "recent":
            url += "&s=date-desc-rank"
        elif sort == "price_asc":
            url += "&s=price-asc-rank"
        elif sort == "price_desc":
            url += "&s=price-desc-rank"

        try:
            html = await BrowserManager.fetch_html(
                url,
                wait_until="domcontentloaded",
                extra_sleep=2.0,
                timeout=35000
            )

            if self._check_captcha(html):
                logger.warning(f"Amazon Playwright: CAPTCHA detectado para '{query}'")
                return []

            produtos = self._parse_html(html, max_results)
            logger.info(f"Amazon Playwright: {len(produtos)} produtos para '{query}'")
            return produtos
        except Exception as exc:
            import traceback
            logger.error(f"Amazon Playwright erro: {repr(exc)}\n{traceback.format_exc()}")
            return []

    async def search(
        self,
        query: str,
        max_results: int = 10,
        sort: Optional[str] = None,
        only_in_stock: bool = False,
        zipcode: Optional[str] = None,
        include_shipping: bool = False
    ) -> BrandSearchResult:
        """
        Busca produtos na Amazon.

        1ª tentativa: curl_cffi (rápido, ~2s)
        2ª tentativa: Playwright (fallback quando Amazon retorna 503/CAPTCHA)

        Em caso de CAPTCHA persistente, configure BRIGHTDATA_PROXY_URL ou
        SCRAPERAPI_KEY no .env para rotação de IP.
        """
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://www.amazon.com.br/s?k={encoded_query}"
        if sort == "recent":
            url += "&s=date-desc-rank"
        elif sort == "price_asc":
            url += "&s=price-asc-rank"
        elif sort == "price_desc":
            url += "&s=price-desc-rank"
        max_fetch = max_results * 2
        fallback_error = None
        raw_items: List[Dict[str, Any]] = []

        # --- Tentativa 1: curl_cffi ---
        try:
            async with AsyncSession(
                impersonate="chrome120",
                timeout=relevance_settings.ENGINE_DEFAULT_TIMEOUT_SECONDS
            ) as session:
                response = await session.get(url, headers=self.headers)
                if response.status_code == 200 and not self._check_captcha(response.text):
                    raw_items = self._parse_html(response.text, max_fetch)
                    if raw_items:
                        logger.info(f"✅ Amazon curl_cffi: {len(raw_items)} produtos para '{query}'")
                    else:
                        logger.warning(f"Amazon curl_cffi: 0 produtos para '{query}' (página vazia ou anti-bot).")
                elif response.status_code == 503 or self._check_captcha(response.text):
                    logger.warning(f"Amazon disparou CAPTCHA (HTTP {response.status_code}) — ativando Playwright.")
                else:
                    logger.error(f"Amazon curl_cffi: HTTP {response.status_code}")
                    fallback_error = f"HTTP {response.status_code}"
        except Exception as exc:
            logger.error(f"Amazon curl_cffi erro: {exc}")
            fallback_error = str(exc)

        # --- Tentativa 2: Playwright (se curl_cffi falhou ou retornou vazio) ---
        if not raw_items and relevance_settings.PLAYWRIGHT_AMAZON_FALLBACK:
            logger.info(f"Amazon: ativando Playwright para '{query}'...")
            raw_items = await self._search_with_playwright(query, max_fetch, sort)
            if not raw_items:
                fallback_error = fallback_error or "CAPTCHA — Playwright também não retornou resultados"
                logger.warning(f"Amazon Playwright: sem resultados para '{query}'")

        # --- Montar resultado ---
        filtered = self.filter_mens_fashion(raw_items)[:max_results]
        products = []
        for item in filtered:
            shipping = ShippingInfo(status="Calculado no checkout", price=0.0 if False else None) if include_shipping else None
            products.append(SearchProductResult(
                brand="Amazon",
                product_name=item["titulo"],
                url=item["url"],
                price_full=item["preco"],
                price_discount=None,
                image_url=item["imagem"],
                available=True,
                seller=item["seller"],
                shipping=shipping,
                is_free_shipping=False,
                shipping_price=None
            ))

        return BrandSearchResult(
            brand_key=self.brand_key,
            brand_name="Amazon",
            products=products,
            total_found=len(products),
            error=fallback_error if not products else None,
        )

    async def calculate_shipping(self, product: Any, zipcode: str) -> Optional[Dict[str, Any]]:
        """
        Tier 2: Cálculo de frete para Amazon.
        Sendo extremamente restrita, a Amazon exige sessão com endereço logado 
        ou endpoints de delivery baseados em CSRF tokens para simular frete.
        Neste fallback mockado, retornamos None (frete a calcular).
        """
        return None

    async def _read_delivery_text(self, page) -> str:
        selectors = [
            "#mir-layout-DELIVERY_BLOCK",
            "#mir-layout-DELIVERY_BLOCK-slot-PRIMARY_DELIVERY_MESSAGE_LARGE",
            "#mir-layout-DELIVERY_BLOCK-slot-SECONDARY_DELIVERY_MESSAGE_LARGE",
            "#deliveryBlockMessage",
            "#contextualIngressPtLabel_deliveryShortLine",
            "[data-csa-c-delivery-price]",
        ]
        parts = []
        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    text = (await element.inner_text()).strip()
                    if text:
                        parts.append(text)
            except Exception:
                continue
        return "\n".join(dict.fromkeys(parts))

    def _parse_shipping_text(self, text: str) -> Optional[Dict[str, Any]]:
        if not text:
            return None

        lower = text.lower()
        if re.search(r'(frete|entrega)\s+gr[aá]tis|gr[aá]tis\s+(?:de\s+)?(?:frete|entrega)', lower):
            return {"is_free_shipping": True, "shipping_price": 0.0}

        freight_patterns = [
            r'(?:frete|entrega)[^\n\r]{0,80}?R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})',
            r'R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})[^\n\r]{0,80}?(?:frete|entrega)',
        ]
        for pattern in freight_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).replace(".", "").replace(",", ".")
                return {"is_free_shipping": False, "shipping_price": float(value)}

        return None

    async def calculate_shipping_advanced(self, url: str, zipcode: str) -> Optional[Dict[str, Any]]:
        """
        Calcula o frete real via Playwright interagindo com a página da Amazon.
        Tenta extrair da string de entrega padrão, ou injetar no modal de CEP.
        """
        try:
            logger.info(f"Calculando frete Amazon via Playwright para {url} com CEP {zipcode}")
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True, 
                    args=["--no-sandbox", "--disable-blink-features=AutomationControlled", "--disable-dev-shm-usage"]
                )
                try:
                    ctx = await browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        locale="pt-BR"
                    )
                    page = await ctx.new_page()
                    try:
                        from playwright_stealth import Stealth
                        await Stealth().apply_stealth_async(page)
                    except Exception as e:
                        logger.debug(f"Amazon: stealth não aplicado: {e}")
                    
                    # Amazon bloqueia fácil, então load com sleep extra
                    await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    await asyncio.sleep(3)
                    
                    # Tenta primeiro ver se já existe texto de "Frete GRÁTIS" na página
                    html = await page.content()
                    if self._check_captcha(html):
                        logger.warning("Amazon: CAPTCHA no cálculo de frete.")
                        return {
                            "error": "A Amazon bloqueou o cálculo de frete com CAPTCHA/anti-bot nesta sessão."
                        }
                    
                    parsed_shipping = self._parse_shipping_text(await self._read_delivery_text(page))
                    if parsed_shipping:
                        return parsed_shipping
                    delivery_message = await page.query_selector('#mir-layout-DELIVERY_BLOCK-slot-PRIMARY_DELIVERY_MESSAGE_LARGE')
                    if delivery_message:
                        text = await delivery_message.inner_text()
                        if "grátis" in text.lower():
                            return {"is_free_shipping": True, "shipping_price": 0.0}
                    
                    # Clica no modal de CEP (Enviar para...)
                    location_btn = await page.query_selector('#nav-global-location-popover-link')
                    if location_btn:
                        await location_btn.click()
                        await asyncio.sleep(2)
                        
                        # Amazon BR divide o CEP em 2 campos as vezes (5 dígitos e 3 dígitos)
                        normalized_zipcode = re.sub(r"\D", "", zipcode or "")
                        cep_input_1 = await page.query_selector('#GLUXZipUpdateInput_0')
                        cep_input_2 = await page.query_selector('#GLUXZipUpdateInput_1')
                        
                        if cep_input_1 and cep_input_2 and len(normalized_zipcode) == 8:
                            p1, p2 = normalized_zipcode[:5], normalized_zipcode[5:]
                            await cep_input_1.fill(p1)
                            await cep_input_2.fill(p2)
                        else:
                            single_input = await page.query_selector('#GLUXZipUpdateInput')
                            if single_input:
                                await single_input.fill(normalized_zipcode or zipcode)
                        
                        apply_btn = await page.query_selector('#GLUXZipUpdate, input[aria-labelledby="GLUXZipUpdate-announce"], #GLUXZipUpdate-announce')
                        if apply_btn:
                            await apply_btn.click()
                            await asyncio.sleep(3)
                            
                            # Recarrega a página ou a div de frete
                            confirm_btn = await page.query_selector('#GLUXConfirmClose, input[aria-labelledby="GLUXConfirmClose-announce"]')
                            if confirm_btn:
                                try:
                                    await confirm_btn.click()
                                    await asyncio.sleep(1)
                                except Exception as e:
                                    logger.debug("Amazon: falha ao confirmar/fechar o modal de CEP: %s", e)
                            try:
                                await page.reload(wait_until="domcontentloaded", timeout=25000)
                                await asyncio.sleep(2)
                            except Exception:
                                await asyncio.sleep(2)
                            parsed_shipping = self._parse_shipping_text(await self._read_delivery_text(page))
                            if parsed_shipping:
                                return parsed_shipping
                            delivery_message = await page.query_selector('#mir-layout-DELIVERY_BLOCK-slot-PRIMARY_DELIVERY_MESSAGE_LARGE')
                            if delivery_message:
                                text = await delivery_message.inner_text()
                                if "grátis" in text.lower():
                                    return {"is_free_shipping": True, "shipping_price": 0.0}
                                else:
                                    import re
                                    match = re.search(r'R\$\s*(\d+,\d{2})', text)
                                    if match:
                                        return {
                                            "is_free_shipping": False, 
                                            "shipping_price": float(match.group(1).replace(',', '.'))
                                        }
                    return {
                        "error": "Não foi possível localizar o bloco de frete da Amazon após informar o CEP."
                    }
                finally:
                    await browser.close()
                                    
        except Exception as e:
            logger.error(f"Erro ao calcular frete avançado na Amazon: {e}")
            
        return None
