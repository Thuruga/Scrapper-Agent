"""
API Router Aggregator.

Registra todos os sub-routers em um único router principal.
"""

from fastapi import APIRouter, Depends
from api.auth import get_api_key

from api.routes_product import router as product_router
from api.routes_category import router as category_router
from api.routes_jobs import router as jobs_router
from api.routes_search import router as search_router
from api.routes_brands import router as brands_router

api_router = APIRouter(dependencies=[Depends(get_api_key)])

api_router.include_router(product_router)
api_router.include_router(category_router)
api_router.include_router(jobs_router)
api_router.include_router(search_router)
api_router.include_router(brands_router)
