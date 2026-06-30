from config import Settings
from core.models import (
    RawProductBronze,
    ReviewComment,
    SearchProductResult,
    StockRuptureSummary,
)
from services.stock_summary_service import (
    compute_stock_summary,
    ensure_scan_product_ids,
    load_category_job_stock_summaries,
    load_monitor_stock_summary,
    persist_category_job_stock_summaries,
    persist_monitor_stock_summary,
)


def test_stock_rupture_summary_allows_zero_verified_products():
    summary = StockRuptureSummary(
        brand="aramis",
        total_products=3,
        in_stock_count=0,
        out_of_stock_count=0,
        unknown_stock_count=3,
        verified_stock_count=0,
        rupture_pct=None,
        scan_id="scan-1",
    )

    assert summary.rupture_pct is None


def test_phase44_fields_are_optional_for_existing_product_contracts():
    raw = RawProductBronze(
        url="https://example.com/polo",
        brand="aramis",
        raw_title="Polo Regular",
        raw_description="Polo",
        price_full=199.9,
        image_url="https://example.com/polo.jpg",
    )
    search = SearchProductResult(
        brand="aramis",
        product_name="Polo Regular",
        url="https://example.com/polo",
    )

    assert raw.scan_product_id is None
    assert raw.stock_depth_estimate is None
    assert raw.stock_depth_state is None
    assert raw.reviews_state is None
    assert raw.review_comments == []
    assert raw.review_product_id is None
    assert search.scan_product_id is None
    assert search.stock_depth_estimate is None
    assert search.stock_depth_state is None
    assert search.reviews_state is None
    assert search.review_comments == []
    assert search.review_product_id is None


def test_review_comment_serializes_only_compact_fields():
    comment = ReviewComment(
        review_id="rvw-1",
        rating=5,
        title="Excelente",
        text="Gostei do produto",
        author="Cliente",
        created_at="2026-06-30T12:00:00Z",
        source_provider="trustvox",
        source_ref="product-1",
    )

    assert set(comment.model_dump().keys()) == {
        "review_id",
        "rating",
        "title",
        "text",
        "author",
        "created_at",
        "source_provider",
        "source_ref",
    }


def test_phase44_settings_expose_conservative_defaults():
    settings = Settings()

    assert settings.MAX_REVIEW_PAGES == 2
    assert settings.STOCK_PROBE_QUANTITY == 999
    assert settings.STOCK_PROBE_THROTTLE_SECONDS == 2.0
    assert settings.STOCK_PROBE_TIMEOUT_SECONDS == 8
    assert settings.MAX_STOCK_DEPTH_PROBES_PER_BRAND == 3


def test_compute_stock_summary_counts_only_verified_product_stock():
    summary = compute_stock_summary(
        [
            {"stock_availability": True, "items": [{"available": False}]},
            {"stock_availability": False, "variants": [{"available": True}]},
            {"stock_availability": None, "variants": [{"available": False}]},
        ],
        brand="aramis",
        scan_id="scan-1",
        scanned_at="2026-06-30T12:00:00Z",
    )

    assert summary.total_products == 3
    assert summary.in_stock_count == 1
    assert summary.out_of_stock_count == 1
    assert summary.unknown_stock_count == 1
    assert summary.verified_stock_count == 2
    assert summary.rupture_pct == 0.5


def test_compute_stock_summary_returns_null_percentage_when_all_stock_is_unknown():
    summary = compute_stock_summary(
        [
            {"stock_availability": None},
            {"stock_availability": "false"},
            {"available": False},
        ],
        brand="aramis",
        monitor_id="monitor-1",
        scanned_at="2026-06-30T12:00:00Z",
    )

    assert summary.total_products == 3
    assert summary.verified_stock_count == 0
    assert summary.unknown_stock_count == 3
    assert summary.rupture_pct is None


def test_ensure_scan_product_ids_is_deterministic_and_preserves_existing_fields():
    products = [
        {
            "url": "https://example.com/polo",
            "raw_title": "Polo Regular",
            "stock_availability": True,
        },
        {
            "scan_product_id": "existing-id",
            "url": "https://example.com/camisa",
            "product_name": "Camisa Regular",
            "extra": {"color": "azul"},
        },
    ]

    first = ensure_scan_product_ids(products, brand="aramis", scan_id="scan-1")
    second = ensure_scan_product_ids(products, brand="aramis", scan_id="scan-1")

    assert first[0]["scan_product_id"] == second[0]["scan_product_id"]
    assert first[0]["scan_product_id"]
    assert first[0]["stock_availability"] is True
    assert first[1]["scan_product_id"] == "existing-id"
    assert first[1]["extra"] == {"color": "azul"}
    assert "scan_product_id" not in products[0]


def test_stock_summary_json_helpers_round_trip_under_data_dir(tmp_path, monkeypatch):
    import services.stock_summary_service as stock_summary_service

    monkeypatch.setattr(stock_summary_service, "DATA_DIR", tmp_path)

    monitor_summary = compute_stock_summary(
        [{"stock_availability": True}],
        brand="aramis",
        monitor_id="monitor-1",
        scanned_at="2026-06-30T12:00:00Z",
    )
    persist_monitor_stock_summary("monitor-1", monitor_summary)

    assert (tmp_path / "stock_summary_monitor-1.json").exists()
    loaded_monitor = load_monitor_stock_summary("monitor-1")
    assert loaded_monitor == monitor_summary

    category_summary = compute_stock_summary(
        [{"stock_availability": False}],
        brand="reserva",
        scan_id="job-1:reserva",
        scanned_at="2026-06-30T12:00:00Z",
    )
    persist_category_job_stock_summaries("job-1", [monitor_summary, category_summary])

    assert (tmp_path / "category_scan_summaries_job-1.json").exists()
    loaded_job = load_category_job_stock_summaries("job-1")
    assert loaded_job == [monitor_summary, category_summary]
