from __future__ import annotations

from typing import Any

from services.shipping.base import get_field
from services.shipping.unsupported import UnsupportedShipping


def resolve_shipping_provider(brand: Any):
    engine = str(get_field(brand, "engine", "") or "").lower()
    if engine == "shopify":
        from services.shipping.shopify import ShopifyShipping

        return ShopifyShipping()
    if engine == "wake":
        from services.shipping.wake import WakeShipping

        return WakeShipping()
    if engine == "mercadolivre":
        from services.shipping.mercado_livre import MercadoLivreShipping

        return MercadoLivreShipping()
    if engine == "amazon":
        from services.shipping.amazon import AmazonShipping

        return AmazonShipping()
    if engine == "netshoes":
        from services.shipping.netshoes import NetshoesShipping

        return NetshoesShipping()
    return UnsupportedShipping(reason=f"Frete nao suportado para engine '{engine or 'unknown'}'")
