import asyncio
import sys
import os

# Adiciona o diretório atual ao sys.path para importar os módulos locais
sys.path.append(os.getcwd())

from services.vtex_api_scraper import VtexApiClient

async def test_discovery():
    domains = [
        "www.aramis.com.br",
        "www.usereserva.com",
    ]
    
    for domain in domains:
        print(f"\n--- Testando Descoberta: {domain} ---")
        categories = await VtexApiClient.fetch_categories(domain, depth=1)
        
        if categories:
            print(f"[OK] Sucesso! Encontradas {len(categories)} categorias principais.")
            for cat in categories[:3]:
                print(f" - {cat.get('name')} (ID: {cat.get('id')})")
        else:
            print(f"[ERROR] Falha ao descobrir categorias para {domain}")

if __name__ == "__main__":
    asyncio.run(test_discovery())
