"""
Serviço de Extração de Dados de Produtos VTEX.

Centraliza toda a lógica de parsing do JSON nativo da VTEX (tanto da
Intelligent Search API quanto da Catalog API interceptada via Playwright).

Responsabilidade única: transformar dados brutos da VTEX em primitivas
tipadas, sem dependência de scraper específico ou de marca.

Uso:
    from services.vtex_extractor import (
        extract_colors,
        extract_color_family,
        extract_sizes,
        extract_prices,
        extract_stock,
        extract_category,
        extract_specifications,
    )
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import aiohttp
import requests
from core.models import RawProductBronze

logger = logging.getLogger("VTEXExtractor")


# ---------------------------------------------------------------------------
# Constantes configuráveis — altere aqui para cobrir novos campos sem tocar
# em nenhum scraper.
# ---------------------------------------------------------------------------

# Nomes de campo que a VTEX usa para a COR do produto (em qualquer loja/marca).
COLOR_FIELD_NAMES: List[str] = [
    "Cor",
    "Color",
    "Cor Real",
    "Cores",
    "Cor do Produto",
]

# Nomes de campo que indicam composição/material têxtil.
COMPOSITION_FIELD_NAMES: List[str] = [
    "Composição",
    "Composicao",
    "Material",
    "Tecido",
]

# Separador usado internamente nos nomes de SKU para isolar o tamanho.
# Ex: "Camiseta Aramis Pima - M"  →  "M"
SKU_NAME_SEPARATOR: str = " - "

# Teto de estoque para prevenir "estoque fantasma" (ex: VTEX usa 9999999 para
# produtos sem controle de estoque). Valores acima disso são normalizados.
STOCK_GHOST_THRESHOLD: int = 10_000
STOCK_GHOST_NORMALIZED: int = 9_999


# ---------------------------------------------------------------------------
# Extração de Cores
# ---------------------------------------------------------------------------

def extract_colors(product_json: dict) -> List[str]:
    """
    Extrai a lista de cores disponíveis de um produto VTEX.

    Estratégias (em ordem de prioridade):
    1. Variações dos SKUs: product_json["items"][*]["variations"]
    2. Especificações gerais: product_json["specificationGroups"][*]["specifications"]
    3. Fallback: campo direto de especificações legado (allSpecifications)

    Args:
        product_json: Objeto de produto retornado pela VTEX API.

    Returns:
        Lista de strings de cores sem duplicatas, normalizadas (UPPER).
    """
    cores: set[str] = set()

    # Estratégia 1: Variações dos SKUs (Intelligent Search API)
    for item in product_json.get("items", []):
        for variation in item.get("variations", []):
            if variation.get("name") in COLOR_FIELD_NAMES:
                for value in variation.get("values", []):
                    if value and isinstance(value, str):
                        cores.add(value.strip().upper())

    if cores:
        return sorted(cores)

    # Estratégia 2: specificationGroups (Intelligent Search API)
    for group in product_json.get("specificationGroups", []):
        for spec in group.get("specifications", []):
            if spec.get("name") in COLOR_FIELD_NAMES:
                for value in spec.get("values", []):
                    if value and isinstance(value, str):
                        cores.add(value.strip().upper())

    if cores:
        return sorted(cores)

    # Estratégia 3: allSpecifications (Catalog API legada)
    all_specs = product_json.get("allSpecifications", [])
    for field_name in COLOR_FIELD_NAMES:
        if field_name in all_specs:
            raw = product_json.get(field_name, [])
            if isinstance(raw, list):
                for value in raw:
                    cores.add(str(value).strip().upper())
            elif isinstance(raw, str):
                cores.add(raw.strip().upper())

    return sorted(cores)


def extract_color_family(
    product_reference: str,
    product_id: str,
    domain: str,
    timeout: int = 5,
) -> List[str]:
    """
    Busca cores "irmãs" de um produto usando as APIs públicas da VTEX.

    Estratégias (em ordem):
    1. API de Cross-Selling: /api/catalog_system/pub/products/crossselling/similars/{id}
    2. Fallback inteligente: busca pela raiz da referência no Intelligent Search.
       Ex: "ML-02-1199-001" → busca "ML-02-1199" | "ML021199001" → "ML021199"

    Args:
        product_reference: Referência completa do produto (ex: "ML-02-1199-001").
        product_id: ID numérico do produto na VTEX.
        domain: Domínio da loja (ex: "www.aramis.com.br").
        timeout: Timeout das requisições HTTP em segundos.

    Returns:
        Lista de strings de cores (UPPER), pode estar vazia.
    """
    cores_familia: set[str] = set()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120.0.0.0"
        ),
        "Accept": "application/json",
    }

    # Estratégia 1: API de Cross-Selling
    if product_id:
        try:
            url = (
                f"https://{domain}/api/catalog_system/pub/products"
                f"/crossselling/similars/{product_id}"
            )
            response = requests.get(url, headers=headers, timeout=timeout)
            if response.status_code == 200:
                for prod in response.json():
                    # Tenta todos os nomes de campo de cor configurados
                    for field_name in COLOR_FIELD_NAMES:
                        raw = prod.get(field_name)
                        if isinstance(raw, list) and raw:
                            cores_familia.add(raw[0].strip().upper())
                            break
                        elif isinstance(raw, str) and raw:
                            cores_familia.add(raw.strip().upper())
                            break
        except requests.RequestException as e:
            logger.debug(f"[{domain}] Cross-selling falhou: {e}")

    if cores_familia:
        return sorted(cores_familia)

    # Estratégia 2: Busca pela raiz da referência
    if product_reference:
        referencia_raiz = _derive_reference_root(product_reference)
        if referencia_raiz:
            try:
                url = (
                    f"https://{domain}/api/io/_v/api/intelligent-search"
                    f"/product_search?query={referencia_raiz}"
                )
                response = requests.get(url, headers=headers, timeout=timeout)
                if response.status_code == 200:
                    for prod in response.json().get("products", []):
                        for cor in extract_colors(prod):
                            cores_familia.add(cor)
            except requests.RequestException as e:
                logger.debug(f"[{domain}] Busca por raiz de referência falhou: {e}")

    return sorted(cores_familia)


def _derive_reference_root(reference: str) -> str:
    """
    Deriva a raiz de uma referência VTEX para busca de variantes de cor.

    Lógica:
    - Com hífens (ex: "ML-02-1199-001"): remove o último segmento → "ML-02-1199"
    - Numérico contínuo (ex: "ML021199001"): remove os últimos 3 dígitos → "ML021199"
    - Outros formatos: retorna vazio (não tenta busca)
    """
    if not reference:
        return ""

    if "-" in reference:
        parts = reference.split("-")
        return "-".join(parts[:-1]) if len(parts) > 1 else ""

    if len(reference) > 3 and reference[-3:].isdigit():
        return reference[:-3]

    return ""


# ---------------------------------------------------------------------------
# Extração de Tamanhos
# ---------------------------------------------------------------------------

def extract_sizes(items: list) -> List[str]:
    """
    Extrai e limpa a lista de tamanhos disponíveis de um produto VTEX.

    O nome do SKU na VTEX frequentemente vem no formato
    "Nome do Produto - TAMANHO". Esta função isola apenas o tamanho.

    Args:
        items: Array "items" do produto VTEX (SKUs).

    Returns:
        Lista de tamanhos únicos preservando a ordem de aparição.
    """
    seen: set[str] = set()
    sizes: List[str] = []

    for item in items:
        name = item.get("name", "")
        if not name:
            continue

        # Extrai apenas a parte após o separador, se existir
        if SKU_NAME_SEPARATOR in name:
            size = name.split(SKU_NAME_SEPARATOR)[-1].strip()
        else:
            size = name.strip()

        if size and size not in seen:
            seen.add(size)
            sizes.append(size)

    return sizes


# ---------------------------------------------------------------------------
# Extração de Preços
# ---------------------------------------------------------------------------

def extract_prices(items: list) -> Tuple[float, Optional[float]]:
    """
    Extrai o preço cheio e o preço com desconto de um produto VTEX.

    Percorre todos os SKUs e retorna os preços do primeiro SKU com
    disponibilidade de estoque. Se nenhum SKU tiver estoque, usa o primeiro
    disponível independente de estoque.

    Args:
        items: Array "items" do produto VTEX (SKUs).

    Returns:
        Tupla (price_full, price_discount).
        - price_full: Preço de lista (ListPrice). Fallback para Price.
        - price_discount: Preço de venda, apenas se for menor que price_full.
          None se não houver desconto real.
    """
    first_fallback: Optional[Tuple[float, Optional[float]]] = None

    for item in items:
        for seller in item.get("sellers", []):
            offer = seller.get("commertialOffer", {})
            sale_price = offer.get("Price", 0.0) or 0.0
            list_price = offer.get("ListPrice", 0.0) or 0.0
            in_stock = offer.get("AvailableQuantity", 0) > 0

            if sale_price <= 0:
                continue

            # Garante que list_price nunca seja menor que sale_price
            if list_price <= 0 or list_price < sale_price:
                list_price = sale_price

            price_full = float(list_price)
            price_discount = float(sale_price) if sale_price < list_price else None

            if in_stock:
                return price_full, price_discount

            # Guarda como fallback caso nenhum SKU tenha estoque
            if first_fallback is None:
                first_fallback = (price_full, price_discount)

    return first_fallback or (0.0, None)


# ---------------------------------------------------------------------------
# Extração de Estoque
# ---------------------------------------------------------------------------

def extract_stock(items: list) -> int:
    """
    Soma o estoque disponível de todos os SKUs de um produto VTEX.

    Aplica teto anti-fantasma: lojas VTEX frequentemente usam valores como
    9.999.999 para indicar "estoque ilimitado", o que quebraria análises de ML.
    Valores acima de STOCK_GHOST_THRESHOLD são normalizados para
    STOCK_GHOST_NORMALIZED.

    Args:
        items: Array "items" do produto VTEX (SKUs).

    Returns:
        Total de unidades disponíveis (inteiro não-negativo).
    """
    total = 0
    for item in items:
        for seller in item.get("sellers", []):
            qty = seller.get("commertialOffer", {}).get("AvailableQuantity", 0)
            total += max(0, int(qty))

    if total >= STOCK_GHOST_THRESHOLD:
        logger.debug(
            f"Estoque fantasma detectado ({total} unidades). "
            f"Normalizando para {STOCK_GHOST_NORMALIZED}."
        )
        return STOCK_GHOST_NORMALIZED

    return total


# ---------------------------------------------------------------------------
# Extração de Categorias
# ---------------------------------------------------------------------------

def extract_category(
    categories: list,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Extrai a categoria principal e subcategoria de um produto VTEX.

    A VTEX retorna as categorias como caminhos de URL, ex:
    ["/Roupas/Camisas/", "/Roupas/"]

    Esta função usa o caminho mais profundo (mais específico) e retorna
    os dois primeiros níveis.

    Args:
        categories: Array "categories" do produto VTEX.

    Returns:
        Tupla (category, sub_category). Ambos podem ser None.
    """
    if not categories:
        return None, None

    # O caminho mais profundo é o mais específico
    deepest = max(categories, key=lambda c: c.count("/"))
    parts = [p.strip() for p in deepest.split("/") if p.strip()]

    category = parts[0] if len(parts) >= 1 else None
    sub_category = parts[1] if len(parts) >= 2 else None

    return category, sub_category


