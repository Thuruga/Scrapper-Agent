from fastapi import APIRouter, HTTPException
from typing import List
import logging
import ipaddress
import json as _json
import re
import aiohttp
from bs4 import BeautifulSoup
from pydantic import BaseModel
from urllib.parse import urlparse
from core.models import DynamicBrand, DynamicBrandCreate, CategoryMapping, BrandActiveUpdate
from services.brand_service import brand_service
from services.engines.factory import engine_factory
from core.session_manager import SessionManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Brands"])


# ---------------------------------------------------------------------------
# Pydantic models for POST /brands/identify
# ---------------------------------------------------------------------------

class IdentifyRequest(BaseModel):
    url: str


class IdentifyResponse(BaseModel):
    engine: str
    inferred_name: str
    domain: str
    warning: str | None = None


# ---------------------------------------------------------------------------
# infer_brand_name — D-01 precedence: JSON-LD → OG → <title> → domain
# ---------------------------------------------------------------------------

def infer_brand_name(html: "str | BeautifulSoup | None", domain: str) -> str:
    """Infer brand name from home HTML following D-01 precedence.

    Precedence:
      1. JSON-LD Organization / Brand ``name``
      2. OG ``og:site_name`` meta tag
      3. ``<title>`` first segment (split on `` - ``, `` | ``, `` – ``, `` — ``)
      4. Domain-derived fallback: strip TLD + ccTLD, split camelCase, capitalise.

    Accepts ``html`` as a raw HTML string, a pre-built BeautifulSoup object, or
    ``None`` (triggers domain fallback immediately).
    """
    # Build soup from html when needed
    if html is None:
        soup = None
    elif isinstance(html, BeautifulSoup):
        soup = html
    else:
        soup = BeautifulSoup(html, "html.parser")

    if soup is not None:
        # 1. JSON-LD — iterate all ld+json blocks (analog: zara_parser._jsonld_blocks)
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                block = _json.loads(script.string or "")
            except (ValueError, TypeError):
                continue
            if isinstance(block, dict) and block.get("@type") in ("Organization", "Brand"):
                name = block.get("name", "").strip()
                if name:
                    return name

        # 2. OG site_name (analog: zara_parser.py l.267-270)
        og_tag = soup.find("meta", property="og:site_name")
        if og_tag:
            name = og_tag.get("content", "").strip()
            if name:
                return name

        # 3. <title> — first segment before common separators
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            raw_title = title_tag.string.strip()
            # Split on " - ", " | ", " – ", " — "
            segment = re.split(r"\s[-|–—]\s", raw_title)[0].strip()
            if segment:
                return segment

    # 4. Domain fallback (analog: 40-PATTERNS.md § Domain fallback pattern)
    # Strip www., then take the first label before the first dot.
    host = domain.lower()
    if host.startswith("www."):
        host = host[len("www."):]
    stem = host.split(".")[0]
    # Split camelCase (e.g. "hugoboss" → "hugoboss"; "HugoBoss" → "Hugo Boss")
    with_spaces = re.sub(r"([a-z])([A-Z])", r"\1 \2", stem)
    # Replace hyphens/underscores with spaces then capitalise each word
    return " ".join(w.capitalize() for w in with_spaces.replace("-", " ").replace("_", " ").split())


# ---------------------------------------------------------------------------
# detect_engine — returns (engine, home_html) tuple on EVERY path (D-01)
# ---------------------------------------------------------------------------

