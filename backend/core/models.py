"""
Modelo canônico de dados — Camada Bronze.

Contrato único compartilhado por todos os scrapers e pelo orquestrador.
Qualquer campo específico de uma marca que não se aplique a outra fica Optional.
"""

from datetime import datetime, timezone
from uuid import uuid4
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Dict, List, Any, Literal


def resolve_effective_price(
    price_full: float | None,
    price_discount: float | None,
    price_discount_is_delta: bool = False,
) -> float | None:
    if price_full is None:
        return None
    if price_discount is None:
        return price_full
    return price_full if price_discount_is_delta else price_discount


def resolve_original_price(
    price_full: float | None,
    price_discount: float | None,
    price_discount_is_delta: bool = False,
) -> float | None:
    if price_full is None:
        return None
    if price_discount is None:
        return price_full
    return price_full + price_discount if price_discount_is_delta else price_full


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


class ReviewComment(BaseModel):
    """Comentario de avaliacao normalizado e compacto."""

    review_id: str
    rating: Optional[float] = None
    title: Optional[str] = None
    text: Optional[str] = None
    author: Optional[str] = None
    created_at: Optional[str] = None
    source_provider: str
    source_ref: Optional[str] = None


class ReviewCommentsResult(BaseModel):
    """Resultado sob demanda de comentarios de avaliacao."""

    reviews_state: str = "unsupported"
    comments: List[ReviewComment] = Field(default_factory=list)
    rating: Optional[float] = None
    review_count: Optional[int] = None
    review_product_id: Optional[str] = None
    source_provider: Optional[str] = None
    max_pages: int = 0


class StockDepthResult(BaseModel):
    """Resultado sob demanda de profundidade de estoque."""

    stock_depth_estimate: Optional[int] = None
    stock_depth_state: str
    stock_depth_checked_at: Optional[str] = None
    stock_depth_source: Optional[str] = None
    stock_depth_label: Optional[str] = None


class StockRuptureSummary(BaseModel):
    """Resumo serializavel de ruptura de estoque por varredura."""

    brand: str
    total_products: int
    in_stock_count: int
    out_of_stock_count: int
    unknown_stock_count: int
    verified_stock_count: int
    rupture_pct: Optional[float] = None
    scan_id: Optional[str] = None
    monitor_id: Optional[str] = None
    scanned_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class PromotionInfo(BaseModel):
    """Promocao/selo comercial normalizado de forma aditiva."""

    type: Literal[
        "pix_discount",
        "percentage_discount",
        "bundle",
        "installments",
        "generic_badge",
    ]
    raw_text: str
    value: Optional[float] = None
    unit: Optional[str] = None
    payment_method: Optional[str] = None
    installments_count: Optional[int] = None
    installment_amount: Optional[float] = None
    parsed: bool = True


