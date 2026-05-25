"""
Rota de Busca Comparativa Multi-Brand.

POST /search  —  Busca um termo em todas as marcas simultaneamente e retorna
                 os resultados em formato de comparação lado a lado.

Não usa Playwright — chama a API VTEX full-text diretamente (HTTP puro).
"""

from typing import List, Optional
import io
import pandas as pd
import asyncio
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from services.brand_service import brand_service
from core.models import ComparisonResult
from services.engines.factory import engine_factory

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
            "Se omitido, busca em todas as marcas cadastradas e marketplaces virtuais. "
            "Valores válidos: 'aramis', 'reserva', 'tommy', 'mercadolivre', 'netshoes'."
        ),
        examples=[["aramis", "reserva", "tommy", "mercadolivre", "netshoes"]],
    )
    max_per_brand: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Número máximo de produtos retornados por marca (1-50).",
    )
    sort: Optional[str] = Field(
        default="relevance",
        description="Ordenação: 'relevance', 'price_asc', 'price_desc', 'top_selling'.",
    )
    only_in_stock: bool = Field(
        default=False,
        description="Filtrar apenas produtos em estoque.",
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
    all_brands = [b.brand_key for b in brand_service.list_brands()]
    all_brands.extend(["mercadolivre", "netshoes"])
    if request.brands:
        invalid = [b for b in request.brands if b.lower() not in all_brands]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Marcas inválidas: {invalid}. "
                    f"Marcas suportadas: {all_brands}"
                ),
            )

    target_brands = (
        [b.lower() for b in request.brands]
        if request.brands
        else all_brands
    )

    brand_results = await engine_factory.search_all_brands(
        query=request.query,
        brands=target_brands,
        max_per_brand=request.max_per_brand,
        sort=request.sort,
        only_in_stock=request.only_in_stock
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
    sort: Optional[str] = Query(default="relevance"),
    only_in_stock: bool = Query(default=False),
) -> ComparisonResult:
    """Atalho GET para facilitar testes direto pelo browser/swagger."""
    brand_results = await engine_factory.search_all_brands(
        query=q,
        brands=None,  # Todas as marcas
        max_per_brand=max_per_brand,
        sort=sort,
        only_in_stock=only_in_stock
    )

    all_brands = [b.brand_key for b in brand_service.list_brands()]
    all_brands.extend(["mercadolivre", "netshoes"])

    return ComparisonResult(
        query=q,
        brands_searched=all_brands,
        results=brand_results,
    )


@router.post(
    "/export",
    summary="Exporta a busca comparativa em Excel",
    description="Pesquisa um termo em todas as marcas (ou filtradas) e retorna um arquivo .xlsx."
)
async def export_search_products(request: SearchRequest):
    """
    Executa a busca comparativa e retorna o resultado como download de arquivo Excel.
    """
    all_brands = [b.brand_key for b in brand_service.list_brands()]
    all_brands.extend(["mercadolivre", "netshoes"])
    if request.brands:
        invalid = [b for b in request.brands if b.lower() not in all_brands]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Marcas inválidas: {invalid}. Marcas suportadas: {all_brands}",
            )

    target_brands = (
        [b.lower() for b in request.brands]
        if request.brands
        else all_brands
    )

    brand_results = await engine_factory.search_all_brands(
        query=request.query,
        brands=target_brands,
        max_per_brand=request.max_per_brand,
        sort=request.sort,
        only_in_stock=request.only_in_stock
    )

    # -------------------------------------------------------------------------
    # Busca os detalhes completos de cada produto para garantir que o Excel
    # tenha as mesmas colunas/formato da varredura por categoria.
    # -------------------------------------------------------------------------
    tasks = []

    async def fetch_full_product(brand_key, brand_name, url):
        try:
            engine = engine_factory.get_engine(brand_key)
            prod_dict = await engine.get_product_details(url)
            if prod_dict:
                prod_dict["brand"] = brand_name
                return prod_dict
        except Exception:
            pass
        return None

    for brand_res in brand_results:
        brand_key = brand_res.brand_key
        brand_name = brand_res.brand_name
        for p in brand_res.products:
            tasks.append(fetch_full_product(brand_key, brand_name, p.url))

    full_products = await asyncio.gather(*tasks)
    data = [p for p in full_products if p]

    if not data:
        # Tabela genérica caso a busca não traga nenhum resultado válido
        df = pd.DataFrame(columns=["brand", "url", "raw_title", "price_full", "stock_availability"])
    else:
        df = pd.DataFrame(data)

        # Formatação idêntica ao orchestrator_multi.py
        for col in ["available_colors", "available_sizes"]:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)

        cols = df.columns.tolist()
        if "brand" in cols:
            cols.remove("brand")
            cols.insert(0, "brand")
            df = df[cols]

        if "specifications" in df.columns:
            specs_df = df["specifications"].apply(pd.Series)
            df = pd.concat([df.drop("specifications", axis=1), specs_df], axis=1)

        sort_cols = []
        if "brand" in df.columns:
            sort_cols.append("brand")
        if "price_full" in df.columns:
            sort_cols.append("price_full")
        if sort_cols:
            df = df.sort_values(sort_cols, na_position="last")

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Comparativo')
        
        # Opcional: auto-ajustar largura das colunas se openpyxl permitir de forma simples
        # Mas para garantir robustez sem erro, usaremos o padrão
    output.seek(0)

    # Formatar nome do arquivo
    safe_query = "".join([c if c.isalnum() else "_" for c in request.query])
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"busca_comparativa_{safe_query}_{timestamp}.xlsx"

    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"',
        'Access-Control-Expose-Headers': 'Content-Disposition'
    }

    return StreamingResponse(
        output,
        headers=headers,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
