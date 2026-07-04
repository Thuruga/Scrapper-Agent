"""
Rota de Busca Comparativa Multi-Brand.

POST /search  —  Busca um termo em todas as marcas simultaneamente e retorna
                 os resultados em formato de comparação lado a lado.

Não usa Playwright — chama a API VTEX full-text diretamente (HTTP puro).
"""

from typing import Any, List, Optional
import io
import json
import re
import pandas as pd
import asyncio
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from config import settings
from services.brand_service import brand_service
from core.models import ComparisonResult, SearchProductResult, ShippingInfo
from services.engines.factory import engine_factory
from services.cross_marketplace_service import cross_marketplace_service
from services.map_evaluator_service import evaluate_map_violation
from services.map_rules_service import map_rules_service
from services.product_contract import build_canonical_export_dataframe
from services.search_history_service import search_history_service
from services.shipping.base import apply_shipping_calculation, is_url_allowed_for_brand
from services.shipping.resolver import resolve_shipping_provider
from services.shipping.regional_matrix import calculate_regional_matrix, load_cep_matrix

router = APIRouter(prefix="/search", tags=["search"])


def _has_export_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        cleaned = value.strip()
        return bool(cleaned) and cleaned.lower() != "none"
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _seed_search_export_product(
    product: SearchProductResult,
    brand_name: str,
) -> dict[str, Any]:
    return {
        "brand": brand_name or product.brand,
        "url": product.url,
        "product_name": product.product_name,
        "price_full": product.price_full,
        "price_discount": product.price_discount,
        "price_discount_is_delta": product.price_discount_is_delta,
        "image_url": product.image_url,
        "category": product.category,
        "available": product.available,
        "rating": product.rating,
        "review_count": product.review_count,
        "available_colors": product.available_colors,
        "available_sizes": product.available_sizes,
        "seller": product.seller,
        "sku_id": product.sku_id,
        "seller_id": product.seller_id,
        "is_free_shipping": product.is_free_shipping,
        "shipping_price": product.shipping_price,
        "landed_price": product.landed_price,
        "promotions": [p.model_dump(mode="json") for p in product.promotions],
        "map_violation": product.map_violation,
        "map_price_floor": product.map_price_floor,
        "map_rule_scope": product.map_rule_scope,
        "map_rule_id": product.map_rule_id,
        "map_infractor": product.map_infractor,
        "map_infractor_is_default": product.map_infractor_is_default,
    }


def _merge_search_export_product(
    product: SearchProductResult,
    brand_name: str,
    details: Optional[dict[str, Any]],
) -> dict[str, Any]:
    merged = _seed_search_export_product(product, brand_name)
    detail_payload = dict(details or {})
    detail_price = detail_payload.pop("price", None)
    if _has_export_value(detail_price) and not _has_export_value(
        detail_payload.get("price_full")
    ):
        detail_payload["price_full"] = detail_price

    for key, value in detail_payload.items():
        if _has_export_value(value):
            merged[key] = value

    merged["brand"] = brand_name or merged.get("brand")
    return merged


def _normalize_search_product_price(product: SearchProductResult) -> SearchProductResult:
    if (
        not product.price_discount_is_delta
        or product.price_full is None
        or product.price_discount is None
    ):
        return product

    payload = product.model_dump(mode="json")
    payload["price_full"] = round(product.price_full + product.price_discount, 2)
    payload["price_discount"] = round(product.price_full, 2)
    payload["price_discount_is_delta"] = False
    payload["landed_price"] = None
    return SearchProductResult.model_validate(payload)


def _normalize_brand_results_for_response(
    brand_results: List[Any],
) -> List[Any]:
    normalized: list[Any] = []
    for brand_result in brand_results:
        normalized.append(
            brand_result.model_copy(
                update={
                    "products": [
                        _normalize_search_product_price(product)
                        for product in brand_result.products
                    ]
                }
            )
        )
    return normalized


