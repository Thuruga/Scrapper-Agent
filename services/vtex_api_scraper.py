import asyncio
import aiohttp
from typing import Optional, List, Dict
from urllib.parse import urlparse

from core.models import RawProductBronze
from services.review_service import get_single_review

class VtexApiClient:
    """
    Cliente robusto para integração direta com as APIs da VTEX (Intelligent Search & Catalog System).
    Substitui a necessidade de usar Playwright, garantindo altíssima performance e estabilidade.
    """
    def __init__(self, brand_name: str, session: Optional[aiohttp.ClientSession] = None):
        self.brand_name = brand_name
        self.session = session
        self._owns_session = session is None
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    async def __aenter__(self):
        if self._owns_session and self.session is None:
            # Limite de conexões simultâneas para não causar banimento
            connector = aiohttp.TCPConnector(limit=20)
            self.session = aiohttp.ClientSession(connector=connector, headers=self.headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._owns_session and self.session:
            await self.session.close()

    def _transform_url_to_api(self, url: str) -> str:
        """Converte uma URL de produto frontend para a API Catalog System."""
        url = url.strip()
        if "/api/catalog_system/" in url:
            return url
        parsed = urlparse(url)
        dominio = f"{parsed.scheme}://{parsed.netloc}"
        slug = parsed.path.strip("/").split("/")[-1]
        if slug == "p":
            slug = parsed.path.strip("/").split("/")[-2]
        return f"{dominio}/api/catalog_system/pub/products/search/{slug}/p"

    def _extract_colors(self, produto: dict) -> List[str]:
        """Varre as variações e especificações em busca das cores na API Catalog System."""
        cores_encontradas = set()
        nomes_chaves_cor = ["Cor", "Color", "Cor Real", "Cores"]

        for item in produto.get("items", []):
            variations = item.get("variations", [])
            for var_name in variations:
                if isinstance(var_name, str) and var_name in nomes_chaves_cor:
                    valores = item.get(var_name, [])
                    for valor in valores:
                        cores_encontradas.add(str(valor).strip().upper())

        if not cores_encontradas:
            all_specs = produto.get("allSpecifications", [])
            for spec_name in all_specs:
                if spec_name in nomes_chaves_cor:
                    valores = produto.get(spec_name, [])
                    for valor in valores:
                        cores_encontradas.add(str(valor).strip().upper())

        return list(cores_encontradas)

    async def _get_color_family(self, domain: str, product_id: str) -> List[str]:
        """Chama a API de Cross-Selling da VTEX para achar as outras cores do mesmo modelo."""
        if not self.session:
            return []
            
        cores_da_familia = set()
        url_similares = f"https://{domain}/api/catalog_system/pub/products/crossselling/similars/{product_id}"
        
        try:
            async with self.session.get(url_similares, timeout=5) as res:
                if res.status in (200, 206):
                    similares = await res.json()
                    for prod in similares:
                        for cor in self._extract_colors(prod):
                            cores_da_familia.add(cor)
        except Exception:
            pass # Silencioso para fallback gracioso
            
        return list(cores_da_familia)

    def _extract_sizes(self, items: list) -> List[str]:
        """Extrai os tamanhos disponíveis dos SKUs que têm estoque (>0)."""
        tamanhos = []
        for item in items:
            tem_estoque = False
            for seller in item.get("sellers", []):
                # Apenas verifica se é > 0. A quantidade exata é irrelevante e evitada.
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

    async def parse_product_dict(self, p: dict, product_url: str, domain: str) -> Optional[RawProductBronze]:
        """Faz o parse estrutural de um produto (dict) retornando o modelo Camada Bronze."""
        try:
            # Extração de Preços (usa a primeira variação com estoque)
            price_full = 0.0
            price_discount = None
            has_availability = False
            
            for item in p.get("items", []):
                for seller in item.get("sellers", []):
                    offer = seller.get("commertialOffer", {})
                    if offer.get("AvailableQuantity", 0) > 0:
                        has_availability = True
                        if price_full == 0.0:
                            p_list = offer.get("ListPrice")
                            p_sale = offer.get("Price")
                            if p_sale:
                                price_full = p_sale
                                if p_list and p_list > p_sale:
                                    price_discount = p_list - p_sale
                            break
                if price_full > 0.0:
                    break

            # Caso nenhum item tenha estoque, tenta pegar preço do primeiro sku
            if price_full == 0.0 and p.get("items"):
                try:
                    offer = p["items"][0]["sellers"][0]["commertialOffer"]
                    price_full = offer.get("Price", 0.0)
                except (IndexError, KeyError):
                    pass

            # Extração de Especificações
            specs_dict = {}
            for k in p.get("allSpecifications", []):
                v = p.get(k, [])
                specs_dict[k] = v[0] if isinstance(v, list) and v else str(v)
            
            # Extração de Cores e Família
            cor_atual = self._extract_colors(p)
            product_id = str(p.get("productId", ""))
            cores_irmas = await self._get_color_family(domain, product_id)
            todas_as_cores = list(set(cor_atual + cores_irmas))
            
            # Avaliações (Integrado com o serviço existente)
            brand_key = self.brand_name.lower().split()[0]
            rating, count = await get_single_review(brand_key, product_id)
            
            # Categoria
            cat_array = p.get("categories", [])
            category, sub_category = None, None
            if cat_array:
                parts = [pt for pt in cat_array[0].split("/") if pt]
                if len(parts) >= 1:
                    category = parts[0]
                if len(parts) >= 2:
                    sub_category = parts[1]
            
            composition = specs_dict.get("Composição") or specs_dict.get("Material")

            return RawProductBronze(
                url=product_url,
                brand=self.brand_name,
                raw_title=p.get("productName", ""),
                raw_description=p.get("description", "Sem descrição"),
                price_full=price_full,
                price_discount=price_discount,
                stock_availability=has_availability,
                category=category,
                sub_category=sub_category,
                composition=composition,
                available_colors=todas_as_cores,
                available_sizes=self._extract_sizes(p.get("items", [])),
                rating=rating,
                review_count=count,
                specifications=specs_dict
            )
        except Exception as e:
            print(f"Erro no parse_product_dict para {product_url}: {e}")
            return None

    async def get_product_by_url(self, product_url: str) -> Optional[RawProductBronze]:
        """Extrai todos os dados estruturados de um produto VTEX usando apenas chamadas de API."""
        if not self.session:
            raise RuntimeError("VtexApiClient session not initialized. Use 'async with VtexApiClient(...) as client:'")
            
        api_url = self._transform_url_to_api(product_url)
        parsed_url = urlparse(product_url)
        domain = parsed_url.netloc
        
        try:
            async with self.session.get(api_url, timeout=10) as response:
                if response.status not in (200, 206):
                    return None
                    
                json_data = await response.json()
                if not json_data or not isinstance(json_data, list):
                    return None
                    
                p = json_data[0]
                return await self.parse_product_dict(p, product_url, domain)
                
        except Exception as e:
            print(f"Erro em VtexApiClient para {product_url}: {e}")
            return None

    async def scrape_category_paged(
        self,
        category_url: str,
        log_callback=None,
        cancel_event=None,
        chunk_size=50
    ) -> List[RawProductBronze]:
        """
        Varre a categoria paginando o endpoint Search API.
        Processa todos os produtos de cada bloco de forma assíncrona, extraindo
        preços, estoques e avaliações/cores. Retorna a lista de produtos processados.
        """
        if not self.session:
            raise RuntimeError("VtexApiClient session not initialized. Use 'async with VtexApiClient(...) as client:'")
            
        def log(msg):
            if log_callback:
                if isinstance(msg, dict):
                    log_callback(msg)
                else:
                    log_callback({"type": "info", "message": msg})
            else:
                print(msg)

        parsed = urlparse(category_url)
        domain = parsed.netloc
        path = parsed.path.strip("/")
        
        # A VTEX aceita mapeamento de diretório diretamente na busca
        api_base_url = f"https://{domain}/api/catalog_system/pub/products/search/{path}"

        produtos_extraidos = []
        pagina = 0

        log(f"🚀 Iniciando extração API-First paginada: {category_url}")
        
        # Pequena pausa para garantir que o frontend (WebSocket) conecte antes de enviarmos os logs
        await asyncio.sleep(1.5)

        total_produtos = None
        stats_emitido = False

        while True:
            if cancel_event and cancel_event.is_set():
                log("🛑 Varredura interrompida pelo usuário.")
                break

            _from = pagina * chunk_size
            _to = _from + chunk_size - 1
            url = f"{api_base_url}?_from={_from}&_to={_to}"
            
            log(f"📥 Buscando página {pagina + 1} (itens de {_from} a {_to})...")
            
            try:
                async with self.session.get(url, timeout=15) as response:
                    if response.status not in (200, 206):
                        log(f"❌ API retornou HTTP {response.status}")
                        break
                        
                    # Puxa o total de produtos pelo header na primeira requisição
                    if not stats_emitido and "resources" in response.headers:
                        res_header = response.headers.get("resources", "")
                        if "/" in res_header:
                            try:
                                total_produtos = int(res_header.split("/")[-1])
                                log({
                                    "type": "stats",
                                    "total_links": total_produtos,
                                    "message": f"Total de produtos na categoria: {total_produtos}"
                                })
                                stats_emitido = True
                            except ValueError:
                                pass
                        
                    raw_products = await response.json()
                    
                    if not raw_products or not isinstance(raw_products, list):
                        log("✅ Fim da categoria alcançado!")
                        break

                    async def build_product(p):
                        link = p.get("link")
                        if not link:
                            link_text = p.get("linkText")
                            if link_text:
                                link = f"https://{domain}/{link_text}/p"
                        
                        # Garante link absoluto
                        if link and not link.startswith("http"):
                            link = f"https://{domain}{link}"
                            
                        if not link:
                            return None
                            
                        prod = await self.parse_product_dict(p, link, domain)
                        if prod:
                            log({"type": "success", "message": f"Sucesso: {prod.raw_title}"})
                        return prod

                    # Executa as chamadas secundárias (ex: familia de cores) concorrentemente para todos do chunk
                    tarefas = [build_product(p) for p in raw_products]
                    resultados_chunk = await asyncio.gather(*tarefas)
                    
                    # Filtra None
                    valid_produtos = [r for r in resultados_chunk if r is not None]
                    produtos_extraidos.extend(valid_produtos)

                    if not raw_products:
                        break

            except Exception as e:
                log(f"❌ Falha ao varrer página {pagina + 1}: {e}")
                break

            pagina += 1
            await asyncio.sleep(0.5) # Respeito ao rate limit VTEX
            
        log(f"🎉 Extração concluída! {len(produtos_extraidos)} produtos capturados.")
        return produtos_extraidos

