import asyncio

from core.models import DynamicBrand


def _brand(engine: str = "vtex", domain: str = "www.aramis.com.br") -> DynamicBrand:
    return DynamicBrand(
        brand_key=f"{engine}_brand",
        brand_name=f"{engine.title()} Brand",
        domain=domain,
        engine=engine,
    )


def test_stock_depth_states_are_exact_contract():
    from services.stock_depth.base import StockDepthState

    states = {
        value
        for name, value in vars(StockDepthState).items()
        if name.isupper() and not name.startswith("_")
    }

    assert states == {
        "estimated",
        "availability_only",
        "unavailable",
        "unsupported",
        "blocked",
        "temporary_failure",
    }


def test_resolver_returns_vtex_provider_for_vtex_engine():
    from services.stock_depth.resolver import resolve_stock_depth_provider
    from services.stock_depth.vtex import VtexStockDepthProvider

    assert isinstance(resolve_stock_depth_provider(_brand("vtex")), VtexStockDepthProvider)


def test_resolver_returns_availability_provider_for_supported_non_vtex_engines():
    from services.stock_depth.resolver import resolve_stock_depth_provider
    from services.stock_depth.availability import AvailabilityStockDepthProvider

    for engine in ("wake", "shopify", "sfcc", "mercadolivre", "netshoes", "amazon", "zara"):
        assert isinstance(
            resolve_stock_depth_provider(_brand(engine)),
            AvailabilityStockDepthProvider,
        )


def test_resolver_returns_unsupported_for_unknown_engines():
    from services.stock_depth.resolver import resolve_stock_depth_provider
    from services.stock_depth.unsupported import UnsupportedStockDepthProvider

    for engine in ("unknown", ""):
        assert isinstance(resolve_stock_depth_provider(_brand(engine)), UnsupportedStockDepthProvider)


def test_unsupported_provider_returns_explicit_unsupported_state():
    from services.stock_depth.unsupported import UnsupportedStockDepthProvider

    result = asyncio.run(
        UnsupportedStockDepthProvider(reason="sem provider").probe(
            {"url": "https://example.com/produto"},
            _brand("wake"),
            quantity=999,
        )
    )

    assert result.stock_depth_state == "unsupported"
    assert result.stock_depth_estimate is None
    assert result.stock_depth_source == "unsupported"


def test_availability_provider_confirms_live_availability_without_quantity():
    from services.stock_depth.availability import AvailabilityStockDepthProvider

    provider = AvailabilityStockDepthProvider(
        engine_factory=lambda brand_key: _FakeDetailEngine(
            {"stock_availability": True}
        )
    )

    result = asyncio.run(
        provider.probe(
            {"url": "https://www.richards.com.br/produto/camisa-123"},
            _brand("wake", "www.richards.com.br"),
            quantity=999,
        )
    )

    assert result.stock_depth_state == "availability_only"
    assert result.stock_depth_estimate is None
    assert result.stock_depth_source == "pdp-availability"


def test_availability_provider_maps_live_out_of_stock_to_unavailable():
    from services.stock_depth.availability import AvailabilityStockDepthProvider

    provider = AvailabilityStockDepthProvider(
        engine_factory=lambda brand_key: _FakeDetailEngine(
            {"stock_availability": False}
        )
    )

    result = asyncio.run(
        provider.probe(
            {"url": "https://www.zara.com/br/pt/produto-p123.html"},
            _brand("zara", "www.zara.com"),
            quantity=999,
        )
    )

    assert result.stock_depth_state == "unavailable"
    assert result.stock_depth_estimate == 0
    assert result.stock_depth_source == "pdp-availability"


def test_availability_provider_falls_back_to_persisted_availability():
    from services.stock_depth.availability import AvailabilityStockDepthProvider

    provider = AvailabilityStockDepthProvider(
        engine_factory=lambda brand_key: _FakeDetailEngine(None)
    )

    result = asyncio.run(
        provider.probe(
            {
                "url": "https://www.netshoes.com.br/produto/p",
                "stock_availability": True,
            },
            _brand("netshoes", "netshoes.com.br"),
            quantity=999,
        )
    )

    assert result.stock_depth_state == "availability_only"
    assert result.stock_depth_source == "persisted-availability"


def test_vtex_provider_maps_timeout_to_temporary_failure_not_zero():
    from services.stock_depth.vtex import VtexStockDepthProvider

    provider = VtexStockDepthProvider(
        playwright_factory=lambda: _FakePlaywright(goto_error=TimeoutError("timeout"))
    )

    result = asyncio.run(
        provider.probe(
            {"url": "https://www.aramis.com.br/produto/p"},
            _brand("vtex", "www.aramis.com.br"),
            quantity=999,
        )
    )

    assert result.stock_depth_state == "temporary_failure"
    assert result.stock_depth_estimate is None