def _enrich_brand_results_for_phase43(brand_results: List[Any]) -> List[Any]:
    rules = map_rules_service.list_rules(active_only=True)
    enriched: list[Any] = []
    for brand_result in brand_results:
        products = []
        for product in brand_result.products:
            promotions = product.promotions
            map_metadata = evaluate_map_violation(
                product,
                rules,
                brand_name=getattr(brand_result, "brand_name", None),
                marketplace=getattr(brand_result, "brand_name", None) or product.brand,
            )
            products.append(
                product.model_copy(update={**map_metadata, "promotions": promotions})
            )
        enriched.append(brand_result.model_copy(update={"products": products}))
    return enriched


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
    zipcode: Optional[str] = Field(
        default=None,
        pattern=r"^\d{5}-?\d{3}$",
        description="CEP de destino para o cálculo do frete"
    )
    include_shipping: bool = Field(
        default=False,
        description="Incluir a extração do valor de frete nos motores que suportam"
    )

class CrossMarketplaceRequest(BaseModel):
    target_sku: str = Field(..., description="SKU base para referência.")
    search_query: Optional[str] = Field(None, description="Query estrita/específica. Se vazia, será extraída da VTEX.")
    broad_query: Optional[str] = Field(None, description="Query ampla para buscar volume.")
    min_score: float = Field(55.0, description="Match score mínimo.")
    zipcode: Optional[str] = Field(None, pattern=r"^\d{5}-?\d{3}$", description="CEP de destino")



class SearchConfigResponse(BaseModel):
    """Resposta do endpoint de configuração de busca — somente dados não-sensíveis."""

    default_cep: str = Field(
        ...,
        description="CEP padrão configurado no backend para cálculo de frete.",
    )


class CalculateShippingRequest(BaseModel):
    marketplace: str = Field(..., description="Nome do marketplace (Netshoes, Amazon, Mercado Livre)")
    url: str = Field(..., description="URL do produto no marketplace")
    zipcode: str = Field(..., description="CEP de destino")


class CalculateVtexShippingRequest(BaseModel):
    """Cálculo de frete VTEX sob demanda para um produto da busca comparativa."""

    brand_key: str = Field(..., min_length=1, description="Chave da marca VTEX (ex: 'aramis', 'foxton').")
    sku_id: str = Field(..., min_length=1, description="itemId do SKU (vem do produto da busca).")
    seller_id: str = Field(default="1", description="ID do seller do SKU.")
    zipcode: str = Field(..., pattern=r"^\d{5}-?\d{3}$", description="CEP de destino.")


class CalculateBrandShippingRequest(BaseModel):
    """Calculo de frete sob demanda para marcas nao-VTEX."""

    brand_key: str = Field(..., min_length=1, description="Chave da marca.")
    product_url: str = Field(..., min_length=1, description="URL do produto na marca.")
    zipcode: str = Field(..., pattern=r"^\d{5}-?\d{3}$", description="CEP de destino.")


class CalculateBrandShippingResponse(BaseModel):
    state: str
    shipping_options: List[ShippingInfo] = Field(default_factory=list)
    shipping: Optional[ShippingInfo] = None
    shipping_price: Optional[float] = None
    is_free_shipping: bool = False
    message: Optional[str] = None


class CalculateShippingMatrixRequest(BaseModel):
    """Matriz de frete multi-regional sob demanda para um produto (FRET-09)."""

    brand_key: str = Field(..., min_length=1, description="Chave da marca.")
    product_url: str = Field(..., min_length=1, description="URL do produto na marca.")


class ShippingMatrixRegionResult(BaseModel):
    region: str
    capital: str
    cep: str
    state: str
    shipping: Optional[ShippingInfo] = None
    message: Optional[str] = None
    cached: bool = False


class CalculateShippingMatrixResponse(BaseModel):
    regions: List[ShippingMatrixRegionResult] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Export helpers and models — POST /cross-marketplace/export
# ---------------------------------------------------------------------------

FORMULA_CHARS_RE = re.compile(r'^[=+\-@]')


def _sanitize_cell(value):
    """Prepend single-quote to strings starting with a formula character (injection guard)."""
    if isinstance(value, str) and FORMULA_CHARS_RE.match(value):
        return "'" + value
    return value


