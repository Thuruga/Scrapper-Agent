import asyncio
from playwright.async_api import async_playwright

async def check_reviews(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000)
            
            # extrair scripts e iframes
            content = await page.content()
            keywords = ["trustvox", "yotpo", "bazaarvoice", "powerreviews", "stamped", "loox", "vtex.reviews-and-ratings"]
            found = {k: k in content.lower() for k in keywords}
            print(f"URL: {url}")
            print(f"Found review providers: {[k for k, v in found.items() if v]}")
        except Exception as e:
            print(f"Error checking {url}: {e}")
        finally:
            await browser.close()

async def main():
    urls = [
        "https://www.aramis.com.br/polo-manga-curta-pima-performing-marinho-po-12-0014-010/p",
        "https://www.usereserva.com/polo-risca-tech-0097130-195/p",
        "https://br.tommy.com/polo-performance-jersey-thmw0mw37310_thbds/p"
    ]
    for url in urls:
        await check_reviews(url)

asyncio.run(main())
