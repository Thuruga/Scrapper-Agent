from fastapi import APIRouter, HTTPException
from typing import List
import aiohttp
from core.models import DynamicBrand, DynamicBrandCreate, CategoryMapping
from services.brand_service import brand_service
from services.engines.factory import engine_factory
from core.session_manager import SessionManager

router = APIRouter(tags=["Brands"])

async def detect_engine(domain: str) -> str:
    """Tenta descobrir automaticamente a plataforma (motor) do domínio."""
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
                    return "shopify"
    except Exception:
        pass

    # 2. Tenta VTEX via API padrão
    try:
        async with session.get(f"{base_url}/api/catalog_system/pub/category/tree/1", timeout=aiohttp.ClientTimeout(total=5), headers=headers) as resp:
            if resp.status == 200:
                return "vtex"
    except Exception:
        pass
        
    # 3. Fallback: Analisa o HTML da home page
    try:
        async with session.get(base_url, timeout=aiohttp.ClientTimeout(total=5), headers=headers) as resp:
            html = await resp.text()
            html_lower = html.lower()
            if "vtexassets.com" in html_lower or "vtexcommercestable.com" in html_lower or "vtex" in html_lower:
                return "vtex"
            if "cdn.shopify.com" in html_lower or "window.shopify" in html_lower:
                return "shopify"
    except Exception:
        pass

    # Se falhar tudo, assume VTEX
    return "vtex"


@router.post("/brands/", response_model=DynamicBrand)
async def create_brand(brand_data: DynamicBrandCreate):
    """Cadastra ou atualiza uma nova marca no sistema."""
    try:
        if brand_data.engine == "auto":
            # Realiza a deteccao automatica
            brand_data.engine = await detect_engine(brand_data.domain)
            
        return brand_service.add_brand(brand_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/brands/", response_model=List[DynamicBrand])
async def list_brands():
    """Lista todas as marcas cadastradas."""
    return brand_service.list_brands()


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