class ExportItem(BaseModel):
    marketplace: str
    seller: str
    title: str
    price: float
    shipping_price: Optional[float] = None
    landed_price: float
    is_free_shipping: bool = False
    final_match_score: float = 0.0
    match_score: float = 0.0
    is_similar: bool = False
    url: str
    promotions: List[dict[str, Any]] = Field(default_factory=list)
    map_violation: bool = False
    map_price_floor: Optional[float] = None
    map_rule_scope: Optional[str] = None
    map_rule_id: Optional[str] = None
    map_infractor: Optional[str] = None
    map_infractor_is_default: bool = False
    display_order: Optional[int] = Field(None, alias="_display_order")

    model_config = {"extra": "allow", "populate_by_name": True}


class CrossMarketplaceExportRequest(BaseModel):
    items: List[ExportItem] = Field(..., min_length=1, max_length=500)
    search_query: Optional[str] = None
    target_sku: str = Field(..., min_length=1)


def _serialize_promotions_for_export(promotions: List[dict[str, Any]]) -> str:
    if not promotions:
        return ""
    return json.dumps(promotions, ensure_ascii=False, sort_keys=True)


def _has_phase43_cross_export_data(items: List[ExportItem]) -> bool:
    return any(
        item.promotions
        or item.map_violation
        or item.map_price_floor is not None
        or item.map_rule_scope
        or item.map_rule_id
        or item.map_infractor
        for item in items
    )

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=ComparisonResult,
    summary="Busca comparativa multi-brand",
    description=(
        "Busca um termo em todas as marcas simultaneamente e retorna "
        "os resultados em formato de comparação lado a lado."
    ),
)
async def search_products(request: SearchRequest) -> ComparisonResult:
    """
    Executa a busca comparativa de forma síncrona e retorna o resultado diretamente.
    """
    import uuid

    # list_brands(active_only=True) já inclui os marketplaces (mercado_livre,
    # netshoes, amazon) como entradas reais em brands.json (Plan 04 / D-10) —
    # nenhum .extend() hardcoded é necessário (era a 2ª fonte de verdade que
    # duplicava cada marketplace na lista-alvo e quebrava ao desativar um deles).
    all_brands = [b.brand_key for b in brand_service.list_brands(active_only=True)]
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
    # Salvaguarda: dedupe preservando ordem (dict.fromkeys, NÃO set — a ordem das
    # colunas no front depende desta sequência).
    target_brands = list(dict.fromkeys(b.lower() for b in target_brands))

    clean_zipcode = request.zipcode.replace("-", "") if request.zipcode else None

    job_id = str(uuid.uuid4())
    # DEVIATION 1 (Pitfall 2): store raw query term — NOT a composed display label.
    # SearchPage reopen (App.tsx:656) dumps res.query back into the search box;
    # a label string would corrupt it. Label composition happens in the frontend.
    search_history_service.create_job(
        job_id=job_id,
        query=request.query,
        brands=target_brands,
        type="search",
    )

    try:
        brand_results = await engine_factory.search_all_brands(
            query=request.query,
            brands=target_brands,
            max_per_brand=request.max_per_brand,
            sort=request.sort,
            only_in_stock=request.only_in_stock,
            zipcode=clean_zipcode,
            include_shipping=request.include_shipping
        )
        brand_results = _enrich_brand_results_for_phase43(brand_results)
        brand_results = _normalize_brand_results_for_response(brand_results)

        result = ComparisonResult(
            query=request.query,
            brands_searched=target_brands,
            results=brand_results,
        )
        # DEVIATION 2 (Pitfall 1 / Resolution A): store the INNER list only.
        # SearchPage reopen sets setResults({ results: res.results, ... }) and
        # expects res.results to BE the List[BrandSearchResult] array. Storing
        # the ComparisonResult wrapper causes a silent empty render.
        search_history_service.update_job(
            job_id=job_id,
            status="COMPLETED",
            results=result.model_dump(mode="json")["results"],
        )
        return result
    except Exception as e:
        search_history_service.update_job(
            job_id=job_id,
            status="FAILED",
            error=str(e),
        )
        raise


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
    zipcode: Optional[str] = Query(None, pattern=r"^\d{5}-?\d{3}$", description="CEP de destino"),
    include_shipping: bool = Query(default=False)
) -> ComparisonResult:
    """Atalho GET para facilitar testes direto pelo browser/swagger."""
    clean_zipcode = zipcode.replace("-", "") if zipcode else None

    brand_results = await engine_factory.search_all_brands(
        query=q,
        brands=None,  # Todas as marcas
        max_per_brand=max_per_brand,
        sort=sort,
        only_in_stock=only_in_stock,
        zipcode=clean_zipcode,
        include_shipping=include_shipping
    )
    brand_results = _enrich_brand_results_for_phase43(brand_results)
    brand_results = _normalize_brand_results_for_response(brand_results)

    # search_all_brands roda com brands=None → usa list_brands(active_only=True)
    # como fonte única. Montar brands_searched da MESMA fonte (sem .extend) mantém
    # a metadata alinhada com o que foi de fato buscado (D-10).
    all_brands = [b.brand_key for b in brand_service.list_brands(active_only=True)]

    return ComparisonResult(
        query=q,
        brands_searched=all_brands,
        results=brand_results,
    )


