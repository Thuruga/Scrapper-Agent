import asyncio
from pathlib import Path

import pytest

from services.banner_extraction_service import BannerExtractionService, is_safe_public_http_url, normalize_image_content_type
from services.banner_storage_service import BannerStorageService


FIXTURE = Path(__file__).parent / "fixtures" / "banner_carousels.html"


def test_public_url_policy_rejects_local_and_non_http():
    assert not is_safe_public_http_url("file:///etc/passwd")
    assert not is_safe_public_http_url("http://localhost/admin")
    assert not is_safe_public_http_url("http://127.0.0.1/admin")
    assert not is_safe_public_http_url("http://169.254.169.254/latest/meta-data")
    assert is_safe_public_http_url("https://example.com/banner.webp", resolve_dns=False)


def test_octet_stream_uses_safe_url_extension_or_image_signature():
    assert normalize_image_content_type("application/octet-stream", "https://cdn.example/banner.webp?x=1", b"x") == "image/webp"
    assert normalize_image_content_type("", "https://cdn.example/image", b"\x89PNG\r\n\x1a\nrest") == "image/png"
    with pytest.raises(ValueError):
        normalize_image_content_type("application/octet-stream", "https://cdn.example/file.bin", b"not-an-image")


def test_cancelled_before_collection_does_no_browser_or_file_work(tmp_path):
    service = BannerExtractionService(BannerStorageService(tmp_path))
    event = asyncio.Event(); event.set()
    with pytest.raises(InterruptedError):
        service.collect_page(None, "aramis", "Aramis", event)
    assert list((tmp_path / "assets").iterdir()) == []


def test_fixture_discovers_images_after_video_and_excludes_lower_false_positive(tmp_path):
    sync_api = pytest.importorskip("playwright.sync_api")
    storage = BannerStorageService(tmp_path)
    fetched = []

    def fake_fetch(_context, url, _referer):
        fetched.append(url)
        return f"bytes:{url}".encode(), "image/webp"

    service = BannerExtractionService(storage, max_slides=4, asset_fetcher=fake_fetch)
    try:
        with sync_api.sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1366, "height": 768})
            page.set_content(FIXTURE.read_text(encoding="utf-8"), wait_until="load")
            result = service.collect_page(page, "aramis", "Aramis")
            browser.close()
    except Exception as exc:
        if "Executable doesn't exist" in str(exc):
            pytest.skip("Playwright Chromium is not installed")
        raise

    assert [b.source_url for b in result.banners] == [
        "https://example.com/first-2200.webp",
        "https://example.com/third.webp",
    ]
    assert result.banners[0].rendered_url.endswith("first-1366.webp")
    assert result.banners[0].friendly_filename == "01-sale-inverno-aramis.webp"
    assert [v.source_url for v in result.videos] == ["https://example.com/interstitial.mp4"]
    assert all("product.webp" not in url for url in fetched)
    assert storage.resolve_asset(result.screenshot_asset).exists()


def test_video_without_declared_slide_count_does_not_stop_next_image(tmp_path):
    sync_api = pytest.importorskip("playwright.sync_api")
    html = FIXTURE.read_text(encoding="utf-8").replace(
        '<i aria-label="Slide 1 of 3"></i><i aria-label="Slide 2 of 3"></i><i aria-label="Slide 3 of 3"></i>',
        "",
    )
    service = BannerExtractionService(
        BannerStorageService(tmp_path), max_slides=4,
        asset_fetcher=lambda _context, url, _referer: (url.encode(), "image/webp"),
    )
    try:
        with sync_api.sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1366, "height": 768})
            page.set_content(html)
            result = service.collect_page(page, "aramis", "Aramis")
            browser.close()
    except Exception as exc:
        if "Executable doesn't exist" in str(exc):
            pytest.skip("Playwright Chromium is not installed")
        raise
    assert [b.slide_order for b in result.banners] == [1, 2]
