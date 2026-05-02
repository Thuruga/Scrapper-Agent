import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://www.usereserva.com/reserva/masculino/bermudas-e-shorts/colecao", timeout=30000)
        
        seletor_seguro = (
            "a"
            ":not(footer a)"
            ":not(header a)"
            ":not([class*='shelf'] a)"
            ":not([class*='recommendation'] a)"
            ":not([class*='slider'] a)"
            ":not([class*='carousel'] a)"
            ":not([class*='minicart'] a)"
            ":not([id*='minicart'] a)"
        )
        try:
            links = await page.locator(seletor_seguro).count()
            print(f"Links encontrados (com seletor seguro): {links}")
        except Exception as e:
            print(f"Erro com seletor seguro: {e}")
            
        await browser.close()

asyncio.run(main())
