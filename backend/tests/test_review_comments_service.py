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


def test_brands_json_does_not_commit_wake_access_tokens():
    rows = _load_brand_rows()

    for brand_key, row in rows.items():
        assert row.get("wake_access_token") in (None, ""), brand_key


def test_aramis_remains_trustvox_with_existing_store_id():
    rows = _load_brand_rows()

    aramis = rows["aramis"]

    assert aramis["review_provider"] == "trustvox"
    assert aramis["review_store_id"] == "114327"
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


def test_trustvox_opinion_items_normalize_nested_user_author():
    import services.review_service as review_service

    data = {
        "items": [
            {
                "id": 35297171,
                "rate": 5,
                "created_at": "01/06/2026",
                "user": {"name": "Wendell C."},
                "comments": [],
            }
        ]
    }

    [entry] = review_service._extract_comment_entries(data)
    comment = review_service._normalize_comment(
        entry,
        provider="trustvox",
        product_id="74291",
    )

    assert comment.review_id == "35297171"
    assert comment.rating == 5.0
    assert comment.author == "Wendell C."
    assert comment.created_at == "01/06/2026"
    assert comment.source_provider == "trustvox"


def test_fetch_trustvox_comments_reads_root_summary_and_opinion_items(monkeypatch):
    import services.review_service as review_service

    calls = []
    session = _FakeAiohttpSession(
        [
            (200, {"rate": {"average": 5, "count": 3}}),
            (
                200,
                {
                    "items": [
                        {
                            "id": 35297171,
                            "rate": 5,
                            "created_at": "01/06/2026",
                            "user": {"name": "Wendell C."},
                            "comments": [],
                        }
                    ]
                },
            ),
        ],
        calls,
    )
    monkeypatch.setattr(
        review_service.aiohttp,
        "ClientSession",
        lambda timeout: session,
    )

    result = asyncio.run(
        review_service._fetch_trustvox_comments(
            _brand(store_id="114327"),
            "74291",
            max_pages=1,
        )
    )

    assert [call["url"] for call in calls] == [
        "https://trustvox.com.br/widget/root",
        "https://trustvox.com.br/widget/opinions",
    ]
    assert calls[1]["params"] == {"store_id": "114327", "code": "74291", "page": 1}
    assert result.reviews_state == "available"
    assert result.rating == 5.0
    assert result.review_count == 3
    assert len(result.comments) == 1
    assert result.comments[0].author == "Wendell C."


def test_fetch_trustvox_comments_treats_opinion_failure_as_temporary_failure(
    monkeypatch,
):
    import services.review_service as review_service

    session = _FakeAiohttpSession(
        [
            (200, {"rate": {"average": 5, "count": 3}}),
            (500, {"error": "temporarily unavailable"}),
        ],
        [],
    )
    monkeypatch.setattr(
        review_service.aiohttp,
        "ClientSession",
        lambda timeout: session,
    )

    result = asyncio.run(
        review_service._fetch_trustvox_comments(
            _brand(store_id="114327"),
            "74291",
            max_pages=1,
        )
    )

    assert result.reviews_state == "temporary_failure"
    assert result.rating == 5.0
    assert result.review_count == 3
    assert result.comments == []


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

    async def fake_engine_summary(*args, **kwargs):
        return None

    monkeypatch.setattr(review_service, "DATA_DIR", tmp_path)
    monkeypatch.setattr(
        review_service,
        "_fetch_engine_review_summary",
        fake_engine_summary,
    )
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


def test_fetch_scan_product_review_comments_uses_engine_summary_without_provider(
    tmp_path, monkeypatch
):
    import services.review_service as review_service

    (tmp_path / "monitored_categories.json").write_text(
        json.dumps(
            [
                {
                    "id": "monitor-1",
                    "brand": "amazon",
                    "url": "https://www.amazon.com.br/s?k=camisa",
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
                    "url": "https://www.amazon.com.br/dp/B123",
                    "raw_title": "Camisa",
                }
            ]
        ),
        encoding="utf-8",
    )

    class _Engine:
        async def get_pdp_product(self, url):
            return {"rating": 4.6, "review_count": 128}

    import services.engines.factory as engine_factory_module

    monkeypatch.setattr(review_service, "DATA_DIR", tmp_path)
    monkeypatch.setattr(
        engine_factory_module.engine_factory,
        "get_engine",
        lambda brand_key: _Engine(),
    )

    result = asyncio.run(
        review_service.fetch_scan_product_review_comments("monitor-1", "scan-1")
    )

    assert result.reviews_state == "available"
    assert result.rating == 4.6
    assert result.review_count == 128
    assert result.comments == []
    products = json.loads(
        (tmp_path / "monitored_products_monitor-1.json").read_text(encoding="utf-8")
    )
    assert products[0]["reviews_state"] == "available"
    assert products[0]["review_count"] == 128


def test_summary_result_from_product_reads_aggregate_rating():
    import services.review_service as review_service

    result = review_service._summary_result_from_product(
        {
            "aggregateRating": {
                "ratingValue": "4,7",
                "reviewCount": "1.234",
            }
        },
        provider="engine-summary",
        max_pages=1,
    )

    assert result is not None
    assert result.reviews_state == "available"
    assert result.rating == 4.7
    assert result.review_count == 1234


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


class _FakeAiohttpResponse:
    def __init__(self, status, payload):
        self.status = status
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self, content_type=None):
        return self._payload


class _FakeAiohttpSession:
    def __init__(self, responses, calls):
        self._responses = list(responses)
        self._calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get(self, url, params=None, headers=None):
        self._calls.append({"url": url, "params": params, "headers": headers})
        if not self._responses:
            raise AssertionError(f"No fake response for {url}")
        status, payload = self._responses.pop(0)
        return _FakeAiohttpResponse(status, payload)
