import asyncio
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.models import (
    RawProductBronze,
    ReviewComment,
    ReviewCommentsResult,
    StockDepthResult,
    StockRuptureSummary,
)


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class _FakeCategoryEngine:
    def __init__(self, products):
        self._products = products

    async def run_bulk_scrape(self, category_url: str, **kwargs):
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


def test_stock_depth_endpoint_calls_service_with_path_parameters_only(monkeypatch):
    import api.routes_monitor as routes_monitor

    called = {}

    async def fake_probe(monitor_id, scan_product_id):
        called["monitor_id"] = monitor_id
        called["scan_product_id"] = scan_product_id
        return StockDepthResult(
            stock_depth_state="estimated",
            stock_depth_estimate=8,
            stock_depth_checked_at="2026-06-30T18:40:00Z",
            stock_depth_source="vtex-cart-probe",
            stock_depth_label="maximo observado/estimativa via cart-probe",
        )

    monkeypatch.setattr(routes_monitor, "probe_scan_product_stock_depth", fake_probe)

    app = FastAPI()
    app.include_router(routes_monitor.router)

    response = TestClient(app).post(
        "/monitor/category/monitor-1/products/scan-product-1/stock-depth",
        json={
            "domain": "evil.example",
            "url": "https://evil.example/p",
            "quantity": 5000,
            "provider": "forced",
        },
    )

    assert response.status_code == 200
    assert called == {
        "monitor_id": "monitor-1",
        "scan_product_id": "scan-product-1",
    }


