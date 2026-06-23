"""
Testes RED do contrato HIST-01 — persistencia da busca comparativa (Phase 27, Wave 0).

Cobertura:
  - test_history_service_search_type: round-trip no servico em memoria
  - test_post_search_persists_history: POST /search persiste um registro type='search'
  - test_persisted_results_shape_is_inner_list: resultados armazenados sao a LISTA INTERNA
      (BrandSearchResult[]), NAO o wrapper ComparisonResult (Pitfall 1 / Resolution A)
  - test_search_failure_marks_failed: excecao no engine marca o registro FAILED (Pitfall 5)

Estes testes devem coletar sem erros de importacao e FALHAR (RED) contra o codigo atual
enquanto POST /search nao tiver a persistencia de Wave 1 (27-01). Isso e comportamento
esperado — nao e um defeito.

Padrao de projeto seguido: tests/test_brand_active.py
  - Servico em memoria via SomeService.__new__(...)
  - I/O patchado via patch.object(svc, "_save_history")
  - Singletons de modulo substituidos via try/finally (monkeypatch manual)
  - Rotas chamadas via asyncio.run(route_fn(...))
  - Asserts simples dentro de classes Test*
"""
import asyncio
import unittest.mock
from unittest.mock import AsyncMock, MagicMock

import pytest

import api.routes_search as routes_search
from core.models import BrandSearchResult, SearchProductResult
from services.search_history_service import SearchHistoryService


# ---------------------------------------------------------------------------
# Helper — constroi SearchHistoryService em memoria sem I/O
# ---------------------------------------------------------------------------

def _make_history_service():
    """Retorna SearchHistoryService com dados em memoria (sem arquivo em disco).

    _save_history e patchado como no-op para que os testes nao toquem
    data/search_history.json — espelha o patch de _save em test_brand_active.py.
    """
    svc = SearchHistoryService.__new__(SearchHistoryService)
    svc.history = {}
    svc._save_history = unittest.mock.MagicMock()  # no-op — sem I/O
    return svc


def _make_brand_search_result(brand_key: str = "aramis") -> BrandSearchResult:
    """Constroi um BrandSearchResult canned para o mock do engine."""
    return BrandSearchResult(
        brand_key=brand_key,
        brand_name=brand_key.capitalize(),
        products=[],
        total_found=0,
    )


# ---------------------------------------------------------------------------
# Classe 1 — round-trip unitario no servico
# ---------------------------------------------------------------------------

class TestHistoryServiceSearchType:
    """Exercita create_job / update_job / get_job com type='search'."""

    def test_history_service_search_type(self):
        """create_job(type='search') + update_job round-trip preserva type e status.

        Este e um teste unitario puro — apenas o servico, sem rotas.
        Deve PASSAR mesmo antes de 27-01 porque a implementacao do servico ja existe.
        """
        svc = _make_history_service()
        job_id = "test-job-001"
        canned_results = [{"brand": "aramis", "products": []}]

        svc.create_job(
            job_id=job_id,
            query="polo",
            brands=["aramis"],
            type="search",
        )
        svc.update_job(
            job_id=job_id,
            status="COMPLETED",
            results=canned_results,
        )

        record = svc.get_job(job_id)
        assert record is not None, "get_job deve retornar o registro criado"
        assert record.type == "search", (
            f"Esperado type='search', obtido '{record.type}'"
        )
        assert record.status == "COMPLETED", (
            f"Esperado status='COMPLETED', obtido '{record.status}'"
        )
        assert record.results == canned_results, (
            f"Resultados armazenados nao batem: {record.results}"
        )


# ---------------------------------------------------------------------------
# Classe 2 — testes de integracao (rota + servico)
# ---------------------------------------------------------------------------

