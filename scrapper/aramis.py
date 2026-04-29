import asyncio
import json
from playwright.async_api import async_playwright
from pydantic import BaseModel, Field
from typing import Optional, Dict


# ---------------------------------------------------------
# 1. Contrato de Dados (Camada Bronze)
# ---------------------------------------------------------
class RawProductBronze(BaseModel):
    url: str
    brand: str
    raw_title: str
    raw_description: str
    price_full: float
    price_discount: Optional[float] = None
    stock_availability: bool
    category: Optional[str] = None
    sub_category: Optional[str] = None
    composition: Optional[str] = None
    specifications: Dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------
# 2. O Motor do Scraper (Playwright)
# ---------------------------------------------------------
async def scrape_competitor_product(
    product_url: str, brand_name: str
) -> Optional[RawProductBronze]:
    async with async_playwright() as p:
        # headless=True para debugar visualmente.
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
                for bad_word in ["crossselling", "similars", "recommendations"]
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

            # --- NOVO: Interação Ativa (Forçando o Lazy Loading) ---
            print("Procurando botões de Especificações para forçar carregamento...")
            try:
                elementos_clicaveis = await page.locator("text='Especificações'").all()
                for el in elementos_clicaveis:
                    if await el.is_visible():
                        await el.click(timeout=2000)
                        await page.wait_for_timeout(1500)  # Espera a animação e a API
                        break
            except Exception:
                pass  # Se não achar o botão, ignora

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
                        composition=composition
                    )
                except Exception:
                    pass

            # --- TENTATIVA 2: Fallback (Meta Tags + React State + DOM Ativo) ---
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

                # --- CORREÇÃO: Captura da Descrição Rica ---
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

                dom_specs = await page.evaluate("""() => {
                    let specs = {};
                    const chavesDesejadas = ['Composição', 'Atributos', 'Cor Real', 'Medidas Complementares'];
                    
                    // 1. Busca no Estado do React
                    let state = window.__STATE__ || {};
                    Object.values(state).forEach(obj => {
                        if (obj && typeof obj === 'object') {
                            let name = obj.name || obj.originalName || obj.Name;
                            if (chavesDesejadas.includes(name)) {
                                let val = obj.values || obj.Values;
                                if (Array.isArray(val) && val.length > 0) specs[name] = val[0];
                                else if (val && Array.isArray(val.json) && val.json.length > 0) specs[name] = val.json[0];
                                else if (typeof val === 'string') specs[name] = val;
                            }
                        }
                    });

                    // 2. Busca Força Bruta via Regex no JSON inteiro
                    if (!specs['Composição']) {
                        let stateStr = JSON.stringify(state);
                        let match = stateStr.match(/"name":"Composição".*?"values":\\["(.*?)"\\]/);
                        if (match) specs['Composição'] = match[1];
                    }

                    // 3. Busca no DOM Visível
                    if (!specs['Composição']) {
                        for (let el of document.querySelectorAll('*')) {
                            if (el.children.length > 0) continue; 
                            let text = (el.textContent || "").trim();
                            for (let chave of chavesDesejadas) {
                                if (text === chave || text === chave + ":") {
                                    let fullText = (el.parentElement.textContent || "").trim();
                                    let valor = fullText.replace(text, "").replace(":", "").trim();
                                    if (valor) specs[chave] = valor.split('\\n')[0].trim();
                                }
                            }
                        }
                    }

                    // Puxando os Tamanhos visuais
                    let tamanhos = [];
                    document.querySelectorAll('span, p, div, li').forEach(el => {
                        let txt = (el.textContent || "").trim();
                        if (['P', 'M', 'G', 'GG', 'XGG', 'XXG', '38', '40', '42', '44', '46'].includes(txt)) {
                            if (!tamanhos.includes(txt) && el.children.length === 0) tamanhos.push(txt);
                        }
                    });
                    if(tamanhos.length > 0) specs["Tamanhos"] = tamanhos.join(", ");

                    return specs;
                }""")

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
                        composition=comp
                    )
                print("[SUCESSO] Extração do estado do React concluída!")

            await browser.close()
            return product_data

        except Exception as e:
            print(f"Erro fatal: {e}")
            await browser.close()
            return None


# --- Testando a execução ---
async def main():
    url_teste = "https://www.aramis.com.br/polo-tricot-manga-curta-explorer-fishbone-azul-indigo-po-12-0034-156/p?theme=urban"
    resultado = await scrape_competitor_product(url_teste, "Aramis")

    if resultado:
        print("\n--- Dado Bruto Capturado (Camada Bronze) ---")
        print(resultado.model_dump_json(indent=2))
    else:
        print("\nFalha na extração.")


if __name__ == "__main__":
    asyncio.run(main())