def test_stock_depth_endpoint_maps_value_error_to_http_400(monkeypatch):
    import api.routes_monitor as routes_monitor

    async def fake_probe(monitor_id, scan_product_id):
        raise ValueError("Produto do scan nao encontrado.")

    monkeypatch.setattr(routes_monitor, "probe_scan_product_stock_depth", fake_probe)

    app = FastAPI()
    app.include_router(routes_monitor.router)

    response = TestClient(app).post(
        "/monitor/category/monitor-1/products/missing/stock-depth"
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Produto do scan nao encontrado."


def test_stock_depth_endpoint_returns_stock_depth_payload(monkeypatch):
    import api.routes_monitor as routes_monitor

    expected = StockDepthResult(
        stock_depth_state="blocked",
        stock_depth_estimate=None,
        stock_depth_checked_at="2026-06-30T18:40:00Z",
        stock_depth_source="vtex-cart-probe",
        stock_depth_label="maximo observado/estimativa via cart-probe",
    )

    async def fake_probe(monitor_id, scan_product_id):
        return expected

    monkeypatch.setattr(routes_monitor, "probe_scan_product_stock_depth", fake_probe)

    app = FastAPI()
    app.include_router(routes_monitor.router)

    response = TestClient(app).post(
        "/monitor/category/monitor-1/products/scan-product-1/stock-depth"
    )

    assert response.status_code == 200
    assert response.json() == expected.model_dump(mode="json")


def test_review_comments_request_model_contains_only_max_pages():
    import api.routes_monitor as routes_monitor

    assert set(routes_monitor.ReviewCommentsRequest.model_fields) == {"max_pages"}


def test_review_comments_endpoint_caps_max_pages_and_returns_payload(monkeypatch):
    import api.routes_monitor as routes_monitor

    called = {}
    expected = ReviewCommentsResult(
        reviews_state="available",
        comments=[
            ReviewComment(
                review_id="r1",
                rating=5,
                text="Bom",
                source_provider="trustvox",
            )
        ],
        rating=5,
        review_count=1,
        review_product_id="123",
        source_provider="trustvox",
        max_pages=2,
    )

    async def fake_fetch(monitor_id, scan_product_id, max_pages=None):
        called["monitor_id"] = monitor_id
        called["scan_product_id"] = scan_product_id
        called["max_pages"] = max_pages
        return expected

    monkeypatch.setattr(routes_monitor.settings, "MAX_REVIEW_PAGES", 2)
    monkeypatch.setattr(
        routes_monitor,
        "fetch_scan_product_review_comments",
        fake_fetch,
    )

    app = FastAPI()
    app.include_router(routes_monitor.router)

    response = TestClient(app).post(
        "/monitor/category/monitor-1/products/scan-product-1/reviews",
        json={"max_pages": 99},
    )

    assert response.status_code == 200
    assert called == {
        "monitor_id": "monitor-1",
        "scan_product_id": "scan-product-1",
        "max_pages": 2,
    }
    assert response.json() == expected.model_dump(mode="json")


def test_stock_depth_route_does_not_involve_search_routes():
    routes_search = (BACKEND_ROOT / "api" / "routes_search.py").read_text(
        encoding="utf-8"
    )
    assert "probe_scan_product_stock_depth" not in routes_search
    assert "stock_depth_service" not in routes_search
    assert "cart_probe" not in routes_search


def test_scrape_category_passes_generated_job_id_to_orchestrator(monkeypatch):
    import api.routes_category as routes_category
    import services.orchestrator as orchestrator

    called = {}

    async def fake_run_orchestrator(
        *,
        marca,
        url_categoria,
        log_callback,
        cancel_event,
        job_id,
    ):
        called["marca"] = marca
        called["url_categoria"] = url_categoria
        called["job_id"] = job_id

    monkeypatch.setattr(routes_category.uuid, "uuid4", lambda: "job-1")
    monkeypatch.setattr(orchestrator, "run_orchestrator", fake_run_orchestrator)

    app = FastAPI()
    app.include_router(routes_category.router)

    response = TestClient(app).post(
        "/scrape-category",
        json={
            "brand": "aramis",
            "custom_url": "https://www.aramis.com.br/camisas",
        },
    )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-1"
    assert called == {
        "marca": "aramis",
        "url_categoria": "https://www.aramis.com.br/camisas",
        "job_id": "job-1",
    }


def test_run_orchestrator_persists_single_brand_stock_summary(
    tmp_path, monkeypatch
):
    import services.orchestrator as orchestrator
    import services.stock_summary_service as stock_summary_service
    from services.engines import factory

    products = [
        {"url": "https://example.com/a", "raw_title": "Produto A", "stock_availability": True},
        {"url": "https://example.com/b", "raw_title": "Produto B", "stock_availability": False},
        {"url": "https://example.com/c", "raw_title": "Produto C", "stock_availability": None},
    ]
    monkeypatch.setattr(stock_summary_service, "DATA_DIR", tmp_path)
    monkeypatch.setattr(
        factory.engine_factory,
        "get_engine",
        lambda brand: _FakeCategoryEngine(products),
    )
    monkeypatch.setattr(
        orchestrator.pd.DataFrame,
        "to_excel",
        lambda self, *args, **kwargs: None,
    )

    emitted = []
    asyncio.run(
        orchestrator.run_orchestrator(
            "aramis",
            "https://www.aramis.com.br/camisas",
            log_callback=emitted.append,
            job_id="job-1",
        )
    )

    payload = json.loads(
        (tmp_path / "category_scan_summaries_job-1.json").read_text(
            encoding="utf-8"
        )
    )
    assert len(payload) == 1
    assert payload[0]["brand"] == "aramis"
    assert payload[0]["scan_id"] == "job-1:aramis"
    assert payload[0]["verified_stock_count"] == 2
    assert payload[0]["unknown_stock_count"] == 1
    assert emitted[-2]["stock_summary"]["rupture_pct"] == 0.5


def test_run_multi_orchestrator_persists_one_stock_summary_per_brand(
    tmp_path, monkeypatch
):
    import services.orchestrator_multi as orchestrator_multi
    import services.stock_summary_service as stock_summary_service

    async def fake_send_message(message, job_id):
        return None

    async def fake_brand_pipeline(brand_key, url, cancel_event, log_callback=None):
        products = [
            {
                "url": f"https://example.com/{brand_key}/a",
                "raw_title": "Produto A",
                "stock_availability": brand_key == "aramis",
            },
            {
                "url": f"https://example.com/{brand_key}/b",
                "raw_title": "Produto B",
                "stock_availability": None,
            },
        ]
        return orchestrator_multi.BrandJobResult(
            brand_key=brand_key,
            brand_name=brand_key.title(),
            products=products,
            success_count=len(products),
            finished=True,
        )

    monkeypatch.setattr(stock_summary_service, "DATA_DIR", tmp_path)
    monkeypatch.setattr(orchestrator_multi.manager, "send_message", fake_send_message)
    monkeypatch.setattr(
        orchestrator_multi,
        "_run_brand_pipeline",
        fake_brand_pipeline,
    )
    monkeypatch.setattr(orchestrator_multi, "consolidate_and_save", lambda *args: None)

    async def run_job():
        await orchestrator_multi.run_multi_orchestrator(
            job_id="job-1",
            brand_url_map={
                "aramis": "https://www.aramis.com.br/camisas",
                "reserva": "https://www.usereserva.com/camisas",
            },
            category_label="Camisas",
            cancel_event=asyncio.Event(),
        )

    asyncio.run(run_job())

    payload = json.loads(
        (tmp_path / "category_scan_summaries_job-1.json").read_text(
            encoding="utf-8"
        )
    )
    assert [item["brand"] for item in payload] == ["aramis", "reserva"]
    assert [item["scan_id"] for item in payload] == [
        "job-1:aramis",
        "job-1:reserva",
    ]
    assert payload[0]["in_stock_count"] == 1
    assert payload[1]["out_of_stock_count"] == 1


def test_category_job_stock_summary_endpoint_returns_persisted_summaries(monkeypatch):
    import api.routes_category as routes_category

    summaries = [
        StockRuptureSummary(
            brand="aramis",
            total_products=1,
            in_stock_count=1,
            out_of_stock_count=0,
            unknown_stock_count=0,
            verified_stock_count=1,
            rupture_pct=0.0,
            scan_id="job-1:aramis",
            scanned_at="2026-06-30T12:00:00Z",
        )
    ]
    monkeypatch.setattr(
        routes_category,
        "load_category_job_stock_summaries",
        lambda job_id: summaries if job_id == "job-1" else [],
    )

    app = FastAPI()
    app.include_router(routes_category.router)

    response = TestClient(app).get("/scrape-category/job-1/stock-summary")

    assert response.status_code == 200
    assert response.json() == {
        "job_id": "job-1",
        "summaries": [summaries[0].model_dump(mode="json")],
    }
