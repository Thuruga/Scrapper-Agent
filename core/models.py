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
    image_url: Optional[str] = None



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


# ---------------------------------------------------------------------------
# Monitoramento de Preços
# ---------------------------------------------------------------------------

class PriceHistoryEntry(BaseModel):
    """Registro de uma variação de preço ou disponibilidade no tempo."""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    price: float
    available: bool


class PriceMonitorConfig(BaseModel):
    """Configuração e estado de um monitoramento ativo."""
    job_id: str
    url: str
    brand: str
    interval_minutes: int = 10
    duration_hours: int = 24
    start_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_price: Optional[float] = None
    history: List[PriceHistoryEntry] = Field(default_factory=list)
    active: bool = True
    image_url: Optional[str] = None
    product_name: Optional[str] = None


# ---------------------------------------------------------------------------
# Marcas Dinâmicas e Mapeamentos
# ---------------------------------------------------------------------------

class CategoryMapping(BaseModel):
    """Mapeamento entre uma categoria canônica e o caminho real na VTEX."""
    canonical_slug: str  # ex: "polos", "camisas"
    vtex_fq_path: str   # ex: "C:/1/2/"
    label: str          # ex: "Polos Masculinas"

class DynamicBrandCreate(BaseModel):
    """Dados básicos para cadastrar uma nova marca."""
    brand_key: str      # ex: "reserva", "aramis"
    brand_name: str     # ex: "Reserva"
    domain: str         # ex: "www.usereserva.com"
    review_provider: Optional[str] = "none" # ex: "trustvox", "vtex_native"
    review_store_id: Optional[str] = None   # ex: "78800"
    vtex_account: Optional[str] = None      # ex: "foxton" (se diferente do domínio)

class DynamicBrand(DynamicBrandCreate):
    """Marca completa com seus mapeamentos e estado."""
    mappings: List[CategoryMapping] = Field(default_factory=list)
    is_active: bool = True


