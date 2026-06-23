"""
Funções puras de parsing/normalização da integração VTEX.

Extraídas de ``VtexApiClient`` para isolar a lógica determinística (sem rede,
sem sessão HTTP, sem estado) e permitir teste unitário. ``VtexApiClient``
continua sendo a fachada pública e delega para estas funções.
"""
import re
from typing import List
from urllib.parse import urlparse

from core.vtex_schemas import VtexProduct, VtexItem


# Chaves de especificação que carregam cor na API Catalog System da VTEX.
_COLOR_SPEC_KEYS = ["Cor", "Color", "Cor Real", "Cores"]


def discover_account_from_html(domain: str, html_content: str) -> str:
    """Extrai o nome da conta VTEX de um HTML bruto (CDN vtexassets ou domínio)."""
    # 1. Procura pela CDN
    vtexassets_match = re.search(r"https:\/\/([^.]+)\.vtexassets\.com", html_content)
    if vtexassets_match:
        return vtexassets_match.group(1)

    # 2. Fallback pelo domínio
    account_match = re.search(r"^(?:www\.)?([^.]+)", domain)
    return account_match.group(1) if account_match else domain.split(".")[0]


def transform_url_to_api(url: str) -> str:
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


def sanitize_product_url(url: str, public_domain: str) -> str:
    """Garante que o link aponte para o domínio público (www.brand.com.br)."""
    if not url:
        return url
    parsed_p = urlparse(url)
    if "vtexcommercestable" in parsed_p.netloc or "vtexcommerce" in parsed_p.netloc:
        return url.replace(parsed_p.netloc, public_domain)
    return url


def extract_colors(p: VtexProduct) -> List[str]:
    """Varre as especificações em busca das cores na API Catalog System."""
    cores_encontradas = set()

    # Foca em allSpecifications, que é a fonte mais confiável de cor.
    for spec_name in p.allSpecifications:
        if spec_name in _COLOR_SPEC_KEYS:
            valores = getattr(p, spec_name, [])
            if isinstance(valores, list):
                for valor in valores:
                    cores_encontradas.add(str(valor).strip().upper())

    return list(cores_encontradas)


def extract_sizes(items: List[VtexItem]) -> List[str]:
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
