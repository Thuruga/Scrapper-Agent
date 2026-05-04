"""
Mapeamento Canônico de Categorias — De/Para Multi-Marca.

Define um vocabulário único de categorias semânticas e mapeia cada uma
para o path VTEX real de cada marca suportada.  Isso garante que ao
selecionar "Camisas", a varredura use o caminho correto em Aramis,
Reserva e Tommy simultaneamente ("banana com banana").

Fontes:
    - config.py → BRAND_REGISTRY (domínios)
    - category_resolver.py → _BRAND_CATEGORY_PATHS (referência original)
    - vtex_catalog.py → STATIC_FALLBACK (paths do frontend)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from config import BRAND_REGISTRY


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class BrandCategoryInfo:
    """Informações de uma categoria para uma marca específica."""
    path: str          # Path relativo usado na URL do site (ex: /roupas/camisas)
    vtex_fq: str       # Filtro VTEX fq=C:/... para busca exata


@dataclass(frozen=True)
class CanonicalCategory:
    """Categoria canônica com seus mapeamentos para cada marca."""
    slug: str
    label: str
    group: str                                      # Agrupamento visual (ex: "Roupas")
    brands: Dict[str, BrandCategoryInfo]             # brand_key → info


# ---------------------------------------------------------------------------
# Definição Centralizada — De/Para
# ---------------------------------------------------------------------------
_RAW_CATEGORIES: List[dict] = [
    # ── Roupas ──────────────────────────────────────────────────────────
    {
        "slug": "camisas",
        "label": "Camisas",
        "group": "Roupas",
        "brands": {
            "aramis":  {"path": "/roupas/camisas",                "vtex_fq": "C:/480/507/"},
            "reserva": {"path": "/reserva/masculino/camisas",     "vtex_fq": "C:/1/101/10103/"},
            "tommy":   {"path": "/roupas/camisas",                "vtex_fq": "C:/1/5/"},
        },
    },
    {
        "slug": "polos",
        "label": "Polos",
        "group": "Roupas",
        "brands": {
            "aramis":  {"path": "/roupas/polos",                  "vtex_fq": "C:/480/523/"},
            "reserva": {"path": "/reserva/masculino/polos",       "vtex_fq": "C:/1/101/10113/"},
            "tommy":   {"path": "/roupas/polos",                  "vtex_fq": "C:/1/18/"},
        },
    },
    {
        "slug": "camisetas",
        "label": "Camisetas",
        "group": "Roupas",
        "brands": {
            "aramis":  {"path": "/roupas/camisetas",              "vtex_fq": "C:/480/510/"},
            "reserva": {"path": "/reserva/masculino/camisetas",   "vtex_fq": "C:/1/101/10104/"},
            "tommy":   {"path": "/roupas/camisetas",              "vtex_fq": "C:/1/19/"},
        },
    },
    {
        "slug": "calcas",
        "label": "Calças",
        "group": "Roupas",
        "brands": {
            "aramis":  {"path": "/roupas/calcas",                 "vtex_fq": "C:/480/501/"},
            "reserva": {"path": "/reserva/masculino/calcas",      "vtex_fq": "C:/1/101/10102/"},
            "tommy":   {"path": "/roupas/calcas",                 "vtex_fq": "C:/1/4/"},
        },
    },
    {
        "slug": "bermudas",
        "label": "Bermudas & Shorts",
        "group": "Roupas",
        "brands": {
            "aramis":  {"path": "/roupas/bermudas-e-shorts",      "vtex_fq": "C:/480/491/"},
            "reserva": {"path": "/reserva/masculino/bermudas-e-shorts", "vtex_fq": "C:/1/101/10101/"},
            "tommy":   {"path": "/roupas/bermudas",               "vtex_fq": "C:/1/10/"},
        },
    },
    {
        "slug": "jaquetas",
        "label": "Jaquetas & Casacos",
        "group": "Roupas",
        "brands": {
            "aramis":  {"path": "/roupas/jaquetas",               "vtex_fq": "C:/480/514/"},
            "reserva": {"path": "/reserva/masculino/jaquetas-e-casacos", "vtex_fq": "C:/1/101/10105/"},
            "tommy":   {"path": "/roupas/jaquetas",               "vtex_fq": "C:/1/6/"},
        },
    },
    # ── Segmentos Especiais ─────────────────────────────────────────────
    {
        "slug": "infantil",
        "label": "Infantil",
        "group": "Segmentos",
        "brands": {
            "aramis":  {"path": "/infantil",                      "vtex_fq": "C:/582/"},
            "reserva": {"path": "/mini/infantil",                 "vtex_fq": "C:/2/201/"},
            "tommy":   {"path": "/infantil",                      "vtex_fq": "B:2000003"},
        },
    },
]


# ---------------------------------------------------------------------------
# Índice para acesso rápido
# ---------------------------------------------------------------------------
_CATEGORY_INDEX: Dict[str, CanonicalCategory] = {}

for _raw in _RAW_CATEGORIES:
    _brands_map = {
        bk: BrandCategoryInfo(path=bv["path"], vtex_fq=bv["vtex_fq"])
        for bk, bv in _raw["brands"].items()
    }
    _cat = CanonicalCategory(
        slug=_raw["slug"],
        label=_raw["label"],
        group=_raw["group"],
        brands=_brands_map,
    )
    _CATEGORY_INDEX[_cat.slug] = _cat


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_canonical_categories() -> List[dict]:
    """
    Retorna todas as categorias canônicas agrupadas, pronto para o frontend.

    Returns:
        [
            {
                "group": "Roupas",
                "categories": [
                    {
                        "slug": "camisas",
                        "label": "Camisas",
                        "available_brands": ["aramis", "reserva", "tommy"]
                    },
                    ...
                ]
            }
        ]
    """
    groups: Dict[str, list] = {}
    for cat in _CATEGORY_INDEX.values():
        if cat.group not in groups:
            groups[cat.group] = []
        groups[cat.group].append({
            "slug": cat.slug,
            "label": cat.label,
            "available_brands": list(cat.brands.keys()),
        })

    return [
        {"group": group_name, "categories": items}
        for group_name, items in groups.items()
    ]


def resolve_category_for_brands(
    category_slug: str,
    brand_keys: List[str],
) -> Dict[str, dict]:
    """
    Dado um slug canônico e lista de marcas, retorna o mapeamento de/para.

    Returns:
        {
            "aramis": {"url": "https://www.aramis.com.br/roupas/camisas", "path": "/roupas/camisas"},
            "reserva": {"url": "https://www.usereserva.com/reserva/masculino/camisas", "path": "/reserva/masculino/camisas"},
        }

    Raises:
        ValueError: se o slug não existir ou se uma marca não tiver a categoria.
    """
    cat = _CATEGORY_INDEX.get(category_slug)
    if not cat:
        available = [c.slug for c in _CATEGORY_INDEX.values()]
        raise ValueError(
            f"Categoria '{category_slug}' não encontrada. "
            f"Categorias disponíveis: {available}"
        )

    result: Dict[str, dict] = {}
    missing_brands: List[str] = []

    for bk in brand_keys:
        bk_lower = bk.lower()
        brand_info = cat.brands.get(bk_lower)
        if not brand_info:
            missing_brands.append(bk)
            continue

        registry = BRAND_REGISTRY.get(bk_lower, {})
        base_url = registry.get("base_url", "")

        result[bk_lower] = {
            "url": f"{base_url}{brand_info.path}",
            "path": brand_info.path,
            "label": cat.label,
        }

    if missing_brands:
        raise ValueError(
            f"Categoria '{category_slug}' não disponível para: {missing_brands}"
        )

    return result


def get_category_preview(
    category_slug: str,
    brand_keys: List[str],
) -> Optional[dict]:
    """
    Retorna preview do mapeamento de/para para o frontend mostrar antes de iniciar.

    Returns:
        {
            "category": "Camisas",
            "slug": "camisas",
            "mappings": [
                {"brand": "aramis", "brand_name": "Aramis", "url": "https://..."},
                {"brand": "reserva", "brand_name": "Reserva", "url": "https://..."},
            ]
        }
    """
    cat = _CATEGORY_INDEX.get(category_slug)
    if not cat:
        return None

    mappings = []
    for bk in brand_keys:
        bk_lower = bk.lower()
        brand_info = cat.brands.get(bk_lower)
        if not brand_info:
            continue

        registry = BRAND_REGISTRY.get(bk_lower, {})
        base_url = registry.get("base_url", "")
        brand_name = registry.get("name", bk)

        mappings.append({
            "brand": bk_lower,
            "brand_name": brand_name,
            "path": brand_info.path,
            "url": f"{base_url}{brand_info.path}",
        })

    return {
        "category": cat.label,
        "slug": cat.slug,
        "mappings": mappings,
    }