class TestSearchHistoryComparative:
    """Testa a persistencia de historico em POST /search (HIST-01).

    Todos os testes nesta classe sao RED enquanto a implementacao de 27-01
    nao existir (POST /search ainda nao cria/atualiza registros de historico).
    """

    def _make_engine_mock(self, brand_results=None, raise_exc=None):
        """Retorna um mock do engine_factory configurado para a rota."""
        if brand_results is None:
            brand_results = [_make_brand_search_result("aramis")]

        mock_factory = MagicMock()
        if raise_exc is not None:
            mock_factory.search_all_brands = AsyncMock(side_effect=raise_exc)
        else:
            mock_factory.search_all_brands = AsyncMock(return_value=brand_results)
        return mock_factory

    def _make_brand_service_mock(self):
        """Retorna um mock do brand_service retornando uma marca ativa."""
        from core.models import DynamicBrand

        fake_brand = DynamicBrand(
            brand_key="aramis",
            brand_name="Aramis",
            domain="www.aramis.com.br",
            engine="vtex",
            is_active=True,
        )
        mock_svc = MagicMock()
        mock_svc.list_brands = MagicMock(return_value=[fake_brand])
        return mock_svc

    def _run_search(self, history_svc, engine_mock, brand_svc_mock):
        """Executa POST /search com os singletons injetados e retorna o resultado."""
        from api.routes_search import SearchRequest

        req = SearchRequest(query="polo", brands=["aramis"])

        original_history = getattr(routes_search, "search_history_service", None)
        original_engine = routes_search.engine_factory
        original_brand_svc = routes_search.brand_service

        routes_search.engine_factory = engine_mock
        routes_search.brand_service = brand_svc_mock
        try:
            # Injeta o servico de historico no modulo de rotas.
            # POST /search usa `search_history_service` como atributo do modulo
            # (importado no topo de routes_search.py apos 27-01); por enquanto
            # preparamos a injecao para que o teste falhe RED de forma clara.
            routes_search.search_history_service = history_svc
            result = asyncio.run(routes_search.search_products(req))
        finally:
            routes_search.engine_factory = original_engine
            routes_search.brand_service = original_brand_svc
            if original_history is None:
                # Atributo nao existia antes (pre-27-01): remove para nao poluir
                if hasattr(routes_search, "search_history_service"):
                    del routes_search.search_history_service
            else:
                routes_search.search_history_service = original_history
        return result

    # ------------------------------------------------------------------
    # Test 2 — POST /search persiste um registro
    # ------------------------------------------------------------------

    def test_post_search_persists_history(self):
        """POST /search deve criar um registro de historico type='search' COMPLETED.

        RED: a rota atual nao tem persistencia → history_svc.history permanece
        vazio apos a chamada. Torna GREEN em 27-01.
        """
        history_svc = _make_history_service()
        engine_mock = self._make_engine_mock()
        brand_svc_mock = self._make_brand_service_mock()

        self._run_search(history_svc, engine_mock, brand_svc_mock)

        assert len(history_svc.history) == 1, (
            f"Esperado 1 registro no historico, obtido {len(history_svc.history)}"
        )
        record = list(history_svc.history.values())[0]
        assert record.type == "search", (
            f"Esperado type='search', obtido '{record.type}'"
        )
        assert record.status == "COMPLETED", (
            f"Esperado status='COMPLETED', obtido '{record.status}'"
        )
        # Pitfall 2: query deve ser o termo bruto, NAO um rotulo composto
        assert record.query == "polo", (
            f"Esperado query='polo' (termo bruto), obtido '{record.query}'"
        )

    # ------------------------------------------------------------------
    # Test 3 — shape do resultado armazenado (Pitfall 1, Resolution A)
    # ------------------------------------------------------------------

    def test_persisted_results_shape_is_inner_list(self):
        """O campo results armazenado deve ser List[BrandSearchResult], NAO o wrapper.

        Resolution A (RESEARCH.md "Stored Result Shape Contract"):
          store ComparisonResult.model_dump(mode='json')['results']
          (a lista interna de BrandSearchResult), NAO o ComparisonResult inteiro.

        Por que importa: SearchPage reabre via
          setResults({ results: res.results, query: res.query, ... })
          (App.tsx:655) — ela espera que res.results JA SEJA a lista interna.
          Se a lista armazenada for o wrapper ComparisonResult (com chave
          'brands_searched'), o reopen renderiza vazio silenciosamente.

        RED: a rota atual nao persiste nada → results == None.
        Torna GREEN em 27-01 quando a rota armazenar a lista correta.
        """
        brand_result = _make_brand_search_result("aramis")
        history_svc = _make_history_service()
        engine_mock = self._make_engine_mock(brand_results=[brand_result])
        brand_svc_mock = self._make_brand_service_mock()

        self._run_search(history_svc, engine_mock, brand_svc_mock)

        assert len(history_svc.history) >= 1, (
            "POST /search nao criou nenhum registro de historico"
        )
        stored = list(history_svc.history.values())[0]

        # O campo results deve ser uma LISTA (a lista interna de BrandSearchResult)
        assert isinstance(stored.results, list), (
            f"stored.results deve ser list (inner BrandSearchResult[]), "
            f"obtido {type(stored.results)}: {stored.results}"
        )

        # Cada elemento deve ter as chaves de BrandSearchResult (brand_key, products)
        if stored.results:
            first = stored.results[0]
            # Suporta dict (apos model_dump) ou objeto Pydantic
            if isinstance(first, dict):
                assert "brand_key" in first, (
                    f"Elemento da lista nao tem 'brand_key': {first}"
                )
            else:
                assert hasattr(first, "brand_key"), (
                    f"Elemento da lista nao tem atributo brand_key: {first}"
                )

        # NEGATIVE ASSERTION: NAO deve ser o wrapper ComparisonResult.
        # Se stored.results fosse o dict ComparisonResult serializado, teria
        # a chave 'brands_searched'. Isso QUEBRARIA o reopen em SearchPage
        # (App.tsx:655) que faz setResults({ results: res.results, ... }).
        assert not (
            isinstance(stored.results, dict) and "brands_searched" in stored.results
        ), (
            "stored.results nao deve ser o wrapper ComparisonResult "
            "(com 'brands_searched'). Armazene apenas a lista interna "
            "ComparisonResult.model_dump(mode='json')['results'] — "
            "veja RESEARCH.md Stored Result Shape Contract / Resolution A."
        )

    # ------------------------------------------------------------------
    # Test 4 — falha no engine marca o registro FAILED (Pitfall 5)
    # ------------------------------------------------------------------

    def test_search_failure_marks_failed(self):
        """Excecao no engine deve marcar o registro FAILED com error preenchido.

        Pitfall 5 (RESEARCH.md): sem try/except na rota, qualquer excecao do
        engine_factory.search_all_brands propaga sem atualizar o registro para FAILED.
        Isso resulta em entradas PENDING permanentes no historico.

        O teste espera que:
          1. A rota re-raise a excecao (pytest.raises(RuntimeError)).
          2. O registro no historico tenha status='FAILED' e error contendo 'boom'.

        RED: a rota atual nao tem try/except nem persistencia → o registro nem
        chega a ser criado. Torna GREEN em 27-01.
        """
        history_svc = _make_history_service()
        engine_mock = self._make_engine_mock(raise_exc=RuntimeError("boom"))
        brand_svc_mock = self._make_brand_service_mock()

        with pytest.raises(RuntimeError):
            self._run_search(history_svc, engine_mock, brand_svc_mock)

        # Deve existir exatamente um registro no historico
        assert len(history_svc.history) == 1, (
            f"Esperado 1 registro FAILED no historico, obtido {len(history_svc.history)}"
        )
        record = list(history_svc.history.values())[0]
        assert record.status == "FAILED", (
            f"Esperado status='FAILED', obtido '{record.status}'"
        )
        assert record.error is not None and "boom" in record.error, (
            f"Campo error deve conter 'boom', obtido: '{record.error}'"
        )
