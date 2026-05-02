import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        url_categoria = "https://www.usereserva.com/reserva/masculino/bermudas-e-shorts/colecao"
        await page.goto(url_categoria, timeout=30000)
        await page.wait_for_timeout(3000)
        await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)
        
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
        
        links_produtos = set()
        blacklist = ["assinatura", "prime", "servicos", "gift-card", "vale-presente", "customizacao"]

        for el in elementos_a:
            href = await el.get_attribute("href")
            if href and ("/p?" in href or href.endswith("/p")):
                if href.startswith("/"):
                    dominio = url_categoria.split("/")[2]
                    href = f"https://{dominio}{href}"
                
                link_limpo = href.split("?")[0]

                if any(term in link_limpo.lower() for term in blacklist):
                    continue
                    
                if url_categoria.split("/")[2] not in link_limpo:
                    continue

                links_produtos.add(link_limpo)
                
        print(f"Links de produto limpos: {len(links_produtos)}")
        for link in list(links_produtos)[:5]:
            print(link)
            
        await browser.close()

asyncio.run(main())
