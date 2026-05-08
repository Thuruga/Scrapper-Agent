import asyncio
import sys
import os

# Adiciona o diretório raiz ao path para permitir imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.engines.factory import engine_factory

async def verify():
    print("=== Iniciando Verificação da Abstração de Engine ===")
    
    brand_key = "aramis"
    print(f"\n1. Testando Engine para '{brand_key}':")
    try:
        engine = engine_factory.get_engine(brand_key)
        print(f"   [OK] Engine carregada: {engine.get_engine_name()}")
        
        print("2. Testando get_catalog():")
        catalog = await engine.get_catalog()
        print(f"   [OK] Catálogo retornado com {len(catalog)} grupos.")
        
        print("3. Testando search('polo'):")
        search_res = await engine.search("polo", max_results=2)
        print(f"   [OK] Busca retornada para {search_res.brand_name} com {len(search_res.products)} produtos.")
        
        print("4. Testando search_all_brands('polo'):")
        multi_search = await engine_factory.search_all_brands("polo", max_per_brand=1)
        print(f"   [OK] Busca multi-marca retornada para {len(multi_search)} marcas.")
        
    except Exception as e:
        print(f"   [FAIL] Erro durante a verificação: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify())
