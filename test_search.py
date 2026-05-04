import asyncio
from services.vtex_search import search_all_brands

async def main():
    res = await search_all_brands("camiseta", ["reserva"], max_per_brand=5)
    for b in res:
        for p in b.products:
            print(f"Product: {p.product_name}")
            print(f"Rating: {p.rating} / Count: {p.review_count}")

asyncio.run(main())
