import asyncio
import httpx

async def test():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Start a multi-brand job
        resp = await client.post("/scrape-category-multi", json={
            "brands": ["aramis"],
            "category_slug": "camisas" # Assume valid
        })
        print("Start response:", resp.status_code, resp.text)
        if resp.status_code == 200:
            job_id = resp.json()["job_id"]
            print("Job ID:", job_id)
            # Cancel the job
            resp_cancel = await client.delete(f"/jobs/{job_id}")
            print("Cancel response:", resp_cancel.status_code, resp_cancel.text)

if __name__ == "__main__":
    asyncio.run(test())