async def detect_engine(domain: str) -> tuple[str, str | None]:
    """Tenta descobrir automaticamente a plataforma (motor) do domínio.

    Returns a 2-tuple (engine: str, home_html: str | None).
    home_html is the raw HTML of the home page when the Step-3 HTTP probe
    successfully fetched it; None for early API-based detections and for
    fallback/error paths.
    """
    session = await SessionManager.get_session()
    base_url = f"https://{domain}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # 1. Tenta Shopify via collections.json
    try:
        async with session.get(f"{base_url}/collections.json", timeout=aiohttp.ClientTimeout(total=5), headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                if "collections" in data:
                    return "shopify", None
    except Exception as e:
        logger.debug("Detecção Shopify via collections.json falhou para %s: %s", domain, e)

    # 2. Tenta VTEX via API padrão
    try:
        async with session.get(f"{base_url}/api/catalog_system/pub/category/tree/1", timeout=aiohttp.ClientTimeout(total=5), headers=headers) as resp:
            if resp.status == 200:
                return "vtex", None
    except Exception as e:
        logger.debug("Detecção VTEX via API de categorias falhou para %s: %s", domain, e)

    # 3. Fallback: Analisa o HTML da home page
    # Security (T-25-01-SR): allow_redirects=False evita que um redirect malicioso
    # faça a detecção ler HTML de um domínio atacante em vez do domínio-alvo.
    # Pitfall 1 (D-01): when no marker is matched but HTML was successfully fetched,
    # save it so name inference can reuse it — but still fall through to the browser
    # probe (step 6) which may identify sfcc/zara via rendered markers.
    _step3_html: str | None = None
    try:
        async with session.get(base_url, timeout=aiohttp.ClientTimeout(total=5), headers=headers, allow_redirects=False) as resp:
            html = await resp.text()
            html_lower = html.lower()

            # Step 3 (Wake Commerce — D-02, D-05, Pitfall 1): probe ANTES do VTEX HTML.
            # fbitsstatic.net é o CDN exclusivo da plataforma Wake Commerce.
            # D-05: retorna "wake" (engine correto) para não acionar a regra D-04 (unknown → inativo).
            if "fbitsstatic.net" in html_lower:
                logger.info("detect_engine: Wake Commerce detectado para %s (fbitsstatic.net)", domain)
                return "wake", html

            # Step 4 (VTEX HTML — T-25-01-WK): apenas marcadores exclusivos da VTEX.
            # Removida a condição solta '"vtex" in html_lower' que causava falso
            # positivo em páginas Wake/marketplace (Pitfall 1).
            if "vtexassets.com" in html_lower or "vtexcommercestable.com" in html_lower:
                return "vtex", html

            # Step 5 (Shopify HTML): marcadores exclusivos da plataforma Shopify.
            if "cdn.shopify.com" in html_lower or "window.shopify" in html_lower:
                return "shopify", html

            # Step 5b (Zara / Inditex): storefront proprio da Zara.
            if "static.zara.net" in html_lower or (
                "zara.com" in html_lower and "data-store=" in html_lower
            ):
                logger.info("detect_engine: Zara detectado para %s", domain)
                return "zara", html

            # No marker matched — save HTML for name inference fallback, then
            # continue to the browser probe (step 6) which may still identify sfcc/zara.
            _step3_html = html

    except Exception as e:
        logger.debug("Detecção via análise do HTML da home falhou para %s: %s", domain, e)

    # Step 6 (D-01, D-02, D-03, D-07): SFCC browser probe — last resort.
    # Renderiza a home via Playwright para expor assets demandware que HTTP direto
    # não entrega (403 em Lacoste/HugoBoss). Só dispara depois que Shopify, VTEX
    # e as probes HTML falharam (D-07 — last-resort ordering).
    # Marcadores exclusivos: demandware.static e demandware.edgesuite.net (D-02).
    # A substring ampla "demandware" NÃO é usada para evitar falsos positivos (SC-4).
    # Import lazy (dentro do try) para que uma instalação sem Playwright não quebre
    # o módulo no startup (D-03 — reusa BrowserManager existente, sem nova infra).
    try:
        from core.browser_manager import BrowserManager
        rendered_html = await BrowserManager.fetch_html(f"https://{domain}")
        rendered_lower = rendered_html.lower()
        if "static.zara.net" in rendered_lower or (
            "zara.com" in rendered_lower and "data-store=" in rendered_lower
        ):
            logger.info("detect_engine: Zara detectado para %s (rendered marker)", domain)
            return "zara", rendered_html
        if "demandware.static" in rendered_lower or "demandware.edgesuite.net" in rendered_lower:
            logger.info("detect_engine: SFCC detectado para %s (demandware marker)", domain)
            return "sfcc", rendered_html
    except Exception as e:
        # D-04: probe failure é normal (timeout, Playwright desabilitado, 403 sem markers) —
        # degrada silenciosamente para "unknown" sem crash.
        logger.debug("Detecção SFCC via browser falhou para %s: %s", domain, e)

    # Step 7: plataforma desconhecida. NÃO assume VTEX (evita mascaramento silencioso).
    # Carry step-3 HTML when available so name inference can still run (Pitfall 1 / D-01).
    return "unknown", _step3_html


@router.post("/brands/", response_model=DynamicBrand)
async def create_brand(brand_data: DynamicBrandCreate):
    """Cadastra ou atualiza uma nova marca no sistema."""
    try:
        if brand_data.engine == "auto":
            # Realiza a deteccao automatica
            brand_data.engine, _ = await detect_engine(brand_data.domain)

        saved = brand_service.add_brand(brand_data)

        # D-04: Motor desconhecido → persiste inativo sem levantar erro HTTP.
        # Plataformas não suportadas não devem entrar na busca ativa (o chokepoint
        # list_brands(active_only=True) os excluirá). set_active é idempotente.
        if saved.engine == "unknown":
            logger.info(
                "create_brand: engine 'unknown' para '%s' — marcando is_active=False (D-04)",
                saved.brand_key,
            )
            saved = brand_service.set_active(saved.brand_key, False)

        return saved
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/brands/", response_model=List[DynamicBrand])
async def list_brands():
    """Lista todas as marcas cadastradas."""
    brands = brand_service.list_brands()
    
    # Inject virtual marketplaces so they appear in the UI filters
    brands.append(
        DynamicBrand(
            brand_key="mercado_livre",
            brand_name="Mercado Livre",
            domain="mercadolivre.com.br",
            engine="mercadolivre",
            mappings=[]
        )
    )
    brands.append(
        DynamicBrand(
            brand_key="netshoes",
            brand_name="Netshoes",
            domain="netshoes.com.br",
            engine="netshoes",
            mappings=[]
        )
    )
    brands.append(
        DynamicBrand(
            brand_key="amazon",
            brand_name="Amazon",
            domain="amazon.com.br",
            engine="amazon",
            mappings=[]
        )
    )

    return brands


@router.get("/brands/{brand_key}/discover")
async def discover_categories(brand_key: str):
    """
    Aciona o motor de Auto-Discovery para encontrar a árvore de categorias real.
    Não salva nada no banco, apenas retorna para o frontend.
    """
    brand = brand_service.get_brand(brand_key)
    if not brand:
        raise HTTPException(status_code=404, detail="Marca não encontrada")
    
    engine = engine_factory.get_engine(brand_key)
    categories = await engine.discover_categories()
    
    if not categories:
        raise HTTPException(
            status_code=400, 
            detail="Não foi possível descobrir as categorias. Verifique o domínio ou motor."
        )
    
    return categories


@router.get("/brands/{brand_key}/mappings", response_model=List[CategoryMapping])
async def get_brand_mappings(brand_key: str):
    """Retorna os mapeamentos atuais de uma marca."""
    brand = brand_service.get_brand(brand_key)
    if not brand:
        raise HTTPException(status_code=404, detail="Marca não encontrada")
    return brand.mappings


@router.put("/brands/{brand_key}/mappings", response_model=DynamicBrand)
async def update_brand_mappings(brand_key: str, mappings: List[CategoryMapping]):
    """Salva os mapeamentos de categoria selecionados pelo usuário."""
    try:
        return brand_service.update_mappings(brand_key, mappings)
    except KeyError:
        raise HTTPException(status_code=404, detail="Marca não encontrada")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/brands/{brand_key}/active", response_model=DynamicBrand)
async def set_brand_active(brand_key: str, payload: BrandActiveUpdate):
    """Ativa ou desativa uma marca (idempotente). 404 se a marca não existir."""
    result = brand_service.set_active(brand_key, payload.is_active)
    if result is None:
        raise HTTPException(status_code=404, detail="Marca não encontrada")
    return result


@router.delete("/brands/{brand_key}")
async def delete_brand(brand_key: str):
    """Exclui uma marca do sistema e limpa monitores ativos."""
    from services.price_monitor_service import monitor_service
    
    # 1. Limpa monitores ativos desta marca
    await monitor_service.delete_monitors_by_brand(brand_key)
    
    # 2. Exclui a marca do banco
    success = brand_service.delete_brand(brand_key)
    if not success:
        raise HTTPException(status_code=404, detail="Marca não encontrada")
    return {"message": f"Marca '{brand_key}' excluída com sucesso (monitores também removidos)."}
