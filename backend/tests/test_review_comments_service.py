import json
import asyncio
from pathlib import Path

from core.models import DynamicBrand, ReviewComment, ReviewCommentsResult
from services.brand_service import BrandDatabase


BACKEND_ROOT = Path(__file__).resolve().parents[1]
BRANDS_PATH = BACKEND_ROOT / "data" / "brands.json"


def _load_brand_rows() -> dict:
    return json.loads(BRANDS_PATH.read_text(encoding="utf-8"))


def test_brands_json_validates_after_review_provider_audit_metadata():
    rows = _load_brand_rows()

    validated = BrandDatabase.model_validate(rows)

    assert set(validated.root) == set(rows)


def test_trustvox_brands_have_store_id_and_provider_evidence():
    rows = _load_brand_rows()
    trustvox_rows = [
        row for row in rows.values() if row.get("review_provider") == "trustvox"
    ]

    assert trustvox_rows
    for row in trustvox_rows:
        assert row.get("review_store_id")
        assert row.get("review_provider_evidence")


def test_vtex_native_brands_have_explicit_provider_evidence():
    rows = _load_brand_rows()

    for row in rows.values():
        if row.get("review_provider") == "vtex_native":
            assert row.get("review_provider_evidence")


def test_unsupported_review_provider_brands_have_rationale():
    rows = _load_brand_rows()

    unsupported_rows = [
        row for row in rows.values() if row.get("review_provider") == "none"
    ]
    assert unsupported_rows
    for row in unsupported_rows:
        assert row.get("review_store_id") is None
        assert row.get("review_unsupported_reason")


def test_aramis_remains_trustvox_with_existing_store_id():
    rows = _load_brand_rows()

    aramis = rows["aramis"]

    assert aramis["review_provider"] == "trustvox"
    assert aramis["review_store_id"] == "78800"
    assert aramis.get("review_provider_evidence")


def _brand(
    *,
    provider: str = "trustvox",
    store_id: str | None = "78800",
    evidence: str | None = "Trustvox widget/root validated in brands.json",
    unsupported_reason: str | None = None,
) -> DynamicBrand:
    return DynamicBrand(
        brand_key="aramis",
        brand_name="Aramis",
        domain="www.aramis.com.br",
        review_provider=provider,
        review_store_id=store_id,
        review_provider_evidence=evidence,
        review_unsupported_reason=unsupported_reason,
        engine="vtex",
    )


def test_get_review_comments_returns_unsupported_for_unknown_and_none(monkeypatch):
    import services.review_service as review_service

    monkeypatch.setattr(review_service.brand_service, "get_brand", lambda key: None)

    missing = asyncio.run(review_service.get_review_comments("missing", "123"))

    assert missing.reviews_state == "unsupported"
    assert missing.comments == []

    monkeypatch.setattr(
        review_service.brand_service,
        "get_brand",
        lambda key: _brand(
            provider="none",
            store_id=None,
            evidence=None,
            unsupported_reason="Sem provider validado.",
        ),
    )

    unsupported = asyncio.run(review_service.get_review_comments("aramis", "123"))

    assert unsupported.reviews_state == "unsupported"
    assert unsupported.comments == []
    assert unsupported.source_provider == "none"


def test_get_review_comments_caps_requested_max_pages(monkeypatch):
    import services.review_service as review_service

    called = {}

    async def fake_fetch(brand, product_id, max_pages):
        called["product_id"] = product_id
        called["max_pages"] = max_pages
        return ReviewCommentsResult(
            reviews_state="available",
            comments=[],
            source_provider="trustvox",
            max_pages=max_pages,
        )

    monkeypatch.setattr(review_service.brand_service, "get_brand", lambda key: _brand())
    monkeypatch.setattr(review_service.settings, "MAX_REVIEW_PAGES", 2)
    monkeypatch.setattr(review_service, "_fetch_trustvox_comments", fake_fetch)

    result = asyncio.run(
        review_service.get_review_comments("aramis", "123", max_pages=99)
    )

    assert called == {"product_id": "123", "max_pages": 2}
    assert result.max_pages == 2


