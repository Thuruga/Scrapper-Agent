from core.models import DynamicBrand


def _brand(engine: str) -> DynamicBrand:
    return DynamicBrand(
        brand_key=f"{engine}_brand",
        brand_name=f"{engine} Brand",
        domain=f"{engine}.example.com",
        engine=engine,
    )


def test_resolver_returns_shopify_provider():
    from services.shipping.resolver import resolve_shipping_provider
    from services.shipping.shopify import ShopifyShipping

    assert isinstance(resolve_shipping_provider(_brand("shopify")), ShopifyShipping)


def test_resolver_returns_wake_provider():
    from services.shipping.resolver import resolve_shipping_provider
    from services.shipping.wake import WakeShipping

    assert isinstance(resolve_shipping_provider(_brand("wake")), WakeShipping)


def test_resolver_returns_unsupported_for_sfcc_unknown_and_vtex():
    from services.shipping.resolver import resolve_shipping_provider
    from services.shipping.unsupported import UnsupportedShipping

    for engine in ("sfcc", "unknown", "vtex"):
        assert isinstance(resolve_shipping_provider(_brand(engine)), UnsupportedShipping)
