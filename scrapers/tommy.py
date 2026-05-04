import asyncio
import json
from playwright.async_api import async_playwright
from typing import Optional, Dict
from core.models import RawProductBronze
from services.review_service import get_single_review


# ---------------------------------------------------------
# 2. O Motor do Scraper (Playwright)
# ---------------------------------------------------------
async def scrape_competitor_product(
    product_url: str, brand_name: str
) -> Optional[RawProductBronze]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        intercepted_api_data = None

        # --- ESTRATÉGIA A: Interceptação de Rede ---
        async def handle_response(response):
            nonlocal intercepted_api_data
            if intercepted_api_data:
                return

            url_lower = response.url.lower()
            if any(
                bad_word in url_lower
                for bad_word in [
                    "crossselling",
                    "similars",
                    "recommendations",
                    "whosawalsosaw",
                ]
            ):
                return

            if "api" in url_lower or "graphql" in url_lower or "products" in url_lower:
                if response.status == 200:
                    try:
                        data = await response.json()
                        if (
                            isinstance(data, list)
                            and len(data) > 0
                            and "productName" in data[0]
                        ):
                            intercepted_api_data = data[0]
                        elif isinstance(data, dict) and "productName" in data:
                            intercepted_api_data = data
                    except:
                        pass

        page.on("response", handle_response)

        try:
            print(f"Acessando: {product_url}")
            await page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            # --- AGENTE ATIVO GENERALISTA (Cobre Tommy, Reserva, Aramis) ---
            print("Procurando botões de expansão de detalhes...")
            botoes_alvo = [
                "Especificações",
                "Características",
                "Detalhes",
                "Descrição",
                "Composição",
            ]

            for texto in botoes_alvo:
                try:
                    elementos = await page.locator(
                        f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{texto.lower()}')] | //div[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{texto.lower()}')]"
                    ).all()
                    for el in elementos:
                        if await el.is_visible():
                            await el.click(timeout=1500)
                            await page.wait_for_timeout(1000)
                            print(f"Botão '{texto}' clicado!")
                            break
                except:
                    continue

            product_data = None

            # --- TENTATIVA 1: Mapeamento via API de Rede ---
            if intercepted_api_data:
                print("[SUCESSO] API Interceptada via Rede. Mapeando...")
                try:
                    preco_venda = (
                        intercepted_api_data.get("items", [{}])[0]
                        .get("sellers", [{}])[0]
                        .get("commertialOffer", {})
                        .get("Price", 0.0)
                    )

                    specs_dict = {}
                    if "allSpecifications" in intercepted_api_data:
                        for k in intercepted_api_data["allSpecifications"]:
                            v = intercepted_api_data.get(k, [])
                            specs_dict[k] = v[0] if isinstance(v, list) else str(v)

                    tamanhos = []
                    for sku in intercepted_api_data.get("items", []):
                        if sku.get("name") and sku.get("name") not in tamanhos:
                            tamanhos.append(sku.get("name"))
                    if tamanhos:
                        specs_dict["Tamanhos"] = ", ".join(tamanhos)

                    cat_array = intercepted_api_data.get("categories", [])
                    category, sub_category = None, None
                    if cat_array:
                        parts = [p for p in cat_array[0].split("/") if p]
                        if len(parts) >= 1:
                            category = parts[0]
                        if len(parts) >= 2:
                            sub_category = parts[1]

                    composition = specs_dict.get("Composição") or specs_dict.get("Material")
                    
                    product_id_str = str(intercepted_api_data.get("productId", ""))
                    rating, count = await get_single_review("tommy", product_id_str)

                    product_data = RawProductBronze(
                        url=product_url,
                        brand=brand_name,
                        raw_title=intercepted_api_data.get("productName", ""),
                        raw_description=intercepted_api_data.get(
                            "description", "Sem descrição"
                        ),
                        price_full=float(preco_venda),
                        stock_availability=True,
                        specifications=specs_dict,
                        category=category,
                        sub_category=sub_category,
                        composition=composition,
                        rating=rating,
                        review_count=count
                    )
                except Exception:
                    pass

            # --- TENTATIVA 2: Fallback Blindado ---
            if (
                not product_data
                or product_data.price_full == 0.0
                or not product_data.specifications.get("Composição")
            ):
                print(
                    "Lendo dados via Server-Side Rendering (DOM Ativo + React State)..."
                )

                meta_price = await page.evaluate("""() => {
                    let meta = document.querySelector('meta[property="product:price:amount"]');
                    return meta ? parseFloat(meta.content) : 0.0;
                }""")

                meta_title = await page.evaluate("""() => {
                    let meta = document.querySelector('meta[property="og:title"]');
                    return meta ? meta.content : "";
                }""")

                # Captura da Descrição Rica
                meta_desc = await page.evaluate("""() => {
                    let state = window.__STATE__ || {};
                    for (let key in state) {
                        if (key.startsWith('Product:') && state[key].description) {
                            return state[key].description;
                        }
                    }
                    let meta = document.querySelector('meta[name="description"], meta[property="og:description"]');
                    return meta ? meta.content : "Descrição não encontrada.";
                }""")

                dom_result = await page.evaluate("""() => {
                    let specs = {};
                    let productId = null;
                    const chavesDesejadas = ['Composição', 'Atributos', 'Cor', 'Cor Real', 'Material', 'Modelagem'];
                    
                    // 1. Busca no Estado do React
                    let state = window.__STATE__ || {};
                    Object.values(state).forEach(obj => {
                        if (obj && typeof obj === 'object') {
                            if (obj.__typename === 'Product' && obj.productId && !productId) productId = obj.productId;
                            let name = obj.name || obj.originalName || obj.Name;
                            if (chavesDesejadas.includes(name)) {
                                let val = obj.values || obj.Values;
                                if (Array.isArray(val) && val.length > 0) specs[name] = val[0];
                                else if (val && Array.isArray(val.json) && val.json.length > 0) specs[name] = val.json[0];
                                else if (typeof val === 'string') specs[name] = val;
                            }
                        }
                    });

                    // 2. Busca Força Bruta via Regex
                    if (!specs['Composição']) {
                        let stateStr = JSON.stringify(state);
                        let match = stateStr.match(/"name":"Composi[çc][ãa]o".*?"values":\\["(.*?)"\\]/);
                        if (match) specs['Composição'] = match[1];
                        
                        let matchMaterial = stateStr.match(/"name":"Material".*?"values":\\["(.*?)"\\]/);
                        if (matchMaterial && !specs['Composição']) specs['Composição'] = matchMaterial[1];
                    }

                    // 3. Busca no DOM Visível
                    if (!specs['Composição']) {
                        for (let el of document.querySelectorAll('*')) {
                            if (el.children.length > 0) continue; 
                            let text = (el.textContent || "").trim();
                            for (let chave of chavesDesejadas) {
                                if (text === chave || text === chave + ":" || text.toLowerCase() === 'composição') {
                                    let fullText = (el.parentElement.textContent || "").trim();
                                    let valor = fullText.replace(text, "").replace(":", "").trim();
                                    if (valor) specs[chave] = valor.split('\\n')[0].trim();
                                }
                            }
                        }
                    }

                    // Puxando os Tamanhos visuais (Adicionados tamanhos Internacionais para Tommy)
                    let tamanhos = [];
                    document.querySelectorAll('span, p, div, li').forEach(el => {
                        let txt = (el.textContent || "").trim();
                        if (['PP', 'P', 'M', 'G', 'GG', 'XGG', 'XXG', 'S', 'L', 'XL', 'XXL', '38', '40', '42'].includes(txt)) {
                            if (!tamanhos.includes(txt) && el.children.length === 0) tamanhos.push(txt);
                        }
                    });
                    if(tamanhos.length > 0) specs["Tamanhos"] = tamanhos.join(", ");

                    return {specs: specs, productId: productId};
                }""")
                
                dom_specs = dom_result["specs"]
                product_id_str = str(dom_result.get("productId") or "")
                rating, count = await get_single_review("tommy", product_id_str)

                dom_category = await page.evaluate("""() => {
                    let breadcrumbs = Array.from(document.querySelectorAll('.vtex-breadcrumb-1-x-link, [class*="breadcrumb"] a'));
                    if(breadcrumbs.length > 0) {
                        let parts = breadcrumbs.map(el => el.textContent.trim()).filter(t => t);
                        if(parts[0] && parts[0].toLowerCase() === 'home') parts.shift();
                        return { category: parts[0] || null, sub_category: parts[1] || null };
                    }
                    return { category: null, sub_category: null };
                }""")

                comp = dom_specs.get('Composição') or dom_specs.get('Material')

                if product_data:
                    product_data.specifications.update(dom_specs)
                    if (
                        not product_data.raw_description
                        or product_data.raw_description == "Sem descrição"
                    ):
                        product_data.raw_description = meta_desc
                    if not product_data.category:
                        product_data.category = dom_category['category']
                    if not product_data.sub_category:
                        product_data.sub_category = dom_category['sub_category']
                    if not product_data.composition:
                        product_data.composition = comp
                    if not product_data.rating:
                        product_data.rating = rating
                        product_data.review_count = count
                else:
                    product_data = RawProductBronze(
                        url=product_url,
                        brand=brand_name,
                        raw_title=meta_title or "Título não encontrado",
                        raw_description=meta_desc or "Extração via DOM Interativo realizada.",
                        price_full=meta_price,
                        price_discount=None,
                        stock_availability=True,
                        specifications=dom_specs,
                        category=dom_category['category'],
                        sub_category=dom_category['sub_category'],
                        composition=comp,
                        rating=rating,
                        review_count=count
                    )
                print("[SUCESSO] Extração do estado do React/DOM concluída!")

            await browser.close()
            return product_data

        except Exception as e:
            print(f"Erro fatal: {e}")
            await browser.close()
            return None


async def main():
    # Testando a Polo da Tommy Hilfiger
    url_teste = "https://br.tommy.com/polo-performance-jersey-thmw0mw37310_thbds/p"
    resultado = await scrape_competitor_product(url_teste, "Tommy Hilfiger")

    if resultado:
        print("\n--- Dado Bruto Capturado (Camada Bronze) ---")
        print(resultado.model_dump_json(indent=2))
    else:
        print("\nFalha na extração.")


if __name__ == "__main__":
    asyncio.run(main())
