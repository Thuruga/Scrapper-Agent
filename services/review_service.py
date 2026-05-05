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
import logging
import json
from typing import List, Dict, Tuple, Optional

import aiohttp

from services.brand_service import brand_service

logger = logging.getLogger("ReviewService")

_REVIEW_TIMEOUT = aiohttp.ClientTimeout(total=8)
_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"


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
    logger.info(f"🔍 Buscando reviews para {brand_key} usando provedor: {provider}")

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