def test_dedupe_review_comments_collapses_duplicate_review_ids():
    import services.review_service as review_service

    comments = [
        ReviewComment(
            review_id="same-id",
            rating=5,
            text="Otimo produto",
            source_provider="trustvox",
        ),
        ReviewComment(
            review_id="same-id",
            rating=1,
            text="Duplicado",
            source_provider="trustvox",
        ),
    ]

    deduped = review_service.dedupe_review_comments(comments)

    assert len(deduped) == 1
    assert deduped[0].text == "Otimo produto"


def test_review_comment_key_hashes_comments_without_stable_id():
    import services.review_service as review_service

    first = {
        "rating": 4,
        "title": "Bom",
        "text": "Gostei",
        "author": "Ana",
        "created_at": "2026-06-30",
    }
    second = dict(first)

    key = review_service.review_comment_key(first)

    assert key
    assert key == review_service.review_comment_key(second)
    assert key != review_service.review_comment_key({**first, "text": "Outro"})


def test_get_review_comments_returns_only_compact_comment_fields(monkeypatch):
    import services.review_service as review_service

    async def fake_fetch(brand, product_id, max_pages):
        return ReviewCommentsResult(
            reviews_state="available",
            comments=[
                ReviewComment(
                    review_id="r1",
                    rating=5,
                    title="Excelente",
                    text="Muito bom",
                    author="Cliente",
                    created_at="2026-06-30",
                    source_provider="trustvox",
                    source_ref="123",
                )
            ],
            rating=5,
            review_count=1,
            source_provider="trustvox",
            max_pages=max_pages,
        )

    monkeypatch.setattr(review_service.brand_service, "get_brand", lambda key: _brand())
    monkeypatch.setattr(review_service, "_fetch_trustvox_comments", fake_fetch)

    result = asyncio.run(review_service.get_review_comments("aramis", "123"))
    payload = result.model_dump(mode="json")

    assert payload["comments"] == [
        {
            "review_id": "r1",
            "rating": 5.0,
            "title": "Excelente",
            "text": "Muito bom",
            "author": "Cliente",
            "created_at": "2026-06-30",
            "source_provider": "trustvox",
            "source_ref": "123",
        }
    ]
    assert "raw_reviews" not in json.dumps(payload)
    assert "raw_payload" not in json.dumps(payload)
    assert "payload" not in payload


