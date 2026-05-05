import os
import sys
import json

# Adiciona o diretório atual ao sys.path para importar os módulos locais
sys.path.append(os.getcwd())

from config import BRAND_REGISTRY
from services.brand_service import brand_service
from core.models import DynamicBrandCreate

def migrate_brands():
    print("[INFO] Iniciando migração de marcas hardcoded para JSON...")
    
    for key, info in BRAND_REGISTRY.items():
        try:
            brand_data = DynamicBrandCreate(
                brand_key=key,
                brand_name=info["name"],
                domain=info["domain"]
            )
            brand_service.add_brand(brand_data)
            print(f"[OK] Marca '{info['name']}' migrada com sucesso.")
        except Exception as e:
            print(f"[ERROR] Falha ao migrar marca '{key}': {e}")
            
    print("[DONE] Migração concluída!")

if __name__ == "__main__":
    migrate_brands()
