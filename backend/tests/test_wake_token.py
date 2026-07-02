from types import SimpleNamespace


def test_wake_token_resolves_brand_specific_env(monkeypatch):
    from services.wake_token import resolve_wake_access_token_override

    brand = SimpleNamespace(
        brand_key="richards",
        brand_name="Richards",
        domain="www.richards.com.br",
    )
    monkeypatch.setenv("WAKE_ACCESS_TOKEN", "global-token")
    monkeypatch.setenv("WAKE_ACCESS_TOKEN_RICHARDS", "brand-token")

    assert resolve_wake_access_token_override(brand) == "brand-token"


def test_wake_token_resolves_dict_domain_env(monkeypatch):
    from services.wake_token import resolve_wake_access_token_override

    brand = {"domain": "www.richards.com.br"}
    monkeypatch.setenv("WAKE_ACCESS_TOKEN_WWW_RICHARDS_COM_BR", "domain-token")

    assert resolve_wake_access_token_override(brand) == "domain-token"
