import asyncio
import logging
from typing import Optional, Dict, Callable
from playwright.async_api import async_playwright
from core.models import RawProductBronze

# ---------------------------------------------------------
# Configuração Profissional de Log
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("ScraperAramis")


# ---------------------------------------------------------
# Mecanismo de Resiliência (Retry Assíncrono)
# ---------------------------------------------------------
def retry_async(retries: int = 3, delay: int = 3):
    """
    Decorador para lidar com instabilidades de rede e timeouts de renderização.
    Tenta executar a função e, em caso de exceção, aguarda e tenta de novo.
    """
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(f"Tentativa {attempt}/{retries} falhou: {e}")
                    if attempt < retries:
                        logger.info(f"Aguardando {delay}s para nova tentativa...")
                        await asyncio.sleep(delay)
            logger.error(f"Todas as {retries} tentativas falharam. Último erro: {last_exception}")
            return None
        return wrapper
    return decorator


# ---------------------------------------------------------
# O Motor do Scraper (Playwright)
# ---------------------------------------------------------
@retry_async(retries=3, delay=5)
async def scrape_competitor_product(product_url: str, brand_name: str) -> Optional[RawProductBronze]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # OTIMIZAÇÃO: Bloqueia recursos visuais para extremar a performance
        await page.route(
            "**/*",
            lambda route: route.abort()
            if route.request.resource_type in ["image", "stylesheet", "font", "media"]
            else route.continue_()
        )

        intercepted_api_data = None

        # --- ESTRATÉGIA A: Interceptação Profunda VTEX (GraphQL) ---
        async def handle_response(response):
            nonlocal intercepted_api_data
            if intercepted_api_data:
                return
            
            # Filtra apenas chamadas relevantes ao GraphQL da VTEX public api
            if "graphql" in response.url.lower():
                try:
                    data = await response.json()
                    # A VTEX envia arrays de query mutations
                    if isinstance(data, list):
                        for operation in data:
                            if operation.get("data", {}).get("product"):
                                intercepted_api_data = operation["data"]["product"]
                                break
                    elif isinstance(data, dict):
                        if data.get("data", {}).get("product"):
                            intercepted_api_data = data["data"]["product"]
                except Exception:
                    pass

        page.on("response", handle_response)

        try:
            logger.info(f"Acessando URL: {product_url}")
            await page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
            
            # Pequeno tempo extra para queries de graphql assíncronas
            await page.wait_for_timeout(2500)

            # ESTRATÉGIA DE GARANTIA: Forçar clique na tabela de especificações
            try:
                spec_buttons = await page.locator("text='Especificações'").all()
                for btn in spec_buttons:
                    if await btn.is_visible():
                        logger.info("Forçando o carregamento das especificações no DOM...")
                        await btn.click(timeout=1500)
                        await page.wait_for_timeout(1000)
                        break
            except Exception:
                pass  # Elemento já aberto ou não existe

            # ESTRATÉGIA B: Fallback para React State / DOM Validation
            # Se a API de Graphql falhou em capturar dados, vamos olhar para window.__STATE__ nativo do Apollo Client
            if intercepted_api_data:
                logger.info("Mapeamento sendo realizado via API (VTEX GraphQL)...")
            else:
                logger.info("Mapeamento sendo realizado via React State (__STATE__)...")

            # Script injetado para ler o cache state da loja (VTEX IO)
            dom_data = await page.evaluate("""() => {
                let specs = {};
                let category = null;
                let sub_category = null;
                let sizes = [];
                let productName = "";
                let description = "";
                let price = 0.0;
                
                let state = window.__STATE__ || {};
                
                // Chaves importantes que englobam composição
                const validSpecKeys = ['Composição', 'Atributos', 'Material', 'Gênero', 'Modelagem', 'Tecido'];

                // Varrer de forma polimórfica o cache state do GraphQL
                Object.values(state).forEach(obj => {
                    if (!obj || typeof obj !== 'object') return;
                    
                    let type = obj.__typename;
                    
                    // 1. Extração de Especificações / Composição
                    if (type === 'Property') {
                        let name = obj.name || obj.originalName || obj.Name;
                        let valObj = obj.values || obj.Values;
                        let val = "";
                        
                        if (Array.isArray(valObj) && valObj.length > 0) val = valObj[0];
                        else if (valObj && Array.isArray(valObj.json) && valObj.json.length > 0) val = valObj.json[0];
                        else if (typeof valObj === 'string') val = valObj;

                        if (name && val && validSpecKeys.includes(name)) {
                            specs[name] = val;
                        }
                    }

                    // 2. Título e Descrição
                    if (type === 'Product') {
                        if (obj.productName && !productName) productName = obj.productName;
                        if (obj.description && !description) description = obj.description;
                    }

                    // 3. Oferta Comercial (Price)
                    if (type === 'Offer' && obj.Price > 0 && price === 0.0) {
                        price = obj.Price;
                    }

                    // 4. Extração Limpa de Tamanhos (Apenas usando os SKUs Reais)
                    if (type === 'SKU' && obj.name) {
                        let sName = obj.name;
                        if (sName.includes(' - ')) {
                            sName = sName.split(' - ').pop().trim();
                        }
                        if (sName.length <= 6 && !sizes.includes(sName)) {
                            sizes.push(sName);
                        }
                    }
                });

                // Fallback de Metatags
                if (!price) {
                    let metaPrice = document.querySelector('meta[property="product:price:amount"]');
                    if (metaPrice) price = parseFloat(metaPrice.content);
                }
                if (!productName) {
                    let metaTitle = document.querySelector('meta[property="og:title"]');
                    if (metaTitle) productName = metaTitle.content;
                }
                if (!description) {
                    let metaDesc = document.querySelector('meta[name="description"]');
                    if (metaDesc) description = metaDesc.content;
                }

                if (sizes.length > 0) {
                    specs['Tamanhos'] = sizes.join(', ');
                }

                if (productName) {
                    let words = productName.split(' ').filter(w => w.trim().length > 0);
                    if (words.length > 0) {
                        category = words[0]; 
                        let nameLower = productName.toLowerCase();
                        if (nameLower.includes('manga longa')) sub_category = 'Manga Longa';
                        else if (nameLower.includes('manga curta')) sub_category = 'Manga Curta';
                        else if (nameLower.includes('polo') && category.toLowerCase() !== 'polo') sub_category = 'Polo';
                        else if (words.length >= 2) sub_category = words[1];
                    }
                }

                return {
                    price: price || 0.0,
                    productName: productName || "Sem Título",
                    description: description || "Sem descrição",
                    category: category,
                    sub_category: sub_category,
                    specs: specs
                };
            }""")

            # Integra as informações se a API pegou algo mas o React State pegou mais coisas (Ex: Descrição ou Preço)
            if intercepted_api_data:
                api_name = intercepted_api_data.get("productName", "")
                api_desc = intercepted_api_data.get("description", "")
                
                # Trata as propriedades (Composição, Gênero, etc) vindo da API
                api_specs = {}
                for prop in intercepted_api_data.get("properties", []):
                    if prop.get("name") and prop.get("values"):
                        api_specs[prop["name"]] = prop["values"][0]
                
                if "Tamanhos" in dom_data["specs"]:
                    api_specs["Tamanhos"] = dom_data["specs"]["Tamanhos"]

                # Extrair composição das specs
                merged_specs = {**dom_data["specs"], **api_specs}
                composition = merged_specs.get("Composição") or merged_specs.get("Material")
                
                # Merge entre dados da API interceptada e do DOM/React State
                product_data = RawProductBronze(
                    url=product_url,
                    brand=brand_name,
                    raw_title=api_name if api_name else dom_data["productName"],
                    raw_description=api_desc if api_desc else dom_data["description"],
                    price_full=dom_data["price"], # DOM Price Costuma ser mais preciso nas ofertas
                    category=dom_data["category"],
                    sub_category=dom_data["sub_category"],
                    composition=composition,
                    specifications=merged_specs, # Junta as duas fontes
                )
            else:
                composition = dom_data["specs"].get("Composição") or dom_data["specs"].get("Material")
                product_data = RawProductBronze(
                    url=product_url,
                    brand=brand_name,
                    raw_title=dom_data["productName"],
                    raw_description=dom_data["description"],
                    price_full=dom_data["price"],
                    category=dom_data["category"],
                    sub_category=dom_data["sub_category"],
                    composition=composition,
                    specifications=dom_data["specs"],
                )

            logger.info("Extração concluída com sucesso.")
            await browser.close()
            return product_data

        except Exception as e:
            await browser.close()
            raise Exception(f"Falha na automação da página: {e}")


# --- Testando a execução ---
async def main():
    url_teste = "https://www.aramis.com.br/polo-manga-curta-pima-performing-marinho-po-12-0014-010/p"
    logger.info("Iniciando rotina de scraping do produto teste...")
    
    resultado = await scrape_competitor_product(url_teste, "Aramis")

    if resultado:
        print("\n--- Dado Bruto Capturado (Camada Bronze) ---")
        print(resultado.model_dump_json(indent=2))
    else:
        logger.error("\nExtração finalizada com falha definitiva após os Retries.")


if __name__ == "__main__":
    asyncio.run(main())
