import pytest
from pydantic import ValidationError

from core.banner_models import StoredBannerAsset
from services.banner_storage_service import friendly_banner_filename


def test_stored_asset_requires_sha256():
    with pytest.raises(ValidationError):
        StoredBannerAsset(sha256="../escape", extension="webp", content_type="image/webp", byte_count=1)


def test_friendly_filename_is_order_description_brand():
    assert friendly_banner_filename(1, "Sale Inverno", "Áramis", "webp") == "01-sale-inverno-aramis.webp"
    assert "/" not in friendly_banner_filename(2, "../../x", "foo\\bar", "png")

