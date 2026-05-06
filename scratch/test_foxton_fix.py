import asyncio
import logging
import sys
import os

# Adiciona o diretório raiz ao path para importar os serviços
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.vtex_api_scraper import VtexApiClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

async def test_brands():
    tests = [
        {"brand": "foxton", "url": "https://www.foxtonbrasil.com.br/roupas/camisas"},
        {"brand": "aramis", "url": "https://www.aramis.com.br/roupas/polos"},
    ]
    
    for t in tests:
        brand = t["brand"]
        category_url = t["url"]
        print(f"\n--- Testando fix para {brand} ({category_url}) ---")
        async with VtexApiClient(brand) as client:
            try:
                products = await client.scrape_category_paged(
                    category_url=category_url,
                    chunk_size=10
                )
                print(f"✅ Resultado: {len(products)} produtos extraídos.")
                if products:
                    print(f"Primeiro produto: {products[0].raw_title} - {products[0].price_full}")
            except Exception as e:
                print(f"❌ Erro durante a extração: {e}")

if __name__ == "__main__":
    asyncio.run(test_brands())
