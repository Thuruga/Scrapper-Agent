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


def test_resolver_returns_mercado_livre_provider():
    from services.shipping.resolver import resolve_shipping_provider
    from services.shipping.mercado_livre import MercadoLivreShipping

    assert isinstance(resolve_shipping_provider(_brand("mercadolivre")), MercadoLivreShipping)


def test_resolver_returns_amazon_provider():
    from services.shipping.resolver import resolve_shipping_provider
    from services.shipping.amazon import AmazonShipping

    assert isinstance(resolve_shipping_provider(_brand("amazon")), AmazonShipping)


def test_resolver_returns_netshoes_provider():
    from services.shipping.resolver import resolve_shipping_provider
    from services.shipping.netshoes import NetshoesShipping

    assert isinstance(resolve_shipping_provider(_brand("netshoes")), NetshoesShipping)


def test_resolver_underscore_mercado_livre_falls_through():
    from services.shipping.resolver import resolve_shipping_provider
    from services.shipping.unsupported import UnsupportedShipping

    assert isinstance(resolve_shipping_provider(_brand("mercado_livre")), UnsupportedShipping)