@router.get(
    "/config",
    response_model=SearchConfigResponse,
    summary="Configuração de busca (somente leitura)",
    description=(
        "Retorna dados de configuração não-sensíveis para o frontend, "
        "como o CEP padrão usado no cálculo de frete. "
        "Não requer autenticação e não expõe segredos (T-33-01)."
    ),
)
async def get_search_config() -> SearchConfigResponse:
    """Endpoint read-only que expõe DEFAULT_CEP para o frontend (D-04).

    Sem acesso a banco, sem segredos — somente leitura de settings.
    CEP nunca é interpolado em URL; apenas retornado no corpo JSON.
    """
    return SearchConfigResponse(default_cep=settings.DEFAULT_CEP)


@router.post(
    "/export",
    summary="Exporta a busca comparativa em Excel",
    description="Pesquisa um termo em todas as marcas (ou filtradas) e retorna um arquivo .xlsx."
)
async def export_search_products(request: SearchRequest):
    """
    Executa a busca comparativa e retorna o resultado como download de arquivo Excel.
    """
    # list_brands(active_only=True) já inclui os marketplaces como entradas reais
    # (Plan 04 / D-10) — sem .extend() hardcoded redundante.
    all_brands = [b.brand_key for b in brand_service.list_brands(active_only=True)]
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
    # Salvaguarda: dedupe preservando ordem (dict.fromkeys, NÃO set).
    target_brands = list(dict.fromkeys(b.lower() for b in target_brands))

    clean_zipcode = request.zipcode.replace("-", "") if request.zipcode else None

    brand_results = await engine_factory.search_all_brands(
        query=request.query,
        brands=target_brands,
        max_per_brand=request.max_per_brand,
        sort=request.sort,
        only_in_stock=request.only_in_stock,
        zipcode=clean_zipcode,
        include_shipping=request.include_shipping
    )
    brand_results = _enrich_brand_results_for_phase43(brand_results)
    brand_results = _normalize_brand_results_for_response(brand_results)

    # -------------------------------------------------------------------------
    # Enriquece cada card de busca com PDP quando esse detalhe realmente agrega
    # dados, mas preserva a linha original para engines parciais/sparsos.
    # -------------------------------------------------------------------------
    tasks = []

    async def fetch_full_product(brand_key, brand_name, product):
        try:
            engine = engine_factory.get_engine(brand_key)
            prod_dict = await engine.get_product_details(product.url)
            return _merge_search_export_product(product, brand_name, prod_dict)
        except Exception as e:
            import logging
            logging.getLogger("routes_search").warning(
                f"Erro ao buscar detalhes de {product.url}: {e}"
            )
        return _merge_search_export_product(product, brand_name, None)

    for brand_res in brand_results:
        brand_key = brand_res.brand_key
        brand_name = brand_res.brand_name
        for p in brand_res.products:
            tasks.append(fetch_full_product(brand_key, brand_name, p))

    full_products = await asyncio.gather(*tasks)
    data = [p for p in full_products if p]

    df = build_canonical_export_dataframe(data)
    if not df.empty:
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


