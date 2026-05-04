import requests
import csv
from tqdm import tqdm
from urllib.parse import urlparse


def transformar_para_api(url):
    url = url.strip()

    # Se já for API, retorna direto
    if "/api/catalog_system/" in url:
        return url

    parsed = urlparse(url)

    dominio = f"{parsed.scheme}://{parsed.netloc}"
    slug = parsed.path.strip("/").split("/")[-1]

    return f"{dominio}/api/catalog_system/pub/products/search/{slug}/p"


with open("urls.txt", "r", encoding="utf-8") as arquivo_urls:
    urls = [url.strip() for url in arquivo_urls if url.strip()]

    headers = {
        "accept": "application/json",
        "user-agent": "Mozilla/5.0"
    }

    with open("dadosProdutos.csv", "w", newline="", encoding="utf-8") as arquivo_resultado:

        nomes_colunas = ["sku", "nome_produto", "gtin", "fabricante", "preco"]
        
        writer = csv.DictWriter(arquivo_resultado, fieldnames=nomes_colunas)
        writer.writeheader()

        for url in tqdm(urls):
            try:
                api_url = transformar_para_api(url)

                response = requests.get(api_url, headers=headers, timeout=10)
                response.raise_for_status()

                json_products = response.json()

                if not json_products:
                    print(f"Sem dados: {url}")
                    continue

                produto = json_products[0]

                dados = {
                    "sku": produto.get("productId"),
                    "nome_produto": produto.get("productName"),
                    "gtin": produto.get("items", [{}])[0].get("ean"),
                    "fabricante": produto.get("brand"),
                    "preco": produto.get("items", [{}])[0]
                                        .get("sellers", [{}])[0]
                                        .get("commertialOffer", {})
                                        .get("Price")
                }

                writer.writerow(dados)
            except Exception as e:
                print(f"Erro em {url}: {e}")