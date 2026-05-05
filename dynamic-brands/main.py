from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware  # <--- Importe aqui
from typing import List

from models import DynamicBrand, DynamicBrandCreate, CategoryMapping
from service import brand_service
from vtex_client import fetch_vtex_categories

app = FastAPI(title="Dynamic Brands PoC")

# 🚀 Liberando o CORS para o nosso Frontend local funcionar
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/brands", response_model=DynamicBrand)
async def create_brand(brand: DynamicBrandCreate):
    """Cadastra uma nova marca (apenas o domínio e nome)."""
    try:
        return brand_service.add_brand(brand)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/brands", response_model=List[DynamicBrand])
async def get_all_brands():
    """Lista todas as marcas cadastradas e seus mapeamentos."""
    return brand_service.list_brands()


@app.get("/brands/{brand_key}/vtex-tree")
async def preview_vtex_tree(brand_key: str, depth: int = 3):  # <--- Adicionado aqui
    """
    Busca a árvore real da VTEX para o domínio cadastrado.
    Pode passar ?depth=2 ou ?depth=3 na URL para controlar o tamanho do retorno.
    """
    brand_key = brand_key.lower()
    if brand_key not in brand_service.brands:
        raise HTTPException(status_code=404, detail="Marca não encontrada.")

    domain = brand_service.brands[brand_key].domain

    # Repassa a profundidade para o cliente
    tree = await fetch_vtex_categories(domain, depth)
    if not tree:
        raise HTTPException(
            status_code=502, detail="Falha ao comunicar com a VTEX ou loja inválida."
        )

    return {"brand": brand_key, "domain": domain, "depth": depth, "vtex_tree": tree}


@app.put("/brands/{brand_key}/mappings", response_model=DynamicBrand)
async def set_category_mappings(brand_key: str, mappings: List[CategoryMapping]):
    """
    Salva o 'De/Para' gerado pelo usuário.
    Ex: {"canonical_slug": "polos", "vtex_fq_path": "C:/1/2/", "label": "Polos e Camisas"}
    """
    try:
        return brand_service.update_mappings(brand_key, mappings)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    # Inicia o servidor isolado na porta 8001 para não conflitar com o seu Scrapper principal
    uvicorn.run("main:app", host="localhost", port=8001, reload=True)