@router.post(
    "/cross-marketplace",
    summary="Busca cruzada em Marketplaces (ML, NS, AMZ)",
    description=(
        "Pesquisa no Mercado Livre, Netshoes e Amazon. "
        "Usa um 'broad_query' para buscar resultados e os filtra com 'strict_query' "
        "calculando um match score. Retorna o JSON unificado para dashboards."
    )
)
async def cross_marketplace_search(request: CrossMarketplaceRequest):
    """Executa a busca concorrente nos marketplaces e consolida os resultados."""
    
    strict_q = request.search_query
    broad_q = request.broad_query

    ref_product_data = None
    if not strict_q:
        from services.vtex_api_scraper import VtexApiClient
        # Instancia para a Aramis como referência primária
        scraper = VtexApiClient(brand_name="Aramis")
        
        # Busca na Aramis pelo SKU
        vtex_result = await scraper.search(query=request.target_sku, max_results=1)
        
        if not vtex_result.products:
            import logging
            logger = logging.getLogger("routes_search")
            logger.warning(f"SKU '{request.target_sku}' não encontrado na Aramis. Usando o SKU como fallback para a busca nos marketplaces.")
            strict_q = request.target_sku
            broad_q = request.target_sku
        else:
            ref_product = vtex_result.products[0]
            
            ref_product_data = {
                "name": ref_product.product_name,
                "url": ref_product.url,
                "image_url": getattr(ref_product, "image_url", ""),
                "price": ref_product.price_full
            }
            
            # A query estrita se torna o nome completo do produto (Sniper)
            strict_q = ref_product.product_name
            
            # A query ampla será mapeada para ser enxuta: Categoria (Mapeada) + Primeiro Token + Aramis
            # Isso evita queries grandes que os motores rejeitam (PREC-01).
            CATEGORY_SYNONYMS = {
                "tênis": "tênis",
                "sapatênis": "tênis",
                "camisa": "camisa",
                "t-shirt": "camiseta",
                "polo": "polo"
            }
            
            cat_lower = ref_product.category.lower() if ref_product.category else ""
            mapped_cat = CATEGORY_SYNONYMS.get(cat_lower, ref_product.category)
            
            tokens = strict_q.split()[:4] # Usar 4 tokens para capturar o modelo, ex: Tênis Aramis Icon Light
            if mapped_cat and mapped_cat.lower() not in strict_q.lower():
                broad_q = f"{mapped_cat} {' '.join(tokens)} Aramis"
            else:
                broad_q = f"{' '.join(tokens)} Aramis"
            
    else:
        broad_q = broad_q or strict_q
        
    # Adiciona 'aramis' ao termo de busca para os marketplaces (se já não estiver presente)
    if broad_q and "aramis" not in broad_q.lower():
        broad_q = f"{broad_q} aramis"
    if strict_q and "aramis" not in strict_q.lower():
        strict_q = f"{strict_q} aramis"
        
    from services.nlp_service import nlp_service
    
    broad_q_no_color = nlp_service.remove_colors(broad_q) if broad_q else broad_q
    strict_q_no_color = nlp_service.remove_colors(strict_q) if strict_q else strict_q
    
    import uuid
    job_id = str(uuid.uuid4())

    # Store query string for display: either strict_q, broad_q or target_sku
    display_query = strict_q or broad_q or request.target_sku
    search_history_service.create_job(
        job_id=job_id,
        query=f"SKU: {display_query}",
        brands=["mercadolivre", "netshoes", "amazon"],
        type="cross",
        target_sku=request.target_sku
    )

    try:
        result = await cross_marketplace_service.compare_product(
            broad_query=broad_q,
            strict_query=strict_q_no_color,
            target_sku=request.target_sku,
            min_score=request.min_score,
            zipcode=request.zipcode
        )
        
        result["reference_product"] = ref_product_data
        result["job_id"] = job_id
        
        search_history_service.update_job(
            job_id=job_id,
            status="COMPLETED",
            results=result
        )
        return result
    except Exception as e:
        search_history_service.update_job(
            job_id=job_id,
            status="FAILED",
            error=str(e)
        )
        raise

