"""
Testes RED de gestao de ativacao de marca (Phase 25, Wave 0 — MGMT-01).

Cobertura:
  - TestListBrandsActiveOnly: exercita list_brands com active_only
      1. default (sem args) retorna todas as marcas
      2. active_only=True exclui marcas inativas   (RED: list_brands nao tem este param)
      3. active_only=False retorna todas as marcas
  - TestSetActive: exercita o novo metodo set_active
      4. deactivate: set_active(key, False) → is_active=False  (RED: nao existe ainda)
      5. reactivate: set_active(key, True) → is_active=True    (RED: nao existe ainda)
      6. key invalida: set_active(nonexistent, True) → None    (RED: nao existe ainda)
  - TestBrandRouteReturnsInactive: integracao SC-4
      7. GET /brands/ retorna marca inativa (active_only=False por padrao)
         (pode passar hoje — guarda contra regressao futura)
  - TestMarketplacesInBrandsJson: Phase 40 Plan 04 (UX-05 / D-10)
      8. Os 3 marketplaces (mercado_livre, netshoes, amazon) estao em brands.json
         com is_active=True e engine correto — proves that GET /brands/ returns them
         from the file, not from runtime injection (which was removed in Plan 02).

Estes testes devem coletar sem erros de importacao e FALHAR (RED) contra o
codigo atual enquanto as implementacoes de Wave 2 nao existirem.
"""
import asyncio
import unittest.mock

from services.brand_service import BrandManagerService
from core.models import DynamicBrand

# ---------------------------------------------------------------------------
# Helper — constroi servico em memoria sem I/O (padrao do projeto)
# ---------------------------------------------------------------------------

def _make_service_with_brands():
    """Retorna BrandManagerService com dados em memoria (sem arquivo, sem Supabase).

    _check_reload e patchado como no-op para que list_brands nao recarregue
    o arquivo brands.json real e sobrescreva os dados de teste.
    """
    svc = BrandManagerService.__new__(BrandManagerService)
    svc.brands = {}
    svc.last_modified = 0
    svc.updated_event = asyncio.Event()
    # Desabilita recarregamento de arquivo — testes sao deterministicos
    svc._check_reload = unittest.mock.MagicMock()
    # Duas marcas: uma ativa (vtex), uma inativa (unknown)
    svc.brands["active_brand"] = DynamicBrand(
        brand_key="active_brand",
        brand_name="Active",
        domain="active.com",
        engine="vtex",
        is_active=True,
    )
    svc.brands["inactive_brand"] = DynamicBrand(
        brand_key="inactive_brand",
        brand_name="Inactive",
        domain="inactive.com",
        engine="unknown",
        is_active=False,
    )
    return svc


# ---------------------------------------------------------------------------
# TestListBrandsActiveOnly — list_brands(active_only)
# ---------------------------------------------------------------------------

class TestListBrandsActiveOnly:
    """Testa filtragem de marcas ativas via active_only.

    Tests 2 e 3 sao RED enquanto list_brands nao tiver o parametro active_only.
    """

    def test_default_returns_all_brands(self):
        """list_brands() sem argumento retorna todas as marcas (ativa + inativa)."""
        svc = _make_service_with_brands()
        result = svc.list_brands()
        assert len(result) == 2, (
            f"Expected 2 brands, got {len(result)}"
        )

    def test_active_only_excludes_inactive(self):
        """list_brands(active_only=True) retorna apenas marcas ativas.

        RED: list_brands atual nao tem parametro active_only → TypeError.
        Esta falha e esperada ate a implementacao de Wave 2 (D-07, MGMT-01).
        """
        svc = _make_service_with_brands()
        result = svc.list_brands(active_only=True)
        assert len(result) == 1, (
            f"Expected 1 active brand, got {len(result)}"
        )
        assert result[0].brand_key == "active_brand", (
            f"Expected 'active_brand', got '{result[0].brand_key}'"
        )

    def test_active_only_false_returns_all(self):
        """list_brands(active_only=False) retorna todas as marcas (equivalente ao default).

        RED: list_brands atual nao tem parametro active_only → TypeError.
        Esta falha e esperada ate a implementacao de Wave 2 (D-07).
        """
        svc = _make_service_with_brands()
        result = svc.list_brands(active_only=False)
        assert len(result) == 2, (
            f"Expected 2 brands with active_only=False, got {len(result)}"
        )


# ---------------------------------------------------------------------------
# TestSetActive — set_active() nao existe ainda
# ---------------------------------------------------------------------------

