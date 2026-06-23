import asyncio
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

import api.routes_banners as routes
from app import app
from core.banner_models import (
    BannerCandidate, BannerRun, BannerRunStatus, BrandBannerStatus, StoredBannerAsset,
)
from core.job_manager import JOB_CANCEL_FLAGS
from core.models import DynamicBrand
from services.banner_extraction_service import BrandExtractionResult
from services.banner_job_service import BannerJobService
from services.banner_report_service import BannerReportService
from services.banner_storage_service import BannerStorageService, friendly_banner_filename


class FakeBrands:
    def __init__(self):
        self.items = [
            DynamicBrand(brand_key="a", brand_name="Marca A", domain="a.example.com", is_active=True),
            DynamicBrand(brand_key="b", brand_name="Marca B", domain="b.example.com", is_active=True),
        ]

    def list_brands(self, active_only=False):
        return self.items


@contextmanager
def fake_browser():
    yield object()


def make_candidate(storage, brand_key, order=1):
    asset = storage.store_asset(f"{brand_key}-{order}".encode(), "image/webp")
    return BannerCandidate(
        banner_id=f"{brand_key}-{order}", brand_key=brand_key, brand_name=f"Marca {brand_key.upper()}",
        slide_order=order, friendly_filename=friendly_banner_filename(order, "hero", brand_key, "webp"),
        asset=asset, source_url="https://example.com/source.webp", rendered_url="https://example.com/rendered.webp",
    )


class FakeCollector:
    def __init__(self, storage, *, fail=None, stop_after=None):
        self.storage = storage; self.fail = fail; self.stop_after = stop_after; self.calls = []

    def extract_brand(self, _browser, brand, cancel_event=None, progress_callback=None):
        self.calls.append(brand.brand_key)
        if brand.brand_key == self.fail:
            raise RuntimeError("site failed")
        banner = make_candidate(self.storage, brand.brand_key)
        if progress_callback:
            progress_callback({"kind": "banner", "banner": banner.model_dump(mode="json")})
        if brand.brand_key == self.stop_after:
            cancel_event.set()
        screenshot = self.storage.store_asset(b"png", "image/png")
        return BrandExtractionResult([banner], [], screenshot, f"https://{brand.domain}")


def test_job_is_sequential_and_stop_preserves_completed_session_results(tmp_path):
    storage = BannerStorageService(tmp_path)
    collector = FakeCollector(storage, stop_after="a")
    service = BannerJobService(storage, collector, FakeBrands(), fake_browser)
    run = service.create_job(["a", "b"])
    result = asyncio.run(service.run_job(run.run_id))
    assert collector.calls == ["a"]
    assert result.status == BannerRunStatus.CANCELLED
    assert result.brand_progress["a"].status == BrandBannerStatus.COMPLETED
    assert result.brand_progress["b"].status == BrandBannerStatus.CANCELLED
    assert [banner.brand_key for banner in result.banners] == ["a"]
    assert storage.list_history() == []


def test_brand_failure_is_isolated_but_run_stays_out_of_history(tmp_path):
    storage = BannerStorageService(tmp_path)
    collector = FakeCollector(storage, fail="a")
    service = BannerJobService(storage, collector, FakeBrands(), fake_browser)
    run = service.create_job(["a", "b"])
    result = asyncio.run(service.run_job(run.run_id))
    assert collector.calls == ["a", "b"]
    assert result.status == BannerRunStatus.PARTIAL
    assert result.brand_progress["a"].status == BrandBannerStatus.FAILED
    assert result.brand_progress["b"].status == BrandBannerStatus.COMPLETED
    assert storage.list_history() == []


def test_authenticated_routes_approve_reopen_asset_report_and_delete(tmp_path, monkeypatch):
    from api.auth import verify_api_key

    storage = BannerStorageService(tmp_path)
    service = BannerJobService(storage, FakeCollector(storage), FakeBrands(), fake_browser)
    monkeypatch.setattr(routes, "banner_storage_service", storage)
    monkeypatch.setattr(routes, "banner_job_service", service)
    monkeypatch.setattr(routes, "banner_report_service", BannerReportService(storage))
    client = TestClient(app)
    headers = {"X-API-Key": "dev-api-key"}
    # Another test module installs a collection-time dependency override globally;
    # temporarily remove it so this route proves it inherits api_router auth.
    prior_override = app.dependency_overrides.pop(verify_api_key, None)
    try:
        assert client.get("/banners/history").status_code in {422, 403}
    finally:
        if prior_override is not None:
            app.dependency_overrides[verify_api_key] = prior_override

    run = service.create_job(["a"])
    # Route start is tested independently from browser work; direct lifecycle state is authoritative.
    banner = make_candidate(storage, "a")
    stored = storage.get_run(run.run_id)
    stored.banners = [banner]
    stored.status = BannerRunStatus.REVIEW
    storage.save_run(stored)

    status = client.get(f"/banners/jobs/{run.run_id}", headers=headers)
    assert status.status_code == 200
    approved = client.post(
        f"/banners/jobs/{run.run_id}/approve", headers=headers, json={"banner_ids": [banner.banner_id]},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "COMPLETED"
    assert len(client.get("/banners/history", headers=headers).json()) == 1
    assert client.get(f"/banners/history/{run.run_id}", headers=headers).status_code == 200
    assert client.get(f"/banners/assets/{run.run_id}/{banner.banner_id}", headers=headers).content == b"a-1"
    assert client.get(f"/banners/runs/{run.run_id}/reports/json", headers=headers).status_code == 200
    assert client.post(
        f"/banners/jobs/{run.run_id}/approve", headers=headers, json={"banner_ids": [banner.banner_id]},
    ).status_code == 409
    assert client.delete(f"/banners/history/{run.run_id}", headers=headers).status_code == 204
    assert client.get(f"/banners/assets/{run.run_id}/../../config.py", headers=headers).status_code in {404, 400}
    JOB_CANCEL_FLAGS.pop(run.run_id, None)


def test_create_job_rejects_unknown_or_empty_brand(tmp_path):
    service = BannerJobService(BannerStorageService(tmp_path), FakeCollector(BannerStorageService(tmp_path / "x")), FakeBrands(), fake_browser)
    for brands in ([], ["unknown"]):
        try:
            service.create_job(brands)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid brand selection should fail")
