import json
import asyncio
from pathlib import Path

from core.models import DynamicBrand, ReviewComment, ReviewCommentsResult
from services.brand_service import BrandDatabase


BRANDS_PATH = Path("backend/data/brands.json")


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
