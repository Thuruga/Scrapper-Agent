from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import app
from core.models import BrandSearchResult, SearchProductResult
from services.product_contract import CANONICAL_PRODUCT_COLUMNS


@pytest.fixture(autouse=True)
def isolate_map_rules(monkeypatch):
    import api.routes_search as routes_search

    monkeypatch.setattr(
        routes_search.map_rules_service,
        "list_rules",
        lambda active_only=True: [],
    )


def test_search_export_uses_only_canonical_columns(monkeypatch):
    import api.routes_search as routes_search

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        routes_search.brand_service,
        "list_brands",
        lambda active_only=True: [SimpleNamespace(brand_key="aramis")],
    )

    async def fake_search_all_brands(**kwargs):
        return [
            BrandSearchResult(
                brand_key="aramis",
                brand_name="Aramis",
                products=[
                    SearchProductResult(
                        brand="Aramis",
                        product_name="Camisa Linho",
                        url="https://www.aramis.com.br/p/camisa-linho",
                        price_full=199.9,
                    )
                ],
            )
        ]

    class _FakeEngine:
        async def get_product_details(self, product_url: str):
            return {
                "brand": "Aramis",
                "url": product_url,
                "raw_title": "Camisa Linho",
                "raw_description": "Camisa em linho leve.",
                "price_full": 199.9,
                "available_colors": ["Azul"],
                "available_sizes": ["M"],
                "specifications": {
                    "Composicao": "100% Linho",
                    "Referencia": "REF-123",
                },
            }

    class _FakeExcelWriter:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_to_excel(self, *args, **kwargs):
        captured["columns"] = self.columns.tolist()
        captured["row"] = self.iloc[0].to_dict() if len(self.index) else {}

    monkeypatch.setattr(routes_search.engine_factory, "search_all_brands", fake_search_all_brands)
    monkeypatch.setattr(routes_search.engine_factory, "get_engine", lambda brand_key: _FakeEngine())
    monkeypatch.setattr(routes_search.pd, "ExcelWriter", _FakeExcelWriter)
    monkeypatch.setattr(routes_search.pd.DataFrame, "to_excel", fake_to_excel)

    response = TestClient(app).post(
        "/search/export",
        headers={"X-API-Key": "dev-api-key"},
        json={
            "query": "camisa",
            "max_per_brand": 5,
            "only_in_stock": False,
            "include_shipping": False,
        },
    )

    assert response.status_code == 200
    assert captured["columns"] == CANONICAL_PRODUCT_COLUMNS
    assert captured["row"]["product_name"] == "Camisa Linho"
    assert captured["row"]["product_code"] == "REF-123"


def test_search_export_preserves_sparse_rows_with_only_canonical_columns(monkeypatch):
    import api.routes_search as routes_search

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        routes_search.brand_service,
        "list_brands",
        lambda active_only=True: [
            SimpleNamespace(brand_key="amazon"),
            SimpleNamespace(brand_key="richards"),
        ],
    )

    async def fake_search_all_brands(**kwargs):
        return [
            BrandSearchResult(
                brand_key="amazon",
                brand_name="Amazon",
                products=[
                    SearchProductResult(
                        brand="Amazon",
                        product_name="Tenis Runner",
                        url="https://www.amazon.com.br/dp/B0EXAMPLE1",
                        price_full=249.0,
                        available=True,
                    )
                ],
            ),
            BrandSearchResult(
                brand_key="richards",
                brand_name="Richards",
                products=[
                    SearchProductResult(
                        brand="Richards",
                        product_name="Camisa Slim",
                        url="https://www.richards.com.br/produto/camisa-slim-123",
                        price_full=799.0,
                        available=False,
                    )
                ],
            ),
        ]

    class _AmazonEngine:
        async def get_product_details(self, product_url: str):
            return {"seller": "Loja Oficial Amazon"}

    class _WakeLikeEngine:
        async def get_product_details(self, product_url: str):
            return None

    class _FakeExcelWriter:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_to_excel(self, *args, **kwargs):
        captured["columns"] = self.columns.tolist()
        captured["rows"] = self.to_dict("records")

    monkeypatch.setattr(routes_search.engine_factory, "search_all_brands", fake_search_all_brands)
    monkeypatch.setattr(
        routes_search.engine_factory,
        "get_engine",
        lambda brand_key: _AmazonEngine() if brand_key == "amazon" else _WakeLikeEngine(),
    )
    monkeypatch.setattr(routes_search.pd, "ExcelWriter", _FakeExcelWriter)
    monkeypatch.setattr(routes_search.pd.DataFrame, "to_excel", fake_to_excel)

    response = TestClient(app).post(
        "/search/export",
        headers={"X-API-Key": "dev-api-key"},
        json={
            "query": "camisa",
            "max_per_brand": 5,
            "only_in_stock": False,
            "include_shipping": False,
        },
    )

    assert response.status_code == 200
    assert captured["columns"] == CANONICAL_PRODUCT_COLUMNS

    rows = captured["rows"]
    assert isinstance(rows, list)
    assert len(rows) == 2

    rows_by_brand = {row["brand"]: row for row in rows}
    assert rows_by_brand["Amazon"]["url"] == "https://www.amazon.com.br/dp/B0EXAMPLE1"
    assert rows_by_brand["Amazon"]["product_name"] == "Tenis Runner"
    assert rows_by_brand["Amazon"]["price_full"] == 249.0

    assert rows_by_brand["Richards"]["url"] == "https://www.richards.com.br/produto/camisa-slim-123"
    assert rows_by_brand["Richards"]["product_name"] == "Camisa Slim"
    assert rows_by_brand["Richards"]["price_full"] == 799.0


