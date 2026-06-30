"""Unit tests for services.url_utils.normalize_url (UX-04 / D-08).

Pure unit tests — no async, no network, no filesystem I/O.
Covers the four canonical behaviours the validation map requires:
  (a) tracking-param strip with SKU preservation
  (b) www. removal
  (c) https enforcement
  (d) distinct-SKU non-merge (dedup must not collide on different skuIds)
"""

from services.url_utils import normalize_url


# ---------------------------------------------------------------------------
# (a) Tracking-param strip + SKU preservation
# ---------------------------------------------------------------------------

def test_normalize_strips_utm():
    """utm_source, utm_campaign, gclid, fbclid are dropped; skuId=123 kept."""
    url = "https://www.example.com/produto?utm_source=google&utm_campaign=sale&gclid=abc&fbclid=xyz&skuId=123"
    result = normalize_url(url)
    assert "utm_source" not in result
    assert "utm_campaign" not in result
    assert "gclid" not in result
    assert "fbclid" not in result
    assert "skuId=123" in result


def test_normalize_strips_all_tracking_variants():
    """All known tracking params in _TRACKING_PARAMS are removed."""
    url = (
        "https://example.com/p"
        "?utm_source=a&utm_medium=b&utm_campaign=c&utm_term=d"
        "&utm_content=e&utm_id=f&gclid=g&fbclid=h&msclkid=i&dclid=j"
        "&skuId=999"
    )
    result = normalize_url(url)
    for param in ("utm_source", "utm_medium", "utm_campaign", "utm_term",
                  "utm_content", "utm_id", "gclid", "fbclid", "msclkid", "dclid"):
        assert param not in result, f"{param} was not stripped"
    assert "skuId=999" in result


def test_normalize_strips_dynamic_utm_prefix():
    """Keys that start with utm_ but are not in the hardcoded set are also dropped."""
    url = "https://example.com/p?utm_custom_param=foo&skuId=7"
    result = normalize_url(url)
    assert "utm_custom_param" not in result
    assert "skuId=7" in result


# ---------------------------------------------------------------------------
# (b) www. removal
# ---------------------------------------------------------------------------

def test_normalize_removes_www():
    """Leading www. in host is stripped; trailing / in path is stripped."""
    result = normalize_url("https://www.example.com/path/")
    assert result == "https://example.com/path"


def test_normalize_does_not_corrupt_wwww_host():
    """A host starting with 'wwww' is not incorrectly trimmed."""
    result = normalize_url("https://wwww.example.com/page")
    assert "wwww.example.com" in result


# ---------------------------------------------------------------------------
# (c) https enforcement
# ---------------------------------------------------------------------------

def test_normalize_forces_https():
    """http scheme is replaced with https regardless of case."""
    result = normalize_url("http://example.com/page")
    assert result.startswith("https://")


def test_normalize_forces_https_from_http_with_uppercase_host():
    """http + uppercase host → https + lowercase host."""
    result = normalize_url("http://EXAMPLE.COM/x")
    assert result == "https://example.com/x"


# ---------------------------------------------------------------------------
# (d) Distinct SKUs must normalize to DIFFERENT strings
# ---------------------------------------------------------------------------

def test_normalize_preserves_distinct_skus():
    """Two URLs differing only by skuId must NOT be merged by normalize_url."""
    url_a = "https://example.com/produto?skuId=1"
    url_b = "https://example.com/produto?skuId=2"
    assert normalize_url(url_a) != normalize_url(url_b)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_normalize_malformed_returns_original():
    """A string with no valid host returns the original input unchanged."""
    bad = "not-a-url"
    assert normalize_url(bad) == bad


def test_normalize_no_trailing_slash_on_root():
    """Root path without trailing slash is kept as '/'."""
    result = normalize_url("https://example.com")
    # Root of host — path should be '/'
    assert result == "https://example.com/"


def test_normalize_strips_trailing_slash_non_root():
    """Non-root path trailing slash is stripped."""
    result = normalize_url("https://example.com/categoria/")
    assert result == "https://example.com/categoria"
