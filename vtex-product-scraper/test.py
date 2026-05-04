import requests
from pydantic import BaseModel, Field
from typing import Optional, Dict, List

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
    stock_quantity: int = 0  # Fundamental para o modelo no Databricks
    category: Optional[str] = None
    sub_category: Optional[str] = None
    composition: Optional[str] = None
    available_colors: List[str] = Field(default_factory=list)
    available_sizes: List[str] = Field(default_factory=list)
    specifications: Dict[str, str] = Field(default_factory=dict)

# ---------------------------------------------------------
# 2. Extratores Específicos de Cores
# ---------------------------------------------------------
def extrair_cores_vtex(produto_json: dict) -> list[str]:
    """
    Varre o JSON de um produto no Intelligent Search e extrai as cores únicas nativas.
    """
    cores_encontradas = set()
    nomes_chaves_cor = ["Cor", "Color", "Cor Real", "Cores"]

    # TENTATIVA 1: Procurar nas Variações dos SKUs
    for item in produto_json.get("items", []):
        variations = item.get("variations", [])
        for var in variations:
            if var.get("name") in nomes_chaves_cor:
                for valor in var.get("values", []):
                    cores_encontradas.add(valor)

    # TENTATIVA 2: Fallback para as Especificações Gerais do Produto
    if not cores_encontradas:
        for grupo in produto_json.get("specificationGroups", []):
            for spec in grupo.get("specifications", []):
                if spec.get("name") in nomes_chaves_cor:
                    for valor in spec.get("values", []):
                        cores_encontradas.add(valor)

    return list(cores_encontradas)


def buscar_familia_de_cores(referencia_completa: str, product_id: str, dominio: str) -> list[str]:
    """
    Procura outras cores do produto utilizando a API de Similares da VTEX 
    e um fallback inteligente de pesquisa pela raiz da referência.
    """
    cores_da_familia = set()

    # ESTRATÉGIA 1: API de Produtos Similares (Cross-Selling)
    if product_id:
        try:
            url_similares = f"https://{dominio}/api/catalog_system/pub/products/crossselling/similars/{product_id}"
            res_sim = requests.get(url_similares, timeout=5)
            
            if res_sim.status_code == 200:
                for prod in res_sim.json():
                    if "Cor Real" in prod and isinstance(prod["Cor Real"], list):
                        cores_da_familia.add(prod["Cor Real"][0].strip().upper())
                    elif "Cor" in prod and isinstance(prod["Cor"], list):
                        cores_da_familia.add(prod["Cor"][0].strip().upper())
                    
                    for item in prod.get("items", []):
                        if "Cor Real" in item and isinstance(item["Cor Real"], list):
                            cores_da_familia.add(item["Cor Real"][0].strip().upper())
                        elif "Cor" in item and isinstance(item["Cor"], list):
                            cores_da_familia.add(item["Cor"][0].strip().upper())
        except Exception:
            pass

    # ESTRATÉGIA 2: Pesquisa por Raiz da Referência (Fallback Inteligente)
    if not cores_da_familia and referencia_completa:
        referencia_raiz = ""
        # Se tiver traço (ex: ML-02-1199-001)
        if "-" in referencia_completa:
            referencia_raiz = "-".join(referencia_completa.split("-")[:-1])
        # Se for tudo junto (ex: ML021199001), retira os últimos 3 números
        elif len(referencia_completa) > 3 and referencia_completa[-3:].isdigit():
            referencia_raiz = referencia_completa[:-3]
            
        if referencia_raiz:
            try:
                url_busca = f"https://{dominio}/api/io/_v/api/intelligent-search/product_search?query={referencia_raiz}"
                res_busca = requests.get(url_busca, timeout=5)
                
                if res_busca.status_code == 200:
                    for prod in res_busca.json().get("products", []):
                        for cor in extrair_cores_vtex(prod):
                            cores_da_familia.add(cor.strip().upper())
            except Exception:
                pass

    return list(cores_da_familia)


