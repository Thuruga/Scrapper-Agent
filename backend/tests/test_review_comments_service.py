import json
from pathlib import Path

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