class MapRule(BaseModel):
    """Regra de preco minimo anunciado (MAP) persistida em JSON local."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    scope: Literal["product", "category", "brand"]
    target: str = Field(min_length=1)
    min_price: float = Field(gt=0)
    active: bool = True
    brand: Optional[str] = None
    category: Optional[str] = None
    product_code: Optional[str] = None
    product_url: Optional[str] = None
    normalized_url: Optional[str] = None
    notes: Optional[str] = None
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class RawProductBronze(BaseModel):
    """Dado bruto de um produto concorrente, sem transformações."""

    url: str
    brand: str
    raw_title: str
    raw_description: str
    price_full: float
    price_discount: Optional[float] = None
    price_discount_is_delta: bool = False
    stock_availability: Optional[bool] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    composition: Optional[str] = None
    product_code: Optional[str] = None
    available_colors: List[str] = Field(default_factory=list)
    available_sizes: List[str] = Field(default_factory=list)
    rating: Optional[float] = None
    review_count: Optional[int] = None
    scan_product_id: Optional[str] = None
    stock_depth_estimate: Optional[int] = None
    stock_depth_state: Optional[str] = None
    stock_depth_checked_at: Optional[str] = None
    stock_depth_source: Optional[str] = None
    stock_depth_label: Optional[str] = None
    reviews_state: Optional[str] = None
    review_comments: List[ReviewComment] = Field(default_factory=list)
    review_product_id: Optional[str] = None
    specifications: Dict[str, str] = Field(default_factory=dict)
    image_url: Optional[str] = None
    shipping: ShippingInfo | None = None
    promotions: List[PromotionInfo] = Field(default_factory=list)
    map_violation: bool = False
    map_price_floor: Optional[float] = None
    map_rule_scope: Optional[str] = None
    map_rule_id: Optional[str] = None
    map_infractor: Optional[str] = None
    map_infractor_is_default: bool = False

    is_free_shipping: bool = False
    shipping_price: Optional[float] = None
    landed_price: Optional[float] = None

    @model_validator(mode="after")
    def calculate_landed_price(self):
        if self.landed_price is None:
            base_price = resolve_effective_price(
                self.price_full,
                self.price_discount,
                self.price_discount_is_delta,
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
    price_discount_is_delta: bool = False
    image_url: Optional[str] = None
    category: Optional[str] = None
    available: Optional[bool] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    scan_product_id: Optional[str] = None
    stock_depth_estimate: Optional[int] = None
    stock_depth_state: Optional[str] = None
    stock_depth_checked_at: Optional[str] = None
    stock_depth_source: Optional[str] = None
    stock_depth_label: Optional[str] = None
    reviews_state: Optional[str] = None
    review_comments: List[ReviewComment] = Field(default_factory=list)
    review_product_id: Optional[str] = None
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
    promotions: List[PromotionInfo] = Field(default_factory=list)
    map_violation: bool = False
    map_price_floor: Optional[float] = None
    map_rule_scope: Optional[str] = None
    map_rule_id: Optional[str] = None
    map_infractor: Optional[str] = None
    map_infractor_is_default: bool = False

    is_free_shipping: bool = False
    shipping_price: Optional[float] = None
    landed_price: Optional[float] = None

    @model_validator(mode="after")
    def calculate_landed_price(self):
        if self.landed_price is None:
            base_price = resolve_effective_price(
                self.price_full,
                self.price_discount,
                self.price_discount_is_delta,
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
    price_original: Optional[float] = None
    last_price_discount: Optional[float] = None
    available: bool
    available_colors: List[str] = Field(default_factory=list)
    available_sizes: List[str] = Field(default_factory=list)
    map_violation: bool = False
    map_price_floor: Optional[float] = None
    map_rule_scope: Optional[str] = None
    map_rule_id: Optional[str] = None
    map_infractor: Optional[str] = None
    map_infractor_is_default: bool = False


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
    last_price_original: Optional[float] = None
    last_price_discount: Optional[float] = None
    # Estado da última checagem — alimenta o card do front:
    #   None      = ainda não checado (mostra "Pendente")
    #   "ok"      = preço resolvido
    #   "blocked" = não foi possível ler o produto (anti-bot / 403 / sem dados)
    #   "error"   = erro inesperado no ciclo
    last_status: Optional[str] = None
    last_error: Optional[str] = None
    last_checked_at: Optional[str] = None
    history: List[PriceHistoryEntry] = Field(default_factory=list)
    active: bool = True
    image_url: Optional[str] = None
    product_name: Optional[str] = None
    available_colors: List[str] = Field(default_factory=list)
    available_sizes: List[str] = Field(default_factory=list)
    map_violation: bool = False
    map_price_floor: Optional[float] = None
    map_rule_scope: Optional[str] = None
    map_rule_id: Optional[str] = None
    map_infractor: Optional[str] = None
    map_infractor_is_default: bool = False


# ---------------------------------------------------------------------------
# Notificações
# ---------------------------------------------------------------------------


class Notification(BaseModel):
    """Notificação persistente exibida na central do frontend."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    type: str  # "price_change" | "category_price_change" | "scan_finished"
    title: str
    message: str
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    read: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


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
    review_provider_evidence: Optional[str] = None
    review_unsupported_reason: Optional[str] = None
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
    target_sku: Optional[str] = Field(default=None, description="SKU alvo da busca cross (exibido no histórico no lugar do nome do produto)")
    type: str = Field(default="search", description="Tipo de busca: 'search' ou 'cross'")
    brands: List[str] = Field(default_factory=list)
    status: str = Field(default="PENDING", description="PENDING, COMPLETED, FAILED")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    results: Optional[Any] = None
    error: Optional[str] = None
