"""Wave-0 tests for the on-demand Multi-Regional Shipping Matrix (FRET-09).

Covers: 5-region results, (product-identity, cep) TTL cache hit/expiry,
throttle between CEP calls, the inline-execution guard (D-10), the static
regression assertion that the matrix is unreachable from live-scan/search
code paths, and batch error isolation.
"""

import time
from unittest.mock import AsyncMock

import pytest

from core.models import DynamicBrand, SearchProductResult
from services.shipping.base import ShippingCalculation, ShippingState


CEP_LIST = [
    {"region": "Sudeste", "capital": "São Paulo-SP", "cep": "01310100"},
    {"region": "Sul", "capital": "Porto Alegre-RS", "cep": "90010150"},
    {"region": "Centro-Oeste", "capital": "Brasília-DF", "cep": "70040010"},
    {"region": "Nordeste", "capital": "Salvador-BA", "cep": "40020000"},
    {"region": "Norte", "capital": "Manaus-AM", "cep": "69010001"},
]


class FakeProvider:
    def __init__(self, calculation=None, raise_on_cep=None):
        self.calculation = calculation or ShippingCalculation(
            state=ShippingState.AVAILABLE,
        )
        self.raise_on_cep = raise_on_cep
        self.calls = []

    async def calculate(self, product, zipcode, brand):
        self.calls.append((product, zipcode, brand))
        if self.raise_on_cep is not None and zipcode == self.raise_on_cep:
            raise RuntimeError("provider boom")
        return self.calculation


def _brand():
    return DynamicBrand(
        brand_key="bck",
        brand_name="Buckman",
        domain="buckmanbck.com.br",
        engine="shopify",
    )


def _product():
    return SearchProductResult(
        brand="bck",
        product_name="Produto",
        url="https://buckmanbck.com.br/products/blazer",
        price_full=None,
    )


def _patch_resolver(monkeypatch, provider):
    import services.shipping.regional_matrix as regional_matrix

    monkeypatch.setattr(
        regional_matrix, "resolve_shipping_provider", lambda _brand: provider
    )
    return regional_matrix


@pytest.mark.asyncio
async def test_matrix_returns_five_region_results(monkeypatch, tmp_path):
    regional_matrix = _patch_resolver(monkeypatch, FakeProvider())
    cache_path = tmp_path / "cache.json"

    results = await regional_matrix.calculate_regional_matrix(
        _product(),
        _brand(),
        CEP_LIST,
        triggered_by="on_demand_matrix_button",
        cache_path=cache_path,
    )

    assert len(results) == 5
    for entry, region in zip(results, CEP_LIST):
        assert entry["region"] == region["region"]
        assert entry["capital"] == region["capital"]
        assert entry["cep"] == region["cep"]
        assert entry["state"] == ShippingState.AVAILABLE


@pytest.mark.asyncio
async def test_matrix_cache_hit_skips_provider(monkeypatch, tmp_path):
    provider = FakeProvider()
    regional_matrix = _patch_resolver(monkeypatch, provider)
    cache_path = tmp_path / "cache.json"

    await regional_matrix.calculate_regional_matrix(
        _product(),
        _brand(),
        CEP_LIST,
        triggered_by="on_demand_matrix_button",
        cache_path=cache_path,
    )
    assert len(provider.calls) == 5

    results = await regional_matrix.calculate_regional_matrix(
        _product(),
        _brand(),
        CEP_LIST,
        triggered_by="on_demand_matrix_button",
        cache_path=cache_path,
    )

    assert len(provider.calls) == 5  # unchanged — no new provider calls
    assert all(entry["cached"] is True for entry in results)


@pytest.mark.asyncio
async def test_matrix_throttle_between_calls(monkeypatch, tmp_path):
    provider = FakeProvider()
    regional_matrix = _patch_resolver(monkeypatch, provider)
    cache_path = tmp_path / "cache.json"

    sleep_mock = AsyncMock()
    monkeypatch.setattr(regional_matrix.asyncio, "sleep", sleep_mock)

    await regional_matrix.calculate_regional_matrix(
        _product(),
        _brand(),
        CEP_LIST,
        triggered_by="on_demand_matrix_button",
        cache_path=cache_path,
    )

    assert sleep_mock.await_count == len(CEP_LIST) - 1
    for call in sleep_mock.await_args_list:
        assert call.args[0] == regional_matrix.settings.SHIPPING_MATRIX_THROTTLE_SECONDS


@pytest.mark.asyncio
async def test_matrix_guard_blocks_inline_trigger(monkeypatch, tmp_path):
    provider = FakeProvider()
    regional_matrix = _patch_resolver(monkeypatch, provider)
    cache_path = tmp_path / "cache.json"

    for bad_trigger in ("", "category_scan"):
        with pytest.raises(RuntimeError):
            await regional_matrix.calculate_regional_matrix(
                _product(),
                _brand(),
                CEP_LIST,
                triggered_by=bad_trigger,
                cache_path=cache_path,
            )

    assert provider.calls == []


def test_matrix_guard_no_inline_import():
    import ast
    import inspect

    import api.routes_search as routes_search
    import services.category_monitor_service as category_monitor_service

    def _references_matrix(func) -> bool:
        source = inspect.getsource(func)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and "regional_matrix" in node.id:
                return True
            if isinstance(node, ast.Attribute) and "regional_matrix" in node.attr:
                return True
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    if "regional_matrix" in (alias.name or ""):
                        return True
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if "regional_matrix" in node.value:
                    return True
        return "regional_matrix" in source or "calculate_regional_matrix" in source

    assert not _references_matrix(routes_search.cross_marketplace_search)
    assert not _references_matrix(category_monitor_service.run_category_scan)


@pytest.mark.asyncio
async def test_matrix_batch_error_isolation(monkeypatch, tmp_path):
    provider = FakeProvider(raise_on_cep="70040010")  # Centro-Oeste
    regional_matrix = _patch_resolver(monkeypatch, provider)
    cache_path = tmp_path / "cache.json"

    results = await regional_matrix.calculate_regional_matrix(
        _product(),
        _brand(),
        CEP_LIST,
        triggered_by="on_demand_matrix_button",
        cache_path=cache_path,
    )

    assert len(results) == 5
    failing = [r for r in results if r["cep"] == "70040010"][0]
    assert failing["state"] == ShippingState.TEMPORARY_FAILURE
    others = [r for r in results if r["cep"] != "70040010"]
    assert all(r["state"] == ShippingState.AVAILABLE for r in others)


@pytest.mark.asyncio
async def test_cache_ttl_expiry(monkeypatch, tmp_path):
    provider = FakeProvider()
    regional_matrix = _patch_resolver(monkeypatch, provider)
    cache_path = tmp_path / "cache.json"

    await regional_matrix.calculate_regional_matrix(
        _product(),
        _brand(),
        CEP_LIST,
        triggered_by="on_demand_matrix_button",
        cache_path=cache_path,
    )
    assert len(provider.calls) == 5

    # Manually age every cache entry past the TTL.
    ttl = regional_matrix.settings.SHIPPING_MATRIX_CACHE_TTL_SECONDS
    cache = regional_matrix._load_cache(cache_path)
    for entry in cache.values():
        entry["checked_at"] = time.time() - ttl - 1
    regional_matrix._save_cache(cache_path, cache)

    await regional_matrix.calculate_regional_matrix(
        _product(),
        _brand(),
        CEP_LIST,
        triggered_by="on_demand_matrix_button",
        cache_path=cache_path,
    )

    assert len(provider.calls) == 10  # every CEP re-fetched — expired entries are misses
