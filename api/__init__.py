"""
API Router Aggregator.

Registra todos os sub-routers em um único router principal.
"""

from fastapi import APIRouter

from api.routes_product import router as product_router
from api.routes_category import router as category_router
from api.routes_jobs import router as jobs_router
from api.routes_search import router as search_router

api_router = APIRouter()

api_router.include_router(product_router)
api_router.include_router(category_router)
api_router.include_router(jobs_router)
api_router.include_router(search_router)
