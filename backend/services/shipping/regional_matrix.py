"""On-demand Multi-Regional Shipping Matrix orchestrator (FRET-09).

This module is ONLY called from the on-demand ``POST /search/calculate-shipping-matrix``
route (see ``api/routes_search.py``). It MUST NEVER be imported or called from
``cross_marketplace_service._enrich_pdp_and_shipping`` or from
``category_monitor_service.run_category_scan`` — those live-scan/search code paths
must remain unreachable from this module (D-10). A dedicated regression test
(``test_matrix_guard_no_inline_import``) statically asserts this boundary holds.

Behaviour:
    - Resolves the shipping provider ONCE per matrix request via
      ``resolve_shipping_provider`` (the single chokepoint), then calls
      ``provider.calculate`` once per curated capital CEP (see
      ``backend/data/cep_matrix.json``).
    - A throttle (``settings.SHIPPING_MATRIX_THROTTLE_SECONDS``) is awaited
      between CEP calls, but never before the first call.
    - Results are cached by ``(normalized-product-url, cep)`` in a flat JSON
      file (``backend/data/shipping_matrix_cache.json`` by default) with a
      TTL (``settings.SHIPPING_MATRIX_CACHE_TTL_SECONDS``); TTL comparisons
      use ``time.time()`` epoch floats, never ``datetime``, to avoid
      timezone ambiguity.
    - One CEP's provider exception is isolated to that region's result
      (``temporary_failure``) and does not abort the other regions.
    - The raw CEP is never logged — only the region label (T-42-02).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

from config import settings
from services.shipping.base import ShippingState, get_field
from services.shipping.resolver import resolve_shipping_provider
from services.url_utils import normalize_url

logger = logging.getLogger("regional_matrix")

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
CEP_MATRIX_FILE = DATA_DIR / "cep_matrix.json"
DEFAULT_CACHE_FILE = DATA_DIR / "shipping_matrix_cache.json"

ON_DEMAND_TRIGGER = "on_demand_matrix_button"


def _stable_product_identity(product: Any) -> str:
    """Primary cache-key half — normalized product URL, never ``sku_id`` (Pitfall 6)."""
    return normalize_url(get_field(product, "url", "") or "")


def _cache_key(identity: str, cep: str) -> str:
    return f"{identity}|{cep}"


def _load_cache(path: Path) -> dict:
    if not path or not Path(path).exists():
        return {}
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(path: Path, cache: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_matrix_cache(cache: dict, key: str, ttl_seconds: float) -> dict | None:
    entry = cache.get(key)
    if not entry:
        return None
    if time.time() - entry.get("checked_at", 0) >= ttl_seconds:
        return None
    return entry.get("result")


def _write_matrix_cache(cache: dict, key: str, result: dict) -> None:
    cache[key] = {"checked_at": time.time(), "result": result}


def load_cep_matrix() -> list[dict]:
    """Read the curated capital-CEP list (one per region), operator-editable."""
    return json.loads(CEP_MATRIX_FILE.read_text(encoding="utf-8"))


async def calculate_regional_matrix(
    product: Any,
    brand: Any,
    cep_list: list[dict],
    *,
    triggered_by: str,
    cache_path: Path | str | None = None,
) -> list[dict]:
    """Calculate shipping cost/prazo for *product* across every region in *cep_list*.

    Guard-rail (D-10): only reachable when ``triggered_by == "on_demand_matrix_button"``.
    Any other value raises ``RuntimeError`` BEFORE any provider call.
    """
    if triggered_by != ON_DEMAND_TRIGGER:
        raise RuntimeError(
            "Regional matrix guard: only reachable from the on-demand route."
        )

    resolved_cache_path = Path(cache_path) if cache_path is not None else DEFAULT_CACHE_FILE

    provider = resolve_shipping_provider(brand)
    identity = _stable_product_identity(product)
    cache = _load_cache(resolved_cache_path)

    ttl_seconds = settings.SHIPPING_MATRIX_CACHE_TTL_SECONDS
    throttle_seconds = settings.SHIPPING_MATRIX_THROTTLE_SECONDS

    results: list[dict] = []
    provider_call_made = False

    for i, region_cep in enumerate(cep_list):
        cep = region_cep["cep"]
        key = _cache_key(identity, cep)

        cached_result = _read_matrix_cache(cache, key, ttl_seconds)
        if cached_result is not None:
            results.append({**cached_result, "cached": True})
            continue

        if provider_call_made:
            await asyncio.sleep(throttle_seconds)

        try:
            calculation = await provider.calculate(product, cep, brand)
            provider_call_made = True
            state = calculation.state
            shipping = (
                calculation.shipping_options[0].model_dump(mode="json")
                if calculation.shipping_options
                else None
            )
            message = calculation.message
        except Exception:
            provider_call_made = True
            logger.warning(
                "Falha ao calcular frete da matriz regional para a regiao %s",
                region_cep.get("region"),
            )
            state = ShippingState.TEMPORARY_FAILURE
            shipping = None
            message = "Frete temporariamente indisponivel"

        entry = {
            "region": region_cep["region"],
            "capital": region_cep["capital"],
            "cep": cep,
            "state": state,
            "shipping": shipping,
            "message": message,
            "cached": False,
        }
        _write_matrix_cache(cache, key, entry)
        results.append(entry)

    _save_cache(resolved_cache_path, cache)
    return results
