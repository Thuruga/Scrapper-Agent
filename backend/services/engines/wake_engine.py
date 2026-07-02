"""
Wake Commerce engine.

Extracts product catalog and price data from Wake Commerce storefronts via
the public GraphQL Storefront API (storefront-api.fbits.net/graphql) using
a TCS-Access-Token per store.  Target: Richards (www.richards.com.br).

Design decisions from Phase 32 CONTEXT.md and confirmed by spike 007:
  - D-05: Auto-extract TCS-Access-Token from the storefront home page via
          regex; cache per instance; support manual override via brand field.
  - D-06: Optional field wake_access_token in DynamicBrandCreate remains
          backward-compatible; committed brand data should use env overrides.
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

import aiohttp

from core.models import BrandSearchResult, SearchProductResult
from core.session_manager import SessionManager
from services.engines.base_engine import BaseEngine
from services.shipping.base import ShippingCalculation, apply_shipping_calculation
from services.shipping.resolver import resolve_shipping_provider
from services.wake_token import resolve_wake_access_token_override

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
          productId
          productVariantId
          sku
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


# GraphQL query (WakeHotsite) — collection/section listing (e.g. /sale/masculino,
# /camisas). Wake category/sale pages are "hotsites"; the products node is the same
# Product type as `search`, so the node field set mirrors _WAKE_SEARCH_QUERY.
_WAKE_HOTSITE_QUERY: str = """
query WakeHotsite($url: String!, $first: Int!) {
  hotsite(url: $url) {
    products(first: $first) {
      edges {
        node {
          productName
          aliasComplete
          productId
          productVariantId
          sku
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
            # Fallback — enables smoke-testing before brand is formally onboarded.
            # WR-01: use the www. form (not the bare apex) — Wake storefronts commonly
            # 301 apex -> www, which would silently break token auto-extraction with
            # allow_redirects=False. Stored brand domains already include www. (self-consistent;
            # avoids the double-www the GET builder would otherwise produce).
            domain = f"www.{self.brand_key}.com.br"
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
        # WR-02: clamp/coerce max_results to a bounded positive int before it
        # flows into $first (Int!) — rejects 0/negative/huge values at the boundary.
        try:
            first = max(1, min(int(max_results), 50))
        except (TypeError, ValueError):
            first = DEFAULT_MAX_RESULTS
        payload = {
            "query": _WAKE_SEARCH_QUERY,
            "variables": {
                "q": query.strip(),
                "first": first,
            },
        }
        headers = {"TCS-Access-Token": token}

        try:
            async with session.post(
                GRAPHQL_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),  # WR-05: bound a hung storefront
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except Exception as exc:
            logger.warning("[Wake] GraphQL request failed for brand=%s: %s", self.brand_key, exc)
            return BrandSearchResult(
                brand_key=self.brand_key,
                brand_name=brand_name,
                error=f"GraphQL request failed: {exc}",
            )

        # GraphQL returns application errors as HTTP 200 with {"errors": [...], "data": null}.
        # raise_for_status() only catches non-2xx, so surface those here — otherwise the null
        # `data` would raise a cryptic AttributeError and bypass the D-07 structured-error path
        # (CR-01 / SC-2).
        gql_errors = data.get("errors")
        payload_data = data.get("data")
        if gql_errors or payload_data is None:
            if isinstance(gql_errors, list) and gql_errors:
                msg = "; ".join(str(e.get("message", e)) for e in gql_errors)
            else:
                msg = "resposta GraphQL sem dados (data=null)"
            logger.warning("[Wake] GraphQL error response for brand=%s: %s", self.brand_key, msg)
            return BrandSearchResult(
                brand_key=self.brand_key,
                brand_name=brand_name,
                error=f"GraphQL error: {msg}",
            )

        # Parse response — spike 007 confirmed the nested path
        search_node = payload_data.get("search") or {}
        products_node = search_node.get("products") or {}
        edges: List[Dict[str, Any]] = products_node.get("edges") or []

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
            product_id = node.get("productId")
            product_variant_id = node.get("productVariantId")
            sku = node.get("sku")
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
                    "shipping_product_id": str(product_id) if product_id is not None else None,
                    "shipping_variant_id": str(product_variant_id) if product_variant_id is not None else None,
                    "shipping_sku": str(sku) if sku is not None else None,
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
                        shipping_product_id=validated_dict.get("shipping_product_id"),
                        shipping_variant_id=validated_dict.get("shipping_variant_id"),
                        shipping_sku=validated_dict.get("shipping_sku"),
                    )
                )

        if include_shipping and zipcode and validated:
            await self._populate_shipping(validated, zipcode)

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

        1. Manual/env override (D-06)
        2. In-memory instance cache (T-32-06 — per-instance, not class-level)
        3. Auto-extraction via GET to the store home page (D-05 / T-32-01)
        4. Return None -> caller raises ValueError (D-07)
        """
        # 1. Manual/env override
        if brand is not None:
            override: Optional[str] = getattr(brand, "wake_access_token", None) or (
                brand.get("wake_access_token") if isinstance(brand, dict) else None
            )
            override = override or resolve_wake_access_token_override(brand)
            if override:
                # WR-03: seed the instance cache so the documented
                # "override > cache > auto-extract" precedence holds consistently
                # and the override path is not re-resolved on every search call.
                self._token_cache = override
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
            # T-32-01: allow_redirects=False — same pattern as T-25-01-SR in routes_brands.py:44.
            # WR-05: bound a hung storefront with an explicit timeout.
            async with session.get(
                store_url,
                allow_redirects=False,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                # WR-01: a 3xx (commonly apex -> www, e.g. richards.com.br -> www.richards.com.br)
                # yields only a short redirect body with redirects disabled (kept off for the
                # open-redirect threat T-32-01), so the token regex would silently miss. Surface
                # this distinctly instead of collapsing into a generic "not found".
                if resp.status in (301, 302, 303, 307, 308):
                    logger.warning(
                        "[Wake] %s redirected (%s) with redirects disabled; token HTML not read. "
                        "Check the registered domain form (www vs apex).",
                        store_url,
                        resp.status,
                    )
                    return None
                # WR-04: do not parse non-200 bodies (403 anti-bot, 404, 5xx, cached CDN error
                # pages). Only a healthy 200 storefront should feed the token regex.
                if resp.status != 200:
                    logger.warning(
                        "[Wake] home GET %s returned %s; skipping token extraction",
                        store_url,
                        resp.status,
                    )
                    return None
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
    ) -> Optional[ShippingCalculation]:
        from services.brand_service import brand_service

        brand = brand_service.get_brand(self.brand_key)
        if not brand:
            return None
        provider = resolve_shipping_provider(brand)
        return await provider.calculate(product, zipcode, brand)

    async def _populate_shipping(self, products: List[SearchProductResult], zipcode: str) -> None:
        semaphore = asyncio.Semaphore(3)

        async def _one(product: SearchProductResult) -> None:
            async with semaphore:
                try:
                    calculation = await self.calculate_shipping(product, zipcode)
                    if calculation is not None:
                        apply_shipping_calculation(product, calculation)
                except Exception:
                    return

        await asyncio.gather(*(_one(product) for product in products))

    async def discover_categories(self) -> List[Dict[str, Any]]:
        """Categorias da marca derivadas do de/para (`brand.mappings`).

        Wake não expõe uma árvore de categorias navegável como a VTEX; o
        catálogo de categorias da marca vem do mapeamento de/para configurado
        no cadastro (mesmo mecanismo usado por `resolve_category_for_brands` e
        pelo padrão Shopify). Retorna uma lista plana de {name, path}.
        """
        from services.brand_service import brand_service  # lazy — circular import

        brand = brand_service.get_brand(self.brand_key)
        mappings = getattr(brand, "mappings", None) if brand else None
        if not mappings:
            return []

        flat: List[Dict[str, Any]] = []
        for m in mappings:
            label = getattr(m, "label", None) or getattr(m, "canonical_slug", "")
            path = getattr(m, "vtex_fq_path", "") or ""
            if not path:
                continue
            flat.append({"name": label, "path": path})
        return flat

    async def get_catalog(self) -> List[Dict[str, Any]]:
        """Catálogo agrupado para o dropdown do frontend.

        Como o Wake não possui árvore navegável, agrupamos todas as categorias
        do de/para sob um único grupo — mesmo contrato de retorno do Shopify
        ({group, items:[{label, path}]}), consumido por
        `GET /brands/{brand}/categories` e pelo componente de Varredura por
        Categoria do frontend.
        """
        flat = await self.discover_categories()
        if not flat:
            return []
        return [
            {
                "group": "Categorias",
                "items": [{"label": c["name"], "path": c["path"]} for c in flat],
            }
        ]

    async def run_bulk_scrape(
        self,
        category_url: str,
        log_callback: Any = None,
        cancel_event: Any = None,
        zipcode: Optional[str] = None,
        include_shipping: bool = False,
    ):
        """Varredura por categoria — hotsite primeiro, busca por termo como fallback.

        As páginas de coleção/seção do Wake (ex.: /sale/masculino, /camisas) são
        "hotsites". `hotsite(url:)` devolve a listagem REAL da coleção que o usuário
        vê no site — inclusive seções como Outlet que não correspondem a nenhum
        termo de busca (o motivo de "Outlet" antes retornar 0 produtos). Quando o
        path não é um hotsite, caímos para um termo de busca derivado do último
        segmento do path via `search(query:)` (spike 007).

        Yields product dicts validados (mesmo contrato de VTEX/Shopify), após os
        Quality Gates (filter_mens_fashion -> validate_single).
        """
        def emit(msg: Any) -> None:
            self.emit_log(log_callback, msg)

        from services.brand_service import brand_service  # lazy — avoid circular import

        brand = brand_service.get_brand(self.brand_key)
        domain, brand_name = self._resolve_domain_and_name(brand)
        token = await self._resolve_token(brand, domain)
        if not token:
            emit(
                {
                    "type": "error_done",
                    "message": (
                        f"[Wake] token não resolvido para '{self.brand_key}'. "
                        "Configure wake_access_token na marca ou verifique o storefront."
                    ),
                }
            )
            return

        # 1. HOTSITE — listagem real da coleção (cobre Outlet/Sale e categorias)
        path = self._hotsite_path(category_url)
        hotsite_raw = await self._fetch_hotsite_products(path, domain, brand_name, token)
        if hotsite_raw:
            emit(f"[Wake] coleção '{path}' via hotsite: {len(hotsite_raw)} itens brutos")
            for product in self._apply_quality_gates(hotsite_raw, brand_name):
                if cancel_event is not None and cancel_event.is_set():
                    return
                yield product
            return

        # 2. FALLBACK — busca por termo derivado do path
        term = self._category_url_to_search_term(category_url)
        if not term:
            emit(
                {
                    "type": "brand_warning",
                    "message": (
                        "[Wake] sem hotsite e sem termo de busca derivável da "
                        f"categoria '{category_url}'. Varredura abortada."
                    ),
                }
            )
            return

        emit(f"[Wake] sem hotsite para '{path}'; varredura por busca: termo='{term}'")

        # WR-06: clamp para um teto razoável de itens por varredura de categoria.
        result = await self.search(term, max_results=50, only_in_stock=False)

        if result.error:
            emit({"type": "error_done", "message": f"[Wake] busca falhou: {result.error}"})
            return

        for product in result.products:
            if cancel_event is not None and cancel_event.is_set():
                return
            # SearchProductResult -> dict no contrato esperado pelo orchestrator
            yield {
                "raw_title": product.product_name,
                "url": product.url,
                "price_full": product.price_full,
                "image_url": product.image_url,
                "brand": result.brand_name,
                "raw_description": "",
                "stock_availability": product.available,
            }

    async def _fetch_hotsite_products(
        self, path: str, domain: str, brand_name: str, token: str
    ) -> Optional[List[Dict[str, Any]]]:
        """POST `hotsite(url:path)` e retorna dicts de produto (pré-gate).

        Retorna None quando o path não é um hotsite, a resposta tem erro/null, ou
        a coleção não tem produtos — sinalizando ao chamador que use o fallback
        por busca. Não levanta: falhas viram None (varredura nunca quebra aqui).
        """
        if not path:
            return None

        session = await SessionManager.get_session()
        payload = {
            "query": _WAKE_HOTSITE_QUERY,
            # WR-06: mesmo teto de 50 itens por varredura usado na busca.
            "variables": {"url": path, "first": 50},
        }
        try:
            async with session.post(
                GRAPHQL_ENDPOINT,
                json=payload,
                headers={"TCS-Access-Token": token},
                timeout=aiohttp.ClientTimeout(total=10),  # WR-05
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except Exception as exc:
            logger.warning(
                "[Wake] hotsite request failed for brand=%s path=%s: %s",
                self.brand_key, path, exc,
            )
            return None

        if data.get("errors") or data.get("data") is None:
            return None
        hotsite = (data.get("data") or {}).get("hotsite")
        if not hotsite:
            return None

        edges = ((hotsite.get("products") or {}).get("edges")) or []
        raw: List[Dict[str, Any]] = []
        for edge in edges:
            parsed = self._node_to_dict(edge.get("node", {}), domain, brand_name)
            if parsed:
                raw.append(parsed)
        return raw or None

    def _apply_quality_gates(
        self, raw: List[Dict[str, Any]], brand_name: str
    ) -> List[Dict[str, Any]]:
        """Quality Gates (CAT-01 + Pydantic): filter_mens_fashion -> validate_single.

        Mesma ordem obrigatória usada em `search` (PATTERNS §Quality Gates).
        """
        out: List[Dict[str, Any]] = []
        for p in self.filter_mens_fashion(raw):
            validated = self.validate_single(p)
            if validated:
                out.append(
                    {
                        "raw_title": validated["raw_title"],
                        "url": validated["url"],
                        "price_full": validated.get("price_full"),
                        "image_url": validated.get("image_url"),
                        "brand": brand_name,
                        "raw_description": "",
                        "stock_availability": validated.get("stock_availability"),
                    }
                )
        return out

    def _resolve_domain_and_name(self, brand: Any) -> tuple[str, str]:
        """Resolve (domain, brand_name) com compat dict/Pydantic (PATTERNS §Shared)."""
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
            domain = f"www.{self.brand_key}.com.br"
        return domain, brand_name

    @staticmethod
    def _node_to_dict(
        node: Dict[str, Any], domain: str, brand_name: str
    ) -> Optional[Dict[str, Any]]:
        """Converte um nó GraphQL de produto no dict do orchestrator (ou None se incompleto).

        Mesmas armadilhas tratadas em `search`: aliasComplete relativo (Armadilha 2),
        prices.price em reais (Armadilha 4), images é lista (Armadilha 3).
        """
        product_name = node.get("productName", "")
        alias = node.get("aliasComplete", "")
        product_url = f"https://{domain}/{alias.lstrip('/')}" if alias else ""
        prices = node.get("prices") or {}
        price_raw = prices.get("price")
        price_full = float(price_raw) if price_raw is not None else None
        images = node.get("images") or []
        image_url = images[0].get("url") if images else None
        available = node.get("available", True)
        if not product_name or not product_url or price_full is None:
            return None
        return {
            "raw_title": product_name,
            "url": product_url,
            "price_full": price_full,
            "image_url": image_url,
            "brand": brand_name,
            "raw_description": "",
            "stock_availability": bool(available),
        }

    @staticmethod
    def _hotsite_path(category_url: str) -> str:
        """Normaliza o path do hotsite (com barra inicial, sem host/query/barra final).

        Ex.: 'https://www.richards.com.br/sale/masculino' -> '/sale/masculino'
             'camisas' -> '/camisas'
        """
        if not category_url:
            return ""
        path = category_url
        if "://" in path:
            path = path.split("://", 1)[1]
            path = path[path.find("/"):] if "/" in path else ""
        path = path.split("?", 1)[0].rstrip("/")
        if path and not path.startswith("/"):
            path = "/" + path
        return path

    @staticmethod
    def _category_url_to_search_term(category_url: str) -> str:
        """Deriva um termo de busca a partir do path/URL da categoria.

        Ex.: 'https://www.richards.com.br/roupas-masculinas/camisas' -> 'camisas'
             '/roupas/polos' -> 'polos'
        Usa o último segmento não-vazio do path, normalizando hífens em espaços.
        """
        if not category_url:
            return ""
        # Remove esquema/host se vier URL completa
        path = category_url
        if "://" in path:
            path = path.split("://", 1)[1]
            path = path[path.find("/"):] if "/" in path else ""
        segments = [s for s in path.split("/") if s]
        if not segments:
            return ""
        last = segments[-1]
        # remove query string e normaliza
        last = last.split("?", 1)[0]
        return last.replace("-", " ").strip()

    async def get_product_details(self, product_url: str) -> Optional[Dict[str, Any]]:
        """Stub — returns None (D-10: no PDP enrichment in this phase)."""
        return None
