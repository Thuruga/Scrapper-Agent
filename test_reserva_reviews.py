import asyncio
from services.review_service import get_bulk_reviews

async def main():
    print("Fetching reviews...")
    res = await get_bulk_reviews("reserva", ["8988"])
    print(res)

asyncio.run(main())
