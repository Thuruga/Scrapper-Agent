import asyncio
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.models import RawProductBronze, StockRuptureSummary


class _FakeCategoryEngine:
    def __init__(self, products):
        self._products = products

    async def run_bulk_scrape(self, category_url: str):
        for product in self._products:
            yield product


def _raw_product(title: str, url: str, stock_availability: bool | None):
    return RawProductBronze(
        url=url,
        brand="aramis",
        raw_title=title,
        raw_description=title,
        price_full=199.9,
        stock_availability=stock_availability,
        image_url=f"{url}.jpg",
    )


def test_run_category_scan_persists_products_with_scan_ids_and_stock_summary(
    tmp_path, monkeypatch
):
    import services.category_monitor_service as category_monitor_service
    import services.stock_summary_service as stock_summary_service
    from services.engines import factory

    monitor = {
        "id": "monitor-1",
        "url": "https://www.aramis.com.br/camisas",
        "brand": "aramis",
        "status": "active",
    }
    products = [
        _raw_product("Camisa Azul", "https://example.com/camisa-azul", True),
        _raw_product("Camisa Verde", "https://example.com/camisa-verde", False),
        _raw_product("Camisa Branca", "https://example.com/camisa-branca", None),
    ]

    monkeypatch.setattr(category_monitor_service, "DATA_DIR", tmp_path)
    monkeypatch.setattr(
        category_monitor_service,
        "MONITORS_FILE",
        tmp_path / "monitored_categories.json",
    )
    monkeypatch.setattr(stock_summary_service, "DATA_DIR", tmp_path)
    monkeypatch.setattr(
        factory.engine_factory,
        "get_engine",
        lambda brand: _FakeCategoryEngine(products),
    )
    category_monitor_service._save_local([monitor])

    asyncio.run(category_monitor_service.run_category_scan(monitor))

    persisted_products = json.loads(
        (tmp_path / "monitored_products_monitor-1.json").read_text(encoding="utf-8")
    )
    assert len(persisted_products) == 3
    assert all(product["scan_product_id"] for product in persisted_products)
    assert persisted_products[0]["stock_availability"] is True
    assert persisted_products[1]["stock_availability"] is False
    assert persisted_products[2]["stock_availability"] is None

    summary = json.loads(
        (tmp_path / "stock_summary_monitor-1.json").read_text(encoding="utf-8")
    )
    assert summary["monitor_id"] == "monitor-1"
    assert summary["brand"] == "aramis"
    assert summary["total_products"] == 3
    assert summary["verified_stock_count"] == 2
    assert summary["out_of_stock_count"] == 1
    assert summary["unknown_stock_count"] == 1
    assert summary["rupture_pct"] == 0.5

    [updated_monitor] = category_monitor_service._load_local()
    assert updated_monitor["last_scraped_at"]
    assert updated_monitor["last_stock_summary"] == {
        "total_products": 3,
        "verified_stock_count": 2,
        "in_stock_count": 1,
        "out_of_stock_count": 1,
        "unknown_stock_count": 1,
        "rupture_pct": 0.5,
    }


def test_run_category_scan_persists_all_unknown_summary_with_null_rupture(
    tmp_path, monkeypatch
):
    import services.category_monitor_service as category_monitor_service
    import services.stock_summary_service as stock_summary_service
    from services.engines import factory

    monitor = {
        "id": "monitor-unknown",
        "url": "https://www.aramis.com.br/camisas",
        "brand": "aramis",
        "status": "active",
    }
    products = [
        _raw_product("Camisa Azul", "https://example.com/camisa-azul", None),
        _raw_product("Camisa Verde", "https://example.com/camisa-verde", None),
    ]

    monkeypatch.setattr(category_monitor_service, "DATA_DIR", tmp_path)
    monkeypatch.setattr(
        category_monitor_service,
        "MONITORS_FILE",
        tmp_path / "monitored_categories.json",
    )
    monkeypatch.setattr(stock_summary_service, "DATA_DIR", tmp_path)
    monkeypatch.setattr(
        factory.engine_factory,
        "get_engine",
        lambda brand: _FakeCategoryEngine(products),
    )
    category_monitor_service._save_local([monitor])

    asyncio.run(category_monitor_service.run_category_scan(monitor))

    summary = json.loads(
        (tmp_path / "stock_summary_monitor-unknown.json").read_text(encoding="utf-8")
    )
    assert summary["total_products"] == 2
    assert summary["verified_stock_count"] == 0
    assert summary["unknown_stock_count"] == 2
    assert summary["rupture_pct"] is None


def test_monitor_stock_summary_endpoint_returns_persisted_summary(monkeypatch):
    import api.routes_monitor as routes_monitor

    summary = StockRuptureSummary(
        brand="aramis",
        total_products=1,
        in_stock_count=0,
        out_of_stock_count=1,
        unknown_stock_count=0,
        verified_stock_count=1,
        rupture_pct=1.0,
        monitor_id="monitor-1",
        scanned_at="2026-06-30T12:00:00Z",
    )
    monkeypatch.setattr(
        routes_monitor,
        "load_monitor_stock_summary",
        lambda monitor_id: summary if monitor_id == "monitor-1" else None,
    )

    app = FastAPI()
    app.include_router(routes_monitor.router)

    response = TestClient(app).get("/monitor/category/monitor-1/stock-summary")

    assert response.status_code == 200
    assert response.json() == summary.model_dump(mode="json")


def test_monitor_stock_summary_endpoint_returns_404_when_missing(monkeypatch):
    import api.routes_monitor as routes_monitor

    monkeypatch.setattr(routes_monitor, "load_monitor_stock_summary", lambda _: None)

    app = FastAPI()
    app.include_router(routes_monitor.router)

    response = TestClient(app).get("/monitor/category/missing/stock-summary")

    assert response.status_code == 404
    assert response.json()["detail"] == "Resumo de estoque nao encontrado."
