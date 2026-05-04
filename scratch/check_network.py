import asyncio
from playwright.async_api import async_playwright

async def check_network(url):
    print(f"--- Checking {url} ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        async def handle_response(response):
            try:
                url_lower = response.url.lower()
                if "review" in url_lower or "rating" in url_lower or "trustvox" in url_lower:
                    print(f"Review API Found: {response.url}")
            except:
                pass
                
        page.on("response", handle_response)
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"Error checking {url}: {e}")
        finally:
            await browser.close()

async def main():
    urls = [
        "https://www.usereserva.com/polo-risca-tech-0097130-195/p",
        "https://br.tommy.com/polo-performance-jersey-thmw0mw37310_thbds/p"
    ]
    for url in urls:
        await check_network(url)

asyncio.run(main())
