"""
SFCC (Salesforce Commerce Cloud / Demandware) engine.

Extracts product catalog and price data from SFCC storefronts via
browser-rendered HTML (Playwright / BrowserManager).  Targets the BR
storefronts `lacoste.com.br` and `hugoboss.com.br` (D-01).

Design decisions from Phase 31 CONTEXT.md:
  - D-03: search renders the native search page then enriches via PDP.
  - D-04: implements every abstract method in BaseEngine (no TypeError).
  - D-07: ALL results up to max_results are PDP-enriched (price + image).
  - D-08: max_results=10 default; Semaphore(3) throttles concurrent fetches.
  - D-09: calculate_shipping returns None — public path, no checkout.
  - D-06: discover_categories() and get_catalog() are minimal stubs
          returning [] gracefully; real impl lands in Wave 2 (Plan 03).

Security (threat model):
  - T-31-03 (open-redirect): query is URL-encoded; URL stays on brand domain.
  - T-31-04 (DoS / partial HTML): per-PDP try/except swallows failures;
            Semaphore(3) limits concurrent browser hits; validate_single
            rejects products missing url/raw_title/price_full/image_url.
  - T-31-05 (factory elevation): handled in factory.py guard split.
  - T-31-06 (false Frete Grátis): is_free_shipping / shipping_price never set.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import quote_plus

from core.browser_manager import BrowserManager
from core.models import BrandSearchResult, SearchProductResult
from services.engines.base_engine import BaseEngine
from services.engines.sfcc_parser import parse_pdp, parse_search_results

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level constants (D-08 / CRQ-3)
# ---------------------------------------------------------------------------

DEFAULT_MAX_RESULTS: int = 10
"""Default number of PDPs to enrich per search.  Each PDP = one browser
navigation, so keep this modest to limit latency and anti-bot exposure."""

PDP_CONCURRENCY: int = 3
"""Maximum concurrent PDP browser sessions.  BrowserManager launches a fresh
Chromium per call; 3 concurrent sessions is a conservative RAM-safe limit."""

# T-31-03: search URL template kept as a module constant so a live smoke can
# update the pattern without touching call sites.  The query placeholder is
# filled with URL-encoded text at call time.
SEARCH_URL_TEMPLATE: str = "https://www.{domain}/search?q={query}"
"""SFCC BR search URL pattern.  Pitfall 5 notes this is unverified for the
BR stores; built as a constant/helper so the live smoke can correct it."""


# ---------------------------------------------------------------------------
# SFCCEngine
# ---------------------------------------------------------------------------

class SFCCEngine(BaseEngine):
    """
    Engine for SFCC (Demandware) storefronts via public browser rendering.

    Mirrors ShopifyEngine structurally:
      - thin __init__ storing brand_key
      - search() renders the native search page then enriches each PDP
      - calculate_shipping() returns None (D-09)
      - discover_categories() / get_catalog() return [] stubs (D-06)

    All parsing logic stays in sfcc_parser.py (Clean Code / thin engine).
    """

    def __init__(self, brand_key: str) -> None:
        self.brand_key = brand_key

    # ------------------------------------------------------------------
    # BaseEngine contract — identity
    # ------------------------------------------------------------------

    def get_engine_name(self) -> str:
        """Return the friendly engine name."""
        return "SFCC"

    # ------------------------------------------------------------------
    # BaseEngine contract — search (SC-1, SC-3)
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
        """
        Render the store's native search page then enrich each PDP.

        Steps:
          1. Resolve brand domain from brand_service.
          2. Build the search URL (T-31-03: URL-encode query, same-domain).
          3. `await BrowserManager.fetch_html(search_url)` — never inside
             asyncio.to_thread (Pitfall 2).
          4. `parse_search_results(html, domain)` → candidate PDP URLs.
          5. `_enrich_results(urls, max_results, brand_name)` →
             validated SearchProductResult list.
          6. Return BrandSearchResult.
        """
        from services.brand_service import brand_service  # lazy — avoid circular import

        brand = brand_service.get_brand(self.brand_key)

        # Resolve domain — prefer registered brand, fall back to {brand_key}.com.br
        # (BR storefront convention for Lacoste/HugoBoss: lacoste.com.br, hugoboss.com.br)
        domain: str = ""
        brand_name: str = self.brand_key
        if brand:
            domain = getattr(brand, "domain", None) or (
                brand.get("domain", "") if isinstance(brand, dict) else ""
            )
            brand_name = getattr(brand, "brand_name", None) or (
                brand.get("brand_name", self.brand_key) if isinstance(brand, dict) else self.brand_key
            )

        # T-31-03: If no domain from brand registry, derive from brand_key as BR domain
        # This enables smoke-testing before the brand is formally onboarded.
        if not domain:
            domain = f"{self.brand_key}.com.br"
            logger.info(
                "[SFCC] no registered domain for brand_key=%s; using fallback domain=%s",
                self.brand_key,
                domain,
            )

        # T-31-03: URL-encode the query; navigation stays on the same domain.
        encoded_query = quote_plus(query.strip())
        search_url = SEARCH_URL_TEMPLATE.format(domain=domain, query=encoded_query)
        logger.info("[SFCC] search url: %s (brand=%s)", search_url, self.brand_key)

        try:
            search_html = await BrowserManager.fetch_html(search_url)
        except Exception as exc:
            logger.warning("[SFCC] search page fetch failed for %s: %s", search_url, exc)
            return BrandSearchResult(
                brand_key=self.brand_key,
                brand_name=brand_name,
                error=f"Search page fetch failed: {exc}",
            )

        candidate_urls = parse_search_results(search_html, domain)
        logger.info(
            "[SFCC] found %d candidate PDP URLs for brand=%s",
            len(candidate_urls),
            self.brand_key,
        )

        validated_products = await self._enrich_results(candidate_urls, max_results, brand_name)

        return BrandSearchResult(
            brand_key=self.brand_key,
            brand_name=brand_name,
            products=validated_products,
            total_found=len(validated_products),
        )

    # ------------------------------------------------------------------
    # PDP enrichment (D-07, D-08 / T-31-04)
    # ------------------------------------------------------------------

    async def _enrich_results(
        self,
        candidate_urls: List[str],
        max_results: int,
        brand_name: str,
    ) -> List[SearchProductResult]:
        """
        Enrich up to `max_results` candidate URLs by fetching each PDP.

        Uses asyncio.Semaphore(PDP_CONCURRENCY) to throttle concurrent browser
        sessions (D-08 / T-31-04).  Per-PDP failures are swallowed (logged)
        so a single blocked/partial page does not abort the whole search.

        After parsing, applies:
          - filter_mens_fashion()    — CAT-01 consistency
          - validate_single()        — Quality Gate (RawProductBronze)

        Never sets is_free_shipping or shipping_price (T-31-06).
        """
        sem = asyncio.Semaphore(PDP_CONCURRENCY)
        urls_to_fetch = candidate_urls[:max_results]

        async def _enrich_one(url: str) -> Optional[Dict[str, Any]]:
            async with sem:
                try:
                    html = await BrowserManager.fetch_html(url)
                    return parse_pdp(html, url)
                except Exception as exc:
                    # T-31-04: swallow individual PDP failures — DoS mitigation
                    logger.warning("[SFCC] PDP fetch failed for %s: %s", url, exc)
                    return None

        raw_results = await asyncio.gather(*[_enrich_one(u) for u in urls_to_fetch])

        # Drop None (failed / empty PDPs)
        parsed: List[Dict[str, Any]] = [r for r in raw_results if r is not None]

        # CAT-01: filter feminine / off-category items
        filtered = self.filter_mens_fashion(parsed)

        # Quality Gate — rejects products missing url/raw_title/price_full/image_url
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
                        # T-31-06: do NOT set is_free_shipping or shipping_price
                    )
                )

        return validated

    # ------------------------------------------------------------------
    # BaseEngine contract — shipping (D-09 / SC-4)
    # ------------------------------------------------------------------

    async def calculate_shipping(
        self, product: Any, zipcode: str
    ) -> Optional[Dict[str, Any]]:
        """
        Return None — SFCC public path has no checkout / shipping calc (D-09).

        Mirrors ShopifyEngine.calculate_shipping.  Returning None means:
          - No "Frete Grátis" badge in the frontend (App.tsx:1348, 1777).
          - No false shipping_price displayed (T-31-06).
        """
        return None

    # ------------------------------------------------------------------
    # BaseEngine contract — bulk scrape
    # ------------------------------------------------------------------

    async def run_bulk_scrape(
        self,
        category_url: str,
        log_callback: Optional[Callable] = None,
        cancel_event: Optional[asyncio.Event] = None,
        zipcode: Optional[str] = None,
        include_shipping: bool = False,
    ):
        """
        Yield products from a category URL (async generator).

        Renders the category page, extracts PDP URLs, enriches each PDP, then
        applies the Quality Gate and yields valid products one by one.
        Mirrors the ShopifyEngine.run_bulk_scrape emit pattern.
        """
        self.emit_log(log_callback, f"[SFCC] bulk scrape start: {category_url}")

        try:
            html = await BrowserManager.fetch_html(category_url)
        except Exception as exc:
            self.emit_log(log_callback, f"[SFCC] category page fetch failed: {exc}", type="error")
            return

        # Resolve brand domain for URL normalisation
        from services.brand_service import brand_service
        brand = brand_service.get_brand(self.brand_key)
        domain = (
            getattr(brand, "domain", None)
            or (brand.get("domain") if isinstance(brand, dict) else None)
            or ""
        )
        brand_name = (
            getattr(brand, "brand_name", None)
            or (brand.get("brand_name", self.brand_key) if isinstance(brand, dict) else self.brand_key)
        )

        candidate_urls = parse_search_results(html, domain)
        self.emit_log(log_callback, f"[SFCC] {len(candidate_urls)} PDP candidates found")

        sem = asyncio.Semaphore(PDP_CONCURRENCY)

        async def _enrich_one(url: str) -> Optional[Dict[str, Any]]:
            async with sem:
                try:
                    pdp_html = await BrowserManager.fetch_html(url)
                    return parse_pdp(pdp_html, url)
                except Exception as exc:
                    logger.warning("[SFCC] bulk PDP fetch failed for %s: %s", url, exc)
                    return None

        for raw in await asyncio.gather(*[_enrich_one(u) for u in candidate_urls]):
            if raw is None:
                continue
            if cancel_event and cancel_event.is_set():
                self.emit_log(log_callback, "[SFCC] bulk scrape cancelled")
                return
            validated = self.validate_single(raw, log_callback=log_callback)
            if validated:
                yield validated

    # ------------------------------------------------------------------
    # BaseEngine contract — single product details
    # ------------------------------------------------------------------

    async def get_product_details(self, product_url: str) -> Optional[Dict[str, Any]]:
        """Fetch and parse a single SFCC PDP."""
        try:
            html = await BrowserManager.fetch_html(product_url)
        except Exception as exc:
            logger.warning("[SFCC] get_product_details fetch failed for %s: %s", product_url, exc)
            return None
        parsed = parse_pdp(html, product_url)
        if not parsed:
            return None
        return self.validate_single(parsed)

    # ------------------------------------------------------------------
    # BaseEngine contract — category discovery (D-06 stub; real impl Plan 03)
    # ------------------------------------------------------------------

    async def discover_categories(self) -> List[Dict[str, Any]]:
        """
        Return [] graceful stub (D-06).

        Real implementation (home page render → nav link extraction) lands in
        Wave 2 / Plan 03.  Returning [] here satisfies D-04 (full BaseEngine
        contract) without crashing if the nav is absent or blocked.
        """
        return []

    async def get_catalog(self) -> List[Dict[str, Any]]:
        """
        Return [] graceful stub (D-06).

        Mirrors discover_categories() stub.  Real implementation in Plan 03.
        """
        return []