@router.post("/cross-marketplace/export", summary="Exporta busca por SKU em Excel")
async def export_cross_marketplace(request: CrossMarketplaceExportRequest):
    """
    Recebe os itens já exibidos no frontend e devolve um .xlsx com 10 colunas PT-BR.
    Não re-executa a busca nem re-raspa nenhum produto (EXPORT-05 fidelity).
    """
    sorted_items = sorted(
        request.items,
        key=lambda i: i.display_order if i.display_order is not None else float('inf'),
    )
    include_phase43 = _has_phase43_cross_export_data(sorted_items)

    rows = []
    for item in sorted_items:
        score = round(item.final_match_score if item.final_match_score != 0.0 else item.match_score)

        if item.shipping_price is None and not item.is_free_shipping:
            frete_display = "A calcular"
            total_display = item.price
        elif item.is_free_shipping:
            frete_display = 0.0
            total_display = item.landed_price
        else:
            frete_display = item.shipping_price
            total_display = item.landed_price

        row = {
            "Plataforma":     _sanitize_cell(item.marketplace),
            "Vendedor":       _sanitize_cell(item.seller),
            "Título":         _sanitize_cell(item.title),
            "Preço":          item.price,
            "Frete":          frete_display,
            "Preço Total":    total_display,
            "Frete Grátis":   "Sim" if item.is_free_shipping else "Não",
            "Score de Match": score,
            "Similar":        "Sim" if item.is_similar else "Não",
            "URL":            _sanitize_cell(item.url),
        }
        if include_phase43:
            row.update(
                {
                    "Violacao MAP": "Sim" if item.map_violation else "Nao",
                    "Piso MAP": item.map_price_floor,
                    "Escopo MAP": item.map_rule_scope,
                    "Regra MAP": item.map_rule_id,
                    "Infrator MAP": _sanitize_cell(item.map_infractor),
                    "Infrator Default": "Sim" if item.map_infractor_is_default else "Nao",
                    "Promocoes": _sanitize_cell(_serialize_promotions_for_export(item.promotions)),
                }
            )
        rows.append(row)

    df = pd.DataFrame(rows)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Busca SKU")
    output.seek(0)

    query_token = request.search_query or request.target_sku
    safe_query = "".join(c if c.isalnum() else "_" for c in query_token)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"busca_sku_{safe_query}_{timestamp}.xlsx"

    return StreamingResponse(
        output,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.post(
    "/calculate-shipping",
    summary="Cálculo avançado de frete sob demanda",
    description="Calcula o frete unitário usando Playwright para Netshoes/Amazon ou API para ML."
)
async def calculate_shipping_single(request: CalculateShippingRequest):
    """
    Aciona o engine específico do marketplace para buscar o valor real de frete
    usando automação de navegador ou endpoint privado.
    """
    engine = engine_factory.get_engine(request.marketplace)
    if not engine:
        raise HTTPException(status_code=400, detail=f"Marketplace '{request.marketplace}' não suportado.")
        
    try:
        # A engine deve implementar calculate_shipping_advanced
        if hasattr(engine, "calculate_shipping_advanced"):
            shipping_info = await engine.calculate_shipping_advanced(request.url, request.zipcode)
            if shipping_info:
                if isinstance(shipping_info, dict) and shipping_info.get("error"):
                    return {"status": "error", "message": shipping_info["error"]}
                return {"status": "success", "shipping_info": shipping_info}
            else:
                return {"status": "error", "message": "Não foi possível extrair o frete desta página."}
        else:
            raise HTTPException(status_code=501, detail=f"O motor {request.marketplace} não suporta cálculo avançado de frete sob demanda.")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/calculate-shipping-vtex",
    summary="Cálculo de frete VTEX sob demanda (busca comparativa)",
    description=(
        "Calcula o frete de um produto VTEX via simulação de checkout, sob demanda. "
        "O domínio é resolvido a partir da marca persistida (nunca de input do caller — T-33-01). "
        "Retorna o estado (available / unavailable_for_cep / temporary_failure) e a lista de opções."
    ),
)
async def calculate_shipping_vtex(request: CalculateVtexShippingRequest):
    """Aciona a simulação de checkout VTEX para um único SKU e retorna as modalidades de entrega."""
    from services.vtex_api_scraper import VtexApiClient

    clean_zipcode = request.zipcode.replace("-", "")

    try:
        result = await VtexApiClient.calculate_for_brand(
            brand_key=request.brand_key.lower(),
            sku_id=request.sku_id,
            seller_id=request.seller_id or "1",
            zipcode=clean_zipcode,
        )
    except ValueError as e:
        # Marca inexistente ou não-VTEX → erro de cliente.
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "state": result["state"],
        "shipping_options": [opt.model_dump(mode="json") for opt in result["shipping_options"]],
    }


