"""
Testes das funções puras de parsing da VTEX (services/vtex_parsing.py).

Cobrem descoberta de conta, transformação/sanitização de URL e extração de
cores/tamanhos — lógica antes embutida em VtexApiClient e sem cobertura.
Usa objetos duck-typed (SimpleNamespace) para evitar construir modelos Pydantic.
"""
from types import SimpleNamespace

from services import vtex_parsing as vp


class TestDiscoverAccount:
    def test_prefers_vtexassets_cdn(self):
        html = '<img src="https://aramisstore.vtexassets.com/arquivos/x.png">'
        assert vp.discover_account_from_html("www.aramis.com.br", html) == "aramisstore"

    def test_falls_back_to_domain_without_www(self):
        assert vp.discover_account_from_html("www.lojax.com.br", "<html></html>") == "lojax"

    def test_falls_back_to_bare_domain(self):
        assert vp.discover_account_from_html("lojay.com.br", "no match here") == "lojay"


class TestTransformUrlToApi:
    def test_already_api_url_is_unchanged(self):
        url = "https://x.com/api/catalog_system/pub/products/search/slug/p"
        assert vp.transform_url_to_api(url) == url

    def test_builds_api_url_from_product_slug(self):
        out = vp.transform_url_to_api("https://www.brand.com.br/camisa-azul/p")
        assert out == "https://www.brand.com.br/api/catalog_system/pub/products/search/camisa-azul/p"

    def test_strips_whitespace(self):
        out = vp.transform_url_to_api("  https://www.brand.com.br/tenis/p  ")
        assert out.endswith("/search/tenis/p")


class TestSanitizeProductUrl:
    def test_rewrites_internal_vtex_domain_to_public(self):
        url = "https://aramis.vtexcommercestable.com.br/produto/p"
        out = vp.sanitize_product_url(url, "www.aramis.com.br")
        assert out == "https://www.aramis.com.br/produto/p"

    def test_keeps_public_url(self):
        url = "https://www.aramis.com.br/produto/p"
        assert vp.sanitize_product_url(url, "www.aramis.com.br") == url

    def test_empty_url_returns_empty(self):
        assert vp.sanitize_product_url("", "www.aramis.com.br") == ""


class TestExtractColors:
    def test_collects_colors_from_spec_keys(self):
        p = SimpleNamespace(allSpecifications=["Cores", "Tamanho"], Cores=["Azul", " preto "])
        result = sorted(vp.extract_colors(p))
        assert result == ["AZUL", "PRETO"]

    def test_ignores_non_color_specs(self):
        p = SimpleNamespace(allSpecifications=["Material"], Material=["Algodão"])
        assert vp.extract_colors(p) == []

    def test_no_specs_returns_empty(self):
        p = SimpleNamespace(allSpecifications=[])
        assert vp.extract_colors(p) == []


class TestExtractSizes:
    def _item(self, name, qty):
        seller = SimpleNamespace(commertialOffer=SimpleNamespace(AvailableQuantity=qty))
        return SimpleNamespace(name=name, sellers=[seller])

    def test_only_includes_sizes_with_stock(self):
        items = [self._item("Camisa - P", 5), self._item("Camisa - M", 0)]
        assert vp.extract_sizes(items) == ["P"]

    def test_takes_suffix_after_dash(self):
        items = [self._item("Produto Longo - GG", 3)]
        assert vp.extract_sizes(items) == ["GG"]

    def test_dedups_sizes(self):
        items = [self._item("X - P", 1), self._item("Y - P", 2)]
        assert vp.extract_sizes(items) == ["P"]

    def test_no_stock_returns_empty(self):
        items = [self._item("Camisa - P", 0)]
        assert vp.extract_sizes(items) == []
