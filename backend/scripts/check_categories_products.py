import json
import asyncio
import aiohttp
import os
import sys

async def check_category_url(url, session, domain, sem, delays):
    async with sem:
        # Sleep slightly to avoid rate limit per domain
        await asyncio.sleep(delays.get(domain, 0.5))
        try:
            async with session.get(url, timeout=10) as response:
                if response.status != 200:
                    return False, f"Status {response.status}"
                
                text = await response.text()
                text_lower = text.lower()
                
                # Check for common "empty category" markers
                empty_markers = [
                    "nenhum produto encontrado",
                    "não encontramos nenhum produto",
                    "0 produtos",
                    "nenhum resultado",
                    "sua busca não retornou",
                    "nao encontramos nenhum produto",
                    "nenhum produto correspondente"
                ]
                
                for marker in empty_markers:
                    if marker in text_lower:
                        return False, "Sem produtos (texto de página vazia detectado)"
                
                return True, "Ok"
        except Exception as e:
            return False, f"Erro: {str(e)}"

async def main():
    print("Iniciando verificação de produtos em TODAS as categorias extraídas...")
    print("Isto levará vários minutos para não sermos bloqueados.")
    
    file_path = "/home/zallu/.gemini/antigravity-ide/brain/1ceedcaa-75c1-400c-b276-8a9e895d576c/all_categories_extracted.json"
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    tasks = []
    # Create a semaphore per domain to limit concurrency to 2 requests per brand at a time
    semaphores = {}
    delays = {}
    
    for brand_key, brand_info in data.items():
        domain = brand_info.get("domain")
        if domain not in semaphores:
            semaphores[domain] = asyncio.Semaphore(2)  # Max 2 concurrent reqs per domain
            delays[domain] = 0.5 # 500ms between concurrent kicks
            
    # Headers to pretend to be a browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        for brand_key, brand_info in data.items():
            domain = brand_info.get("domain")
            categories = brand_info.get("categories", [])
            
            if not categories:
                continue
                
            for cat in categories:
                # categories format from discover_categories can be list of dicts with 'name' and 'path', or nested.
                # In the JSON we saw: {"name": "...", "path": "https://..."}
                if "path" in cat:
                    url = cat["path"]
                    task = asyncio.create_task(
                        check_category_url(url, session, domain, semaphores[domain], delays)
                    )
                    tasks.append((brand_key, cat["name"], url, task))

        print(f"Total de categorias a verificar: {len(tasks)}")
        
        # Await all tasks with a progress indicator
        results = []
        completed = 0
        total = len(tasks)
        for brand, name, url, task in tasks:
            has_products, reason = await task
            results.append({
                "brand": brand,
                "category": name,
                "url": url,
                "has_products": has_products,
                "reason": reason
            })
            completed += 1
            if completed % 50 == 0 or completed == total:
                print(f"Progresso: {completed}/{total} concluídos...")
                
    # Save results
    out_path = "/home/zallu/.gemini/antigravity-ide/brain/1ceedcaa-75c1-400c-b276-8a9e895d576c/categories_products_check.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print(f"\nConcluído! Salvo em categories_products_check.json")

    # Resumo
    with_products = sum(1 for r in results if r["has_products"])
    without_products = len(results) - with_products
    print(f"Total com produtos (estimado): {with_products}")
    print(f"Total vazias/erro: {without_products}")

if __name__ == "__main__":
    asyncio.run(main())