@router.post(
    "/calculate-shipping-brand",
    response_model=CalculateBrandShippingResponse,
    summary="Calculo de frete nao-VTEX sob demanda",
    description=(
        "Calcula frete para marcas Wake/Shopify/Mercado Livre/Amazon/Netshoes "
        "usando o resolver nao-VTEX. VTEX permanece no endpoint /calculate-shipping-vtex."
    ),
)
async def calculate_shipping_brand(request: CalculateBrandShippingRequest):
    brand_key = request.brand_key.lower()
    brand = brand_service.get_brand(brand_key)
    if not brand:
        raise HTTPException(status_code=404, detail=f"Marca '{brand_key}' nao encontrada.")

    engine = getattr(brand, "engine", "vtex")
    if engine == "vtex":
        raise HTTPException(
            status_code=400,
            detail="Use /search/calculate-shipping-vtex para marcas VTEX.",
        )

    if not is_url_allowed_for_brand(request.product_url, brand):
        raise HTTPException(
            status_code=400,
            detail="URL do produto nao pertence ao dominio da marca.",
        )

    clean_zipcode = request.zipcode.replace("-", "")
    product = SearchProductResult(
        brand=brand_key,
        product_name="Produto",
        url=request.product_url,
        price_full=None,
    )
    provider = resolve_shipping_provider(brand)
    calculation = await provider.calculate(product, clean_zipcode, brand)
    apply_shipping_calculation(product, calculation)

    return CalculateBrandShippingResponse(
        state=calculation.state,
        shipping_options=product.shipping_options,
        shipping=product.shipping,
        shipping_price=product.shipping_price,
        is_free_shipping=product.is_free_shipping,
        message=calculation.message,
    )


@router.post(
    "/calculate-shipping-matrix",
    response_model=CalculateShippingMatrixResponse,
    summary="Matriz de frete multi-regional sob demanda (FRET-09)",
    description=(
        "Calcula frete/prazo para um produto nos 5 CEPs curados (uma capital por regiao). "
        "On-demand/batched apenas — nunca chamado durante varredura/busca ao vivo (D-10)."
    ),
)
async def calculate_shipping_matrix(request: CalculateShippingMatrixRequest):
    brand_key = request.brand_key.lower()
    brand = brand_service.get_brand(brand_key)
    if not brand:
        raise HTTPException(status_code=404, detail=f"Marca '{brand_key}' nao encontrada.")

    if not is_url_allowed_for_brand(request.product_url, brand):
        raise HTTPException(
            status_code=400,
            detail="URL do produto nao pertence ao dominio da marca.",
        )

    product = SearchProductResult(
        brand=brand_key,
        product_name="Produto",
        url=request.product_url,
        price_full=None,
    )
    cep_list = load_cep_matrix()
    results = await calculate_regional_matrix(
        product, brand, cep_list, triggered_by="on_demand_matrix_button"
    )

    return CalculateShippingMatrixResponse(regions=results)
