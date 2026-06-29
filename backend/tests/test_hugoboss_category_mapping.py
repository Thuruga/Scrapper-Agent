"""
Testes herméticos para o de/para da Hugo Boss (Phase 39, COMP-06-b / COMP-06-c).

Zero I/O de arquivo, zero rede.
Injeta mappings em memória via BrandManagerService.__new__ e
monkeypatcha brand_service no módulo category_mapping.
"""
import asyncio
import unittest.mock

import services.category_mapping as category_mapping_module
from services.brand_service import BrandManagerService
from services.category_mapping import get_canonical_categories, resolve_category_for_brands
from core.models import CategoryMapping, DynamicBrand


# ---------------------------------------------------------------------------
# Factory — constrói BrandManagerService em memória sem I/O
# ---------------------------------------------------------------------------

def _make_hugoboss_service(mappings=None) -> BrandManagerService:
    """Retorna BrandManagerService com a Hugo Boss em memória (sem arquivo, sem rede).

    Espelha o padrão de _make_service_with_vtex_brand de
    test_vtex_brand_onboarding_contract.py (linhas 36–64).
    """
    svc = BrandManagerService.__new__(BrandManagerService)
    svc.brands = {}
    svc.last_modified = 0
    svc.updated_event = asyncio.Event()
    svc._check_reload = unittest.mock.MagicMock()

    svc.brands["hugoboss"] = DynamicBrand(
        brand_key="hugoboss",
        brand_name="Hugo Boss",
        domain="www.hugoboss.com.br",
        engine="vtex",
        is_active=True,
        mappings=mappings or [],
    )
    return svc


# ---------------------------------------------------------------------------
# TestHugoBossCategoryMapping — COMP-06-b e COMP-06-c
# ---------------------------------------------------------------------------

class TestHugoBossCategoryMapping:
    """Contrato COMP-06-b / COMP-06-c: mapeamento de categoria via mappings dinâmicos."""

    def test_resolve_category_returns_valid_url_hugoboss(self):
        """COMP-06-b: resolve_category_for_brands retorna URL válida para a Hugo Boss.

        Com vtex_fq_path="/masculino/roupas/camisas" injetado em memória,
        a URL montada deve começar com "https://www.hugoboss.com.br/" e
        terminar com "/masculino/roupas/camisas".
        """
        mappings = [
            CategoryMapping(
                canonical_slug="camisas",
                vtex_fq_path="/masculino/roupas/camisas",
                label="Camisas",
            ),
        ]
        svc = _make_hugoboss_service(mappings=mappings)

        with unittest.mock.patch.object(category_mapping_module, "brand_service", svc):
            result = resolve_category_for_brands("camisas", ["hugoboss"])

        assert "hugoboss" in result, (
            f"'hugoboss' não encontrada no resultado. Resultado: {result}"
        )
        url = result["hugoboss"]["url"]
        assert url.startswith("https://www.hugoboss.com.br/"), (
            f"URL deve começar com 'https://www.hugoboss.com.br/', obtido: '{url}'"
        )
        assert url.endswith("/masculino/roupas/camisas"), (
            f"URL deve terminar com '/masculino/roupas/camisas', obtido: '{url}'"
        )

    def test_get_canonical_categories_includes_hugoboss(self):
        """COMP-06-c: get_canonical_categories inclui 'hugoboss' em available_brands.

        Com um mapping de "camisas" injetado, hugoboss deve aparecer na lista
        de available_brands da categoria correspondente.
        """
        mappings = [
            CategoryMapping(
                canonical_slug="camisas",
                vtex_fq_path="/masculino/roupas/camisas",
                label="Camisas",
            ),
        ]
        svc = _make_hugoboss_service(mappings=mappings)

        with unittest.mock.patch.object(category_mapping_module, "brand_service", svc):
            result = get_canonical_categories()

        all_brands = [
            b
            for group in result
            for cat in group["categories"]
            for b in cat["available_brands"]
        ]
        assert "hugoboss" in all_brands, (
            f"'hugoboss' não encontrada em available_brands. Marcas encontradas: {all_brands}"
        )
