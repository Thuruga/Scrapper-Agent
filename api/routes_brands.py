from fastapi import APIRouter, HTTPException
from typing import List
from core.models import DynamicBrand, DynamicBrandCreate, CategoryMapping
from services.brand_service import brand_service
from services.vtex_api_scraper import VtexApiClient

router = APIRouter(tags=["Brands"])


@router.post("/brands/", response_model=DynamicBrand)
async def create_brand(brand_data: DynamicBrandCreate):
    """Cadastra ou atualiza uma nova marca no sistema."""
    try:
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
    
    categories = await VtexApiClient.fetch_categories(brand.domain)
    if not categories:
        raise HTTPException(
            status_code=400, 
            detail="Não foi possível descobrir as categorias. Verifique o domínio."
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
