import asyncio
import aiohttp
import logging
import random
import re
import json
import urllib.parse
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
from curl_cffi.requests import AsyncSession

from config import settings
from core.models import RawProductBronze, BrandSearchResult, SearchProductResult
from core.vtex_schemas import VtexProduct, VtexItem, VtexSeller
from services.review_service import get_single_review, get_bulk_reviews
from services.brand_service import brand_service
from services.category_resolver import resolve_query_to_vtex_category_path
from core.base_scraper import BaseScraper
from core.identity import IdentityManager

# Configuração de Logs
logger = logging.getLogger("VtexApiClient")


class VtexApiClient(BaseScraper):
    """
    Cliente robusto para integração direta com as APIs da VTEX (Intelligent Search & Catalog System).
    Implementa rotação de identidade, retries exponenciais e validação rigorosa com Pydantic.
    """

    def __init__(self, brand_name: str, session: Optional[aiohttp.ClientSession] = None):
        self.brand_name = brand_name
        self.session = session
        self._owns_session = session is None
        self.semaphore = asyncio.Semaphore(15)
        self.resolved_account = None
        self.use_stable_fallback = False

    @staticmethod
    def _discover_account_from_html(domain: str, html_content: str) -> str:
        """Extrai o nome da conta VTEX de um HTML bruto."""
        # 1. Procura pela CDN
        vtexassets_match = re.search(r"https:\/\/([^.]+)\.vtexassets\.com", html_content)
        if vtexassets_match:
            return vtexassets_match.group(1)
        
        # 2. Fallback pelo domínio
        account_match = re.search(r"^(?:www\.)?([^.]+)", domain)
        return account_match.group(1) if account_match else domain.split(".")[0]

    @staticmethod
    async def fetch_categories(domain: str, depth: int = 3) -> List[Dict[str, Any]]:
        """
        Motor de extração com Auto-Discovery do nome da conta VTEX.
        Perfeito para contornar setups Headless/FastStore sem depender de input manual.
        """
        domain = domain.replace("https://", "").replace("http://", "").strip("/")
        url_principal = f"https://{domain}/api/catalog_system/pub/category/tree/{depth}"

        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        try:
            async with AsyncSession(impersonate="chrome", timeout=15) as session:
                logger.info(f"[FETCH] Tentando domínio principal: {url_principal}")
                response = await session.get(url_principal, headers=headers)

                if response.status_code == 200:
                    try:
                        dados = response.json()
                        if isinstance(dados, list) and len(dados) > 0:
                            return dados
                        logger.warning("[WARNING] Árvore vazia ou inválida no domínio principal.")
                    except (json.JSONDecodeError, Exception):
                        logger.warning("[WARNING] O domínio principal retornou HTML ou JSON inválido.")
                else:
                    logger.warning(f"[WARNING] Status HTTP {response.status_code} no domínio principal.")

                # --- MÓDULO DE AUTO-DISCOVERY ---
                logger.info("[DEBUG] Inspecionando o HTML para descobrir o ID real da conta VTEX...")
                account_name = VtexApiClient._discover_account_from_html(domain, response.text)
                logger.info(f"[MATCH] Conta identificada: '{account_name}'")

                url_fallback = f"https://{account_name}.vtexcommercestable.com.br/api/catalog_system/pub/category/tree/{depth}"

                # --- TENTATIVA 2: Fallback Certeiro ---
                logger.info(f"[RETRY] Acionando Fallback Oculto: {url_fallback}")
                response_fb = await session.get(url_fallback, headers=headers)

                if response_fb.status_code == 200:
                    try:
                        dados = response_fb.json()
                        logger.info("[OK] Sucesso! Conectado diretamente ao Backend da VTEX.")
                        return dados
                    except Exception:
                        logger.error("[ERROR] Falha: O Fallback oculto também retornou dados inválidos.")
                        return []
                else:
                    logger.warning(f"[ERROR] O Fallback falhou com Status HTTP {response_fb.status_code}")

                # --- MÓDULO 3: EXTREME DISCOVERY ---
                # ... (resto do código igual)
                response_home = await session.get(f"https://{domain}/", headers=headers)
                if response_home.status_code == 200:
                    html = response_home.text.lower()
                    # Procura links que pareçam categorias (evita links de sistema, contato, etc)
                    # Busca por padrões como href="/categoria", href="/departamento/categoria"
                    paths = re.findall(r'href="(/[^"]+)"', html)
                    discovered = []
                    seen_paths = set()
                    
                    # Filtros de ruído
                    noise = [".js", ".css", ".png", ".jpg", "login", "carrinho", "checkout", "minha-conta", "institucional", "fale-conosco"]
                    
                    for p in paths:
                        p = p.split("?")[0].split("#")[0].strip("/")
                        if not p or p in seen_paths or any(n in p for n in noise):
                            continue
                        
                        # Categorias costumam ter entre 1 e 3 níveis de path
                        if 1 <= p.count("/") <= 3:
                            name = p.split("/")[-1].replace("-", " ").capitalize()
                            discovered.append({"name": name, "url": f"/{p}"})
                            seen_paths.add(p)
                    
                    if discovered:
                        logger.info(f"[EXTREME] Extreme Discovery encontrou {len(discovered)} links potenciais.")
                        return discovered

                return []

        except Exception as e:
            logger.error(f"[ERROR] Erro crítico na descoberta: {e}")
            return []

    @staticmethod
    async def validate_url(url: str) -> bool:
        """
        Valida se uma URL de categoria é funcional e contém produtos.
        Utiliza curl_cffi para bypass de WAF básico e emulação de browser.
        """
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        try:
            async with AsyncSession(impersonate="chrome", timeout=10) as session:
                logger.info(f"[VALIDATING] Validando URL: {url}")
                resp = await session.get(url, headers=headers, allow_redirects=True)
                
                if resp.status_code != 200:
                    logger.warning(f"[INVALID] URL inválida ({resp.status_code}): {url}")
                    return False
                
                # Heurística: se a página for muito pequena, provavelmente está vazia ou deu erro
                if len(resp.text) < 1000:
                    logger.warning(f"[INVALID] URL com conteúdo insuficiente: {url}")
                    return False

                # Busca por indícios de "vazio"
                content = resp.text.lower()
                empty_markers = ["nenhum produto encontrado", "0 produtos", "não encontramos produtos", "Ops!"]
                if any(marker in content for marker in empty_markers):
                    logger.warning(f"[INVALID] URL parece estar vazia: {url}")
                    return False
                
                logger.info(f"[OK] URL válida: {url}")
                return True
        except Exception as e:
            logger.warning(f"[WARNING] Erro ao validar URL {url}: {e}")
            return False

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
                current_url = self._get_api_url(url)
                current_proxy = IdentityManager.get_proxy()
                
                async with self.session.request(method, current_url, proxy=current_proxy, **kwargs) as resp:
                    if resp.status in (200, 201, 206):
                        # Se for HTML onde deveria ser JSON, aciona fallback
                        if "text/html" in resp.headers.get("Content-Type", "") and "api/" in current_url:
                             if not self.use_stable_fallback:
                                logger.warning(f"[WARNING] Detectado HTML em API. Tentando fallback...")
                                parsed = urlparse(current_url)
                                await self._ensure_account_resolved(parsed.netloc)
                                self.use_stable_fallback = True
                                continue
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

    async def _ensure_account_resolved(self, domain: str):
        """Garante que a conta VTEX foi identificada para uso de fallback."""
        if self.resolved_account:
            return
        
        logger.info(f"[DEBUG] Identificando conta VTEX para {domain}...")
        headers = {"User-Agent": IdentityManager.get_random_user_agent()}
        try:
            # Tenta pegar a home para descobrir a conta
            async with AsyncSession(impersonate="chrome", timeout=10) as session:
                resp = await session.get(f"https://{domain}/", headers=headers)
                if resp.status_code == 200:
                    self.resolved_account = self._discover_account_from_html(domain, resp.text)
                    logger.info(f"[MATCH] Conta resolvida: {self.resolved_account}")
                else:
                    # Fallback básico pelo domínio
                    self.resolved_account = domain.split(".")[0] if "www" not in domain else domain.split(".")[1]
        except Exception as e:
            logger.warning(f"[WARNING] Falha ao resolver conta via HTML: {e}. Usando fallback de domínio.")
            self.resolved_account = domain.split(".")[0] if "www" not in domain else domain.split(".")[1]

    def _get_api_url(self, original_url: str) -> str:
        """Retorna a URL da API, possivelmente usando o domínio estável se habilitado."""
        if not self.use_stable_fallback or not self.resolved_account:
            return original_url
        
        parsed = urlparse(original_url)
        stable_domain = f"{self.resolved_account}.vtexcommercestable.com.br"
        return original_url.replace(parsed.netloc, stable_domain)

    def _sanitize_product_url(self, url: str, public_domain: str) -> str:
        """Garante que o link aponte para o domínio público (www.brand.com.br)."""
        if not url: return url
        parsed_p = urlparse(url)
        if "vtexcommercestable" in parsed_p.netloc or "vtexcommerce" in parsed_p.netloc:
            return url.replace(parsed_p.netloc, public_domain)
        return url

    async def _request_json(self, url: str, **kwargs) -> Optional[Any]:
        """Realiza requisições GET e retorna o JSON validado, com auto-fallback."""
        if not self.session:
            return None

        parsed = urlparse(url)
        domain = parsed.netloc
        
        for attempt in range(settings.MAX_RETRIES):
            try:
                current_url = self._get_api_url(url)
                current_proxy = IdentityManager.get_proxy()
                
                async with self.session.get(current_url, proxy=current_proxy, **kwargs) as resp:
                    if resp.status in (200, 206):
                        try:
                            # Verifica se o content type é mesmo JSON
                            if "text/html" in resp.headers.get("Content-Type", ""):
                                raise ValueError("Recebido HTML em vez de JSON")
                            return await resp.json()
                        except (aiohttp.ContentTypeError, ValueError, json.JSONDecodeError):
                            if not self.use_stable_fallback:
                                logger.warning(f"[WARNING] {domain} retornou HTML. Tentando resolver fallback estável...")
                                await self._ensure_account_resolved(domain)
                                self.use_stable_fallback = True
                                # Recomeça o loop com a nova URL
                                continue
                            else:
                                logger.error(f"[ERROR] Fallback estável também falhou em {current_url}")
                                return None
                    
                    if resp.status == 429:
                        wait = (attempt + 1) * 5
                        logger.warning(f"Rate limit (429) em {current_url}. Aguardando {wait}s...")
                        await asyncio.sleep(wait)
                        continue
                        
                    if resp.status >= 500:
                        logger.warning(f"Erro de servidor ({resp.status}) em {current_url}. Retry {attempt+1}/{settings.MAX_RETRIES}")
                        await asyncio.sleep(2 ** attempt)
                        continue
                    
                    logger.debug(f"HTTP {resp.status} em {current_url}")
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
            final_url = self._sanitize_product_url(product_url, domain)
            return await self.parse_product_dict(json_data[0], final_url, domain)
            
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
                logger.info(msg)

        parsed = urlparse(category_url)
        domain = parsed.netloc
        path = parsed.path.strip("/")
        
        # A VTEX aceita mapeamento de diretório diretamente na busca
        api_base_url = f"https://{domain}/api/catalog_system/pub/products/search/{path}"

        produtos_extraidos = []
        pagina = 0

        log(f"[START] Iniciando extração API-First paginada: {category_url}")
        
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
                current_url = self._get_api_url(url)
                async with self.session.get(current_url, proxy=IdentityManager.get_proxy(), timeout=15) as response:
                    # Detecta se retornou HTML em vez de JSON
                    if "text/html" in response.headers.get("Content-Type", ""):
                        if not self.use_stable_fallback:
                            logger.warning(f"[WARNING] {domain} retornou HTML em busca. Tentando fallback...")
                            await self._ensure_account_resolved(domain)
                            self.use_stable_fallback = True
                            continue # Tenta a mesma página com a nova URL
                        else:
                            log(f"[ERROR] Fallback estável também falhou (HTML) em {current_url}")
                            break

                    if response.status not in (200, 206):
                        log(f"[ERROR] API retornou HTTP {response.status}")
                        break
                        
                    # Puxa o total de produtos pelo header na primeira requisição
                    if not stats_emitido and "resources" in response.headers:
                        res_header = response.headers.get("resources", "")
                        if "/" in res_header:
                            try:
                                 # Nao enviamos mais o total de produtos para evitar confusao de paridade
                                 # total_produtos = int(res_header.split("/")[-1])
                                 # log({
                                 #     "type": "brand_stats",
                                 #     "total_links": total_produtos,
                                 #     "message": f"Total de produtos na categoria: {total_produtos}"
                                 # })
                                 stats_emitido = True
                            except ValueError:
                                pass
                        
                    raw_products = await response.json()
                    
                    if not raw_products or not isinstance(raw_products, list):
                        log("[OK] Fim da categoria alcançado!")
                        break

                    async def build_product(p):
                        link = p.get("link")
                        if not link:
                            link_text = p.get("linkText")
                            if link_text:
                                link = f"https://{domain}/{link_text}/p"
                        
                        # Garante link absoluto e aponta para o domínio público
                        if link:
                            if not link.startswith("http"):
                                link = f"https://{domain}{link}"
                            link = self._sanitize_product_url(link, domain)
                            
                        if not link:
                            return None
                            
                        prod = await self.parse_product_dict(p, link, domain)
                        if prod:
                            log({"type": "brand_success", "message": f"Sucesso: {prod.raw_title}"})
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
                log({"type": "brand_error", "message": f"Falha ao varrer página {pagina + 1}: {e}"})
                break

            pagina += 1
            await asyncio.sleep(0.5) # Respeito ao rate limit VTEX
            
        log(f"[DONE] Extração concluída! {len(produtos_extraidos)} produtos capturados.")
        return produtos_extraidos

    async def search(
        self,
        query: str,
        max_results: int = 10,
        sort: Optional[str] = None,
        only_in_stock: bool = False
    ) -> BrandSearchResult:
        """
        Executa a busca full-text na VTEX.
        Suporta ordenação e filtro de estoque.
        """
        brand_key = self.brand_name.lower().split()[0]
        brand_info = brand_service.get_brand(brand_key)
        brand_name = brand_info.brand_name if brand_info else self.brand_name

        if not brand_info:
            return BrandSearchResult(brand_key=brand_key, brand_name=brand_name, error="Marca não registrada.")

        domain = brand_info.domain.replace("https://", "").replace("http://", "").strip("/")
        sanitized_query = query.replace("-", " ")
        encoded_query = urllib.parse.quote(sanitized_query)

        # Mapeamento de Sort para VTEX Catalog System
        sort_map = {
            "price_asc": "OrderByPriceASC",
            "price_desc": "OrderByPriceDESC",
            "top_selling": "OrderByTopSaleDESC",
            "relevance": "OrderByScoreDESC"
        }
        vtex_sort = sort_map.get(sort, "OrderByScoreDESC")

        products = []
        chunk_size = 10
        max_pages = 5
        last_error = None
        
        category_path = resolve_query_to_vtex_category_path(query, brand_key)

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            self.session = session
            for page in range(max_pages):
                if len(products) >= max_results:
                    break

                _from = page * chunk_size
                _to = _from + chunk_size - 1

                if category_path:
                    url = f"https://{domain}/api/catalog_system/pub/products/search?fq={category_path}&_from={_from}&_to={_to}&O={vtex_sort}"
                else:
                    url = f"https://{domain}/api/catalog_system/pub/products/search?ft={encoded_query}&_from={_from}&_to={_to}&O={vtex_sort}"

                try:
                    raw_products = await self._request_json(url)
                    if not raw_products or not isinstance(raw_products, list):
                        break

                    # Filtro de estoque se solicitado
                    valid_raw = []
                    for p in raw_products:
                        if only_in_stock:
                            is_avail = any(
                                any(s.get("commertialOffer", {}).get("AvailableQuantity", 0) > 0 for s in item.get("sellers", []))
                                for item in p.get("items", [])
                            )
                            if not is_avail:
                                continue
                        valid_raw.append(p)

                    # Reviews em lote
                    pids = [str(p.get("productId")) for p in valid_raw if p.get("productId")]
                    reviews_dict = await get_bulk_reviews(brand_key, pids)

                    for p in valid_raw:
                        pid = str(p.get("productId"))
                        rating, count = reviews_dict.get(pid, (None, None))
                        
                        # Converte para o modelo de busca
                        items = p.get("items", [])
                        price_full = 0.0
                        price_discount = None
                        available = False
                        
                        for item in items:
                            for seller in item.get("sellers", []):
                                offer = seller.get("commertialOffer", {})
                                if offer.get("AvailableQuantity", 0) > 0:
                                    available = True
                                    if price_full == 0.0:
                                        price_full = offer.get("Price", 0.0)
                                        lp = offer.get("ListPrice", 0.0)
                                        if lp > price_full:
                                            price_discount = lp - price_full
                                    break
                        
                        image_url = items[0].get("images", [{}])[0].get("imageUrl") if items else None
                        
                        products.append(SearchProductResult(
                            brand=brand_key,
                            product_name=p.get("productName", ""),
                            url=self._sanitize_product_url(p.get("link", ""), domain),
                            price_full=price_full,
                            price_discount=price_discount,
                            image_url=image_url,
                            category=p.get("categories", [""])[0].split("/")[-2] if p.get("categories") else None,
                            available=available,
                            rating=rating,
                            review_count=count
                        ))
                        
                        if len(products) >= max_results:
                            break

                except Exception as e:
                    last_error = str(e)
                    break

        if last_error and not products:
            return BrandSearchResult(brand_key=brand_key, brand_name=brand_name, error=last_error)

        return BrandSearchResult(
            brand_key=brand_key,
            brand_name=brand_name,
            products=products,
            total_found=len(products)
        )

