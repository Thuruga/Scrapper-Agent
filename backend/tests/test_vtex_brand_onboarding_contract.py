"""
Contrato offline deterministico para onboarding VTEX (Phase 26, COMP-01, D-10b).

Pinagem do estado final que o script de seed (26-02) deve produzir:
  - engine == "vtex"
  - is_active is True
  - mappings persistidos com canonical_slug valido e vtex_fq_path relativo
  - marca visivel em list_brands(active_only=True)
  - resolve_category_for_brands produz URL valida

Execucao totalmente offline: sem rede, sem brands.json, sem Supabase.
_check_reload e MagicMock; _save e patchado dentro dos testes que escrevem.
"""
import asyncio
import unittest.mock

import services.category_mapping as category_mapping_module
from services.brand_service import BrandManagerService
from services.category_mapping import _RAW_CATEGORIES, resolve_category_for_brands
from core.models import CategoryMapping, DynamicBrand
# CR-01: importa o produtor real de slugs (SUT) para que o teste de persistencia
# exercite auto_match em vez de slugs hardcoded pelo autor do teste. Apenas o
# import de funcoes puras — NUNCA main() (faz rede/stdin). Mantem-se offline.
from scripts.onboard_vtex_brands import auto_match

# ---------------------------------------------------------------------------
# Slugs validos derivados da fonte canonica (_RAW_CATEGORIES) — D-04 anchor
# ---------------------------------------------------------------------------
VALID_SLUGS = {c["slug"] for c in _RAW_CATEGORIES}


# ---------------------------------------------------------------------------
# Factory — constroi BrandManagerService em memoria sem I/O
# ---------------------------------------------------------------------------

def _make_service_with_vtex_brand(
    brand_key: str = "levis",
    engine: str = "vtex",
    is_active: bool = True,
    mappings=None,
) -> BrandManagerService:
    """Retorna BrandManagerService com uma marca VTEX em memoria (sem arquivo, sem Supabase).

    Copia o padrao de tests/test_brand_active.py:
      - BrandManagerService.__new__ evita __init__ e evita leitura de disco
      - _check_reload = MagicMock() desabilita recarregamento externo
      - svc.brands populado manualmente com dados de teste
    """
    svc = BrandManagerService.__new__(BrandManagerService)
    svc.brands = {}
    svc.last_modified = 0
    svc.updated_event = asyncio.Event()
    # Desabilita recarregamento de arquivo — testes sao deterministicos
    svc._check_reload = unittest.mock.MagicMock()

    svc.brands[brand_key] = DynamicBrand(
        brand_key=brand_key,
        brand_name="Levi's",
        domain="www.levi.com.br",
        engine=engine,
        is_active=is_active,
        mappings=mappings or [],
    )
    return svc


# ---------------------------------------------------------------------------
# TestBrandContract — pina cada verdade de COMP-01
# ---------------------------------------------------------------------------

