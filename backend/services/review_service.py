"""
Serviço de Avaliações de Produtos — Multi-Provider.

Suporta os seguintes provedores de avaliação:
  - Trustvox (Aramis): via API pública do widget (trustvox.com.br/widget/root)
  - YourViews / VTEX Native (Reserva): via REST /reviews-and-ratings/api/rating/
  - None (Tommy): sem avaliações disponíveis

Estratégia de performance:
  - Trustvox: chamada individual por produto ao /widget/root (retorna rating + count)
  - VTEX Native: chamada individual por produto ao REST endpoint
  - Ambos disparam em paralelo via asyncio.gather para minimizar latência
"""

import asyncio
import hashlib
import logging
import json
from typing import Any, List, Dict, Tuple, Optional

import aiohttp

from config import settings
from core.models import ReviewComment, ReviewCommentsResult
from services.brand_service import brand_service

logger = logging.getLogger("ReviewService")

_REVIEW_TIMEOUT = aiohttp.ClientTimeout(total=8)
_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"


class ReviewState:
    AVAILABLE = "available"
    UNSUPPORTED = "unsupported"
    TEMPORARY_FAILURE = "temporary_failure"


def _safe_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _safe_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first_value(item: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return None


def review_comment_key(item: ReviewComment | dict[str, Any]) -> str:
    """Stable key for provider comments, using provider ID or compact fields."""
    if isinstance(item, ReviewComment):
        if item.review_id:
            return str(item.review_id)
        raw = "|".join(
            str(value or "")
            for value in (
                item.rating,
                item.title,
                item.text,
                item.author,
                item.created_at,
            )
        )
    else:
        stable_id = _first_value(item, ("review_id", "reviewId", "id", "code"))
        if stable_id:
            return str(stable_id)
        raw = "|".join(
            str(item.get(key) or "")
            for key in ("rating", "title", "text", "author", "created_at")
        )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def dedupe_review_comments(comments: List[ReviewComment]) -> List[ReviewComment]:
    seen: set[str] = set()
    deduped: List[ReviewComment] = []
    for comment in comments:
        key = review_comment_key(comment)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(comment)
    return deduped


def _is_review_like(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    review_keys = {
        "review_id",
        "reviewId",
        "id",
        "rating",
        "rate",
        "score",
        "stars",
        "title",
        "text",
        "comment",
        "review",
        "content",
        "message",
    }
    return any(key in item for key in review_keys)


def _extract_comment_entries(data: Any) -> List[dict[str, Any]]:
    if isinstance(data, list):
        entries: List[dict[str, Any]] = []
        for item in data:
            if _is_review_like(item):
                entries.append(item)
            else:
                entries.extend(_extract_comment_entries(item))
        return entries

    if not isinstance(data, dict):
        return []

    for key in ("reviews", "comments", "items"):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if _is_review_like(item)]
        if isinstance(value, dict):
            nested = _extract_comment_entries(value)
            if nested:
                return nested

    nested_data = data.get("data")
    if isinstance(nested_data, (dict, list)):
        nested = _extract_comment_entries(nested_data)
        if nested:
            return nested

    return [data] if _is_review_like(data) else []


def _normalize_comment(
    item: dict[str, Any],
    *,
    provider: str,
    product_id: str,
) -> ReviewComment:
    raw_id = _first_value(item, ("review_id", "reviewId", "id", "code"))
    rating = _safe_float(_first_value(item, ("rating", "rate", "score", "stars")))
    title = _safe_str(_first_value(item, ("title", "headline", "subject")))
    text = _safe_str(
        _first_value(item, ("text", "comment", "review", "content", "message"))
    )
    author = _safe_str(
        _first_value(item, ("author", "name", "customerName", "userName"))
    )
    created_at = _safe_str(
        _first_value(item, ("created_at", "createdAt", "date", "created", "publishedAt"))
    )
    source_ref = _safe_str(_first_value(item, ("source_ref", "url", "permalink")))

    compact = {
        "rating": rating,
        "title": title,
        "text": text,
        "author": author,
        "created_at": created_at,
    }
    return ReviewComment(
        review_id=str(raw_id) if raw_id else review_comment_key(compact),
        rating=rating,
        title=title,
        text=text,
        author=author,
        created_at=created_at,
        source_provider=provider,
        source_ref=source_ref or product_id,
    )


def _extract_summary(data: Any) -> tuple[Optional[float], Optional[int]]:
    if not isinstance(data, dict):
        return None, None

    rate_info = data.get("rate")
    if isinstance(rate_info, dict):
        rating = _safe_float(rate_info.get("average"))
        count = _safe_int(rate_info.get("count"))
        if rating is not None or count is not None:
            return (round(rating, 1) if rating is not None else None, count)

    rating = _safe_float(_first_value(data, ("average", "rating", "score")))
    count = _safe_int(_first_value(data, ("totalCount", "count", "review_count")))
    if rating is not None:
        rating = round(rating, 1)
    return rating, count


def _unsupported_result(
    *,
    provider: Optional[str],
    product_id: Optional[str],
    max_pages: int = 0,
) -> ReviewCommentsResult:
    return ReviewCommentsResult(
        reviews_state=ReviewState.UNSUPPORTED,
        comments=[],
        review_product_id=product_id,
        source_provider=provider,
        max_pages=max_pages,
    )


# ---------------------------------------------------------------------------
# Driver: Trustvox (Aramis)
# ---------------------------------------------------------------------------

async def _fetch_trustvox_single(
    session: aiohttp.ClientSession,
    store_id: str,
    product_id: str,
) -> Tuple[str, Tuple[Optional[float], Optional[int]]]:
    """
    Busca a nota média e total de avaliações de um produto na Trustvox.
    Usa o endpoint /widget/root que retorna o resumo consolidado.
    """
    url = "https://trustvox.com.br/widget/root"
    params = {
        "store_id": store_id,
        "code": product_id,
    }
    headers = {
        "Accept": "application/vnd.trustvox-v2+json",
        "User-Agent": _USER_AGENT,
    }

    try:
        async with session.get(url, params=params, headers=headers) as resp:
            if resp.status != 200:
                logger.debug(f"[Trustvox] HTTP {resp.status} para product {product_id}")
                return product_id, (None, None)

            data = await resp.json(content_type=None)
            rate_info = data.get("rate", {})
            average = rate_info.get("average")
            count = rate_info.get("count", 0)

            if average is not None:
                return product_id, (round(float(average), 1), int(count))

    except Exception as e:
        logger.debug(f"[Trustvox] Erro para product {product_id}: {e}")

    return product_id, (None, None)


async def _fetch_trustvox_bulk(
    store_id: str,
    product_ids: List[str],
) -> Dict[str, Tuple[Optional[float], Optional[int]]]:
    """Dispara chamadas Trustvox em paralelo para todos os product_ids."""
    if not product_ids:
        return {}

    results: Dict[str, Tuple[Optional[float], Optional[int]]] = {}
    async with aiohttp.ClientSession(timeout=_REVIEW_TIMEOUT) as session:
        tasks = [
            _fetch_trustvox_single(session, store_id, pid)
            for pid in product_ids
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for res in responses:
            if isinstance(res, tuple) and len(res) == 2:
                pid, rating_data = res
                results[pid] = rating_data

    return results


# ---------------------------------------------------------------------------
# Driver: VTEX Native Reviews & Ratings (Reserva)
# ---------------------------------------------------------------------------

async def _fetch_vtex_native_single(
    session: aiohttp.ClientSession,
    domain: str,
    product_id: str,
) -> Tuple[str, Tuple[Optional[float], Optional[int]]]:
    """
    Busca avaliação de um produto via endpoint REST nativo do VTEX Reviews & Ratings.
    Endpoint: https://{domain}/reviews-and-ratings/api/rating/{productId}
    """
    url = f"https://{domain}/reviews-and-ratings/api/rating/{product_id}"
    headers = {
        "Accept": "application/json",
        "User-Agent": _USER_AGENT,
    }

    try:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                logger.debug(f"[VTEX Reviews] HTTP {resp.status} para {product_id} em {domain}")
                return product_id, (None, None)

            data = await resp.json(content_type=None)
            average = data.get("average", 0)
            total = data.get("totalCount", 0)

            if average and total > 0:
                return product_id, (round(float(average), 1), int(total))

    except Exception as e:
        logger.debug(f"[VTEX Reviews] Erro para {product_id} em {domain}: {e}")

    return product_id, (None, None)


async def _fetch_vtex_native_bulk(
    domain: str,
    product_ids: List[str],
) -> Dict[str, Tuple[Optional[float], Optional[int]]]:
    """Dispara chamadas VTEX Reviews em paralelo para todos os product_ids."""
    if not product_ids:
        return {}

    results: Dict[str, Tuple[Optional[float], Optional[int]]] = {}
    async with aiohttp.ClientSession(timeout=_REVIEW_TIMEOUT) as session:
        tasks = [
            _fetch_vtex_native_single(session, domain, pid)
            for pid in product_ids
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for res in responses:
            if isinstance(res, tuple) and len(res) == 2:
                pid, rating_data = res
                results[pid] = rating_data

    return results


# ---------------------------------------------------------------------------
# Entrypoint Público
# ---------------------------------------------------------------------------

async def _fetch_trustvox_comments(
    brand,
    product_id: str,
    max_pages: int,
) -> ReviewCommentsResult:
    store_id = brand.review_store_id
    if not store_id:
        return _unsupported_result(
            provider="trustvox",
            product_id=product_id,
            max_pages=max_pages,
        )

    comments: List[ReviewComment] = []
    rating: Optional[float] = None
    review_count: Optional[int] = None
    headers = {
        "Accept": "application/vnd.trustvox-v2+json",
        "User-Agent": _USER_AGENT,
    }

    async with aiohttp.ClientSession(timeout=_REVIEW_TIMEOUT) as session:
        for page in range(1, max_pages + 1):
            params = {
                "store_id": store_id,
                "code": product_id,
                "page": page,
            }
            try:
                async with session.get(
                    "https://trustvox.com.br/widget/root",
                    params=params,
                    headers=headers,
                ) as resp:
                    if resp.status != 200:
                        logger.debug(
                            "[Trustvox] HTTP %s ao buscar comentarios de %s",
                            resp.status,
                            product_id,
                        )
                        return ReviewCommentsResult(
                            reviews_state=ReviewState.TEMPORARY_FAILURE,
                            comments=[],
                            review_product_id=product_id,
                            source_provider="trustvox",
                            max_pages=max_pages,
                        )
                    data = await resp.json(content_type=None)
            except Exception as exc:
                logger.debug("[Trustvox] Erro ao buscar comentarios: %s", exc)
                return ReviewCommentsResult(
                    reviews_state=ReviewState.TEMPORARY_FAILURE,
                    comments=[],
                    review_product_id=product_id,
                    source_provider="trustvox",
                    max_pages=max_pages,
                )

            if page == 1:
                rating, review_count = _extract_summary(data)

            entries = _extract_comment_entries(data)
            comments.extend(
                _normalize_comment(entry, provider="trustvox", product_id=product_id)
                for entry in entries
            )
            if not entries:
                break

    comments = dedupe_review_comments(comments)
    return ReviewCommentsResult(
        reviews_state=ReviewState.AVAILABLE,
        comments=comments,
        rating=rating,
        review_count=review_count,
        review_product_id=product_id,
        source_provider="trustvox",
        max_pages=max_pages,
    )


async def _fetch_vtex_native_comments(
    brand,
    product_id: str,
    max_pages: int,
) -> ReviewCommentsResult:
    domain = str(brand.domain or "").replace("https://", "").replace("http://", "").strip("/")
    if not domain:
        return _unsupported_result(
            provider="vtex_native",
            product_id=product_id,
            max_pages=max_pages,
        )

    comments: List[ReviewComment] = []
    rating: Optional[float] = None
    review_count: Optional[int] = None
    headers = {
        "Accept": "application/json",
        "User-Agent": _USER_AGENT,
    }

    async with aiohttp.ClientSession(timeout=_REVIEW_TIMEOUT) as session:
        for page in range(1, max_pages + 1):
            url = f"https://{domain}/reviews-and-ratings/api/reviews/{product_id}"
            params = {"page": page}
            try:
                async with session.get(url, params=params, headers=headers) as resp:
                    if resp.status in (401, 403, 404):
                        return _unsupported_result(
                            provider="vtex_native",
                            product_id=product_id,
                            max_pages=max_pages,
                        )
                    if resp.status != 200:
                        return ReviewCommentsResult(
                            reviews_state=ReviewState.TEMPORARY_FAILURE,
                            comments=[],
                            review_product_id=product_id,
                            source_provider="vtex_native",
                            max_pages=max_pages,
                        )
                    data = await resp.json(content_type=None)
            except Exception as exc:
                logger.debug("[VTEX Reviews] Erro ao buscar comentarios: %s", exc)
                return ReviewCommentsResult(
                    reviews_state=ReviewState.TEMPORARY_FAILURE,
                    comments=[],
                    review_product_id=product_id,
                    source_provider="vtex_native",
                    max_pages=max_pages,
                )

            if page == 1:
                rating, review_count = _extract_summary(data)

            entries = _extract_comment_entries(data)
            if not entries:
                return _unsupported_result(
                    provider="vtex_native",
                    product_id=product_id,
                    max_pages=max_pages,
                )
            comments.extend(
                _normalize_comment(
                    entry,
                    provider="vtex_native",
                    product_id=product_id,
                )
                for entry in entries
            )

    comments = dedupe_review_comments(comments)
    return ReviewCommentsResult(
        reviews_state=ReviewState.AVAILABLE,
        comments=comments,
        rating=rating,
        review_count=review_count,
        review_product_id=product_id,
        source_provider="vtex_native",
        max_pages=max_pages,
    )


async def get_review_comments(
    brand_key: str,
    product_id: str,
    max_pages: Optional[int] = None,
) -> ReviewCommentsResult:
    """Fetch compact review comments on demand for an audited provider."""
    if not product_id:
        return _unsupported_result(provider=None, product_id=product_id)

    configured_max = max(1, int(settings.MAX_REVIEW_PAGES))
    requested_pages = configured_max if max_pages is None else max(1, int(max_pages))
    capped_pages = min(requested_pages, configured_max)

    brand_config = brand_service.get_brand(brand_key)
    if not brand_config:
        return _unsupported_result(
            provider=None,
            product_id=product_id,
            max_pages=capped_pages,
        )

    provider = brand_config.review_provider or "none"
    has_evidence = bool(getattr(brand_config, "review_provider_evidence", None))
    if provider == "none" or not has_evidence:
        return _unsupported_result(
            provider=provider,
            product_id=product_id,
            max_pages=capped_pages,
        )

    try:
        if provider == "trustvox" and brand_config.review_store_id:
            result = await _fetch_trustvox_comments(
                brand_config,
                product_id,
                capped_pages,
            )
        elif provider == "vtex_native":
            result = await _fetch_vtex_native_comments(
                brand_config,
                product_id,
                capped_pages,
            )
        else:
            return _unsupported_result(
                provider=provider,
                product_id=product_id,
                max_pages=capped_pages,
            )
    except Exception as exc:
        logger.debug("[ReviewService] Erro ao buscar comentarios: %s", exc)
        return ReviewCommentsResult(
            reviews_state=ReviewState.TEMPORARY_FAILURE,
            comments=[],
            review_product_id=product_id,
            source_provider=provider,
            max_pages=capped_pages,
        )

    result.comments = dedupe_review_comments(result.comments)
    result.max_pages = capped_pages
    result.review_product_id = result.review_product_id or product_id
    result.source_provider = result.source_provider or provider
    return result


async def get_bulk_reviews(
    brand_key: str,
    product_ids: List[str],
) -> Dict[str, Tuple[Optional[float], Optional[int]]]:
    """
    Entrypoint principal para coletar reviews em lote.
    Verifica o provedor no BRAND_REGISTRY e roteia para o driver adequado.

    Args:
        brand_key: Identificador da marca (ex: 'aramis', 'reserva')
        product_ids: Lista de IDs únicos de produto (ex: productId da VTEX)

    Returns:
        Um dicionário mapeando productId -> (rating, count)
        Se não houver avaliação, retorna (None, None) para aquele product_id.
    """
    if not product_ids:
        return {}

    brand_config = brand_service.get_brand(brand_key)
    if not brand_config:
        return {}

    provider = brand_config.review_provider
    logger.debug(f"[DEBUG] Buscando reviews para {brand_key} usando provedor: {provider}")

    if provider == "trustvox":
        store_id = brand_config.review_store_id
        if store_id:
            return await _fetch_trustvox_bulk(store_id, product_ids)

    elif provider == "vtex_native":
        domain = brand_config.domain
        if domain:
            return await _fetch_vtex_native_bulk(domain, product_ids)

    # Provedor não suportado ou 'none' (ex: Tommy)
    return {}


async def get_single_review(
    brand_key: str,
    product_id: str,
) -> Tuple[Optional[float], Optional[int]]:
    """
    Helper para consultas unitárias (ex: no scraper de página única).
    Retorna (rating, count) ou (None, None).
    """
    if not product_id:
        return None, None

    res = await get_bulk_reviews(brand_key, [product_id])
    return res.get(str(product_id), (None, None))
