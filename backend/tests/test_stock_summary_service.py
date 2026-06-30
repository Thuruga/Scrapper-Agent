from config import Settings
from core.models import (
    RawProductBronze,
    ReviewComment,
    SearchProductResult,
    StockRuptureSummary,
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