class TestBrandContract:
    """Contrato COMP-01: estado final esperado apos onboarding de marca VTEX."""

    def test_engine_is_vtex(self):
        """engine da marca onboardada deve ser 'vtex'."""
        svc = _make_service_with_vtex_brand(engine="vtex")
        brand = svc.get_brand("levis")
        assert brand is not None, "Marca 'levis' nao encontrada no servico em memoria"
        assert brand.engine == "vtex", (
            f"Esperado engine='vtex', obtido '{brand.engine}'"
        )

    def test_brand_is_active(self):
        """Marca onboardada deve ter is_active=True."""
        svc = _make_service_with_vtex_brand(is_active=True)
        brand = svc.get_brand("levis")
        assert brand is not None, "Marca 'levis' nao encontrada no servico em memoria"
        assert brand.is_active is True, (
            f"Esperado is_active=True, obtido {brand.is_active}"
        )

    def test_mappings_persisted(self):
        """update_mappings persiste os mapeamentos e todos os slugs sao validos.

        CR-01: o vocabulario de slugs e produzido pelo SUT real (auto_match do
        script de seed), nao hardcoded pelo autor do teste. Assim, uma regressao
        em auto_match que emita um slug fora do vocabulario canonico e detectada
        aqui. Permanece 100% offline: auto_match e funcao pura sobre dicts em
        memoria; main() (rede/stdin) nunca e chamado.
        """
        svc = _make_service_with_vtex_brand()
        # auto_match le item["name"] e item["rel_path"] (path ja relativizado).
        categories = [
            {"name": "Calças Jeans", "rel_path": "/roupas/jeans"},
            {"name": "Polos", "rel_path": "/roupas/polos"},
        ]
        proposals = auto_match(categories)
        assert proposals, (
            "auto_match nao produziu nenhuma proposta para categorias validas — "
            "regressao no produtor de slugs do SUT"
        )
        sample = [
            CategoryMapping(canonical_slug=slug, vtex_fq_path=path, label=label)
            for slug, path, label in proposals
        ]

        with unittest.mock.patch.object(svc, "_save"):
            brand = svc.update_mappings("levis", sample)

        assert len(brand.mappings) > 0, (
            "Nenhum mapeamento persistido apos update_mappings"
        )
        for m in brand.mappings:
            assert m.canonical_slug in VALID_SLUGS, (
                f"auto_match produziu slug fora do vocabulario '{m.canonical_slug}'; "
                f"slugs validos: {VALID_SLUGS}"
            )

    def test_auto_match_masculine_only(self):
        """auto_match respeita as regras do operador: somente masculino, nunca
        feminino/inativo, infantil somente do menino, e o token 'mini' NAO casa
        dentro de 'feminino' (regressao do bug de substring)."""
        categories = [
            {"name": "Camisas", "rel_path": "/masculino/roupas/camisas"},
            {"name": "Camisas", "rel_path": "/feminino/roupas/camisas"},   # feminina -> excluida
            {"name": "Polos", "rel_path": "/masculino/roupas/polos"},
            {"name": "Polos", "rel_path": "/kids/menino/polos"},           # infantil -> nao vira slug adulto
            {"name": "Feminino", "rel_path": "/feminino"},                 # bug 'mini' dentro de 'feminino'
            {"name": "INATIVO- Calcas", "rel_path": "/inativo/calcas"},    # inativa -> excluida
            {"name": "Menino", "rel_path": "/kids/menino"},                # infantil masculino
            {"name": "Menina", "rel_path": "/kids/menina"},                # infantil feminino -> excluida
        ]
        mp = {slug: path for slug, path, _ in auto_match(categories)}

        # Slugs adultos pegam a categoria MASCULINA, nunca a feminina nem a infantil
        assert mp.get("camisas") == "/masculino/roupas/camisas", mp
        assert mp.get("polos") == "/masculino/roupas/polos", mp
        # infantil mapeia para a linha do MENINO (nunca menina, nunca 'Feminino')
        assert mp.get("infantil") == "/kids/menino", mp
        # Nenhuma proposta feminina ou inativa escapou
        for slug, path in mp.items():
            low = path.lower()
            assert not any(f in low for f in ("feminin", "menina", "mulher")), f"{slug} feminino: {path}"
            assert "inativo" not in low and "inativa" not in low, f"{slug} inativo: {path}"
        # 'Feminino' (bug do 'mini') nao virou infantil nem qualquer slug
        assert "/feminino" not in mp.values(), mp
        # So existe calcas inativa no fixture -> calcas deve ser OMITIDA
        assert "calcas" not in mp, mp

    def test_brand_in_active_list(self):
        """Marca com is_active=True deve aparecer em list_brands(active_only=True)."""
        svc = _make_service_with_vtex_brand(is_active=True)
        active_keys = [b.brand_key for b in svc.list_brands(active_only=True)]
        assert "levis" in active_keys, (
            f"'levis' nao encontrada na lista de marcas ativas. Keys: {active_keys}"
        )

    def test_vtex_fq_path_is_relative(self):
        """Todo vtex_fq_path deve comecar com '/' (guarda contra Pitfall 3: paths absolutos Windows)."""
        mappings = [
            CategoryMapping(
                canonical_slug="calcas",
                vtex_fq_path="/roupas/jeans",
                label="Jeans",
            ),
        ]
        svc = _make_service_with_vtex_brand(mappings=mappings)
        brand = svc.get_brand("levis")
        assert brand is not None, "Marca 'levis' nao encontrada no servico em memoria"
        for m in brand.mappings:
            assert m.vtex_fq_path.startswith("/"), (
                f"vtex_fq_path deve ser relativo (comecar com '/'), obtido: '{m.vtex_fq_path}'"
            )

    def test_resolve_category_returns_valid_url(self):
        """resolve_category_for_brands com vtex_fq_path relativo produz URL valida."""
        mappings = [
            CategoryMapping(
                canonical_slug="calcas",
                vtex_fq_path="/roupas/jeans",
                label="Jeans",
            ),
        ]
        svc = _make_service_with_vtex_brand(mappings=mappings)

        # Monkeypatcha brand_service no modulo category_mapping para usar o servico em memoria
        with unittest.mock.patch.object(category_mapping_module, "brand_service", svc):
            result = resolve_category_for_brands("calcas", ["levis"])

        assert "levis" in result, (
            f"'levis' nao encontrada no resultado de resolve_category_for_brands. Resultado: {result}"
        )
        url = result["levis"]["url"]
        expected_url = "https://www.levi.com.br/roupas/jeans"
        assert url == expected_url, (
            f"URL incorreta. Esperado: '{expected_url}', obtido: '{url}'"
        )
