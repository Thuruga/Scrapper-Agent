"""
Teste hermético de scan VTEX para a Hugo Boss (Phase 39, COMP-06-d).

Zero I/O de arquivo, zero rede.
Mocka VtexApiClient.search para retornar BrandSearchResult pré-construído
sem bater no endpoint VTEX real.

WR-01: VTEXEngine.search chama SessionManager.get_session() ANTES de
VtexApiClient.search — sem mockar get_session, um aiohttp.ClientSession real
seria alocado e nunca fechado (contradizendo o "zero rede" acima). Mocka
também SessionManager.get_session para retornar um MagicMock em vez de uma
sessão real.
"""
import asyncio
import unittest.mock

from services.engines.vtex_engine import VTEXEngine
from services.vtex_api_scraper import VtexApiClient
from core.session_manager import SessionManager
from core.models import BrandSearchResult, SearchProductResult


# ---------------------------------------------------------------------------
# TestHugoBossVtexScan — COMP-06-d
# ---------------------------------------------------------------------------

class TestHugoBossVtexScan:
    """Contrato COMP-06-d: VTEXEngine.search retorna BrandSearchResult válido (mock)."""

    def test_vtex_scan_returns_valid_schema(self):
        """COMP-06-d: scan da Hugo Boss retorna SearchProductResult com schema canônico.

        VtexApiClient.search é mockado para retornar BrandSearchResult pré-construído
        sem acesso à rede. Verifica brand, url e price_full de cada produto.
        """
        mock_product = SearchProductResult(
            brand="hugoboss",
            product_name="Camisa Social Hugo Boss",
            url="https://www.hugoboss.com.br/masculino/roupas/camisas/produto-teste",
            price_full=599.0,
        )
        mock_result = BrandSearchResult(
            brand_key="hugoboss",
            brand_name="Hugo Boss",
            products=[mock_product],
            total_found=1,
        )

        mock_session = unittest.mock.MagicMock()

        with unittest.mock.patch.object(
            SessionManager,
            "get_session",
            new=unittest.mock.AsyncMock(return_value=mock_session),
        ), unittest.mock.patch.object(
            VtexApiClient,
            "search",
            new=unittest.mock.AsyncMock(return_value=mock_result),
        ):
            engine = VTEXEngine("hugoboss")
            result = asyncio.run(engine.search("camisa", max_results=3))

        assert isinstance(result, BrandSearchResult), (
            f"Esperado BrandSearchResult, obtido {type(result)}"
        )
        assert len(result.products) >= 1, (
            f"Esperado >= 1 produto, obtido {len(result.products)}"
        )
        for p in result.products:
            assert p.brand == "hugoboss", (
                f"brand deve ser 'hugoboss', obtido '{p.brand}'"
            )
            assert p.url.startswith("https://www.hugoboss.com.br/"), (
                f"url deve começar com 'https://www.hugoboss.com.br/', obtido '{p.url}'"
            )
            assert p.price_full is not None and p.price_full > 0, (
                f"price_full deve ser > 0, obtido {p.price_full}"
            )