def test_fetch_scan_product_review_comments_rejects_missing_identity(
    tmp_path, monkeypatch
):
    import services.review_service as review_service

    (tmp_path / "monitored_categories.json").write_text(
        json.dumps(
            [
                {
                    "id": "monitor-1",
                    "brand": "aramis",
                    "url": "https://www.aramis.com.br/camisas",
                    "status": "active",
                }
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "monitored_products_monitor-1.json").write_text(
        json.dumps(
            [
                {
                    "scan_product_id": "scan-1",
                    "url": "https://www.aramis.com.br/camisa/p",
                    "raw_title": "Camisa",
                }
            ]
        ),
        encoding="utf-8",
    )

    called = {"count": 0}

    async def fake_get_review_comments(*args, **kwargs):
        called["count"] += 1
        raise AssertionError("provider should not be called")

    monkeypatch.setattr(review_service, "DATA_DIR", tmp_path)
    monkeypatch.setattr(
        review_service,
        "get_review_comments",
        fake_get_review_comments,
    )

    result = asyncio.run(
        review_service.fetch_scan_product_review_comments("monitor-1", "scan-1")
    )

    assert result.reviews_state == "unsupported"
    assert result.comments == []
    assert called["count"] == 0


def test_fetch_scan_product_review_comments_updates_only_matching_product(
    tmp_path, monkeypatch
):
    import services.review_service as review_service

    (tmp_path / "monitored_categories.json").write_text(
        json.dumps(
            [
                {
                    "id": "monitor-1",
                    "brand": "aramis",
                    "url": "https://www.aramis.com.br/camisas",
                    "status": "active",
                }
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "monitored_products_monitor-1.json").write_text(
        json.dumps(
            [
                {
                    "scan_product_id": "scan-1",
                    "review_product_id": "123",
                    "url": "https://www.aramis.com.br/camisa/p",
                    "raw_title": "Camisa",
                },
                {
                    "scan_product_id": "scan-2",
                    "review_product_id": "456",
                    "url": "https://www.aramis.com.br/polo/p",
                    "raw_title": "Polo",
                },
            ]
        ),
        encoding="utf-8",
    )

    async def fake_get_review_comments(brand_key, product_id, max_pages=None):
        assert (brand_key, product_id, max_pages) == ("aramis", "123", 1)
        return ReviewCommentsResult(
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
            review_product_id=product_id,
            source_provider="trustvox",
            max_pages=1,
        )

    monkeypatch.setattr(review_service, "DATA_DIR", tmp_path)
    monkeypatch.setattr(
        review_service,
        "get_review_comments",
        fake_get_review_comments,
    )

    result = asyncio.run(
        review_service.fetch_scan_product_review_comments(
            "monitor-1",
            "scan-1",
            max_pages=1,
        )
    )

    assert result.reviews_state == "available"
    products = json.loads(
        (tmp_path / "monitored_products_monitor-1.json").read_text(encoding="utf-8")
    )
    assert products[0]["reviews_state"] == "available"
    assert products[0]["rating"] == 5.0
    assert products[0]["review_count"] == 1
    assert products[0]["review_comments"] == [
        {
            "review_id": "r1",
            "rating": 5.0,
            "title": None,
            "text": "Bom",
            "author": None,
            "created_at": None,
            "source_provider": "trustvox",
            "source_ref": None,
        }
    ]
    assert "reviews_state" not in products[1]


def test_vtex_parse_product_dict_sets_review_product_id(monkeypatch):
    import services.vtex_api_scraper as vtex_module
    from services.vtex_api_scraper import VtexApiClient
    from test_vtex_api_client import _PRODUCT

    async def fake_review(brand_key, product_id):
        return (4.5, 12)

    async def fake_color_family(domain, product_id):
        return []

    monkeypatch.setattr(vtex_module, "get_single_review", fake_review)
    client = VtexApiClient(brand_name="Aramis")
    monkeypatch.setattr(client, "_get_color_family", fake_color_family)

    result = asyncio.run(
        client.parse_product_dict(
            _PRODUCT,
            "https://www.aramis.com.br/camisa/p",
            "www.aramis.com.br",
        )
    )

    assert result.review_product_id == "12345"


def test_vtex_search_sets_review_product_id_without_full_comment_fetch(monkeypatch):
    import services.vtex_api_scraper as vtex_module
    from services.vtex_api_scraper import VtexApiClient
    from test_vtex_api_client import _PRODUCT

    class _Brand:
        brand_key = "aramis"
        brand_name = "Aramis"
        domain = "www.aramis.com.br"

    async def fake_request_json(self, url):
        if "_from=0" in url:
            return [_PRODUCT]
        return []

    async def fake_reviews(brand_key, product_ids):
        return {pid: (4.5, 12) for pid in product_ids}

    monkeypatch.setattr(vtex_module.brand_service, "get_brand", lambda brand_key: _Brand())
    monkeypatch.setattr(
        vtex_module,
        "resolve_query_to_vtex_category_path",
        lambda query, brand_key: None,
    )
    monkeypatch.setattr(vtex_module, "get_bulk_reviews", fake_reviews)
    monkeypatch.setattr(VtexApiClient, "_request_json", fake_request_json)

    from services.engines.base_engine import BaseEngine

    monkeypatch.setattr(
        BaseEngine,
        "filter_mens_fashion",
        staticmethod(lambda products: products),
    )

    result = asyncio.run(VtexApiClient("Aramis").search("camisa", max_results=1))

    assert result.products[0].review_product_id == "12345"
