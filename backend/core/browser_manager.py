import logging
import asyncio
from typing import Optional
from config import settings

logger = logging.getLogger("BrowserManager")


class BrowserManager:
    """
    Gerenciador Playwright com otimizações para ambientes com pouca RAM.

    Flags aplicadas para reduzir consumo (fonte da verdade: CHROMIUM_ARGS abaixo):
      --disable-gpu            : Sem renderização GPU (desnecessário em headless)
      --disable-extensions     : Sem extensões
      --disable-dev-shm-usage  : Usa /tmp ao invés de /dev/shm (evita crash em containers)
      --no-sandbox             : Necessário em containers Linux sem root
      --disable-background-networking / --disable-sync / --mute-audio / --no-first-run

    NOTA: --single-process e --js-flags=--max-old-space-size=128 foram REMOVIDOS de propósito —
    quebravam o tratamento de redirects JS (ex: proof-of-work do Anubis no Mercado Livre). Logo o
    Chromium aqui é multiprocesso e sem limite de heap V8; em máquinas com pouca RAM
    evite muitas chamadas Playwright concorrentes.

    O browser é fechado após cada uso (não singleton persistente) para liberar RAM
    quando o servidor entrar em idle. Isso causa um delay de ~2s na próxima chamada
    mas evita que o Chromium fique consumindo memória indefinidamente.
    """

    _instance = None
    _browser = None
    _playwright = None
    _lock: asyncio.Lock = None

    CHROMIUM_ARGS = [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-extensions",
        "--disable-background-networking",
        "--disable-default-apps",
        "--disable-sync",
        "--mute-audio",
        "--no-first-run",
    ]

    @classmethod
    async def _get_lock(cls) -> asyncio.Lock:
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        return cls._lock

    @classmethod
    async def get_browser(cls):
        if not settings.PLAYWRIGHT_ENABLED:
            raise RuntimeError(
                "Playwright desabilitado via PLAYWRIGHT_ENABLED=false. "
                "Use curl_cffi ou aiohttp como alternativa."
            )

        lock = await cls._get_lock()
        async with lock:
            # Recreate browser if it doesn't exist or if it disconnected/crashed
            if cls._browser is None or not cls._browser.is_connected():
                if cls._playwright is None:
                    from playwright.async_api import async_playwright
                    cls._playwright = await async_playwright().start()
                
                cls._browser = await cls._playwright.chromium.launch(
                    headless=True,
                    args=cls.CHROMIUM_ARGS,
                )
                logger.info("[PLAYWRIGHT] Browser Chromium iniciado (modo low-memory).")
        return cls._browser

    @classmethod
    async def fetch_html(
        cls,
        url: str,
        wait_selector: Optional[str] = None,
        timeout: int = 30000,
        wait_until: str = "domcontentloaded",
        extra_sleep: float = 1.0,
    ) -> str:
        """
        Abre o navegador, navega até a URL e retorna o HTML.
        Utiliza sync_playwright em uma thread separada para evitar problemas de
        NotImplementedError com o SelectorEventLoop do Uvicorn no Windows.
        """
        if not settings.PLAYWRIGHT_ENABLED:
            raise RuntimeError(
                "Playwright desabilitado via PLAYWRIGHT_ENABLED=false. "
                "Use curl_cffi ou aiohttp como alternativa."
            )

        def _sync_fetch():
            from playwright.sync_api import sync_playwright
            import time
            
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=cls.CHROMIUM_ARGS,
                )
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
                    ),
                    java_script_enabled=True,
                    viewport={"width": 1366, "height": 768},
                    locale="pt-BR",
                    timezone_id="America/Sao_Paulo",
                    extra_http_headers={
                        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                        "Sec-Ch-Ua": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
                        "Sec-Ch-Ua-Mobile": "?0",
                        "Sec-Ch-Ua-Platform": '"Windows"',
                    },
                )
                page = context.new_page()

                # Mask headless fingerprint
                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                    window.chrome = { runtime: {} };
                """)

                try:
                    logger.info(f"[PLAYWRIGHT] Navegando para {url} (wait_until={wait_until})")
                    page.goto(url, wait_until=wait_until, timeout=timeout)

                    if wait_selector:
                        page.wait_for_selector(wait_selector, timeout=timeout)

                    if extra_sleep > 0:
                        time.sleep(extra_sleep)

                    for attempt in range(3):
                        try:
                            content = page.content()
                            return content
                        except Exception as inner_e:
                            if "navigating" in str(inner_e).lower() and attempt < 2:
                                logger.warning(f"[PLAYWRIGHT] Página {url} navegando, aguardando para capturar HTML... ({attempt+1}/3)")
                                time.sleep(2.0)
                            else:
                                raise inner_e
                    
                    return page.content()
                except Exception as e:
                    logger.error(f"[PLAYWRIGHT] Erro ao buscar {url}: {e}")
                    raise
                finally:
                    page.close()
                    context.close()
                    browser.close()

        # Roda na thread pool para não bloquear o loop principal e garantir
        # que um novo event loop compatível (Proactor) seja criado para o Playwright
        return await asyncio.to_thread(_sync_fetch)

    @classmethod
    async def close(cls):
        """No-op, já que agora o browser é fechado a cada requisição."""
        pass


browser_manager = BrowserManager()
