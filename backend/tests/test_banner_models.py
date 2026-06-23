from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from core.banner_models import StoredBannerAsset
from services.banner_storage_service import friendly_banner_filename


def test_stored_asset_requires_sha256():
    with pytest.raises(ValidationError):
        StoredBannerAsset(sha256="../escape", extension="webp", content_type="image/webp", byte_count=1)


def test_friendly_filename_format():
    captured_at = datetime(2026, 6, 23, 12, 0, tzinfo=timezone.utc)
    filename = friendly_banner_filename(1, "Sale Inverno", "Áramis", "webp", captured_at)
    assert filename == "06-2026-aramis-01.webp"
    assert "/" not in friendly_banner_filename(2, "../../x", "foo\\bar", "png")
