import asyncio
from playwright.async_api import async_playwright


async def varrer_categoria_vtex(url_categoria: str, log_callback=None) -> list[str]:
    def log(msg):
        print(msg)
        if log_callback:
            log_callback(msg)

    async with async_playwright() as p:
        # Headless=True para rodar rápido em background
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

            # Rola a página para baixo para forçar o "Lazy Load" da vitrine
            rolagens = 0
            max_rolagens = 10  # Ajuste dependendo do tamanho da categoria

            while rolagens < max_rolagens:
                log(f"Rolando página (Scroll {rolagens + 1}/{max_rolagens})...")

                # Desce a tela
                await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)  # Espera os novos produtos carregarem

                # Procura por botões de "Carregar Mais" (Padrão de algumas lojas)
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
                except:
                    pass

                # Extrai todos os links (tags <a>) presentes na tela neste momento
                elementos_a = await page.locator("a").all()
                for el in elementos_a:
                    href = await el.get_attribute("href")
                    # Padrão VTEX: links de produtos sempre terminam com /p ou contêm /p?
                    if href and ("/p?" in href or href.endswith("/p")):
                        # Garante que a URL está completa
                        if href.startswith("/"):
                            dominio = url_categoria.split("/")[2]
                            href = f"https://{dominio}{href}"
                        links_produtos.add(
                            href.split("?")[0]
                        )  # Salva a URL limpa (sem parâmetros de tracking)

                rolagens += 1

            log(f"[SPIDER SUCESSO] {len(links_produtos)} links únicos encontrados na categoria!")
            await browser.close()
            return list(links_produtos)

        except Exception as e:
            log(f"[SPIDER ERRO] Falha ao varrer categoria: {e}")
            await browser.close()
            return list(links_produtos)


# --- Testando o Crawler ---
async def main():
    # Vamos testar varrendo a vitrine de Polos da Aramis
    url_categoria = "https://www.aramis.com.br/roupas/polos"
    links = await varrer_categoria_vtex(url_categoria)

    print("\n--- Amostra dos Links Encontrados ---")
    for link in links[
        :10
    ]:  # Mostrando apenas os 10 primeiros para não poluir o terminal
        print(link)


if __name__ == "__main__":
    asyncio.run(main())
