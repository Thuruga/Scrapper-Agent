"""Wave-0 scaffolds for POST /brands/identify tests (UX-03).

These tests are the RED targets for Plan 40-02 (identify endpoint).
They are guarded so the suite stays collectable and green before
identify_brand / infer_brand_name are implemented:

  - test_identify_returns_engine_and_name  — dry-run, no brand persisted
  - test_infer_brand_name                  — 4 fallback cases
  - test_identify_rejects_ssrf             — non-http(s) + RFC1918 rejected

All three tests collect without error even if the symbols do not exist yet:
a module-level importability guard flips them to xfail(strict=False) when
api.routes_brands lacks the required symbols, so Wave 1 is always green.
Plan 02 landing makes them pass for real.
"""

from __future__ import annotations

import importlib
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# Importability guard
# ---------------------------------------------------------------------------
# Check whether the symbols Plan 02 will create already exist.
# If they don't, mark every test in this file as expected-fail (non-strict)
# so the overall suite stays green.

def _has_identify_symbols() -> bool:
    """Return True if routes_brands exposes identify_brand and infer_brand_name."""
    try:
        mod = importlib.import_module("api.routes_brands")
        return (
            hasattr(mod, "identify_brand")
            and hasattr(mod, "infer_brand_name")
        )
    except Exception:
        return False


_SYMBOLS_EXIST = _has_identify_symbols()

_xfail_if_missing = pytest.mark.xfail(
    not _SYMBOLS_EXIST,
    strict=False,
    reason="identify_brand / infer_brand_name not yet implemented (Plan 40-02)",
)


# ---------------------------------------------------------------------------
# test_identify_returns_engine_and_name
# ---------------------------------------------------------------------------

@_xfail_if_missing
@pytest.mark.asyncio
async def test_identify_returns_engine_and_name():
    """POST /brands/identify is a dry-run — returns engine+name+domain, never persists.

    Expectation (Plan 02 target):
    - Response body contains keys: engine, inferred_name, domain
    - brand_service.add_brand is NOT called (dry-run invariant, D-02)
    """
    import api.routes_brands as rb

    # Patch detect_engine to return a fixed tuple (engine, html)
    with patch.object(
        rb,
        "detect_engine",
        new_callable=AsyncMock,
        return_value=("vtex", None),
    ), patch.object(
        rb,
        "infer_brand_name",
        return_value="Example Brand",
    ), patch.object(
        rb.brand_service,
        "add_brand",
    ) as mock_add:
        # Call identify_brand directly (FastAPI endpoint function)
        # Plan 02 should define: async def identify_brand(request: IdentifyBrandRequest)
        # or accept a Pydantic model — we call it with a mock request object.
        request_obj = MagicMock()
        request_obj.url = "https://www.example.com/produto/camisa-1234"

        result = await rb.identify_brand(request_obj)

        # The endpoint must NOT persist the brand
        mock_add.assert_not_called()

        # The response must carry the three required keys
        if hasattr(result, "__dict__"):
            data = result.__dict__
        elif hasattr(result, "model_dump"):
            data = result.model_dump()
        else:
            data = dict(result)

        assert "engine" in data, f"Missing 'engine' in response: {data}"
        assert "inferred_name" in data, f"Missing 'inferred_name' in response: {data}"
        assert "domain" in data, f"Missing 'domain' in response: {data}"
        assert data["engine"] == "vtex"


# ---------------------------------------------------------------------------
# test_infer_brand_name
# ---------------------------------------------------------------------------

@_xfail_if_missing
def test_infer_brand_name():
    """infer_brand_name resolves brand name in order: JSON-LD → OG → <title> → domain.

    Four test cases per validation map:
      1. JSON-LD Organization/name
      2. OG site_name meta tag
      3. <title> element
      4. Domain fallback (host-only extraction)
    """
    import api.routes_brands as rb
    from bs4 import BeautifulSoup

    domain = "example.com"

    # Case 1: JSON-LD Organization name
    html_jsonld = """
    <html><head>
      <script type="application/ld+json">{"@type":"Organization","name":"Example Corp"}</script>
    </head><body></body></html>
    """
    soup = BeautifulSoup(html_jsonld, "html.parser")
    result = rb.infer_brand_name(soup, domain)
    assert result == "Example Corp", f"JSON-LD case failed: {result}"

    # Case 2: OG site_name (fallback when no JSON-LD)
    html_og = """
    <html><head>
      <meta property="og:site_name" content="My OG Brand" />
    </head><body></body></html>
    """
    soup = BeautifulSoup(html_og, "html.parser")
    result = rb.infer_brand_name(soup, domain)
    assert result == "My OG Brand", f"OG site_name case failed: {result}"

    # Case 3: <title> element (fallback when no JSON-LD and no OG)
    html_title = """
    <html><head><title>Title Brand - Shop</title></head><body></body></html>
    """
    soup = BeautifulSoup(html_title, "html.parser")
    result = rb.infer_brand_name(soup, domain)
    # Title is used as-is or first segment — accept any non-empty string from title
    assert result, f"<title> case returned empty: {result}"

    # Case 4: Domain fallback when HTML carries no useful signal
    html_empty = "<html><head></head><body></body></html>"
    soup = BeautifulSoup(html_empty, "html.parser")
    result = rb.infer_brand_name(soup, "hugoboss.com.br")
    # Domain fallback should yield something like "Hugoboss" or "Hugo Boss"
    assert result, f"Domain fallback case returned empty: {result}"
    assert "hugoboss" in result.lower() or "hugo" in result.lower(), (
        f"Domain fallback '{result}' doesn't look like 'hugoboss': {result}"
    )


# ---------------------------------------------------------------------------
# test_identify_rejects_ssrf
# ---------------------------------------------------------------------------

@_xfail_if_missing
@pytest.mark.asyncio
async def test_identify_rejects_ssrf():
    """POST /brands/identify rejects non-http(s) schemes and RFC1918 private IPs.

    Security requirement T-40-SSRF:
      - file://, ftp://, javascript: → HTTP 400
      - 192.168.x.x, 10.x.x.x, 172.16-31.x.x → HTTP 400
      - localhost → HTTP 400
    """
    import api.routes_brands as rb
    from fastapi import HTTPException

    ssrf_cases = [
        "file:///etc/passwd",
        "ftp://example.com/file",
        "javascript:alert(1)",
        "https://192.168.1.1/admin",
        "https://10.0.0.1/secret",
        "https://172.16.0.1/internal",
        "https://localhost/admin",
        "http://127.0.0.1:8080/api",
    ]

    for bad_url in ssrf_cases:
        request_obj = MagicMock()
        request_obj.url = bad_url

        with pytest.raises(HTTPException) as exc_info:
            await rb.identify_brand(request_obj)

        assert exc_info.value.status_code == 400, (
            f"Expected 400 for SSRF URL '{bad_url}', "
            f"got {exc_info.value.status_code}"
        )