# ---------------------------------------------------------------------------
# Extração de Especificações Gerais
# ---------------------------------------------------------------------------

def extract_specifications(product_json: dict) -> Dict[str, str]:
    """
    Extrai todas as especificações de um produto VTEX como dicionário plano.

    Suporta três formatos de API:
    1. specificationGroups → specifications (Intelligent Search API)
    2. allSpecifications como lista de chaves (Catalog API)
    3. Propriedades diretas no nível do produto (GraphQL)

    Args:
        product_json: Objeto de produto VTEX.

    Returns:
        Dicionário {nome_spec: valor_spec}.
    """
    specs: Dict[str, str] = {}

    # Formato 1: specificationGroups (Intelligent Search)
    for group in product_json.get("specificationGroups", []):
        for spec in group.get("specifications", []):
            name = spec.get("name")
            values = spec.get("values", [])
            if name and values:
                specs[name] = values[0] if isinstance(values, list) else str(values)

    # Formato 2: allSpecifications (Catalog API legada)
    all_spec_keys = product_json.get("allSpecifications", [])
    if isinstance(all_spec_keys, list):
        for key in all_spec_keys:
            if key not in specs:  # Não sobrescreve formato 1
                raw = product_json.get(key, [])
                if isinstance(raw, list) and raw:
                    specs[key] = raw[0]
                elif isinstance(raw, str):
                    specs[key] = raw

    # Formato 3: properties (GraphQL/VTEX IO)
    for prop in product_json.get("properties", []):
        name = prop.get("name")
        values = prop.get("values", [])
        if name and values and name not in specs:
            specs[name] = values[0] if isinstance(values, list) else str(values)

    return specs


