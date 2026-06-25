"""
Wake Commerce engine.

Extracts product catalog and price data from Wake Commerce storefronts via
the public GraphQL Storefront API (storefront-api.fbits.net/graphql) using
a TCS-Access-Token per store.  Target: Richards (www.richards.com.br).

Design decisions from Phase 32 CONTEXT.md and confirmed by spike 007:
  - D-05: Auto-extract TCS-Access-Token from the storefront home page via
          regex; cache per instance; support manual override via brand field.
  - D-06: Optional field wake_access_token in DynamicBrandCreate allows
          operators to hard-code the token without relying on auto-extraction.
  - D-07: Token not resolved -> raise ValueError (clear diagnostic message);
          captured by factory._search_one as BrandSearchResult.error —
          never 0 products silently.
  - D-08: calculate_shipping -> None (no public checkout);
          discover_categories / get_catalog -> [] (graceful stubs).
  - D-09: Instantiated by EngineFactory.get_engine for engine_type='wake'.
  - D-10: Single GraphQL search query returns title + URL + price directly.
          No PDP enrichment round-trip.
  - D-11: aiohttp via SessionManager only; no browser rendering.

Security (threat model):
  - T-32-01 (open-redirect): allow_redirects=False in aiohttp GET for
             token auto-extraction — same pattern as T-25-01-SR.
  - T-32-02 (tampering / GraphQL injection): query sent as a GraphQL
             variable ($q: String!) — never string-interpolated into the
             query body.
  - T-32-05 (repudiation): ValueError raised on token absence; caught by
             _search_one and surfaced as BrandSearchResult.error.
  - T-32-06 (token leak): cache stored as instance attribute (_token_cache),
             never as a class variable — prevents cross-brand token leakage
             in concurrent asyncio.gather calls.

Spike 007 confirmed (REPORT.md):
  - Endpoint: https://storefront-api.fbits.net/graphql  -> HTTP 200
  - aliasComplete is relative: "produto/camisa-linho-hortencia-196863"
  - prices.price is int/float in reais (e.g. 479), NOT centavos
  - images[].url present in search.products.edges.node
  - available field present and correct
  - Token extracted via storefrontAccessToken regex from home page HTML
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from core.models import BrandSearchResult, SearchProductResult
from core.session_manager import SessionManager
from services.engines.base_engine import BaseEngine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level constants (D-10 / T-32-02)
# ---------------------------------------------------------------------------

GRAPHQL_ENDPOINT: str = "https://storefront-api.fbits.net/graphql"
"""Public Wake Commerce GraphQL endpoint — confirmed by spike 007."""

DEFAULT_MAX_RESULTS: int = 10
"""Default number of products returned per search call."""

_TOKEN_RE = re.compile(
    r"""storefrontAccessToken\s*:\s*['"]([^'"]+)['"]""",
    re.IGNORECASE,
)
"""Regex that extracts the storefront access token from the Wake SDK inline
script injected into the store home page HTML.  Confirmed working against
www.richards.com.br by spike 007 (strategy: regex storefrontAccessToken)."""

# ---------------------------------------------------------------------------
# GraphQL query (WakeSearch) — confirmed field set from spike 007
# ---------------------------------------------------------------------------

_WAKE_SEARCH_QUERY: str = """
query WakeSearch($q: String!, $first: Int!) {
  search(query: $q) {
    products(first: $first) {
      edges {
        node {
          productName
          aliasComplete
          prices {
            price
          }
          images {
            url
          }
          available
        }
      }
    }
  }
}
""".strip()


class WakeEngine(BaseEngine):
    """Engine for Wake Commerce storefronts (e.g. Richards, Shop2gether).

    Uses the public GraphQL Storefront API with a TCS-Access-Token resolved
    per store instance (D-05/D-06).  No browser required — aiohttp only.
    """

    def __init__(self, brand_key: str) -> None:
        self.brand_key = brand_key
        self._token_cache: Optional[str] = None  # per-instance cache (T-32-06 / Armadilha 5)

    # ------------------------------------------------------------------
    # BaseEngine contract: metadata
    # ------------------------------------------------------------------

    def get_engine_name(self) -> str:
        return "Wake"

    # ------------------------------------------------------------------
    # BaseEngine contract: search (D-10 / D-11)
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        max_results: int = DEFAULT_MAX_RESULTS,
        sort: Optional[str] = None,
        only_in_stock: bool = False,
        zipcode: Optional[str] = None,
        include_shipping: bool = False,
    ) -> BrandSearchResult:
        """Search Wake Commerce via GraphQL and return a BrandSearchResult.

        Steps:
          1. Resolve brand data (domain, brand_name) from brand_service.
          2. Resolve TCS-Access-Token (override > cache > auto-extract).
          3. POST GraphQL WakeSearch query with variables (T-32-02).
          4. Parse search.products.edges[].node into product dicts.
          5. Apply Quality Gates: filter_mens_fashion -> validate_single.
          6. Return BrandSearchResult.
        """
        from services.brand_service import brand_service  # lazy — avoid circular import

        brand = brand_service.get_brand(self.brand_key)

        # Resolve domain and brand_name with dict/Pydantic compat (PATTERNS §Shared)
        domain: str = ""
        brand_name: str = self.brand_key
        if brand:
            domain = getattr(brand, "domain", None) or (
                brand.get("domain", "") if isinstance(brand, dict) else ""
            )
            brand_name = getattr(brand, "brand_name", None) or (
                brand.get("brand_name", self.brand_key) if isinstance(brand, dict) else self.brand_key
            )

        if not domain:
            # Fallback — enables smoke-testing before brand is formally onboarded
            domain = f"{self.brand_key}.com.br"
            logger.info(
                "[Wake] no registered domain for brand_key=%s; using fallback domain=%s",
                self.brand_key,
                domain,
            )

        # Resolve token — D-07: ValueError on failure, never 0-products silently
        token = await self._resolve_token(brand, domain)
        if not token:
            raise ValueError(
                f"Token Wake nao resolvido para '{self.brand_key}'. "
                "Configure wake_access_token na marca ou verifique o storefront."
            )

        # POST GraphQL — T-32-02: variables, not f-string interpolation
        session = await SessionManager.get_session()
        payload = {
            "query": _WAKE_SEARCH_QUERY,
            "variables": {
                "q": query.strip(),
                "first": max_results,
            },
        }
        headers = {"TCS-Access-Token": token}

        try:
            async with session.post(GRAPHQL_ENDPOINT, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except Exception as exc:
            logger.warning("[Wake] GraphQL request failed for brand=%s: %s", self.brand_key, exc)
            return BrandSearchResult(
                brand_key=self.brand_key,
                brand_name=brand_name,
                error=f"GraphQL request failed: {exc}",
            )

        # Parse response — spike 007 confirmed the nested path
        edges: List[Dict[str, Any]] = (
            data.get("data", {})
            .get("search", {})
            .get("products", {})
            .get("edges", [])
        )

        parsed_dicts: List[Dict[str, Any]] = []
        for edge in edges:
            node = edge.get("node", {})
            product_name = node.get("productName", "")
            alias = node.get("aliasComplete", "")
            # Armadilha 2: aliasComplete is relative (e.g. "produto/camisa-123")
            product_url = f"https://{domain}/{alias.lstrip('/')}" if alias else ""
            # Armadilha 4: prices.price is float/int in reais, NOT centavos (spike confirmed 479 for R$479)
            prices = node.get("prices") or {}
            price_raw = prices.get("price")
            price_full = float(price_raw) if price_raw is not None else None
            # Armadilha 3: images is a list (confirmed in spike 007)
            images = node.get("images") or []
            image_url = images[0].get("url") if images else None
            available = node.get("available", True)

            if not product_name or not product_url or price_full is None:
                logger.debug("[Wake] skipping incomplete node: %s", node)
                continue

            parsed_dicts.append(
                {
                    "raw_title": product_name,
                    "url": product_url,
                    "price_full": price_full,
                    "image_url": image_url,
                    "brand": brand_name,
                    "raw_description": "",
                    "stock_availability": bool(available),
                }
            )

        # Quality Gates (CAT-01 + Pydantic) — order is mandatory (PATTERNS §Quality Gates)
        filtered = self.filter_mens_fashion(parsed_dicts)
        validated: List[SearchProductResult] = []
        for p in filtered:
            validated_dict = self.validate_single(p)
            if validated_dict:
                validated.append(
                    SearchProductResult(
                        brand=brand_name,
                        product_name=validated_dict["raw_title"],
                        url=validated_dict["url"],
                        price_full=validated_dict.get("price_full"),
                        image_url=validated_dict.get("image_url"),
                        available=validated_dict.get("stock_availability"),
                    )
                )

        logger.info(
            "[Wake] search brand=%s query=%r -> %d products (after quality gates)",
            self.brand_key,
            query,
            len(validated),
        )

        return BrandSearchResult(
            brand_key=self.brand_key,
            brand_name=brand_name,
            products=validated,
            total_found=len(validated),
        )

    # ------------------------------------------------------------------
    # Token resolution (D-05 / D-06 / D-07)
    # ------------------------------------------------------------------

    async def _resolve_token(self, brand: Any = None, domain: str = "") -> Optional[str]:
        """Resolve TCS-Access-Token with strict precedence (Armadilha 1):

        1. Manual override from brand.wake_access_token (D-06)
        2. In-memory instance cache (T-32-06 — per-instance, not class-level)
        3. Auto-extraction via GET to the store home page (D-05 / T-32-01)
        4. Return None -> caller raises ValueError (D-07)
        """
        # 1. Manual override
        if brand is not None:
            override: Optional[str] = getattr(brand, "wake_access_token", None) or (
                brand.get("wake_access_token") if isinstance(brand, dict) else None
            )
            if override:
                logger.debug("[Wake] using manual token override for brand_key=%s", self.brand_key)
                return override

        # 2. Instance cache (avoids re-fetching home page on every search call)
        if self._token_cache:
            logger.debug("[Wake] using cached token for brand_key=%s", self.brand_key)
            return self._token_cache

        # 3. Auto-extraction from the store home page
        if not domain:
            return None

        store_url = f"https://{domain}"
        logger.info("[Wake] auto-extracting token from %s", store_url)
        try:
            session = await SessionManager.get_session()
            # T-32-01: allow_redirects=False — same pattern as T-25-01-SR in routes_brands.py:44
            async with session.get(store_url, allow_redirects=False) as resp:
                html = await resp.text()
        except Exception as exc:
            logger.warning("[Wake] token auto-extraction GET failed for %s: %s", store_url, exc)
            return None

        match = _TOKEN_RE.search(html)
        if match:
            token = match.group(1)
            self._token_cache = token  # cache per instance — T-32-06
            logger.info("[Wake] token auto-extracted and cached for brand_key=%s", self.brand_key)
            return token

        logger.warning(
            "[Wake] storefrontAccessToken not found in HTML of %s — "
            "set wake_access_token override on the brand or verify the storefront template.",
            store_url,
        )
        return None

    # ------------------------------------------------------------------
    # BaseEngine contract: stubs (D-08)
    # ------------------------------------------------------------------

    async def calculate_shipping(
        self, product: Any, zipcode: str
    ) -> Optional[Dict[str, Any]]:
        """Return None — no public checkout; prevents false 'Frete Gratis' badge."""
        return None

    async def discover_categories(self) -> List[Dict[str, Any]]:
        """Graceful stub — returns [] without crashing (D-08)."""
        return []

    async def get_catalog(self) -> List[Dict[str, Any]]:
        """Graceful stub — returns [] without crashing (D-08)."""
        return []

    async def run_bulk_scrape(
        self,
        category_url: str,
        log_callback: Any = None,
        cancel_event: Any = None,
        zipcode: Optional[str] = None,
        include_shipping: bool = False,
    ) -> None:
        """Stub — yields nothing (D-08)."""
        return

    async def get_product_details(self, product_url: str) -> Optional[Dict[str, Any]]:
        """Stub — returns None (D-10: no PDP enrichment in this phase)."""
        return None
