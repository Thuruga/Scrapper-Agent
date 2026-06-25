"""
Hermetic test suite for the WakeEngine (Phase 32).

Test classes:
  - TestWakeFactory      : EngineFactory.get_engine wires WakeEngine (SC-3)
  - TestWakeEngineSearch : WakeEngine.search() with SessionManager mocked (SC-2)
  - TestWakeTokenFailure : Token absent → BrandSearchResult.error, never silent empty (SC-4 / D-07)
  - TestWakeModels       : DynamicBrandCreate.wake_access_token optional field (D-06)
  - TestWakeStubs        : discover_categories / calculate_shipping graceful stubs (D-08)

Mock seam: core.session_manager.SessionManager.get_session (aiohttp async session).
NO live network — the single real-network verification is the manual spike 007 (32-01).

Decisions confirmed by spike 007 (REPORT.md):
  - aliasComplete is relative ("produto/camisa-123") → prefixed with domain (Armadilha 2)
  - prices.price is float/int in reais (e.g. 479 = R$479), NOT centavos (Armadilha 4)
  - images is a list of {url: ...} objects (Armadilha 3)
  - Endpoint: https://storefront-api.fbits.net/graphql  (GRAPHQL_ENDPOINT)
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Mock seam — aiohttp via SessionManager (NOT BrowserManager — Wake is API-only)
# ---------------------------------------------------------------------------
_SESSION_GET_TARGET = "core.session_manager.SessionManager.get_session"

# ---------------------------------------------------------------------------
# GraphQL response fixture — mirrors spike 007 confirmed shape
# aliasComplete is relative (Armadilha 2); prices.price is float in reais (Armadilha 4)
# ---------------------------------------------------------------------------
_GRAPHQL_RESPONSE = {
    "data": {
        "search": {
            "products": {
                "edges": [
                    {
                        "node": {
                            "productName": "Camisa Slim Richards",
                            "aliasComplete": "produto/camisa-slim-123",
                            "prices": {"price": 799.0},
                            "images": [{"url": "https://www.richards.com.br/img/camisa.jpg"}],
                            "available": True,
                        }
                    }
                ]
            }
        }
    }
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_session_with_post(json_return_value: dict) -> MagicMock:
    """Build a mock aiohttp session whose .post() context manager returns json_return_value."""
    mock_resp = AsyncMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = AsyncMock(return_value=json_return_value)
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=mock_resp)
    return mock_session


def _make_brand_mock(
    *,
    brand_name: str = "Richards",
    domain: str = "www.richards.com.br",
    wake_access_token: str | None = "tcs_loja_test",
    engine: str = "wake",
) -> MagicMock:
    """Build a brand MagicMock with the attributes WakeEngine and EngineFactory expect."""
    mock_brand = MagicMock()
    mock_brand.brand_name = brand_name
    mock_brand.domain = domain
    mock_brand.wake_access_token = wake_access_token
    mock_brand.engine = engine
    return mock_brand


# ---------------------------------------------------------------------------
# TestWakeFactory — SC-3: EngineFactory wires WakeEngine for engine='wake'
# ---------------------------------------------------------------------------

class TestWakeFactory:
    """EngineFactory.get_engine returns WakeEngine for brands with engine='wake' (SC-3)."""

    def test_factory_returns_wake_engine(self):
        """SC-3: EngineFactory.get_engine for a wake brand returns WakeEngine, not NotImplementedError."""
        from services.engines.factory import EngineFactory
        from services.engines.wake_engine import WakeEngine

        mock_brand = _make_brand_mock(engine="wake")

        with patch(
            "services.engines.factory.brand_service.get_brand",
            return_value=mock_brand,
        ):
            engine = EngineFactory.get_engine("richards")

        assert isinstance(engine, WakeEngine), (
            f"Expected WakeEngine, got {type(engine).__name__}"
        )


# ---------------------------------------------------------------------------
# TestWakeEngineSearch — SC-2 / SC-4(shipping): search() + calculate_shipping()
# ---------------------------------------------------------------------------

class TestWakeEngineSearch:
    """WakeEngine.search() returns BrandSearchResult with products (SC-2).
    WakeEngine.calculate_shipping() returns None (SC-4 / D-08).
    """

    def test_search_returns_products(self):
        """SC-2: search('camisa') returns BrandSearchResult with ≥1 product.

        Each product must have:
          - product_name (non-empty title)
          - url starting with https://www.richards.com.br/ (NOT fbits.net — Armadilha 2)
          - price_full > 0 (reais float — Armadilha 4, NOT centavos)
        """
        from services.engines.wake_engine import WakeEngine
        from core.models import BrandSearchResult

        mock_session = _make_mock_session_with_post(_GRAPHQL_RESPONSE)
        mock_brand = _make_brand_mock(
            brand_name="Richards",
            domain="www.richards.com.br",
            wake_access_token="tcs_loja_test",
        )

        with patch(_SESSION_GET_TARGET, return_value=mock_session):
            with patch(
                "services.brand_service.brand_service.get_brand",
                return_value=mock_brand,
            ):
                engine = WakeEngine("richards")
                result = asyncio.run(engine.search("camisa", max_results=3))

        assert isinstance(result, BrandSearchResult)
        assert len(result.products) >= 1, "Expected ≥1 product from mocked GraphQL response"

        first = result.products[0]
        assert first.product_name, "product_name must be non-empty"
        assert first.url, "url must be non-empty"
        assert first.url.startswith("https://www.richards.com.br/"), (
            f"URL must start with https://www.richards.com.br/, got: {first.url} "
            "(Armadilha 2: aliasComplete is relative, must be prefixed with domain)"
        )
        assert first.price_full is not None and first.price_full > 0, (
            f"price_full must be a positive float in reais, got: {first.price_full}"
        )

    def test_search_result_url_not_fbits(self):
        """Armadilha 2: product URL must NOT contain fbits.net (must be the store domain)."""
        from services.engines.wake_engine import WakeEngine

        mock_session = _make_mock_session_with_post(_GRAPHQL_RESPONSE)
        mock_brand = _make_brand_mock(
            brand_name="Richards",
            domain="www.richards.com.br",
            wake_access_token="tcs_loja_test",
        )

        with patch(_SESSION_GET_TARGET, return_value=mock_session):
            with patch(
                "services.brand_service.brand_service.get_brand",
                return_value=mock_brand,
            ):
                engine = WakeEngine("richards")
                result = asyncio.run(engine.search("camisa", max_results=3))

        for product in result.products:
            assert "fbits.net" not in product.url, (
                f"URL must not contain fbits.net: {product.url} — "
                "aliasComplete must be prefixed with the store domain, not the GraphQL endpoint"
            )

    def test_calculate_shipping_returns_none(self):
        """SC-4 / D-08: calculate_shipping returns None — no false 'Frete Grátis' badge."""
        from services.engines.wake_engine import WakeEngine

        engine = WakeEngine("richards")
        result = asyncio.run(engine.calculate_shipping(product={}, zipcode="01310-000"))
        assert result is None, (
            f"calculate_shipping must return None (D-08), got: {result}"
        )


# ---------------------------------------------------------------------------
# TestWakeTokenFailure — SC-4 / D-07: token absent → BrandSearchResult.error
# ---------------------------------------------------------------------------

class TestWakeTokenFailure:
    """Token not resolved → BrandSearchResult.error set, never silent empty list (D-07 / SC-4)."""

    def test_missing_token_returns_error(self):
        """D-07 / SC-4: brand.wake_access_token=None + auto-extraction fails → error in result.

        Verified via search_all_brands() → _search_one() → catches ValueError from WakeEngine
        and surfaces it as BrandSearchResult.error (never 0 products silently).
        """
        from services.engines.factory import EngineFactory
        from core.models import BrandSearchResult

        # Brand registered as engine="wake" but no token override
        mock_brand = _make_brand_mock(engine="wake", wake_access_token=None)

        with patch(
            "services.engines.factory.brand_service.get_brand",
            return_value=mock_brand,
        ):
            with patch(
                "services.brand_service.brand_service.get_brand",
                return_value=mock_brand,
            ):
                # Auto-extraction (GET home page) also fails — no token can be resolved
                with patch(
                    _SESSION_GET_TARGET,
                    side_effect=Exception("network error — no token auto-extraction"),
                ):
                    results = asyncio.run(
                        EngineFactory().search_all_brands("camisa", brands=["richards"])
                    )

        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        result = results[0]
        assert isinstance(result, BrandSearchResult)
        assert result.error is not None, "error must be set (not None) when token is absent"
        assert result.error != "", "error must be non-empty string — never silent failure"
        # Must NOT silently return 0 products with no error
        assert not (len(result.products) == 0 and result.error is None), (
            "D-07: 0 products with error=None is the forbidden silent failure pattern"
        )


# ---------------------------------------------------------------------------
# TestWakeModels — D-06: wake_access_token Optional field in DynamicBrandCreate
# ---------------------------------------------------------------------------

class TestWakeModels:
    """DynamicBrandCreate.wake_access_token is optional (D-06)."""

    def test_model_wake_token_optional(self):
        """D-06: DynamicBrandCreate validates without wake_access_token → None by default."""
        from core.models import DynamicBrandCreate

        brand = DynamicBrandCreate(
            brand_key="x",
            brand_name="X",
            domain="x.com",
        )
        assert brand.wake_access_token is None, (
            f"wake_access_token must default to None when not provided, got: {brand.wake_access_token}"
        )

    def test_model_wake_token_explicit_value_preserved(self):
        """D-06: DynamicBrandCreate preserves explicit wake_access_token override."""
        from core.models import DynamicBrandCreate

        expected_token = "tcs_loja_abc123"
        brand = DynamicBrandCreate(
            brand_key="richards",
            brand_name="Richards",
            domain="www.richards.com.br",
            wake_access_token=expected_token,
        )
        assert brand.wake_access_token == expected_token, (
            f"wake_access_token must preserve explicit value, got: {brand.wake_access_token}"
        )

    def test_model_existing_brands_unaffected(self):
        """D-06: Existing brands without wake_access_token remain valid (Optional field)."""
        from core.models import DynamicBrandCreate

        # Simulate an existing brand that has no wake_access_token field in payload
        brand = DynamicBrandCreate(
            brand_key="aramis",
            brand_name="Aramis",
            domain="www.aramis.com.br",
            engine="vtex",
        )
        assert brand.wake_access_token is None, (
            "Existing brands without wake_access_token must remain valid (D-06 backward compat)"
        )


# ---------------------------------------------------------------------------
# TestWakeStubs — D-08: graceful stubs return [] without crash
# ---------------------------------------------------------------------------

class TestWakeStubs:
    """WakeEngine graceful stubs: discover_categories / get_catalog return [] (D-08)."""

    def test_discover_categories_stub(self):
        """D-08: discover_categories() returns [] without crash (graceful stub)."""
        from services.engines.wake_engine import WakeEngine

        engine = WakeEngine("richards")
        result = asyncio.run(engine.discover_categories())
        assert result == [], (
            f"discover_categories must return [] (D-08 graceful stub), got: {result}"
        )

    def test_get_catalog_stub(self):
        """D-08: get_catalog() returns [] without crash (graceful stub)."""
        from services.engines.wake_engine import WakeEngine

        engine = WakeEngine("richards")
        result = asyncio.run(engine.get_catalog())
        assert result == [], (
            f"get_catalog must return [] (D-08 graceful stub), got: {result}"
        )

    def test_get_product_details_stub(self):
        """D-10: get_product_details() returns None without crash (no PDP enrichment in phase)."""
        from services.engines.wake_engine import WakeEngine

        engine = WakeEngine("richards")
        result = asyncio.run(engine.get_product_details("https://www.richards.com.br/produto/123"))
        assert result is None, (
            f"get_product_details must return None (D-10 stub), got: {result}"
        )