# ---------------------------------------------------------
# 3. O Motor Principal da API
# ---------------------------------------------------------
def extrair_produtos_da_api(dominio: str, marca: str, pagina: int = 1) -> List[RawProductBronze]:
    """
    Consome o endpoint do VTEX Intelligent Search, limpa os dados e converte.
    """
    url_api = f"https://{dominio}/api/io/_v/api/intelligent-search/product_search?page={pagina}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
        "Accept": "application/json",
    }

    try:
        print(f"[{marca}] A consultar API Intelligent Search (Página {pagina})...")
        resposta = requests.get(url_api, headers=headers, timeout=15)

        if resposta.status_code != 200:
            print(f"Erro na API: {resposta.status_code}")
            return []

        dados = resposta.json()
        produtos_extraidos = []

        for p in dados.get("products", []):
            
            # 1. Extração de Cores (Atual + Família Integrada)
            lista_de_cores = [c.strip().upper() for c in extrair_cores_vtex(p)]
            
            id_produto = p.get("productId", "")
            referencia_produto = p.get("productReference", "")
            cores_irmas = buscar_familia_de_cores(referencia_produto, id_produto, dominio)

            # Junta a cor atual com as cores da família, removendo duplicados
            lista_final_cores = list(set(lista_de_cores + cores_irmas))

            # 2. Extração de Categorias
            categorias = p.get("categories", [])
            cat_principal, sub_cat = None, None
            if categorias:
                partes = [c for c in categorias[0].split("/") if c]
                if len(partes) >= 1:
                    cat_principal = partes[0]
                if len(partes) >= 2:
                    sub_cat = partes[1]

            # 3. Extração de Especificações Gerais e Composição
            specs_dict = {}
            composicao = None
            for grupo in p.get("specificationGroups", []):
                for spec in grupo.get("specifications", []):
                    nome_spec = spec.get("name")
                    valor_spec = spec.get("values", [""])[0]
                    specs_dict[nome_spec] = valor_spec

                    if nome_spec in ["Composição", "Material"]:
                        composicao = valor_spec

            # 4. Varredura dos SKUs (Tamanhos com Limpeza, Preços e Stock)
            tamanhos_disponiveis = []
            preco_venda = 0.0
            preco_lista = 0.0
            quantidade_total_stock = 0

            for item in p.get("items", []):
                # Captura e Limpeza de Tamanhos
                nome_tamanho = item.get("name", "")
                if " - " in nome_tamanho:
                    nome_tamanho = nome_tamanho.split(" - ")[-1].strip()

                if nome_tamanho and nome_tamanho not in tamanhos_disponiveis:
                    tamanhos_disponiveis.append(nome_tamanho)

                # Captura de Preço e Stock do Seller 1
                sellers = item.get("sellers", [])
                if sellers:
                    oferta = sellers[0].get("commertialOffer", {})

                    # Soma o stock de todas as variações/tamanhos
                    stock_item = oferta.get("AvailableQuantity", 0)
                    quantidade_total_stock += stock_item

                    # Guarda o preço (apenas se for a primeira variação com stock)
                    if preco_venda == 0.0 and stock_item > 0:
                        preco_venda = oferta.get("Price", 0.0)
                        preco_lista = oferta.get("ListPrice", 0.0)

            # Trava contra o "Estoque Fantasma/Infinito" (Para não quebrar o Machine Learning)
            if quantidade_total_stock >= 10000:
                quantidade_total_stock = 999 

            # Cálculo do Desconto Monetário
            desconto = None
            if preco_lista > preco_venda and preco_venda > 0:
                desconto = preco_lista - preco_venda

            # 5. Instanciação do Objeto
            produto_bronze = RawProductBronze(
                url=f"https://{dominio}/{p.get('linkText')}/p",
                brand=marca,
                raw_title=p.get("productName", ""),
                raw_description=p.get("description", "Sem descrição"),
                price_full=preco_venda if preco_venda > 0 else preco_lista,
                price_discount=desconto,
                stock_availability=(quantidade_total_stock > 0),
                stock_quantity=quantidade_total_stock,
                category=cat_principal,
                sub_category=sub_cat,
                composition=composicao,
                available_colors=lista_final_cores,
                available_sizes=tamanhos_disponiveis,
                specifications=specs_dict,
            )

            produtos_extraidos.append(produto_bronze)

        return produtos_extraidos

    except Exception as e:
        print(f"Falha ao processar API: {e}")
        return []

# ---------------------------------------------------------
# 4. Teste de Execução
# ---------------------------------------------------------
if __name__ == "__main__":
    # Teste no endpoint da Aramis (Página 1)
    produtos = extrair_produtos_da_api(
        dominio="www.aramis.com.br", marca="Aramis", pagina=1
    )

    if produtos:
        print(f"\n[SUCESSO] {len(produtos)} produtos extraídos da API!")
        
        # Procura especificamente a camisa manga longa branca se ela estiver na página 1
        alvo = next((p for p in produtos if "ml-02-1199" in p.url), produtos[0])
        
        print("\nAmostra do produto capturado:")
        print(alvo.model_dump_json(indent=2))
    else:
        print("\nNenhum produto extraído.")