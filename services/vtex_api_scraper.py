import asyncio
import aiohttp
import logging
import random
import re
import json
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
from curl_cffi.requests import AsyncSession

from config import settings
from core.models import RawProductBronze
from core.vtex_schemas import VtexProduct, VtexItem, VtexSeller
from services.review_service import get_single_review

# Configuração de Logs
logger = logging.getLogger("VtexApiClient")


class IdentityManager:
    """Gerencia a identidade do scraper (User-Agent e Proxy) para evitar bloqueios."""

    @staticmethod
    def get_random_user_agent() -> str:
        return random.choice(settings.USER_AGENTS)

    @staticmethod
    def get_random_proxy() -> Optional[str]:
        if not settings.ENABLE_PROXY or not settings.PROXY_LIST:
            return None
        return random.choice(settings.PROXY_LIST)


class VtexApiClient:
    """
    Cliente robuso para integração direta com as APIs da VTEX (Intelligent Search & Catalog System).
    Implementa rotação de identidade, retries exponenciais e validação rigorosa com Pydantic.
    """

    def __init__(self, brand_name: str, session: Optional[aiohttp.ClientSession] = None):
        self.brand_name = brand_name
        self.session = session
        self._owns_session = session is None
        self.semaphore = asyncio.Semaphore(15)

    @staticmethod
    async def fetch_categories(domain: str, depth: int = 3) -> List[Dict[str, Any]]:
        """
        Motor de extração com Auto-Discovery do nome da conta VTEX.
        Perfeito para contornar setups Headless/FastStore sem depender de input manual.
        Utiliza curl_cffi para emular um browser real e evitar bloqueios iniciais.
        """
        domain = domain.replace("https://", "").replace("http://", "").strip("/")
        url_principal = f"https://{domain}/api/catalog_system/pub/category/tree/{depth}"

        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        try:
            async with AsyncSession(impersonate="chrome", timeout=15) as session:
                logger.info(f"📥 Tentando domínio principal: {url_principal}")
                response = await session.get(url_principal, headers=headers)

                conteudo_bruto = response.text

                if response.status_code == 200:
                    try:
                        return response.json()
                    except json.JSONDecodeError:
                        logger.warning("⚠️ O frontend devorou a requisição (Retornou HTML).")
                else:
                    logger.warning(f"⚠️ Status HTTP {response.status_code} no domínio principal.")

                # ─── MÓDULO DE AUTO-DISCOVERY (O "Pulo do Gato") ───
                logger.info("🔍 Inspecionando o HTML para descobrir o ID real da conta VTEX...")

                # Caça qualquer URL da CDN da VTEX dentro do HTML para extrair o nome verdadeiro da conta
                vtexassets_match = re.search(
                    r"https:\/\/([^.]+)\.vtexassets\.com", conteudo_bruto
                )

                if vtexassets_match:
                    account_name = vtexassets_match.group(1)
                    logger.info(f"🎯 Bingo! Conta VTEX descoberta no código-fonte: '{account_name}'")
                else:
                    # Fallback de segurança se não encontrar a CDN no HTML
                    account_match = re.search(r"^(?:www\.)?([^.]+)", domain)
                    account_name = (
                        account_match.group(1) if account_match else domain.split(".")[0]
                    )
                    logger.info(f"⚠️ CDN não encontrada. A inferir a conta pelo domínio: '{account_name}'")

                url_fallback = f"https://{account_name}.vtexcommercestable.com.br/api/catalog_system/pub/category/tree/{depth}"

                # ─── TENTATIVA 2: Fallback Certeiro ───
                logger.info(f"🔄 Acionando Fallback Oculto: {url_fallback}")
                response_fb = await session.get(url_fallback, headers=headers)

                if response_fb.status_code == 200:
                    try:
                        dados = response_fb.json()
                        logger.info("✅ Sucesso! Conectado diretamente ao Backend da VTEX.")
                        return dados
                    except json.JSONDecodeError:
                        logger.error("❌ Falha: O Fallback oculto também retornou HTML.")
                        return []
                else:
                    logger.error(f"❌ O Fallback falhou com Status HTTP {response_fb.status_code}")
                    return []

        except Exception as e:
            logger.error(f"❌ Erro crítico de rede na descoberta de categorias: {e}")
            return []

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "User-Agent": IdentityManager.get_random_user_agent(),
            "X-Requested-With": "XMLHttpRequest",
            "Cache-Control": "no-cache",
        }


    async def __aenter__(self):
        if self._owns_session and self.session is None:
            # Limite de conexões simultâneas para não causar banimento
            connector = aiohttp.TCPConnector(limit=25, ttl_dns_cache=300)
            timeout = aiohttp.ClientTimeout(total=settings.REQUEST_TIMEOUT_SECONDS)
            self.session = aiohttp.ClientSession(
                connector=connector, 
                headers=self._get_headers(),
                timeout=timeout
            )
        return self

    async def _request(self, method: str, url: str, **kwargs) -> Optional[aiohttp.ClientResponse]:
        """Realiza requisições com retry, proxy e UA rotativo."""
        if not self.session:
            return None

        proxy = IdentityManager.get_random_proxy()
        # Atualiza headers para cada requisição para rotacionar UA se desejado
        # kwargs.setdefault("headers", self._get_headers())
        
        for attempt in range(settings.MAX_RETRIES):
            try:
                # Rotaciona proxy em cada tentativa de retry se habilitado
                current_proxy = IdentityManager.get_random_proxy() if attempt > 0 else proxy
                
                async with self.session.request(method, url, proxy=current_proxy, **kwargs) as resp:
                    if resp.status in (200, 201, 206):
                        # Forçamos a leitura aqui pois o context manager da response vai fechar
                        # Mas como queremos usar o json() depois, retornaremos a response 
                        # se o chamador souber lidar, ou faremos o parse aqui.
                        # Para facilitar, retornaremos a response e o chamador deve usar context manager ou read.
                        # No entanto, aiohttp não permite usar a response fora do 'async with'.
                        # Refatoraremos para que o chamador passe um callback ou processe dentro.
                        return resp
                    
                    if resp.status == 429: # Rate Limit
                        wait = (attempt + 1) * 5
                        logger.warning(f"Rate limit (429) em {url}. Aguardando {wait}s...")
                        await asyncio.sleep(wait)
                        continue
                        
                    if resp.status >= 500:
                        logger.warning(f"Erro de servidor ({resp.status}) em {url}. Retry {attempt+1}/{settings.MAX_RETRIES}")
                        await asyncio.sleep(2 ** attempt)
                        continue
                    
                    return resp # Retorna mesmo se for 404, etc (chamador trata)

            except Exception as e:
                logger.error(f"Erro na requisição a {url} (Tentativa {attempt+1}): {e}")
                await asyncio.sleep(2 ** attempt)
        
        return None

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._owns_session and self.session:
            await self.session.close()

    async def _request_json(self, url: str, **kwargs) -> Optional[Any]:
        """Realiza requisições GET e retorna o JSON validado."""
        if not self.session:
            return None

        proxy = IdentityManager.get_random_proxy()
        
        for attempt in range(settings.MAX_RETRIES):
            try:
                current_proxy = IdentityManager.get_random_proxy() if attempt > 0 else proxy
                
                async with self.session.get(url, proxy=current_proxy, **kwargs) as resp:
                    if resp.status in (200, 206):
                        return await resp.json()
                    
                    if resp.status == 429:
                        wait = (attempt + 1) * 5
                        logger.warning(f"Rate limit (429) em {url}. Aguardando {wait}s...")
                        await asyncio.sleep(wait)
                        continue
                        
                    if resp.status >= 500:
                        logger.warning(f"Erro de servidor ({resp.status}) em {url}. Retry {attempt+1}/{settings.MAX_RETRIES}")
                        await asyncio.sleep(2 ** attempt)
                        continue
                    
                    logger.debug(f"HTTP {resp.status} em {url}")
                    return None

            except Exception as e:
                logger.error(f"Erro na requisição a {url} (Tentativa {attempt+1}): {e}")
                await asyncio.sleep(2 ** attempt)
        
        return None
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

    def _extract_colors(self, p: VtexProduct) -> List[str]:
        """Varre as variações e especificações em busca das cores na API Catalog System."""
        cores_encontradas = set()
        nomes_chaves_cor = ["Cor", "Color", "Cor Real", "Cores"]

        # Simplificação profissional: focar em allSpecifications que é mais confiável
        for spec_name in p.allSpecifications:
            if spec_name in nomes_chaves_cor:
                valores = getattr(p, spec_name, [])
                if isinstance(valores, list):
                    for valor in valores:
                        cores_encontradas.add(str(valor).strip().upper())

        return list(cores_encontradas)

    async def _get_color_family(self, domain: str, product_id: str) -> List[str]:
        """Chama a API de Cross-Selling da VTEX para achar as outras cores do mesmo modelo."""
        cores_da_familia = set()
        url_similares = f"https://{domain}/api/catalog_system/pub/products/crossselling/similars/{product_id}"
        
        json_data = await self._request_json(url_similares, timeout=5)
        if json_data and isinstance(json_data, list):
            for prod_data in json_data:
                try:
                    # Validação parcial via Pydantic para extração segura
                    vtex_prod = VtexProduct.model_validate(prod_data)
                    for cor in self._extract_colors(vtex_prod):
                        cores_da_familia.add(cor)
                except Exception:
                    continue
            
        return list(cores_da_familia)

    def _extract_sizes(self, items: List[VtexItem]) -> List[str]:
        """Extrai os tamanhos disponíveis dos SKUs que têm estoque (>0)."""
        tamanhos = []
        for item in items:
            tem_estoque = False
            for seller in item.sellers:
                # Apenas verifica se é > 0. A quantidade exata é irrelevante e evitada.
                if seller.commertialOffer.AvailableQuantity > 0:
                    tem_estoque = True
                    break
                    
            if tem_estoque:
                nome_tamanho = item.name
                if " - " in nome_tamanho:
                    nome_tamanho = nome_tamanho.split(" - ")[-1].strip()
                if nome_tamanho and nome_tamanho not in tamanhos:
                    tamanhos.append(nome_tamanho)
        return tamanhos

    async def parse_product_dict(self, data: dict, product_url: str, domain: str) -> Optional[RawProductBronze]:
        """Faz o parse estrutural de um produto (dict) retornando o modelo Camada Bronze."""
        try:
            # Validação Rigorosa com Pydantic
            p = VtexProduct.model_validate(data)
            
            # Extração de Preços (usa a primeira variação com estoque)
            price_full = 0.0
            price_discount = None
            has_availability = False
            
            for item in p.items:
                for seller in item.sellers:
                    offer = seller.commertialOffer
                    if offer.AvailableQuantity > 0:
                        has_availability = True
                        if price_full == 0.0:
                            p_list = offer.ListPrice
                            p_sale = offer.Price
                            if p_sale:
                                price_full = p_sale
                                if p_list and p_list > p_sale:
                                    price_discount = p_list - p_sale
                            break
                if price_full > 0.0:
                    break

            # Caso nenhum item tenha estoque, tenta pegar preço do primeiro sku
            if price_full == 0.0 and p.items:
                try:
                    offer = p.items[0].sellers[0].commertialOffer
                    price_full = offer.Price
                except (IndexError, AttributeError):
                    pass

            # Extração de Especificações
            specs_dict = {}
            for k in p.allSpecifications:
                v = getattr(p, k, [])
                specs_dict[k] = v[0] if isinstance(v, list) and v else str(v)
            
            # Extração de Cores e Família
            cor_atual = self._extract_colors(p)
            cores_irmas = await self._get_color_family(domain, p.productId)
            todas_as_cores = list(set(cor_atual + cores_irmas))
            
            # Avaliações (Integrado com o serviço existente)
            brand_key = self.brand_name.lower().split()[0]
            rating, count = await get_single_review(brand_key, p.productId)
            
            # Categoria
            category, sub_category = None, None
            if p.categories:
                # VTEX categories são como "/Masculino/Calças/Jeans/"
                parts = [pt for pt in p.categories[0].split("/") if pt]
                if len(parts) >= 1:
                    category = parts[0]
                if len(parts) >= 2:
                    sub_category = parts[1]
            
            composition = specs_dict.get("Composição") or specs_dict.get("Material")

            # Imagem
            image_url = None
            if p.items:
                images = p.items[0].images
                if images:
                    image_url = images[0].imageUrl

            return RawProductBronze(
                url=product_url,
                brand=self.brand_name,
                raw_title=p.productName,
                raw_description=p.description or "Sem descrição",
                price_full=price_full,
                price_discount=price_discount,
                stock_availability=has_availability,
                category=category,
                sub_category=sub_category,
                composition=composition,
                available_colors=todas_as_cores,
                available_sizes=self._extract_sizes(p.items),
                rating=rating,
                review_count=count,
                specifications=specs_dict,
                image_url=image_url
            )

        except Exception as e:
            logger.error(f"Erro no parse_product_dict para {product_url}: {e}")
            return None

    async def get_product_by_url(self, product_url: str) -> Optional[RawProductBronze]:
        """Extrai todos os dados estruturados de um produto VTEX usando apenas chamadas de API."""
        api_url = self._transform_url_to_api(product_url)
        parsed_url = urlparse(product_url)
        domain = parsed_url.netloc
        
        json_data = await self._request_json(api_url, timeout=10)
        if json_data and isinstance(json_data, list) and len(json_data) > 0:
            return await self.parse_product_dict(json_data[0], product_url, domain)
            
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
                # Usamos _request para ter acesso aos headers (total de produtos)
                async with self.session.get(url, proxy=IdentityManager.get_random_proxy(), timeout=15) as response:
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

                    async def build_product_safely(p):
                        async with self.semaphore:
                            return await build_product(p)

                    # Executa as chamadas secundárias (ex: familia de cores) concorrentemente para todos do chunk
                    tarefas = [build_product_safely(p) for p in raw_products]
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

