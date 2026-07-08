import sys
import os
import asyncio
import json

# Adjust python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.brand_service import brand_service
from services.engines.factory import engine_factory

async def main():
    print("Iniciando extração de categorias para todas as marcas...")
    
    results = {}
    
    brands = brand_service.list_brands()
    for brand in brands:
        if not brand.is_active:
            print(f"[{brand.brand_key}] Ignorando marca inativa.")
            continue
            
        print(f"Extraindo categorias para: {brand.brand_name} ({brand.brand_key}) - Engine: {brand.engine}")
        
        try:
            engine = engine_factory.get_engine(brand.brand_key)
            categories = await engine.discover_categories()
            
            results[brand.brand_key] = {
                "brand_name": brand.brand_name,
                "engine": brand.engine,
                "domain": brand.domain,
                "categories": categories
            }
            print(f"  -> Encontrados {len(categories)} grupos de categorias.")
        except Exception as e:
            print(f"  -> Erro ao extrair: {e}")
            results[brand.brand_key] = {
                "brand_name": brand.brand_name,
                "engine": brand.engine,
                "domain": brand.domain,
                "error": str(e),
                "categories": []
            }
            
    with open("all_categories_extracted.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print(f"\nExtração concluída. Salvo em all_categories_extracted.json")

if __name__ == "__main__":
    asyncio.run(main())
