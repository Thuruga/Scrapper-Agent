import sys
import os
import asyncio
import aiohttp

# Adjust python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.category_mapping import _RAW_CATEGORIES
from services.brand_service import brand_service

async def verify_url(url, session):
    try:
        async with session.get(url, timeout=15) as response:
            return response.status
    except Exception as e:
        return str(e)

async def main():
    print("Iniciando teste de categorias mapeadas nos sites...")
    
    urls_to_test = []
    
    # 1. Hardcoded categories from category_mapping.py
    for raw in _RAW_CATEGORIES:
        cat_slug = raw["slug"]
        for brand_key, info in raw["brands"].items():
            brand_data = brand_service.get_brand(brand_key)
            if not brand_data or not brand_data.is_active:
                continue
            domain = brand_data.domain
            path = info["path"]
            url = f"https://{domain}{path}"
            urls_to_test.append((brand_key, cat_slug, url, "Hardcoded"))
            
    # 2. Dynamic categories from brands.json
    for brand in brand_service.list_brands():
        if not brand.is_active:
            continue
        domain = brand.domain
        for mapping in brand.mappings:
            path = mapping.vtex_fq_path
            
            # Skip if it is not a path but a VTEX FQ rule (starts with C:/ etc)
            if path.startswith("C:/") or path.startswith("B:"):
                print(f"Skipping VTEX FQ query path sem URL direta: {brand.brand_key} -> {path}")
                continue
                
            if not path.startswith("/"):
                path = "/" + path
                
            url = f"https://{domain}{path}"
            urls_to_test.append((brand.brand_key, mapping.canonical_slug, url, "Dynamic"))

    # Remove duplicates
    unique_urls = {}
    for b, c, u, source in urls_to_test:
        key = (b, c, u)
        unique_urls[key] = source
    
    urls_to_test = [(b, c, u, unique_urls[(b, c, u)]) for b, c, u in unique_urls.keys()]
    
    results = []
    
    # Use headers to pretend we are a browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        for brand, cat, url, source in urls_to_test:
            print(f"Testando {brand} - {cat}: {url} ({source})")
            status = await verify_url(url, session)
            results.append((brand, cat, url, status, source))
            print(f"  Resultado: {status}")
            await asyncio.sleep(0.5) # small delay to avoid blocks

    print("\n\n=== RESUMO DAS CATEGORIAS MAPEADAS ===")
    
    failures = []
    successes = []
    
    for brand, cat, url, status, source in results:
        res_str = f"[{brand}] {cat} | {url} | STATUS: {status} | Fonte: {source}"
        print(res_str)
        if isinstance(status, int) and status in (200, 301, 302):
            successes.append(res_str)
        else:
            failures.append(res_str)
            
    print("\n--- RESUMO ESTATISTICO ---")
    print(f"Total testados: {len(results)}")
    print(f"Sucessos (200, 301, 302): {len(successes)}")
    print(f"Falhas (404, timeouts, erros): {len(failures)}")
    
    if failures:
        print("\n--- DETALHE DAS FALHAS ---")
        for f in failures:
            print(f)

if __name__ == "__main__":
    asyncio.run(main())
