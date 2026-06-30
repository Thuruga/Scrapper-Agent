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
        "unavailable",
        "unsupported",
        "blocked",
        "temporary_failure",
    }


def test_resolver_returns_vtex_provider_for_vtex_engine():
    from services.stock_depth.resolver import resolve_stock_depth_provider
    from services.stock_depth.vtex import VtexStockDepthProvider

    assert isinstance(resolve_stock_depth_provider(_brand("vtex")), VtexStockDepthProvider)


def test_resolver_returns_unsupported_for_non_vtex_engines():
    from services.stock_depth.resolver import resolve_stock_depth_provider
    from services.stock_depth.unsupported import UnsupportedStockDepthProvider

    for engine in ("wake", "shopify", "sfcc", "unknown", ""):
        assert isinstance(
            resolve_stock_depth_provider(_brand(engine)),
            UnsupportedStockDepthProvider,
        )


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
