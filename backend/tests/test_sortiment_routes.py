from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.models import (
    SortimentBucketSnapshot,
    SortimentCategoryRow,
    SortimentDashboardDimension,
    SortimentDashboardResponse,
)


def _dashboard_payload() -> SortimentDashboardResponse:
    return SortimentDashboardResponse(
        category=SortimentCategoryRow(
            id="sortiment-1",
            source_monitor_id="monitor-1",
            brand="aramis",
            url="https://www.aramis.com.br/polos",
            enabled=True,
        ),
        baseline=True,
        latest_snapshot="sortiment-1__20260706T040000Z.json",
        latest_snapshot_at="2026-07-06T04:00:00Z",
        dimensions=[
            SortimentDashboardDimension(
                dimension="available_colors",
                current_distribution=[
                    SortimentBucketSnapshot(label="azul", count=2, evidence=[])
                ],
                deltas=[],
            )
        ],
    )


def test_sortiment_routes_use_persisted_category_ids_and_forbid_extra_patch_fields(
    monkeypatch,
):
    import api.routes_sortiment as routes_sortiment

    calls = {}

    monkeypatch.setattr(
        routes_sortiment,
        "load_sortiment_categories",
        lambda enabled_only=False: [
            SortimentCategoryRow(
                id="sortiment-1",
                source_monitor_id="monitor-1",
                brand="aramis",
                url="https://www.aramis.com.br/polos",
                enabled=False,
            )
        ],
    )
    monkeypatch.setattr(
        routes_sortiment,
        "sync_sortiment_categories_from_monitor",
        lambda: [
            SortimentCategoryRow(
                id="sortiment-1",
                source_monitor_id="monitor-1",
                brand="aramis",
                url="https://www.aramis.com.br/polos",
                enabled=False,
            )
        ],
    )
    
    def _fake_update(category_id, **changes):
        calls["patch"] = (category_id, changes)
        return SortimentCategoryRow(
            id=category_id,
            source_monitor_id="monitor-1",
            brand="aramis",
            url="https://www.aramis.com.br/polos",
            enabled=changes["enabled"],
        )

    async def _fake_run(category_id):
        calls["run"] = category_id
        return ("completed", None)

    def _fake_dashboard(category_id):
        calls["dashboard"] = category_id
        return _dashboard_payload()

    monkeypatch.setattr(routes_sortiment, "update_sortiment_category", _fake_update)
    monkeypatch.setattr(routes_sortiment, "try_run_sortiment_category", _fake_run)
    monkeypatch.setattr(routes_sortiment, "get_sortiment_dashboard", _fake_dashboard)

    app = FastAPI()
    app.include_router(routes_sortiment.router)
    client = TestClient(app)

    assert client.get("/sortiment/categories").status_code == 200
    assert client.post("/sortiment/categories/sync").status_code == 200

    invalid_patch = client.patch(
        "/sortiment/categories/sortiment-1",
        json={"enabled": True, "url": "https://evil.example"},
    )
    assert invalid_patch.status_code == 422

    valid_patch = client.patch(
        "/sortiment/categories/sortiment-1",
        json={"enabled": True},
    )
    assert valid_patch.status_code == 200
    assert calls["patch"] == ("sortiment-1", {"enabled": True})

    run_response = client.post("/sortiment/categories/sortiment-1/run")
    assert run_response.status_code == 200
    assert calls["run"] == "sortiment-1"

    dashboard_response = client.get("/sortiment/categories/sortiment-1/dashboard")
    assert dashboard_response.status_code == 200
    assert calls["dashboard"] == "sortiment-1"


def test_sortiment_manual_run_busy_status_and_scheduler_registration(monkeypatch):
    import api.routes_sortiment as routes_sortiment
    import app as backend_app

    async def _busy(category_id: str):
        return ("busy", None)

    monkeypatch.setattr(routes_sortiment, "try_run_sortiment_category", _busy)

    app = FastAPI()
    app.include_router(routes_sortiment.router)
    client = TestClient(app)

    response = client.post("/sortiment/categories/sortiment-1/run")
    assert response.status_code == 200
    assert response.json() == {
        "status": "busy",
        "category_id": "sortiment-1",
        "snapshot_id": None,
        "captured_at": None,
    }

    recorded = []

    class _FakeScheduler:
        def add_job(self, func, trigger, **kwargs):
            recorded.append((func, trigger, kwargs))

    backend_app.configure_scheduler(
        _FakeScheduler(),
        category_monitor_job="category-job",
        sortiment_job="sortiment-job",
    )

    assert recorded[0] == ("category-job", "interval", {"id": "category-monitor-job", "minutes": 10})
    assert recorded[1] == (
        "sortiment-job",
        "interval",
        {
            "id": "sortiment-category-job",
            "minutes": backend_app.settings.SORTIMENT_CRON_INTERVAL_MINUTES,
            "max_instances": 1,
            "coalesce": True,
        },
    )
