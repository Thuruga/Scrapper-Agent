import os
import sys
import json
import logging

# Adiciona o diretório atual ao sys.path para importar os módulos locais
sys.path.append(os.getcwd())

# Configura log para ver a saída do logger.error
logging.basicConfig(level=logging.INFO)

DB_DIR = "data"
DB_FILE = os.path.join(DB_DIR, "brands.json")
BACKUP_FILE = os.path.join(DB_DIR, "brands.json.bak")

def test_corruption():
    print("\n--- Testando Validação de Corrupção ---")
    
    # Faz backup
    if os.path.exists(DB_FILE):
        os.rename(DB_FILE, BACKUP_FILE)
    
    try:
        # 1. Teste: JSON Inválido (Sintaxe)
        print("\nCenário 1: Erro de Sintaxe JSON")
        with open(DB_FILE, "w") as f:
            f.write("{ invalid json: ,,, }")
        
        try:
            from services.brand_service import BrandManagerService
            # Como o serviço é um singleton no módulo, precisamos instanciar um novo para o teste
            service = BrandManagerService()
            print("❌ Falha: O sistema aceitou JSON inválido.")
        except RuntimeError as e:
            print(f"✅ Sucesso: O sistema barrou JSON inválido. Erro: {e}")
            
        # 2. Teste: Schema Inválido (Faltando campos obrigatórios)
        print("\nCenário 2: Erro de Schema (Contrato Pydantic)")
        with open(DB_FILE, "w") as f:
            bad_data = {
                "marca_z": {
                    "brand_key": "marca_z",
                    # brand_name está faltando
                    "domain": "www.z.com"
                }
            }
            json.dump(bad_data, f)
            
        try:
            from services.brand_service import BrandManagerService
            service = BrandManagerService()
            print("❌ Falha: O sistema aceitou Schema inválido.")
        except RuntimeError as e:
            print(f"✅ Sucesso: O sistema barrou Schema inválido. Erro: {e}")

    finally:
        # Restaura backup
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        if os.path.exists(BACKUP_FILE):
            os.rename(BACKUP_FILE, DB_FILE)

if __name__ == "__main__":
    test_corruption()