def test_vtex_provider_maps_block_to_blocked_not_zero():
    from services.stock_depth.vtex import VtexStockDepthProvider

    provider = VtexStockDepthProvider(
        playwright_factory=lambda: _FakePlaywright(goto_error=RuntimeError("403 Access Denied"))
    )

    result = asyncio.run(
        provider.probe(
            {"url": "https://www.aramis.com.br/produto/p"},
            _brand("vtex", "www.aramis.com.br"),
            quantity=999,
        )
    )

    assert result.stock_depth_state == "blocked"
    assert result.stock_depth_estimate is None


def test_vtex_provider_closes_page_context_and_browser_on_success():
    from services.stock_depth.vtex import VtexStockDepthProvider

    fake = _FakePlaywright(evaluate_result={"state": "estimated", "estimate": 12})
    provider = VtexStockDepthProvider(playwright_factory=lambda: fake)

    result = asyncio.run(
        provider.probe(
            {"url": "https://www.aramis.com.br/produto/p"},
            _brand("vtex", "www.aramis.com.br"),
            quantity=999,
        )
    )

    assert result.stock_depth_state == "estimated"
    assert result.stock_depth_estimate == 12
    assert fake.page.closed is True
    assert fake.context.closed is True
    assert fake.browser.closed is True


def test_vtex_provider_uses_product_api_quantity_before_browser(monkeypatch):
    import json
    import services.stock_depth.vtex as vtex_module
    from services.stock_depth.vtex import VtexStockDepthProvider

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                [
                    {
                        "items": [
                            {
                                "sellers": [
                                    {"commertialOffer": {"AvailableQuantity": 10}}
                                ]
                            },
                            {
                                "sellers": [
                                    {"commertialOffer": {"AvailableQuantity": 100}}
                                ]
                            },
                        ]
                    }
                ]
            ).encode("utf-8")

    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, timeout))
        return _Response()

    monkeypatch.setattr(vtex_module, "urlopen", fake_urlopen)

    fake_playwright = _FakePlaywright(evaluate_result={"state": "estimated", "estimate": 1})
    provider = VtexStockDepthProvider(playwright_factory=lambda: fake_playwright)

    result = asyncio.run(
        provider.probe(
            {
                "url": "https://www.aramis.com.br/produto/p",
                "review_product_id": "74291",
            },
            _brand("vtex", "www.aramis.com.br"),
            quantity=999,
        )
    )

    assert result.stock_depth_state == "estimated"
    assert result.stock_depth_estimate == 100
    assert result.stock_depth_source == "vtex-product-api"
    assert calls
    assert "fq=productId:74291" in calls[0][0]
    assert fake_playwright.browser.closed is False


def test_vtex_provider_closes_page_context_and_browser_on_exception():
    from services.stock_depth.vtex import VtexStockDepthProvider

    fake = _FakePlaywright(goto_error=RuntimeError("boom"))
    provider = VtexStockDepthProvider(playwright_factory=lambda: fake)

    result = asyncio.run(
        provider.probe(
            {"url": "https://www.aramis.com.br/produto/p"},
            _brand("vtex", "www.aramis.com.br"),
            quantity=999,
        )
    )

    assert result.stock_depth_state == "temporary_failure"
    assert result.stock_depth_estimate is None
    assert fake.page.closed is True
    assert fake.context.closed is True
    assert fake.browser.closed is True


def test_probe_scan_product_rejects_missing_monitor_product_file(tmp_path, monkeypatch):
    import services.stock_depth_service as stock_depth_service

    monkeypatch.setattr(stock_depth_service, "DATA_DIR", tmp_path)
    _write_monitors(tmp_path, [{"id": "monitor-1", "brand": "aramis"}])

    try:
        asyncio.run(
            stock_depth_service.probe_scan_product_stock_depth(
                "monitor-1",
                "scan-product-1",
            )
        )
    except ValueError as exc:
        assert "Produtos monitorados nao encontrados" in str(exc)
    else:
        raise AssertionError("Expected missing product artifact to be rejected")


def test_probe_scan_product_rejects_unknown_scan_product_id(tmp_path, monkeypatch):
    import services.stock_depth_service as stock_depth_service

    monkeypatch.setattr(stock_depth_service, "DATA_DIR", tmp_path)
    _write_monitors(tmp_path, [{"id": "monitor-1", "brand": "aramis"}])
    _write_products(
        tmp_path,
        "monitor-1",
        [{"scan_product_id": "known", "url": "https://www.aramis.com.br/a"}],
    )

    try:
        asyncio.run(
            stock_depth_service.probe_scan_product_stock_depth(
                "monitor-1",
                "missing",
            )
        )
    except ValueError as exc:
        assert "Produto do scan nao encontrado" in str(exc)
    else:
        raise AssertionError("Expected unknown scan product id to be rejected")


