import asyncio
import aiohttp

async def check():
    url = "https://buckmanbck.com.br/products.json"
    headers = {"User-Agent": "Mozilla/5.0"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            print(f"Status: {resp.status}")
            if resp.status == 200:
                print("It is Shopify!")
                data = await resp.json()
                print(f"Products found: {len(data.get('products', []))}")
            else:
                print(f"Content-Type: {resp.headers.get('Content-Type')}")

if __name__ == "__main__":
    asyncio.run(check())
