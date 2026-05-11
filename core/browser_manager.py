import logging
import asyncio
from typing import Optional
from playwright.async_api import async_playwright

logger = logging.getLogger("BrowserManager")

class BrowserManager:
    """
    Gerenciador de navegador Playwright para bypass de anti-bot.
    Implementa um singleton para gerenciar o ciclo de vida do browser.
    Thread-safe via asyncio.Lock para evitar inicializações concorrentes.
    """
    _instance = None
    _browser = None
    _playwright = None
    _lock: asyncio.Lock = None  # Lazy-initialized; asyncio.Lock() must be created inside an event loop

    @classmethod
    async def _get_lock(cls) -> asyncio.Lock:
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        return cls._lock

    @classmethod
    async def get_browser(cls):
        lock = await cls._get_lock()
        async with lock:
            if cls._browser is None:
                cls._playwright = await async_playwright().start()
                cls._browser = await cls._playwright.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
                )
        return cls._browser

    @classmethod
    async def fetch_html(cls, url: str, wait_selector: Optional[str] = None, timeout: int = 30000) -> str:
        """
        Abre o navegador, navega até a URL, aguarda carregamento e retorna o HTML.
        """
        browser = await cls.get_browser()
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            logger.info(f"[PLAYWRIGHT] Navegando para {url}")
            await page.goto(url, wait_until="networkidle", timeout=timeout)
            
            if wait_selector:
                await page.wait_for_selector(wait_selector, timeout=timeout)
            
            # Pequeno delay extra para garantir que JS dinâmico terminou
            await asyncio.sleep(2)
            
            content = await page.content()
            return content
        except Exception as e:
            logger.error(f"[PLAYWRIGHT] Erro ao buscar {url}: {e}")
            raise e
        finally:
            await page.close()
            await context.close()

    @classmethod
    async def close(cls):
        if cls._browser:
            await cls._browser.close()
            cls._browser = None
        if cls._playwright:
            await cls._playwright.stop()
            cls._playwright = None

browser_manager = BrowserManager()
