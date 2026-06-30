"""
Modelo canônico de dados — Camada Bronze.

Contrato único compartilhado por todos os scrapers e pelo orquestrador.
Qualquer campo específico de uma marca que não se aplique a outra fica Optional.
"""

from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Dict, List, Any


class ShippingInfo(BaseModel):
    price: float | None = Field(
        default=None, description="Valor numérico do frete. 0.0 significa grátis."
    )
    status: str = Field(
        default="Disponível",
        description="Ex: 'Indisponível', 'Disponível', 'Calculado no checkout'",
    )
    estimated_delivery_days: int | None = None
    raw_text: str | None = Field(
        default=None,
        description="Texto original extraído (ex: 'Grátis', 'Receba amanhã')",
    )
    # Identidade da modalidade (Phase 33 — additive, safe defaults para registros antigos)
    service_name: str | None = Field(
        default=None,
        description="Nome da modalidade de entrega (ex: 'Expresso', 'Normal')",
    )
    service_id: str | None = Field(
        default=None,
        description="ID interno da SLA VTEX (campo 'id' do SLA)",
    )
    # Metadados do prazo parseados por vtex_shipping.parse_estimate
    estimate_display: str | None = Field(
        default=None,
        description="Texto PT do prazo (ex: 'Até 5 dias úteis', 'Até 12 horas')",
    )
    estimate_unit: str | None = Field(
        default=None,
        description="Unidade VTEX do prazo: 'bd', 'd', 'h' ou 'm'",
    )
    is_free_shipping: bool = Field(
        default=False,
        description="True quando price == 0.0 (grátis); False caso contrário",
    )


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
    shipping: ShippingInfo | None = None

    is_free_shipping: bool = False
    shipping_price: Optional[float] = None
    landed_price: Optional[float] = None

    @model_validator(mode="after")
    def calculate_landed_price(self):
        if self.landed_price is None:
            base_price = (
                self.price_discount
                if self.price_discount is not None
                else self.price_full
            )
            if base_price is not None:
                if self.shipping_price is not None:
                    self.landed_price = base_price + self.shipping_price
                else:
                    self.landed_price = base_price
        return self

    @field_validator("price_full")
    @classmethod
    def price_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Preço zerado ou negativo")
        return v

    @field_validator("image_url")
    @classmethod
    def image_url_must_be_present(cls, v: Optional[str]) -> str:
        if not v or not v.strip() or v == "None":
            raise ValueError("URL da imagem ausente ou inválida")
        return v

    @field_validator("raw_title")
    @classmethod
    def title_must_be_present(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Título do produto ausente")
        return v


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
    available_colors: List[str] = Field(default_factory=list)
    available_sizes: List[str] = Field(default_factory=list)
    seller: Optional[str] = None
    # Identidade do SKU/seller usada para a simulação de frete sob demanda (Phase 33.x).
    # Additive, opcional — registros antigos sem estes campos continuam válidos.
    sku_id: Optional[str] = Field(
        default=None,
        description="itemId do SKU selecionado (oferta disponível) — usado no cálculo de frete on-demand.",
    )
    seller_id: Optional[str] = Field(
        default=None,
        description="ID do seller do SKU selecionado — usado no cálculo de frete on-demand.",
    )
    shipping_product_id: Optional[str] = Field(
        default=None,
        description="ID do produto usado por providers nao-VTEX para cotacao de frete.",
    )
    shipping_variant_id: Optional[str] = Field(
        default=None,
        description="ID da variante usado por providers nao-VTEX para cotacao de frete.",
    )
    shipping_sku: Optional[str] = Field(
        default=None,
        description="SKU externo usado por providers nao-VTEX para cotacao de frete.",
    )
    shipping: ShippingInfo | None = None
    shipping_options: List[ShippingInfo] = Field(
        default_factory=list,
        description="Todas as modalidades de entrega domiciliar válidas, "
                    "ordenadas por preço asc depois prazo asc (Phase 33 VTEX).",
    )

    is_free_shipping: bool = False
    shipping_price: Optional[float] = None
    landed_price: Optional[float] = None

    @model_validator(mode="after")
    def calculate_landed_price(self):
        if self.landed_price is None:
            base_price = (
                self.price_discount
                if self.price_discount is not None
                else self.price_full
            )
            if base_price is not None:
                if self.shipping_price is not None:
                    self.landed_price = base_price + self.shipping_price
                else:
                    self.landed_price = base_price
        return self


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

    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    price: float
    available: bool
    available_colors: List[str] = Field(default_factory=list)
    available_sizes: List[str] = Field(default_factory=list)


class PriceMonitorConfig(BaseModel):
    """Configuração e estado de um monitoramento ativo."""

    job_id: str
    url: str
    brand: str
    interval_minutes: int = 10
    duration_hours: int = 24
    start_time: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_price: Optional[float] = None
    history: List[PriceHistoryEntry] = Field(default_factory=list)
    active: bool = True
    image_url: Optional[str] = None
    product_name: Optional[str] = None
    available_colors: List[str] = Field(default_factory=list)
    available_sizes: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Marcas Dinâmicas e Mapeamentos
# ---------------------------------------------------------------------------


class CategoryMapping(BaseModel):
    """Mapeamento entre uma categoria canônica e o caminho real na VTEX."""

    canonical_slug: str  # ex: "polos", "camisas"
    vtex_fq_path: str  # ex: "C:/1/2/"
    label: str  # ex: "Polos Masculinas"


class DynamicBrandCreate(BaseModel):
    """Dados básicos para cadastrar uma nova marca."""

    brand_key: str  # ex: "reserva", "aramis"
    brand_name: str  # ex: "Reserva"
    domain: str  # ex: "www.usereserva.com"

    @field_validator("domain", mode="before")
    @classmethod
    def clean_domain(cls, v: str) -> str:
        if v:
            return v.replace("https://", "").replace("http://", "").strip("/")
        return v

    review_provider: Optional[str] = "none"  # ex: "trustvox", "vtex_native"
    review_store_id: Optional[str] = None  # ex: "78800"
    vtex_account: Optional[str] = None  # ex: "foxton" (se diferente do domínio)
    engine: Optional[str] = "vtex"  # ex: "vtex", "shopify"
    logo_url: Optional[str] = None  # ex: "https://.../logo.png"
    wake_access_token: Optional[str] = None  # override manual do token público de storefront Wake (D-06)
    # Override por marca da URL de busca. Necessário p/ SFCC Lacoste, cujo host canônico é
    # www.lacoste.com/br/ (o lacoste.com.br redireciona à home e perde o ?q=). {query} = termo URL-encoded.
    search_url_template: Optional[str] = None
    # Egress de IP limpo por marca (proxy Playwright). Lacoste/Akamai bloqueia IP de datacenter/corporativo;
    # None = conexão direta (dev / redes limpas). Formato: http://[user:senha@]host:porta.
    proxy_url: Optional[str] = None


class DynamicBrand(DynamicBrandCreate):
    """Marca completa com seus mapeamentos e estado."""

    mappings: List[CategoryMapping] = Field(default_factory=list)
    is_active: bool = True


class BrandActiveUpdate(BaseModel):
    """Payload para PATCH /brands/{brand_key}/active — V5 Input Validation (T-25-03-BODY)."""

    is_active: bool


# ---------------------------------------------------------------------------
# Histórico local de buscas
# ---------------------------------------------------------------------------

class SearchHistory(BaseModel):
    """Registro de uma pesquisa assíncrona (Histórico)."""
    job_id: str
    query: str
    type: str = Field(default="search", description="Tipo de busca: 'search' ou 'cross'")
    brands: List[str] = Field(default_factory=list)
    status: str = Field(default="PENDING", description="PENDING, COMPLETED, FAILED")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    results: Optional[Any] = None
    error: Optional[str] = None
