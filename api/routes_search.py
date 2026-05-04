"""
Rota de Busca Comparativa Multi-Brand.

POST /search  —  Busca um termo em todas as marcas simultaneamente e retorna
                 os resultados em formato de comparação lado a lado.

Não usa Playwright — chama a API VTEX full-text diretamente (HTTP puro).
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from config import BRAND_REGISTRY
from core.models import ComparisonResult
from services.vtex_search import search_all_brands

router = APIRouter(prefix="/search", tags=["search"])


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    """Payload da busca comparativa."""

    query: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Termo de busca livre. Ex: 'Polo Piquet', 'Camisa Listrada'.",
        examples=["Polo Piquet"],
    )
    brands: Optional[List[str]] = Field(
        default=None,
        description=(
            "Lista de marcas para pesquisar. "
            "Se omitido, busca em todas as marcas cadastradas. "
            "Valores válidos: 'aramis', 'reserva', 'tommy'."
        ),
        examples=[["aramis", "reserva", "tommy"]],
    )
    max_per_brand: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Número máximo de produtos retornados por marca (1-50).",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=ComparisonResult,
    summary="Busca comparativa multi-brand",
    description=(
        "Pesquisa um termo livre em todas as marcas cadastradas em paralelo. "
        "Retorna os resultados agrupados por marca para comparação. "
        "Erros de uma marca não bloqueiam as demais."
    ),
)
async def search_products(request: SearchRequest) -> ComparisonResult:
    """
    Executa a busca comparativa.

    Fluxo:
    1. Valida as marcas solicitadas
    2. Dispara asyncio.gather para buscar em paralelo
    3. Retorna ComparisonResult com resultados por marca
    """
    # Valida marcas fornecidas, se explicitadas
    if request.brands:
        invalid = [b for b in request.brands if b.lower() not in BRAND_REGISTRY]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Marcas inválidas: {invalid}. "
                    f"Marcas suportadas: {list(BRAND_REGISTRY.keys())}"
                ),
            )

    target_brands = (
        [b.lower() for b in request.brands]
        if request.brands
        else list(BRAND_REGISTRY.keys())
    )

    brand_results = await search_all_brands(
        query=request.query,
        brands=target_brands,
        max_per_brand=request.max_per_brand,
    )

    return ComparisonResult(
        query=request.query,
        brands_searched=target_brands,
        results=brand_results,
    )


@router.get(
    "",
    response_model=ComparisonResult,
    summary="Busca comparativa via GET (conveniência)",
    description="Versão GET do endpoint de busca para testes rápidos via browser.",
)
async def search_products_get(
    q: str = Query(..., min_length=2, max_length=100, description="Termo de busca"),
    max_per_brand: int = Query(default=10, ge=1, le=50),
) -> ComparisonResult:
    """Atalho GET para facilitar testes direto pelo browser/swagger."""
    brand_results = await search_all_brands(
        query=q,
        brands=None,  # Todas as marcas
        max_per_brand=max_per_brand,
    )

    return ComparisonResult(
        query=q,
        brands_searched=list(BRAND_REGISTRY.keys()),
        results=brand_results,
    )
