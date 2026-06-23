from datetime import datetime, timedelta, timezone

import pytest

from core.banner_models import BannerCandidate, BannerRun, BannerRunStatus
from services.banner_report_service import BannerReportService
from services.banner_storage_service import BannerStorageService, friendly_banner_filename


def _candidate(storage, banner_id="b1", data=b"same", brand="aramis"):
    asset = storage.store_asset(data, "image/webp")
    return BannerCandidate(
        banner_id=banner_id,
        brand_key=brand,
        brand_name=brand.title(),
        slide_order=1,
        friendly_filename=friendly_banner_filename(1, "sale", brand, "webp"),
        asset=asset,
        source_url="https://example.com/large.webp",
        rendered_url="https://example.com/rendered.webp",
    )


def test_deduplicates_bytes_and_never_uses_friendly_name_as_path(tmp_path):
    storage = BannerStorageService(tmp_path)
    first = storage.store_asset(b"same", "image/webp")
    second = storage.store_asset(b"same", "image/webp")
    assert first.sha256 == second.sha256
    assert len(list(storage.assets_dir.iterdir())) == 1
    assert storage.resolve_asset(first).parent == storage.assets_dir
    with pytest.raises(ValueError):
        storage.store_asset(b"x", "text/html", "../../html")


def test_approval_is_filtered_history_visible_and_immutable(tmp_path):
    storage = BannerStorageService(tmp_path)
    one = _candidate(storage, "b1", b"one")
    two = _candidate(storage, "b2", b"two")
    run = BannerRun(run_id="run_12345678", selected_brands=["aramis"], status=BannerRunStatus.REVIEW, banners=[one, two])
    storage.save_run(run)
    approved = storage.approve_run(run.run_id, ["b1"])
    assert approved.status == BannerRunStatus.COMPLETED
    assert [b.banner_id for b in approved.banners] == ["b1"]
    assert storage.list_history()[0].banner_count == 1
    with pytest.raises(ValueError):
        storage.approve_run(run.run_id, ["b1"])
    with pytest.raises(ValueError):
        approved.error = "mutated"
        storage.save_run(approved)


def test_partial_is_not_history_and_cleanup_keeps_shared_blob(tmp_path):
    storage = BannerStorageService(tmp_path)
    banner1 = _candidate(storage, "b1")
    banner2 = _candidate(storage, "b2")
    old = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
    completed = BannerRun(
        run_id="run_completed1", selected_brands=["aramis"], status=BannerRunStatus.COMPLETED,
        banners=[banner1], approved_at=old,
    )
    partial = BannerRun(
        run_id="run_partial01", selected_brands=["aramis"], status=BannerRunStatus.PARTIAL,
        banners=[banner2],
    )
    storage.save_run(completed)
    storage.save_run(partial)
    assert storage.list_history() == []
    assert storage.resolve_asset(banner1.asset).exists()
    assert storage.get_run(partial.run_id) is not None


def test_reports_match_approved_run_and_escape_html(tmp_path):
    storage = BannerStorageService(tmp_path)
    banner = _candidate(storage)
    banner.alt_text = '<script>alert("x")</script>'
    run = BannerRun(
        run_id="run_reports01", selected_brands=["aramis"], status=BannerRunStatus.COMPLETED,
        banners=[banner], approved_at=datetime.now(timezone.utc).isoformat(),
    )
    storage.save_run(run)
    paths = BannerReportService(storage).generate(run)
    assert set(paths) == {"json", "csv", "html"}
    html_text = paths["html"].read_text(encoding="utf-8")
    assert "<script>" not in html_text
    assert "01-sale-aramis.webp" in paths["csv"].read_text(encoding="utf-8-sig")


def test_delete_history_garbage_collects_last_reference(tmp_path):
    storage = BannerStorageService(tmp_path)
    banner = _candidate(storage)
    run = BannerRun(
        run_id="run_delete001", selected_brands=["aramis"], status=BannerRunStatus.COMPLETED,
        banners=[banner], approved_at=datetime.now(timezone.utc).isoformat(),
    )
    storage.save_run(run)
    assert storage.delete_history(run.run_id)
    assert not (storage.assets_dir / f"{banner.asset.sha256}.{banner.asset.extension}").exists()

