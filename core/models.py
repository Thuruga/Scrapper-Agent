"""
Modelo canônico de dados — Camada Bronze.

Contrato único compartilhado por todos os scrapers e pelo orquestrador.
Qualquer campo específico de uma marca que não se aplique a outra fica Optional.
"""

from datetime import datetime, timezone
from pydantic import BaseModel, Field
from typing import Optional, Dict, List


class RawProductBronze(BaseModel):
    """Dado bruto de um produto concorrente, sem transformações."""

    url: str
    brand: str
    raw_title: str
    raw_description: str
    price_full: float
    price_discount: Optional[float] = None
    stock_availability: Optional[bool] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    composition: Optional[str] = None
    available_colors: List[str] = Field(default_factory=list)
    available_sizes: List[str] = Field(default_factory=list)
    rating: Optional[float] = None
    review_count: Optional[int] = None
    specifications: Dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Modelos de Busca Comparativa
# ---------------------------------------------------------------------------

class SearchProductResult(BaseModel):
    """
    Resultado enxuto de um produto retornado pela busca VTEX.
    Otimizado para exibição na tela comparativa — sem dados pesados de scraping.
    """

    brand: str
    product_name: str
    url: str
    price_full: Optional[float] = None
    price_discount: Optional[float] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    available: Optional[bool] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None


class BrandSearchResult(BaseModel):
    """Resultado de uma marca individual na busca comparativa."""

    brand_key: str
    brand_name: str
    products: List[SearchProductResult] = Field(default_factory=list)
    error: Optional[str] = None  # Preenchido se a busca da marca falhou
    total_found: int = 0


class ComparisonResult(BaseModel):
    """Resposta completa da busca comparativa multi-brand."""

    query: str
    brands_searched: List[str]
    results: List[BrandSearchResult] = Field(default_factory=list)
    searched_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