def test_probe_scan_product_validates_url_before_provider(tmp_path, monkeypatch):
    import services.stock_depth_service as stock_depth_service
    from services.brand_service import brand_service

    provider = _RecordingProvider()
    monkeypatch.setattr(stock_depth_service, "DATA_DIR", tmp_path)
    monkeypatch.setattr(brand_service, "get_brand", lambda key: _brand("vtex", "www.aramis.com.br"))
    monkeypatch.setattr(stock_depth_service, "resolve_stock_depth_provider", lambda brand: provider)
    _write_monitors(tmp_path, [{"id": "monitor-1", "brand": "aramis"}])
    _write_products(
        tmp_path,
        "monitor-1",
        [
            {
                "scan_product_id": "scan-product-1",
                "url": "https://evil.example/produto",
                "raw_title": "Produto",
            }
        ],
    )

    try:
        asyncio.run(
            stock_depth_service.probe_scan_product_stock_depth(
                "monitor-1",
                "scan-product-1",
            )
        )
    except ValueError as exc:
        assert "URL do produto nao pertence ao dominio da marca" in str(exc)
    else:
        raise AssertionError("Expected foreign product URL to be rejected")

    assert provider.calls == []


def test_probe_scan_product_enforces_throttle_and_run_cap_without_sleep(
    tmp_path,
    monkeypatch,
):
    import services.stock_depth_service as stock_depth_service
    from services.brand_service import brand_service

    provider = _RecordingProvider()
    clock = _FakeClock([100.0, 101.0, 103.5, 106.0])
    monkeypatch.setattr(stock_depth_service, "DATA_DIR", tmp_path)
    monkeypatch.setattr(stock_depth_service.settings, "STOCK_PROBE_THROTTLE_SECONDS", 2.0)
    monkeypatch.setattr(stock_depth_service.settings, "MAX_STOCK_DEPTH_PROBES_PER_BRAND", 2)
    monkeypatch.setattr(stock_depth_service, "_now_monotonic", clock)
    monkeypatch.setattr(stock_depth_service, "_PROBE_GUARDS", {})
    monkeypatch.setattr(brand_service, "get_brand", lambda key: _brand("vtex", "www.aramis.com.br"))
    monkeypatch.setattr(stock_depth_service, "resolve_stock_depth_provider", lambda brand: provider)
    _write_monitors(tmp_path, [{"id": "monitor-1", "brand": "aramis"}])
    _write_products(
        tmp_path,
        "monitor-1",
        [
            {"scan_product_id": "p1", "url": "https://www.aramis.com.br/p1"},
            {"scan_product_id": "p2", "url": "https://www.aramis.com.br/p2"},
            {"scan_product_id": "p3", "url": "https://www.aramis.com.br/p3"},
        ],
    )

    asyncio.run(stock_depth_service.probe_scan_product_stock_depth("monitor-1", "p1"))

    throttled = asyncio.run(
        stock_depth_service.probe_scan_product_stock_depth("monitor-1", "p2")
    )
    assert throttled.stock_depth_state == "blocked"
    assert throttled.stock_depth_source == "probe-throttle"

    asyncio.run(stock_depth_service.probe_scan_product_stock_depth("monitor-1", "p2"))

    capped = asyncio.run(
        stock_depth_service.probe_scan_product_stock_depth("monitor-1", "p3")
    )
    assert capped.stock_depth_state == "blocked"
    assert capped.stock_depth_source == "probe-limit"

    assert [call["product"]["scan_product_id"] for call in provider.calls] == ["p1", "p2"]
    persisted = _read_products(tmp_path, "monitor-1")
    assert persisted[2]["stock_depth_state"] == "blocked"
    assert persisted[2]["stock_depth_source"] == "probe-limit"


