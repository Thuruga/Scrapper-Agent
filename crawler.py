import asyncio
import threading
from typing import Optional, Callable
from playwright.async_api import async_playwright


async def varrer_categoria_vtex(
    url_categoria: str,
    log_callback: Optional[Callable] = None,
    cancel_event: Optional[threading.Event] = None,
) -> list[str]:
    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    def is_cancelled() -> bool:
        return cancel_event is not None and cancel_event.is_set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"
        )
        page = await context.new_page()

        links_produtos = set()

        try:
            log(f"[SPIDER] Entrando na categoria: {url_categoria}")
            await page.goto(url_categoria, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            rolagens = 0
            max_rolagens = 10

            while rolagens < max_rolagens:
                if is_cancelled():
                    log("[SPIDER] Varredura interrompida pelo usuário.")
                    break

                log(f"Rolando página (Scroll {rolagens + 1}/{max_rolagens})...")

                await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)

                # Tenta clicar em "Carregar mais"
                try:
                    botao_mais = page.locator(
                        "text='Carregar mais', text='Ver mais', text='Mostrar mais'"
                    )
                    if (
                        await botao_mais.count() > 0
                        and await botao_mais.first.is_visible()
                    ):
                        await botao_mais.first.click()
                        await page.wait_for_timeout(2000)
                except Exception:
                    pass

                # Blacklist de termos que não são produtos reais ou são serviços
                blacklist = ["assinatura", "prime", "servicos", "gift-card", "vale-presente", "customizacao"]

                # ESTRATÉGIA ROBUSTA E PROFISSIONAL (Sem Hardcode)
                # Seleciona todos os links da página, EXCETO os que estão em áreas de "cross-selling", 
                # rodapé, cabeçalho ou minicart. Lojas VTEX usam 'slider' ou 'carousel' para recomendações.
                seletor_seguro = (
                    "a"
                    ":not(footer a)"
                    ":not(header a)"
                    ":not([class*='recommendation'] a)"
                    ":not([class*='slider'] a)"
                    ":not([class*='carousel'] a)"
                    ":not([class*='minicart'] a)"
                    ":not([id*='minicart'] a)"
                )
                
                elementos_a = await page.locator(seletor_seguro).all()

                for el in elementos_a:
                    href = await el.get_attribute("href")
                    if href and ("/p?" in href or href.endswith("/p")):
                        # 1. Normalização
                        if href.startswith("/"):
                            dominio = url_categoria.split("/")[2]
                            href = f"https://{dominio}{href}"
                        
                        link_limpo = href.split("?")[0]

                        # 2. Filtro de Blacklist
                        if any(term in link_limpo.lower() for term in blacklist):
                            continue
                            
                        # 3. Filtro de Segurança (evita capturar links fora do domínio principal)
                        if url_categoria.split("/")[2] not in link_limpo:
                            continue

                        links_produtos.add(link_limpo)

                rolagens += 1

            log(f"[SPIDER SUCESSO] {len(links_produtos)} links únicos encontrados na categoria!")
            await browser.close()
            return list(links_produtos)

        except Exception as e:
            log(f"[SPIDER ERRO] Falha ao varrer categoria: {e}")
            await browser.close()
            return list(links_produtos)


# --- Teste direto ---
async def main():
    url_categoria = "https://www.aramis.com.br/roupas/polos"
    links = await varrer_categoria_vtex(url_categoria)
    print("\n--- Amostra dos Links Encontrados ---")
    for link in links[:10]:
        print(link)


if __name__ == "__main__":
    asyncio.run(main())