class TestSetActive:
    """Testa o metodo set_active de BrandManagerService.

    Todos os testes sao RED enquanto set_active nao for implementado (Wave 2).
    _save e mockado para evitar I/O real nos testes unitarios.
    """

    def test_deactivate_brand(self):
        """set_active('active_brand', False) seta is_active=False e persiste.

        RED: set_active nao existe → AttributeError.
        """
        svc = _make_service_with_brands()
        with unittest.mock.patch.object(svc, "_save"):
            result = svc.set_active("active_brand", False)
        assert result is not None, "set_active deve retornar a marca atualizada"
        assert result.is_active is False, (
            f"Expected is_active=False, got {result.is_active}"
        )
        assert svc.brands["active_brand"].is_active is False, (
            "Mutacao in-place deve refletir no dict de marcas"
        )

    def test_reactivate_brand(self):
        """set_active('inactive_brand', True) seta is_active=True e persiste.

        RED: set_active nao existe → AttributeError.
        """
        svc = _make_service_with_brands()
        with unittest.mock.patch.object(svc, "_save"):
            result = svc.set_active("inactive_brand", True)
        assert result is not None, "set_active deve retornar a marca atualizada"
        assert result.is_active is True, (
            f"Expected is_active=True, got {result.is_active}"
        )

    def test_set_active_unknown_key_returns_none(self):
        """set_active com chave inexistente retorna None (sem corrupcao de dados).

        Comportamento de seguranca: chave arbitraria nao corrompem o dict.
        Ref.: RESEARCH §Security Domain Tampering threat.
        RED: set_active nao existe → AttributeError.
        """
        svc = _make_service_with_brands()
        result = svc.set_active("nonexistent", True)
        assert result is None, (
            f"Expected None for unknown brand_key, got {result}"
        )


# ---------------------------------------------------------------------------
# TestBrandRouteReturnsInactive — integracao SC-4 / D-08
# ---------------------------------------------------------------------------

class TestMarketplacesInBrandsJson:
    """Phase 40 Plan 04: marketplaces as real brands.json entries (UX-05 / D-10).

    Verifica que os 3 marketplaces (mercado_livre, netshoes, amazon) existem em
    brands.json como entradas reais com is_active=True e engine correto.

    Usa brand_service real (lê brands.json) — confirma que GET /brands/ os retornaria
    via arquivo, sem runtime injection (removida em Plan 02).
    """

    _EXPECTED = {
        "mercado_livre": "mercadolivre",
        "netshoes":      "netshoes",
        "amazon":        "amazon",
    }

    def test_marketplaces_in_brands_json(self):
        """Os 3 marketplace brand_keys estao em brands.json com is_active=True e engine correto."""
        from services.brand_service import brand_service

        all_brands = brand_service.list_brands()
        brands_by_key = {b.brand_key: b for b in all_brands}

        for brand_key, expected_engine in self._EXPECTED.items():
            assert brand_key in brands_by_key, (
                f"'{brand_key}' nao encontrado em brands.json. "
                f"Keys presentes: {sorted(brands_by_key.keys())}"
            )
            brand = brands_by_key[brand_key]
            assert brand.is_active is True, (
                f"'{brand_key}' deve ter is_active=True, got {brand.is_active}"
            )
            assert brand.engine == expected_engine, (
                f"'{brand_key}' deve ter engine='{expected_engine}', got '{brand.engine}'"
            )

    def test_marketplaces_returned_by_active_only_filter(self):
        """Os marketplaces aparecem em list_brands(active_only=True) (entradas ativas no arquivo)."""
        from services.brand_service import brand_service

        active_brands = brand_service.list_brands(active_only=True)
        active_keys = {b.brand_key for b in active_brands}

        for brand_key in self._EXPECTED:
            assert brand_key in active_keys, (
                f"'{brand_key}' deveria aparecer em list_brands(active_only=True). "
                f"Keys ativas: {sorted(active_keys)}"
            )

    def test_no_runtime_injection_in_list_brands_route(self):
        """GET /brands/ retorna os marketplaces do arquivo (sem brands.append na rota).

        Confirma que routes_brands.list_brands() nao tem logica de injecao —
        apenas delega para brand_service.list_brands(). Se routes_brands.py contiver
        'brands.append', este teste sinaliza a regressao.
        """
        import inspect
        import api.routes_brands as routes_brands_module

        source = inspect.getsource(routes_brands_module.list_brands)
        assert "brands.append" not in source, (
            "list_brands() nao deve conter 'brands.append' — marketplaces devem vir de brands.json"
        )


class TestBrandRouteReturnsInactive:
    """Guarda contra Pitfall-6 (MGMT-01 SC-4 / D-08).

    Verifica que GET /brands/ retorna marcas inativas, ou seja, a rota chama
    list_brands() com active_only=False (o default). Se o default for mudado
    para True (regressao), este teste falha.

    Implementacao: chama a funcao de rota diretamente com brand_service
    mockado contendo uma marca inativa, e verifica que ela aparece no resultado.

    Hoje este teste DEVE PASSAR (a rota nao filtra) — e o guarda para que nao
    se torne RED quando a implementacao de Wave 2 chegar.
    """

    def test_route_includes_inactive_brand(self):
        """GET /brands/ retorna marca com is_active=False.

        Estrategia: injeta brand_service mockado na funcao de rota e chama
        via asyncio.run. Verifica que a marca inativa esta presente no resultado.
        """
        import api.routes_brands as routes_brands_module

        # Servico em memoria com uma marca inativa
        fake_svc = _make_service_with_brands()

        # Injeta no modulo de rotas temporariamente
        original_service = routes_brands_module.brand_service
        routes_brands_module.brand_service = fake_svc
        try:
            # Chama a funcao de rota diretamente (e async)
            result = asyncio.run(routes_brands_module.list_brands())
        finally:
            routes_brands_module.brand_service = original_service

        # Marca inativa deve estar presente (GET /brands/ nao filtra por active)
        brand_keys = [b.brand_key for b in result]
        assert "inactive_brand" in brand_keys, (
            f"GET /brands/ deve incluir marcas inativas (active_only=False por padrao). "
            f"Keys encontradas: {brand_keys}"
        )
