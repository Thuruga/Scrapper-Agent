import asyncio
import aiohttp
import json
from typing import Optional, Tuple, List

# =====================================================================
# 1. O "De/Para" Inteligente
# =====================================================================
CATEGORY_MAPPING = {
    "aramis": {
        "domain": "www.aramis.com.br",
        "categories": {
            "polos": "C:/480/523/",
            "camisas": "C:/480/507/"
        }
    },
    "reserva": {
        "domain": "www.usereserva.com",
        "categories": {
            "polos": "C:/1/101/10113/",
            "camisas": "C:/1/101/10103/"
        }
    }
}

# =====================================================================
# 2. Funções de Extração Limpa
# =====================================================================
def extrair_precos(items: list) -> Tuple[Optional[float], Optional[float]]:
    best_full = None
    best_discount = None
    for item in items:
        for seller in item.get("sellers", []):
            offer = seller.get("commertialOffer", {})
            list_price = offer.get("ListPrice") or offer.get("Price")
            sale_price = offer.get("Price")
            
            if not sale_price or not offer.get("IsAvailable", False):
                continue

            if best_full is None or list_price < best_full:
                best_full = float(list_price) if list_price else None
                best_discount = float(sale_price) if sale_price < list_price else None
    return best_full, best_discount

def calcular_estoque_total(items: list) -> int:
    estoque_total = 0
    for item in items:
        for seller in item.get("sellers", []):
            estoque_total += seller.get("commertialOffer", {}).get("AvailableQuantity", 0)
    return estoque_total

def extrair_tamanhos(items: list) -> List[str]:
    tamanhos = []
    for item in items:
        tem_estoque = False
        for seller in item.get("sellers", []):
            if seller.get("commertialOffer", {}).get("AvailableQuantity", 0) > 0:
                tem_estoque = True
                break
                
        if tem_estoque:
            nome_tamanho = item.get("name", "")
            if " - " in nome_tamanho:
                nome_tamanho = nome_tamanho.split(" - ")[-1].strip()
                
            if nome_tamanho and nome_tamanho not in tamanhos:
                tamanhos.append(nome_tamanho)
    return tamanhos

def extrair_cores(produto: dict) -> List[str]:
    """Varre as variações e especificações em busca das cores na API Catalog System."""
    cores_encontradas = set()
    nomes_chaves_cor = ["Cor", "Color", "Cor Real", "Cores"]

    # Tentativa 1: Procurar nas Variações dos SKUs (nível de Item)
    for item in produto.get("items", []):
        variations = item.get("variations", [])
        for var_name in variations:
            if isinstance(var_name, str) and var_name in nomes_chaves_cor:
                valores = item.get(var_name, [])
                for valor in valores:
                    cores_encontradas.add(str(valor).strip().upper())

    # Tentativa 2: Fallback para as Especificações Gerais (nível de Produto)
    if not cores_encontradas:
        all_specs = produto.get("allSpecifications", [])
        for spec_name in all_specs:
            if spec_name in nomes_chaves_cor:
                valores = produto.get(spec_name, [])
                for valor in valores:
                    cores_encontradas.add(str(valor).strip().upper())

    return list(cores_encontradas)

async def buscar_familia_de_cores_api(session: aiohttp.ClientSession, dominio: str, product_id: str) -> List[str]:
    """Chama a API de Cross-Selling da VTEX para achar as outras cores do mesmo modelo."""
    cores_da_familia = set()
    url_similares = f"https://{dominio}/api/catalog_system/pub/products/crossselling/similars/{product_id}"
    
    try:
        async with session.get(url_similares) as res:
            if res.status in (200, 206):
                similares = await res.json()
                for prod in similares:
                    for cor in extrair_cores(prod):
                        cores_da_familia.add(cor)
    except Exception as e:
        print(f"⚠️ Erro ao buscar similares para {product_id}: {e}")
        
    return list(cores_da_familia)

# =====================================================================
# 3. O Motor de Paginação e Orquestração Assíncrona
# =====================================================================
async def varrer_categoria_api(marca: str, categoria: str, chunk_size: int = 50):
    config = CATEGORY_MAPPING.get(marca.lower())
    if not config:
        print(f"Marca {marca} não configurada.")
        return

    domain = config["domain"]
    fq_path = config["categories"].get(categoria.lower())
    
    if not fq_path:
        print(f"Categoria {categoria} não configurada para {marca}.")
        return

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    produtos_extraidos = []
    pagina = 0

    print(f"🚀 Iniciando extração API-First: {marca.upper()} -> {categoria.upper()}")
    print("-" * 50)

    # Limite de conexões simultâneas para não derrubar a API da VTEX (ou ser bloqueado)
    connector = aiohttp.TCPConnector(limit=20)
    
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        while True:
            _from = pagina * chunk_size
            _to = _from + chunk_size - 1

            url = (
                f"https://{domain}/api/catalog_system/pub/products/search"
                f"?fq={fq_path}&_from={_from}&_to={_to}"
            )

            print(f"📥 Buscando página {pagina + 1} (itens de {_from} a {_to})...")
            
            async with session.get(url) as response:
                if response.status not in (200, 206):
                    print(f"❌ Erro na API: HTTP {response.status}")
                    break

                raw_products = await response.json()

                if not raw_products:
                    print("✅ Fim da categoria alcançado!")
                    break

                # Função interna para processar um único produto de forma assíncrona
                async def processar_produto(p):
                    items = p.get("items", [])
                    price_full, price_discount = extrair_precos(items)
                    estoque = calcular_estoque_total(items)
                    
                    if estoque >= 10000:
                        estoque = 999 

                    cor_atual = extrair_cores(p)
                    product_id = str(p.get("productId"))
                    
                    # Busca cores irmãs na API de similares
                    cores_irmas = await buscar_familia_de_cores_api(session, domain, product_id)
                    todas_as_cores = list(set(cor_atual + cores_irmas))

                    return {
                        "id": product_id,
                        "nome": p.get("productName"),
                        "preco_cheio": price_full,
                        "preco_desconto": price_discount,
                        "estoque": estoque,
                        "tamanhos_disponiveis": extrair_tamanhos(items),
                        "cores_disponiveis": todas_as_cores,
                        "url": p.get("link")
                    }

                # Dispara o processamento para todos os produtos deste "chunk" simultaneamente
                tarefas = [processar_produto(p) for p in raw_products]
                produtos_limpos = await asyncio.gather(*tarefas)
                
                produtos_extraidos.extend(produtos_limpos)

            pagina += 1
            # Pausa de segurança para respeitar Rate Limits
            await asyncio.sleep(0.5) 

    print("-" * 50)
    print(f"🎉 Extração concluída! {len(produtos_extraidos)} produtos capturados estruturalmente.")
    
    if produtos_extraidos:
        print("\n🔎 Amostra do primeiro produto estruturado com a família de cores:")
        print(json.dumps(produtos_extraidos[0], indent=2, ensure_ascii=False))

# =====================================================================
# 4. Execução Principal
# =====================================================================
if __name__ == "__main__":
    asyncio.run(varrer_categoria_api(marca="aramis", categoria="polos"))