"""
Rotas de Extração de Produto Único.

POST /scrape — Extrai dados de um produto a partir de sua URL.
"""

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from scrapers import get_scraper

router = APIRouter()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class ScrapeProductRequest(BaseModel):
    url: str
    brand: str


# ---------------------------------------------------------------------------
# Utils
# ---------------------------------------------------------------------------
def clean_url(url: str) -> str:
    """Corrige caso a URL venha duplicada (ex: http...http...) ou com espaços."""
    url = url.strip()
    if url.count("http") > 1:
        idx = url.rfind("http")
        url = url[idx:]
    return url


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/scrape")
async def scrape_product(request: ScrapeProductRequest):
    """Extrai dados de um produto único a partir da URL informada."""
    request.url = clean_url(request.url)

    try:
        scraper_module = get_scraper(request.brand)
    except ValueError:
        raise HTTPException(status_code=400, detail="Brand not supported")

    def run_scraper():
        import asyncio as _asyncio
        return _asyncio.run(
            scraper_module.scrape_competitor_product(request.url, request.brand)
        )

    try:
        result = await run_in_threadpool(run_scraper)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to scrape product")
        return result.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
