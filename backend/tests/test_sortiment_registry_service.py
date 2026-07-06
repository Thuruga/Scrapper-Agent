from pydantic import ValidationError

from config import Settings
from core.models import (
    SortimentBucketDelta,
    SortimentBucketEvidence,
    SortimentBucketSnapshot,
    SortimentCategoryRow,
    SortimentDashboardDimension,
    SortimentDashboardResponse,
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
