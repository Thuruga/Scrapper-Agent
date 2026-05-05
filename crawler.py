import asyncio
import aiohttp
import threading
from typing import Optional, Callable
from urllib.parse import urlparse

async def varrer_categoria_vtex(
    url_categoria: str,
    log_callback: Optional[Callable] = None,
    cancel_event: Optional[threading.Event] = None,
) -> list[str]:
    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    def is_cancelled() -> bool:
        return cancel_event is not None and cancel_event.is_set()

    parsed = urlparse(url_categoria)
    domain = parsed.netloc
    path = parsed.path.strip("/")
    
    # A VTEX aceita mapeamento de diretório diretamente na busca
    api_base_url = f"https://{domain}/api/catalog_system/pub/products/search/{path}"
    
    links_produtos = set()
    pagina = 0
    chunk_size = 50
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
        "Accept": "application/json"
    }

    log(f"[SPIDER] Entrando na categoria via API-First: {url_categoria}")

    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        while True:
            if is_cancelled():
                log("[SPIDER] Varredura interrompida pelo usuário.")
                break

            _from = pagina * chunk_size
            _to = _from + chunk_size - 1
            url = f"{api_base_url}?_from={_from}&_to={_to}"
            
            log(f"Buscando página {pagina + 1} (itens de {_from} a {_to})...")
            
            try:
                async with session.get(url, timeout=15) as response:
                    if response.status not in (200, 206):
                        log(f"[SPIDER ERRO] API retornou HTTP {response.status}")
                        break
                        
                    raw_products = await response.json()
                    
                    if not raw_products or not isinstance(raw_products, list):
                        log("✅ Fim da categoria alcançado!")
                        break
                        
                    novos_links = 0
                    for p in raw_products:
                        link = p.get("link")
                        if link:
                            # Trata link para garantir que seja absoluto
                            if link.startswith("http"):
                                produto_url = link
                            else:
                                produto_url = f"https://{domain}{link}"
                                
                            links_produtos.add(produto_url)
                            novos_links += 1
                        else:
                            link_text = p.get("linkText")
                            if link_text:
                                produto_url = f"https://{domain}/{link_text}/p"
                                links_produtos.add(produto_url)
                                novos_links += 1
                            
                    if novos_links == 0:
                        break
                        
            except Exception as e:
                log(f"[SPIDER ERRO] Falha ao varrer página {pagina + 1}: {e}")
                break

            pagina += 1
            await asyncio.sleep(0.5) # Respeito ao rate limit

    log(f"[SPIDER SUCESSO] {len(links_produtos)} links únicos encontrados na categoria!")
    return list(links_produtos)


# --- Teste direto ---
async def main():
    url_categoria = "https://www.aramis.com.br/roupas/polos"
    links = await varrer_categoria_vtex(url_categoria)
    print("\n--- Amostra dos Links Encontrados ---")
    for link in links[:10]:
        print(link)


if __name__ == "__main__":
    asyncio.run(main())
