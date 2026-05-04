"""
Scrapers Registry.

Centraliza o mapeamento de marcas → módulos de scraping.
Permite adicionar novas marcas sem alterar nenhuma outra parte do código.
"""

import importlib
from typing import Any


SCRAPER_REGISTRY = {
    "aramis": "scrapers.aramis",
    "reserva": "scrapers.reserva",
    "tommy": "scrapers.tommy",
}


def get_scraper(brand: str) -> Any:
    """
    Retorna o módulo do scraper para a marca informada.

    Raises:
        ValueError: se a marca não estiver registrada.
    """
    key = brand.lower().split()[0]
    module_path = SCRAPER_REGISTRY.get(key)
    if not module_path:
        raise ValueError(f"Marca não suportada: {brand}")
    return importlib.import_module(module_path)


def list_supported_brands() -> list[str]:
    """Retorna a lista de marcas suportadas."""
    return list(SCRAPER_REGISTRY.keys())