def extract_composition(specs: Dict[str, str]) -> Optional[str]:
    """
    Extrai o valor de composição/material das especificações já parseadas.

    Args:
        specs: Dicionário de especificações (saída de extract_specifications).

    Returns:
        String de composição ou None se não encontrada.
    """
    for field_name in COMPOSITION_FIELD_NAMES:
        value = specs.get(field_name)
        if value:
            return value
    return None


# ---------------------------------------------------------------------------
# Motor de Extração Assíncrono (aiohttp)
# ---------------------------------------------------------------------------

async def buscar_familia_de_cores_async(
    session: aiohttp.ClientSession,
    product_reference: str,
    product_id: str,
    domain: str,
) -> List[str]:
    """
    Versão assíncrona da busca de cores 'irmãs' de um produto.
    """
    cores_familia: set[str] = set()

    # Estratégia 1: API de Cross-Selling
    if product_id:
        try:
            url_similares = (
                f"https://{domain}/api/catalog_system/pub/products/crossselling/similars/{product_id}"
            )
            async with session.get(url_similares, timeout=5) as res_sim:
                if res_sim.status == 200:
                    dados = await res_sim.json()
                    for prod in dados:
                        for field_name in COLOR_FIELD_NAMES:
                            raw = prod.get(field_name)
                            if isinstance(raw, list) and raw:
                                cores_familia.add(raw[0].strip().upper())
                                break
                            elif isinstance(raw, str) and raw:
                                cores_familia.add(raw.strip().upper())
                                break
                        # Busca em itens
                        for item in prod.get("items", []):
                            for field_name in COLOR_FIELD_NAMES:
                                raw = item.get(field_name)
                                if isinstance(raw, list) and raw:
                                    cores_familia.add(raw[0].strip().upper())
                                    break
                                elif isinstance(raw, str) and raw:
                                    cores_familia.add(raw.strip().upper())
                                    break
        except Exception:
            pass

    # Estratégia 2: Busca por Raiz
    if not cores_familia and product_reference:
        referencia_raiz = _derive_reference_root(product_reference)
        if referencia_raiz:
            try:
                url_busca = (
                    f"https://{domain}/api/io/_v/api/intelligent-search/product_search?query={referencia_raiz}"
                )
                async with session.get(url_busca, timeout=5) as res_busca:
                    if res_busca.status == 200:
                        dados = await res_busca.json()
                        for prod in dados.get("products", []):
                            for cor in extract_colors(prod):
                                cores_familia.add(cor)
            except Exception:
                pass

    return sorted(cores_familia)