def test_probe_scan_product_run_cap_is_brand_wide_across_monitors(
    tmp_path,
    monkeypatch,
):
    import services.stock_depth_service as stock_depth_service
    from services.brand_service import brand_service

    provider = _RecordingProvider()
    clock = _FakeClock([100.0, 101.0])
    monkeypatch.setattr(stock_depth_service, "DATA_DIR", tmp_path)
    monkeypatch.setattr(stock_depth_service.settings, "STOCK_PROBE_THROTTLE_SECONDS", 0.0)
    monkeypatch.setattr(stock_depth_service.settings, "MAX_STOCK_DEPTH_PROBES_PER_BRAND", 1)
    monkeypatch.setattr(stock_depth_service, "_now_monotonic", clock)
    monkeypatch.setattr(stock_depth_service, "_PROBE_GUARDS", {})
    monkeypatch.setattr(brand_service, "get_brand", lambda key: _brand("vtex", "www.aramis.com.br"))
    monkeypatch.setattr(stock_depth_service, "resolve_stock_depth_provider", lambda brand: provider)
    _write_monitors(
        tmp_path,
        [
            {"id": "monitor-1", "brand": "aramis"},
            {"id": "monitor-2", "brand": "aramis"},
        ],
    )
    _write_products(
        tmp_path,
        "monitor-1",
        [{"scan_product_id": "p1", "url": "https://www.aramis.com.br/p1"}],
    )
    _write_products(
        tmp_path,
        "monitor-2",
        [{"scan_product_id": "p2", "url": "https://www.aramis.com.br/p2"}],
    )

    asyncio.run(stock_depth_service.probe_scan_product_stock_depth("monitor-1", "p1"))

    capped = asyncio.run(
        stock_depth_service.probe_scan_product_stock_depth("monitor-2", "p2")
    )

    assert capped.stock_depth_state == "blocked"
    assert capped.stock_depth_source == "probe-limit"
    assert [call["product"]["scan_product_id"] for call in provider.calls] == ["p1"]


def test_probe_scan_product_updates_only_matching_record(tmp_path, monkeypatch):
    import services.stock_depth_service as stock_depth_service
    from services.brand_service import brand_service

    checked_at = "2026-06-30T18:30:00+00:00"
    provider = _RecordingProvider(state="estimated", estimate=7)
    monkeypatch.setattr(stock_depth_service, "DATA_DIR", tmp_path)
    monkeypatch.setattr(stock_depth_service, "_utc_now_iso", lambda: checked_at)
    monkeypatch.setattr(stock_depth_service, "_PROBE_GUARDS", {})
    monkeypatch.setattr(brand_service, "get_brand", lambda key: _brand("vtex", "www.aramis.com.br"))
    monkeypatch.setattr(stock_depth_service, "resolve_stock_depth_provider", lambda brand: provider)
    _write_monitors(tmp_path, [{"id": "monitor-1", "brand": "aramis"}])
    original_products = [
        {
            "scan_product_id": "p1",
            "url": "https://www.aramis.com.br/p1",
            "raw_title": "Produto 1",
            "stock_availability": True,
        },
        {
            "scan_product_id": "p2",
            "url": "https://www.aramis.com.br/p2",
            "raw_title": "Produto 2",
            "stock_availability": False,
        },
    ]
    _write_products(tmp_path, "monitor-1", original_products)

    result = asyncio.run(
        stock_depth_service.probe_scan_product_stock_depth("monitor-1", "p2")
    )

    persisted = _read_products(tmp_path, "monitor-1")
    assert persisted[0] == original_products[0]
    assert persisted[1] == {
        **original_products[1],
        "stock_depth_estimate": 7,
        "stock_depth_state": "estimated",
        "stock_depth_checked_at": checked_at,
        "stock_depth_source": "vtex-cart-probe",
        "stock_depth_label": "maximo observado/estimativa via cart-probe",
    }
    assert result.stock_depth_estimate == 7
    assert result.stock_depth_state == "estimated"
    assert result.stock_depth_checked_at == checked_at
    assert result.stock_depth_label == "maximo observado/estimativa via cart-probe"


def test_probe_scan_product_preserves_provider_label_and_source(tmp_path, monkeypatch):
    import services.stock_depth_service as stock_depth_service
    from services.brand_service import brand_service

    provider = _RecordingProvider(
        state="estimated",
        estimate=100,
        source="vtex-product-api",
        label="Estimativa pelo AvailableQuantity da VTEX API publica.",
    )
    monkeypatch.setattr(stock_depth_service, "DATA_DIR", tmp_path)
    monkeypatch.setattr(stock_depth_service, "_PROBE_GUARDS", {})
    monkeypatch.setattr(brand_service, "get_brand", lambda key: _brand("vtex", "www.aramis.com.br"))
    monkeypatch.setattr(stock_depth_service, "resolve_stock_depth_provider", lambda brand: provider)
    _write_monitors(tmp_path, [{"id": "monitor-1", "brand": "aramis"}])
    _write_products(
        tmp_path,
        "monitor-1",
        [{"scan_product_id": "p1", "url": "https://www.aramis.com.br/p1"}],
    )

    result = asyncio.run(
        stock_depth_service.probe_scan_product_stock_depth("monitor-1", "p1")
    )

    [persisted] = _read_products(tmp_path, "monitor-1")
    assert result.stock_depth_source == "vtex-product-api"
    assert result.stock_depth_label == "Estimativa pelo AvailableQuantity da VTEX API publica."
    assert persisted["stock_depth_source"] == "vtex-product-api"
    assert persisted["stock_depth_label"] == "Estimativa pelo AvailableQuantity da VTEX API publica."


