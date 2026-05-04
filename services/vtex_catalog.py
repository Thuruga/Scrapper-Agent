"""
Serviço de Catálogo VTEX Dinâmico.

Busca a árvore de categorias em tempo real via API pública da VTEX,
com cache TTL em memória e fallback estático para resiliência.
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import aiohttp

from config import settings, BRAND_REGISTRY

logger = logging.getLogger("VTEXCatalog")


# ---------------------------------------------------------------------------
# Cache Entry
# ---------------------------------------------------------------------------
@dataclass
class _CacheEntry:
    """Entrada de cache com timestamp de criação."""
    data: List[dict]
    created_at: float = field(default_factory=time.time)

    def is_expired(self, ttl: int) -> bool:
        return (time.time() - self.created_at) > ttl


# ---------------------------------------------------------------------------
# Fallback Estático (Safety Net)
# ---------------------------------------------------------------------------
STATIC_FALLBACK: Dict[str, list] = {
    "aramis": [
        {
            "group": "Novidades",
            "items": [
                {"label": "Novidades (New In)", "path": "/new-in"},
            ],
        },
        {
            "group": "Roupas",
            "items": [
                {"label": "Todas as Roupas",        "path": "/roupas"},
                {"label": "Camisas",                "path": "/roupas/camisas"},
                {"label": "Polos",                  "path": "/roupas/polos"},
                {"label": "Camisetas",              "path": "/roupas/camisetas"},
                {"label": "Calças",                 "path": "/roupas/calcas"},
                {"label": "Bermudas e Shorts",      "path": "/roupas/bermudas-e-shorts"},
            ],
        },
        {
            "group": "Alfaiataria",
            "items": [
                {"label": "Alfaiataria (todas)",    "path": "/roupas/alfaiataria"},
                {"label": "Calças de Alfaiataria",  "path": "/roupas/alfaiataria/calca-alfaiataria"},
                {"label": "Costumes / Ternos",      "path": "/roupas/alfaiataria/costume"},
                {"label": "Paletós / Blazers",      "path": "/roupas/alfaiataria/paleto"},
                {"label": "Gravatas",               "path": "/roupas/alfaiataria/gravata"},
            ],
        },
        {
            "group": "Calçados",
            "items": [
                {"label": "Tênis",                  "path": "/calcados/tenis"},
                {"label": "Sapatos",                "path": "/calcados/sapatos"},
                {"label": "Drive",                  "path": "/calcados/drive"},
                {"label": "Chinelos",               "path": "/calcados/chinelos"},
            ],
        },
        {
            "group": "Acessórios",
            "items": [
                {"label": "Acessórios (todos)",     "path": "/acessorios"},
                {"label": "Cuecas",                 "path": "/acessorios/cuecas"},
                {"label": "Meias",                  "path": "/acessorios/meias"},
                {"label": "Cintos",                 "path": "/acessorios/cintos"},
                {"label": "Bonés",                  "path": "/acessorios/bones"},
                {"label": "Carteiras",              "path": "/acessorios/carteiras"},
                {"label": "Bolsas",                 "path": "/acessorios/bolsas"},
                {"label": "Mochilas",               "path": "/acessorios/mochilas"},
                {"label": "Malas de Bordo",         "path": "/acessorios/malas"},
            ],
        },
        {
            "group": "Outlet",
            "items": [
                {"label": "Outlet (todos)",          "path": "/outlet"},
            ],
        },
    ],
    "reserva": [
        {
            "group": "Masculino — Roupas",
            "items": [
                {"label": "Todas as Roupas Masculinas",  "path": "/reserva/masculino"},
                {"label": "Camisas",                     "path": "/reserva/masculino/camisas"},
                {"label": "Camisetas",                   "path": "/reserva/masculino/camisetas"},
                {"label": "Polos",                       "path": "/reserva/masculino/polos"},
                {"label": "Calças",                      "path": "/reserva/masculino/calcas"},
                {"label": "Bermudas e Shorts",           "path": "/reserva/masculino/bermudas-e-shorts"},
            ],
        },
        {
            "group": "Infantil (Mini)",
            "items": [
                {"label": "Infantil (todos)",            "path": "/mini/infantil"},
            ],
        },
    ],
    "tommy": [
        {
            "group": "Masculino — Roupas",
            "items": [
                {"label": "Todas as Roupas Masculinas",  "path": "/masculino"},
                {"label": "Polos",                       "path": "/roupas/polos"},
                {"label": "Camisetas",                   "path": "/roupas/camisetas"},
                {"label": "Camisas",                     "path": "/roupas/camisas"},
                {"label": "Calças",                      "path": "/roupas/calcas"},
            ],
        },
        {
            "group": "Calçados",
            "items": [
                {"label": "Todos os Calçados",           "path": "/calcados"},
                {"label": "Tênis",                       "path": "/calcados/tenis"},
            ],
        },
    ],
}


# ---------------------------------------------------------------------------
# Filtros para limpar categorias irrelevantes
# ---------------------------------------------------------------------------
BLOCKED_KEYWORDS = [
    "liquida", "gift", "presente", "bazar", "home", "casa", "livro",
    "feminino", "mulher", "menina", "saia", "vestido", "top", "pets",
    "cosmeticos", "cosméticos",
]

BRAND_FILTERS: Dict[str, dict] = {
    "reserva": {
        "require_any": ["/masculino", "/infantil", "/bebe", "/go/", "/mini/"],
    },
}


def _should_keep(url: str, name: str, brand: str) -> bool:
    """Retorna True se a categoria deve ser mantida no catálogo."""
    url_lower = url.lower()
    name_lower = name.lower()

    # Bloqueio universal
    for kw in BLOCKED_KEYWORDS:
        if kw in url_lower or kw in name_lower:
            return False

    # Filtros específicos por marca
    brand_filter = BRAND_FILTERS.get(brand)
    if brand_filter:
        if "require_any" in brand_filter:
            if not any(term in url_lower for term in brand_filter["require_any"]):
                return False
        if "block_any" in brand_filter:
            if any(term in url_lower or term in name_lower for term in brand_filter["block_any"]):
                return False

    return True


# ---------------------------------------------------------------------------
# VTEXCatalogService
# ---------------------------------------------------------------------------
class VTEXCatalogService:
    """
    Serviço que busca e cacheia categorias da VTEX.

    Fluxo:
    1. Verifica cache em memória (TTL configurável)
    2. Se expirado, chama a API VTEX /api/catalog_system/pub/category/tree/3
    3. Transforma a árvore em formato agrupado para o frontend
    4. Se a API falhar, usa o fallback estático
    """

    def __init__(self, cache_ttl: Optional[int] = None):
        self._cache: Dict[str, _CacheEntry] = {}
        self._ttl = cache_ttl or settings.VTEX_CACHE_TTL_SECONDS

    async def get_categories(self, brand: str) -> List[dict]:
        """
        Retorna lista de categorias agrupadas para a marca.

        Returns:
            Lista no formato [{group: str, items: [{label, path}]}]
        """
        brand_key = brand.lower()

        # 1. Verificar cache
        cached = self._cache.get(brand_key)
        if cached and not cached.is_expired(self._ttl):
            logger.info(f"[{brand_key}] Servindo categorias do cache.")
            return cached.data

        # 2. Tentar buscar da API VTEX
        brand_info = BRAND_REGISTRY.get(brand_key)
        if not brand_info:
            logger.warning(f"[{brand_key}] Marca não registrada. Usando fallback.")
            return STATIC_FALLBACK.get(brand_key, [])

        try:
            categories = await self._fetch_and_transform(
                brand_info["domain"], brand_key
            )
            if categories:
                self._cache[brand_key] = _CacheEntry(data=categories)
                logger.info(
                    f"[{brand_key}] {len(categories)} grupos carregados da VTEX API."
                )
                return categories
        except Exception as e:
            logger.error(f"[{brand_key}] Falha na API VTEX: {e}")

        # 3. Fallback: cache antigo ou estático
        if cached:
            logger.warning(f"[{brand_key}] Usando cache expirado como fallback.")
            return cached.data

        logger.warning(f"[{brand_key}] Usando catálogo estático como fallback.")
        return STATIC_FALLBACK.get(brand_key, [])

    async def _fetch_and_transform(
        self, domain: str, brand_key: str
    ) -> List[dict]:
        """Busca árvore da VTEX e transforma no formato do frontend."""
        raw_tree = await self._fetch_from_vtex(domain)
        if not raw_tree:
            return []
        return self._transform_tree(raw_tree, brand_key)

    async def _fetch_from_vtex(self, domain: str) -> list:
        """
        Chama /api/catalog_system/pub/category/tree/3 e retorna o JSON bruto.
        """
        url = f"https://{domain}/api/catalog_system/pub/category/tree/3"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/120.0.0.0"
            ),
            "Accept": "application/json",
        }

        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(
                        f"VTEX API ({domain}): {len(data)} departamentos retornados."
                    )
                    return data
                else:
                    logger.error(
                        f"VTEX API ({domain}): Status {response.status}"
                    )
                    return []

    def _transform_tree(self, raw_tree: list, brand_key: str) -> List[dict]:
        """
        Converte árvore VTEX (hierárquica) → formato plano agrupado:
        [{group: "Departamento", items: [{label: "Cat", path: "/cat"}]}]
        """
        groups: Dict[str, list] = {}

        def walk(nodes: list, department: str = "", parent_name: str = ""):
            for node in nodes:
                name = node.get("name", "")
                url = node.get("url", "")
                has_children = node.get("hasChildren", False)
                children = node.get("children", [])

                dept = department or name

                if has_children and children:
                    walk(children, department=dept, parent_name=name)
                elif url:
                    # Extrair path relativo do URL
                    path = self._extract_path(url)
                    if not path:
                        continue

                    if not _should_keep(path, name, brand_key):
                        continue

                    # Melhoria UX: se o nome final for muito genérico, junta com o do pai
                    label = name
                    if name.lower() in ["coleção", "colecao", "promoção", "promocao", "geral", "todos"]:
                        label = f"{parent_name} ({name})" if parent_name else name

                    if dept not in groups:
                        groups[dept] = []
                    groups[dept].append({"label": label, "path": path})

        walk(raw_tree)

        # Converter dict → list de groups
        return [
            {"group": group_name, "items": items}
            for group_name, items in groups.items()
            if items  # Só inclui grupos com itens
        ]

    @staticmethod
    def _extract_path(url: str) -> str:
        """Extrai o path relativo de uma URL VTEX."""
        if not url:
            return ""
        # Remove protocolo e domínio
        if "://" in url:
            url = url.split("://", 1)[1]
            slash_idx = url.find("/")
            if slash_idx >= 0:
                return url[slash_idx:]
        elif url.startswith("/"):
            return url
        return ""

    def invalidate_cache(self, brand: Optional[str] = None):
        """Invalida o cache de uma marca ou de todas."""
        if brand:
            self._cache.pop(brand.lower(), None)
        else:
            self._cache.clear()


# Instância singleton
vtex_catalog = VTEXCatalogService()