async def extrair_pagina_categoria(
    session: aiohttp.ClientSession,
    url_categoria: str,
    marca: str,
    pagina: int,
) -> List[RawProductBronze]:
    """
    Busca uma página inteira de categoria via API de forma assíncrona.
    Converte a URL amigável na query string map=c,c nativa da VTEX.
    
    Ex: /roupas/polos -> query=roupas/polos & map=c,c
    """
    parsed_url = urlparse(url_categoria)
    dominio = parsed_url.netloc
    
    # Monta a query e o map com base no caminho da URL
    caminho = parsed_url.path.strip('/')
    termos = caminho.split('/')
    map_str = ",".join(["c"] * len(termos))
    query_str = "/".join(termos)

    url_api = f"https://{dominio}/api/io/_v/api/intelligent-search/product_search?query={query_str}&map={map_str}&page={pagina}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
        "Accept": "application/json",
    }

    try:
        async with session.get(url_api, headers=headers, timeout=15) as resposta:
            if resposta.status != 200:
                return []
            dados = await resposta.json()

        produtos_extraidos = []
        for p in dados.get("products", []):
            # Modularidade via funções pure python
            cores = extract_colors(p)
            cores_irmas = await buscar_familia_de_cores_async(
                session,
                p.get("productReference", ""),
                p.get("productId", ""),
                dominio
            )
            lista_final_cores = sorted(set(cores + cores_irmas))
            
            cat_principal, sub_cat = extract_category(p.get("categories", []))
            
            specs_dict = extract_specifications(p)
            composicao = extract_composition(specs_dict)
            
            tamanhos_disponiveis = extract_sizes(p.get("items", []))
            preco_full, preco_discount = extract_prices(p.get("items", []))
            estoque_total = extract_stock(p.get("items", []))

            # Ajusta o fallback para price_full para que não seja 0 se possível
            if preco_full == 0.0 and preco_discount is not None:
                preco_full = preco_discount

            produto_bronze = RawProductBronze(
                url=f"https://{dominio}/{p.get('linkText')}/p",
                brand=marca,
                raw_title=p.get("productName", ""),
                raw_description=p.get("description", "Sem descrição"),
                price_full=preco_full,
                price_discount=preco_discount,
                stock_availability=(estoque_total > 0),
                stock_quantity=estoque_total,
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
        logger.error(f"Erro no extrator assíncrono VTEX: {e}")
        return []