def test_probe_scan_product_persists_non_estimated_state_without_estimate(
    tmp_path,
    monkeypatch,
):
    import services.stock_depth_service as stock_depth_service
    from services.brand_service import brand_service

    provider = _RecordingProvider(state="blocked", estimate=99)
    monkeypatch.setattr(stock_depth_service, "DATA_DIR", tmp_path)
    monkeypatch.setattr(stock_depth_service, "_PROBE_GUARDS", {})
    monkeypatch.setattr(brand_service, "get_brand", lambda key: _brand("vtex", "www.aramis.com.br"))
    monkeypatch.setattr(stock_depth_service, "resolve_stock_depth_provider", lambda brand: provider)
    _write_monitors(tmp_path, [{"id": "monitor-1", "brand": "aramis"}])
    _write_products(
        tmp_path,
        "monitor-1",
        [{"scan_product_id": "p1", "url": "https://www.aramis.com.br/p1"}],
    )

    result = asyncio.run(
        stock_depth_service.probe_scan_product_stock_depth("monitor-1", "p1")
    )

    [persisted] = _read_products(tmp_path, "monitor-1")
    assert result.stock_depth_state == "blocked"
    assert result.stock_depth_estimate is None
    assert persisted["stock_depth_state"] == "blocked"
    assert persisted["stock_depth_estimate"] is None


class _FakePlaywright:
    def __init__(self, goto_error=None, evaluate_result=None):
        self.page = _FakePage(goto_error=goto_error, evaluate_result=evaluate_result)
        self.context = _FakeContext(self.page)
        self.browser = _FakeBrowser(self.context)
        self.chromium = _FakeChromium(self.browser)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeChromium:
    def __init__(self, browser):
        self._browser = browser

    def launch(self, **kwargs):
        return self._browser


class _FakeBrowser:
    def __init__(self, context):
        self._context = context
        self.closed = False

    def new_context(self, **kwargs):
        return self._context

    def close(self):
        self.closed = True


class _RecordingProvider:
    def __init__(
        self,
        state="estimated",
        estimate=5,
        source="vtex-cart-probe",
        label=None,
    ):
        self._state = state
        self._estimate = estimate
        self._source = source
        self._label = label
        self.calls = []

    async def probe(self, product, brand, quantity):
        from core.models import StockDepthResult

        self.calls.append({"product": dict(product), "brand": brand, "quantity": quantity})
        return StockDepthResult(
            stock_depth_estimate=self._estimate if self._state == "estimated" else None,
            stock_depth_state=self._state,
            stock_depth_source=self._source,
            stock_depth_label=self._label,
        )


class _FakeDetailEngine:
    def __init__(self, detail):
        self._detail = detail

    async def get_pdp_product(self, url):
        return self._detail


class _FakeClock:
    def __init__(self, values):
        self._values = list(values)

    def __call__(self):
        if not self._values:
            raise AssertionError("Fake clock exhausted")
        return self._values.pop(0)


def _write_monitors(tmp_path, rows):
    import json

    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "monitored_categories.json").write_text(
        json.dumps(rows, indent=2),
        encoding="utf-8",
    )


def _write_products(tmp_path, monitor_id, rows):
    import json

    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / f"monitored_products_{monitor_id}.json").write_text(
        json.dumps(rows, indent=2),
        encoding="utf-8",
    )


def _read_products(tmp_path, monitor_id):
    import json

    return json.loads(
        (tmp_path / f"monitored_products_{monitor_id}.json").read_text(
            encoding="utf-8"
        )
    )


class _FakeContext:
    def __init__(self, page):
        self._page = page
        self.closed = False

    def new_page(self):
        return self._page

    def close(self):
        self.closed = True


class _FakePage:
    def __init__(self, goto_error=None, evaluate_result=None):
        self._goto_error = goto_error
        self._evaluate_result = evaluate_result
        self.closed = False

    def add_init_script(self, script):
        return None

    def goto(self, url, wait_until, timeout):
        if self._goto_error:
            raise self._goto_error
        return None

    def evaluate(self, script, quantity):
        return self._evaluate_result

    def close(self):
        self.closed = True
