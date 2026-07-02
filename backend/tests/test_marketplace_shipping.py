from __future__ import annotations

from config import settings
from services.shipping.base import DEFAULT_MESSAGES, ShippingState


def test_shipping_state_blocked_exists():
    assert ShippingState.BLOCKED == "blocked"
    assert DEFAULT_MESSAGES[ShippingState.BLOCKED] == "Bloqueado (anti-bot)"


def test_config_has_shipping_matrix_settings():
    assert isinstance(settings.SHIPPING_MATRIX_THROTTLE_SECONDS, (int, float))
    assert isinstance(settings.SHIPPING_MATRIX_CACHE_TTL_SECONDS, (int, float))