def test_search_export_normalizes_vtex_delta_prices(monkeypatch):
    import api.routes_search as routes_search

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        routes_search.brand_service,
        "list_brands",
        lambda active_only=True: [SimpleNamespace(brand_key="aramis")],
    )

    async def fake_search_all_brands(**kwargs):
        return [
            BrandSearchResult(
                brand_key="aramis",
                brand_name="Aramis",
                products=[
                    SearchProductResult(
                        brand="Aramis",
                        product_name="Camisa Polo",
                        url="https://www.aramis.com.br/p/camisa-polo",
                        price_full=199.9,
                        price_discount=100.0,
                        price_discount_is_delta=True,
                    )
                ],
            )
        ]

    class _WakeLikeEngine:
        async def get_product_details(self, product_url: str):
            return None

    class _FakeExcelWriter:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_to_excel(self, *args, **kwargs):
        captured["columns"] = self.columns.tolist()
        captured["row"] = self.iloc[0].to_dict() if len(self.index) else {}

    monkeypatch.setattr(routes_search.engine_factory, "search_all_brands", fake_search_all_brands)
    monkeypatch.setattr(routes_search.engine_factory, "get_engine", lambda brand_key: _WakeLikeEngine())
    monkeypatch.setattr(routes_search.pd, "ExcelWriter", _FakeExcelWriter)
    monkeypatch.setattr(routes_search.pd.DataFrame, "to_excel", fake_to_excel)

    response = TestClient(app).post(
        "/search/export",
        headers={"X-API-Key": "dev-api-key"},
        json={
            "query": "camisa",
            "max_per_brand": 5,
            "only_in_stock": False,
            "include_shipping": False,
        },
    )

    assert response.status_code == 200
    assert captured["columns"] == CANONICAL_PRODUCT_COLUMNS
    assert captured["row"]["price_full"] == 299.9
    assert captured["row"]["price_discount"] == 199.9


def test_single_brand_category_export_uses_same_columns(monkeypatch):
    import services.orchestrator as orchestrator
    from services.engines import factory

    captured: dict[str, object] = {}

    class _FakeCategoryEngine:
        async def run_bulk_scrape(self, category_url, log_callback=None, cancel_event=None):
            yield {
                "brand": "Aramis",
                "url": "https://www.aramis.com.br/p/camisa-a",
                "raw_title": "Camisa A",
                "raw_description": "Descricao A",
                "price_full": 149.9,
                "specifications": {
                    "Composicao": "100% Algodao",
                },
            }

    def fake_to_excel(self, *args, **kwargs):
        captured["columns"] = self.columns.tolist()
        captured["row"] = self.iloc[0].to_dict() if len(self.index) else {}

    monkeypatch.setattr(factory.engine_factory, "get_engine", lambda brand: _FakeCategoryEngine())
    monkeypatch.setattr(orchestrator.pd.DataFrame, "to_excel", fake_to_excel)

    asyncio.run(
        orchestrator.run_orchestrator(
            "aramis",
            "https://www.aramis.com.br/camisas",
        )
    )

    assert captured["columns"] == CANONICAL_PRODUCT_COLUMNS
    assert captured["row"]["product_name"] == "Camisa A"
    assert captured["row"]["composition"] == "100% Algodao"


def test_multi_brand_category_export_uses_same_columns(monkeypatch, tmp_path):
    import services.orchestrator_multi as orchestrator_multi

    captured: dict[str, object] = {}

    def fake_to_excel(self, *args, **kwargs):
        captured["columns"] = self.columns.tolist()
        captured["row"] = self.iloc[0].to_dict() if len(self.index) else {}

    monkeypatch.setattr(orchestrator_multi.pd.DataFrame, "to_excel", fake_to_excel)

    messages = []
    orchestrator_multi.consolidate_and_save(
        all_products=[
            {
                "brand": "Aramis",
                "url": "https://www.aramis.com.br/p/camisa-a",
                "raw_title": "Camisa A",
                "raw_description": "Descricao A",
                "price_full": 149.9,
                "specifications": {"Referencia": "REF-123"},
            },
            {
                "brand": "Reserva",
                "url": "https://www.usereserva.com/p/camisa-b",
                "raw_title": "Camisa B",
                "raw_description": "Descricao B",
                "price_full": 199.9,
            },
        ],
        arquivo_saida=str(tmp_path / "multi.xlsx"),
        is_cancelled=False,
        results_store={"aramis": object(), "reserva": object()},
        total_success=2,
        total_errors=0,
        log_callback=messages.append,
    )

    assert captured["columns"] == CANONICAL_PRODUCT_COLUMNS
    assert captured["row"]["product_name"] == "Camisa A"
    assert captured["row"]["product_code"] == "REF-123"
