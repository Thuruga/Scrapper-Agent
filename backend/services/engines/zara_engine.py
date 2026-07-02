"""Zara/Inditex engine using rendered public storefront pages."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import quote_plus, urlparse

from core.browser_manager import BrowserManager
from core.models import BrandSearchResult, SearchProductResult
from services.engines.base_engine import BaseEngine
from services.engines.zara_parser import (
    parse_nav_categories,
    parse_product_detail,
    parse_products,
)

logger = logging.getLogger(__name__)

DEFAULT_SEARCH_URL_TEMPLATE = (
    "https://www.zara.com/br/pt/search?searchTerm={query}&section=MAN"
)
DEFAULT_CATEGORY_URL = "https://www.zara.com/br/pt/man-mkt534.html"
CATALOG_GROUP_LABEL = "Categorias"


class ZaraEngine(BaseEngine):
    """Engine for Zara BR public pages.

    Zara is not VTEX/Shopify/Wake/SFCC; it is an Inditex storefront rendered
    behind Akamai. HTTP-only fetches can receive an interstitial, so this engine
    follows the existing SFCC pattern and uses BrowserManager.
    """

    def __init__(self, brand_key: str):
        self.brand_key = brand_key

    def get_engine_name(self) -> str:
        return "Zara"

    @staticmethod
    def _clamp_limit(max_results: int) -> int:
        try:
            value = int(max_results)
        except (TypeError, ValueError):
            value = 10
        return max(1, min(value, 50))

    def _brand_config(self) -> Dict[str, Any]:
        from services.brand_service import brand_service

        brand = brand_service.get_brand(self.brand_key)
        if not brand:
            return {
                "brand_name": "Zara",
                "domain": "www.zara.com",
                "search_url_template": DEFAULT_SEARCH_URL_TEMPLATE,
                "proxy_url": None,
                "mappings": [],
            }

        return {
            "brand_name": getattr(brand, "brand_name", "Zara"),
            "domain": getattr(brand, "domain", "www.zara.com") or "www.zara.com",
            "search_url_template": (
                getattr(brand, "search_url_template", None)
                or DEFAULT_SEARCH_URL_TEMPLATE
            ),
            "proxy_url": getattr(brand, "proxy_url", None),
            "mappings": getattr(brand, "mappings", []) or [],
        }

    @staticmethod
    def _base_url(domain: str) -> str:
        clean = domain.replace("https://", "").replace("http://", "").strip("/")
        return f"https://{clean}"

    def _build_search_url(self, query: str, config: Dict[str, Any]) -> str:
        encoded = quote_plus(query.strip())
        domain = config["domain"].replace("https://", "").replace("http://", "").strip("/")
        return config["search_url_template"].format(query=encoded, domain=domain)

    def _build_category_url(self, category_url: str, config: Dict[str, Any]) -> str:
        if category_url.startswith(("http://", "https://")):
            return category_url
        path = category_url if category_url.startswith("/") else f"/{category_url}"
        return f"{self._base_url(config['domain'])}{path}"

    def _build_search_results(
        self,
        raw_products: List[Dict[str, Any]],
        *,
        brand_name: str,
        max_results: int,
        sort: Optional[str],
        only_in_stock: bool,
    ) -> List[SearchProductResult]:
        filtered = self.filter_mens_fashion(raw_products)
        if only_in_stock:
            filtered = [p for p in filtered if p.get("stock_availability") is not False]

        validated_dicts: List[Dict[str, Any]] = []
        for product in filtered:
            validated = self.validate_single(product)
            if validated:
                validated_dicts.append(validated)

        if sort == "price_asc":
            validated_dicts.sort(
                key=lambda p: p.get("price_discount") or p.get("price_full") or float("inf")
            )
        elif sort == "price_desc":
            validated_dicts.sort(
                key=lambda p: p.get("price_discount") or p.get("price_full") or 0,
                reverse=True,
            )

        results: List[SearchProductResult] = []
        for product in validated_dicts[:max_results]:
            results.append(
                SearchProductResult(
                    brand=brand_name,
                    product_name=product["raw_title"],
                    url=product["url"],
                    price_full=product.get("price_full"),
                    price_discount=product.get("price_discount"),
                    image_url=product.get("image_url"),
                    category=product.get("category"),
                    available=product.get("stock_availability"),
                    rating=product.get("rating"),
                    review_count=product.get("review_count"),
                    shipping_product_id=product.get("shipping_product_id"),
                    # No shipping values here: Zara shipping is unsupported for now.
                )
            )
        return results

    async def search(
        self,
        query: str,
        max_results: int = 10,
        sort: Optional[str] = None,
        only_in_stock: bool = False,
        zipcode: Optional[str] = None,  # noqa: ARG002 - shipping unsupported for now
        include_shipping: bool = False,  # noqa: ARG002 - shipping unsupported for now
    ) -> BrandSearchResult:
        config = self._brand_config()
        brand_name = config["brand_name"]
        limit = self._clamp_limit(max_results)
        search_url = self._build_search_url(query, config)

        try:
            html = await BrowserManager.fetch_html(
                search_url,
                timeout=45000,
                extra_sleep=2.0,
                proxy=config["proxy_url"],
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Zara] search fetch failed for %s: %s", search_url, exc)
            return BrandSearchResult(
                brand_key=self.brand_key,
                brand_name=brand_name,
                error=f"Search page fetch failed: {exc}",
            )

        raw_products = parse_products(
            html,
            brand=brand_name,
            base_url=self._base_url(config["domain"]),
        )
        products = self._build_search_results(
            raw_products,
            brand_name=brand_name,
            max_results=limit,
            sort=sort,
            only_in_stock=only_in_stock,
        )
        return BrandSearchResult(
            brand_key=self.brand_key,
            brand_name=brand_name,
            products=products,
            total_found=len(products),
        )

    async def run_bulk_scrape(
        self,
        category_url: str,
        log_callback: Optional[Callable] = None,
        cancel_event: Optional[asyncio.Event] = None,
        zipcode: Optional[str] = None,  # noqa: ARG002 - shipping unsupported for now
        include_shipping: bool = False,  # noqa: ARG002 - shipping unsupported for now
    ):
        config = self._brand_config()
        url = self._build_category_url(category_url, config)
        self.emit_log(log_callback, f"[Zara] varrendo categoria: {url}")

        try:
            html = await BrowserManager.fetch_html(
                url,
                timeout=45000,
                extra_sleep=2.0,
                proxy=config["proxy_url"],
            )
        except Exception as exc:  # noqa: BLE001
            self.emit_log(log_callback, f"[Zara] falha ao buscar categoria: {exc}", type="error")
            return

        raw_products = parse_products(
            html,
            brand=config["brand_name"],
            base_url=self._base_url(config["domain"]),
        )
        for product in self.filter_mens_fashion(raw_products):
            if cancel_event and cancel_event.is_set():
                self.emit_log(log_callback, "[Zara] varredura cancelada")
                return
            validated = self.validate_single(product, log_callback=log_callback)
            if validated:
                yield validated

    async def get_product_details(self, product_url: str) -> Optional[Dict[str, Any]]:
        config = self._brand_config()
        try:
            html = await BrowserManager.fetch_html(
                product_url,
                timeout=45000,
                extra_sleep=2.0,
                proxy=config["proxy_url"],
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Zara] PDP fetch failed for %s: %s", product_url, exc)
            return None

        parsed = parse_product_detail(
            html,
            product_url,
            brand=config["brand_name"],
            base_url=self._base_url(config["domain"]),
        )
        return self.validate_single(parsed) if parsed else None

    async def discover_categories(self) -> List[Dict[str, Any]]:
        config = self._brand_config()
        mappings = config["mappings"]
        if mappings:
            return [
                {"name": mapping.label, "path": mapping.vtex_fq_path, "id": mapping.vtex_fq_path}
                for mapping in mappings
            ]

        try:
            html = await BrowserManager.fetch_html(
                DEFAULT_CATEGORY_URL,
                timeout=45000,
                extra_sleep=2.0,
                proxy=config["proxy_url"],
            )
            return parse_nav_categories(html)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Zara] discover_categories failed: %s", exc)
            return []

    async def get_catalog(self) -> List[Dict[str, Any]]:
        categories = await self.discover_categories()
        if not categories:
            return []
        return [
            {
                "group": CATALOG_GROUP_LABEL,
                "items": [
                    {"label": item["name"], "path": item["path"]}
                    for item in categories
                ],
            }
        ]

    async def calculate_shipping(self, product: Any, zipcode: str) -> Optional[Dict[str, Any]]:  # noqa: ARG002
        return None

    @staticmethod
    def category_url_to_label(category_url: str) -> str:
        path = urlparse(category_url).path or category_url
        slug = path.rstrip("/").split("/")[-1]
        return slug.replace("-", " ")
