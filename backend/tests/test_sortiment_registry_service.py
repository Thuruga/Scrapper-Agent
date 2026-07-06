import json

from pydantic import ValidationError

from config import Settings
from core.models import (
    SortimentBucketDelta,
    SortimentBucketEvidence,
    SortimentBucketSnapshot,
    SortimentCategoryRow,
    SortimentCategorySnapshot,
    SortimentDashboardDimension,
    SortimentDashboardResponse,
    SortimentDimensionSnapshot,
)


def test_sortiment_registry_rows_require_source_monitor_and_default_disabled():
    row = SortimentCategoryRow(
        source_monitor_id="monitor-1",
        brand="aramis",
        url="https://www.aramis.com.br/polos",
    )

    assert row.enabled is False
    assert row.source_monitor_id == "monitor-1"

    preserved = SortimentCategoryRow(
        id="sortiment-1",
        source_monitor_id="monitor-1",
        brand="aramis",
        url="https://www.aramis.com.br/polos",
        enabled=True,
    )

    assert preserved.enabled is True

    try:
        SortimentCategoryRow(
            brand="aramis",
            url="https://www.aramis.com.br/polos",
        )
    except ValidationError as exc:
        assert "source_monitor_id" in str(exc)
    else:
        raise AssertionError("source_monitor_id should be required")


def test_phase45_models_lock_dimensions_and_baseline_delta_metadata():
    evidence = SortimentBucketEvidence(
        scan_product_id="scan-1:item-1",
        product_name="Polo Azul",
        url="https://example.com/polo-azul",
    )
    snapshot_bucket = SortimentBucketSnapshot(
        label="azul",
        count=2,
        evidence=[evidence],
    )
    delta_bucket = SortimentBucketDelta(
        label="azul",
        latest_count=2,
        previous_count=1,
        delta_abs=1,
        delta_pct=100.0,
        evidence=[evidence],
    )

    dashboard = SortimentDashboardResponse(
        category=SortimentCategoryRow(
            id="sortiment-1",
            source_monitor_id="monitor-1",
            brand="aramis",
            url="https://www.aramis.com.br/polos",
        ),
        baseline=False,
        latest_snapshot_at="2026-07-05T12:00:00Z",
        previous_snapshot_at="2026-07-04T12:00:00Z",
        dimensions=[
            SortimentDashboardDimension(
                dimension="available_colors",
                current_distribution=[snapshot_bucket],
                deltas=[delta_bucket],
            )
        ],
    )

    assert dashboard.baseline is False
    assert dashboard.latest_snapshot_at == "2026-07-05T12:00:00Z"
    assert dashboard.previous_snapshot_at == "2026-07-04T12:00:00Z"
    assert dashboard.dimensions[0].dimension == "available_colors"
    assert dashboard.dimensions[0].deltas[0].delta_abs == 1
    assert dashboard.dimensions[0].deltas[0].delta_pct == 100.0

    try:
        SortimentDashboardDimension(
            dimension="category",
            current_distribution=[],
            deltas=[],
        )
    except ValidationError as exc:
        assert "available_colors" in str(exc)
        assert "available_sizes" in str(exc)
        assert "composition" in str(exc)
    else:
        raise AssertionError("unsupported sortiment dimension should be rejected")


def test_phase45_settings_expose_independent_sortiment_defaults():
    settings = Settings()

    assert settings.SORTIMENT_CRON_INTERVAL_MINUTES == 60
    assert settings.SORTIMENT_MAX_PRODUCTS_PER_CATEGORY == 1000
    assert settings.SORTIMENT_EVIDENCE_PER_BUCKET == 3


def test_sortiment_sync_seeds_missing_rows_and_preserves_enabled_state(
    tmp_path, monkeypatch
):
    import services.sortiment_registry_service as sortiment_registry_service

    monitored_rows = [
        {
            "id": "monitor-1",
            "url": "https://www.aramis.com.br/polos",
            "brand": "aramis",
            "status": "active",
            "last_scraped_at": "2026-07-05T10:00:00Z",
        },
        {
            "id": "monitor-2",
            "url": "https://www.usereserva.com/camisas",
            "brand": "reserva",
            "status": "paused",
        },
    ]
    monitored_file = tmp_path / "monitored_categories.json"
    monitored_file.write_text(
        json.dumps(monitored_rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    existing_row = SortimentCategoryRow(
        id="sortiment-existing",
        source_monitor_id="monitor-1",
        brand="aramis",
        url="https://stale.example/old",
        enabled=True,
    )
    registry_file = tmp_path / "sortiment_categories.json"
    registry_file.write_text(
        json.dumps([existing_row.model_dump(mode="json")], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    monkeypatch.setattr(sortiment_registry_service, "DATA_DIR", tmp_path)
    monkeypatch.setattr(sortiment_registry_service, "MONITORS_FILE", monitored_file)
    monkeypatch.setattr(
        sortiment_registry_service,
        "SORTIMENT_REGISTRY_FILE",
        registry_file,
    )

    synced = sortiment_registry_service.sync_sortiment_categories_from_monitor()
    by_source = {row.source_monitor_id: row for row in synced}

    assert list(by_source) == ["monitor-1", "monitor-2"]
    assert by_source["monitor-1"].enabled is True
    assert by_source["monitor-1"].url == monitored_rows[0]["url"]
    assert by_source["monitor-1"].source_status == "active"
    assert by_source["monitor-2"].enabled is False
    assert by_source["monitor-2"].brand == "reserva"
    assert by_source["monitor-2"].source_status == "paused"
    assert by_source["monitor-2"].source_monitor_id == "monitor-2"
    assert json.loads(monitored_file.read_text(encoding="utf-8")) == monitored_rows


def test_sortiment_artifact_helpers_roll_manifest_and_store_aggregate_only_payload(
    tmp_path, monkeypatch
):
    import services.sortiment_artifact_service as sortiment_artifact_service

    monkeypatch.setattr(sortiment_artifact_service, "DATA_DIR", tmp_path)
    monkeypatch.setattr(
        sortiment_artifact_service,
        "SORTIMENT_SNAPSHOT_DIR",
        tmp_path / "sortiment_snapshots",
    )
    monkeypatch.setattr(
        sortiment_artifact_service,
        "SORTIMENT_MANIFEST_DIR",
        tmp_path / "sortiment_manifests",
    )

    evidence = SortimentBucketEvidence(
        scan_product_id="scan-1:item-1",
        product_name="Polo Azul",
        url="https://example.com/polo-azul",
    )
    first_snapshot = SortimentCategorySnapshot(
        snapshot_id="snapshot-1",
        category_id="sortiment-1",
        source_monitor_id="monitor-1",
        brand="aramis",
        url="https://www.aramis.com.br/polos",
        captured_at="2026-07-05T12:00:00Z",
        product_count=4,
        dimensions=[
            SortimentDimensionSnapshot(
                dimension="available_colors",
                buckets=[
                    SortimentBucketSnapshot(
                        label="azul",
                        count=2,
                        evidence=[evidence],
                    )
                ],
            )
        ],
    )

    first_path, first_manifest = sortiment_artifact_service.persist_sortiment_snapshot(
        first_snapshot
    )

    second_snapshot = SortimentCategorySnapshot(
        snapshot_id="snapshot-2",
        category_id="sortiment-1",
        source_monitor_id="monitor-1",
        brand="aramis",
        url="https://www.aramis.com.br/polos",
        captured_at="2026-07-05T13:00:00Z",
        product_count=5,
        dimensions=first_snapshot.dimensions,
    )
    second_path, second_manifest = sortiment_artifact_service.persist_sortiment_snapshot(
        second_snapshot
    )

    assert first_path.name == "sortiment-1__20260705T120000Z.json"
    assert second_path.name == "sortiment-1__20260705T130000Z.json"
    assert first_manifest.latest_snapshot == first_path.name
    assert first_manifest.previous_snapshot is None
    assert second_manifest.latest_snapshot == second_path.name
    assert second_manifest.previous_snapshot == first_path.name

    reloaded_manifest = sortiment_artifact_service.load_sortiment_manifest("sortiment-1")
    assert reloaded_manifest == second_manifest

    persisted_payload = json.loads(second_path.read_text(encoding="utf-8"))
    assert persisted_payload["product_count"] == 5
    assert persisted_payload["dimensions"][0]["dimension"] == "available_colors"
    assert persisted_payload["dimensions"][0]["buckets"][0]["evidence"][0]["scan_product_id"] == "scan-1:item-1"
    assert "products" not in persisted_payload
    assert "normalized_catalog" not in persisted_payload
