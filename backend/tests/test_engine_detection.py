"""
Suite GREEN de deteccao de motor de plataforma (Phase 30 — COMP-05, D-11).

Regression base (mantida da baseline v2.0):
  - TestDetectEngine: exercita detect_engine com sessoes HTTP mockadas
      1. Shopify via collections.json → "shopify"
      2. VTEX via category tree → "vtex"
  - TestCreateBrandUnknown: integração
      5. create_brand com engine detectado "unknown" → marca salva com
         engine="unknown" e is_active=False (regra D-04)

Expansao Phase 30 (prova SC-1..SC-4 contra os plans 30-01/30-02):
  - SC-2: Wake Commerce (fbitsstatic.net) → "wake"  (antes era "unknown")
  - SC-1: SFCC via browser probe (demandware.static no HTML renderizado) → "sfcc"
  - SC-4: anti-falso-positivo — 403 + HTML renderizado SEM marcador demandware → "unknown"
  - SC-4: todas as probes (incl. browser) falham → "unknown"
  - SC-3: marca cujo engine detectado e sfcc/wake permanece ATIVA (a regra D-04
          so desativa "unknown") — verificado SEM modificar create_brand.

A probe SFCC importa `BrowserManager` de forma lazy dentro de detect_engine
(`from core.browser_manager import BrowserManager`), entao o seam de mock e a
classe de origem `core.browser_manager.BrowserManager.fetch_html` (e NAO um
atributo de modulo em api.routes_brands, que nao existe). Todos os casos novos
mockam o browser — nenhum teste lanca um Playwright real (T-30-09, suite hermetica).
"""
import asyncio
import aiohttp
from unittest.mock import MagicMock, AsyncMock, patch

# Seam de mock para a probe SFCC (last-resort). detect_engine faz
# `from core.browser_manager import BrowserManager` lazy; portanto o alvo de
# patch e o metodo na classe de origem (D-11).
_BROWSER_FETCH_TARGET = "core.browser_manager.BrowserManager.fetch_html"

# ---------------------------------------------------------------------------
# Helpers de mock — adaptados do padrao do projeto (test_cross_marketplace_service.py)
# ---------------------------------------------------------------------------

def _make_mock_response(status: int, json_data=None, text_data=""):
    """Constroi uma resposta aiohttp mockada para uso como async context manager."""
    resp = MagicMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data or {})
    resp.text = AsyncMock(return_value=text_data)
    # suporte a context manager assincrono
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp


def _make_mock_session(responses: dict):
    """
    responses: {url_substring: mock_response}
    session.get(url) retorna a resposta correspondente ao primeiro substring encontrado.
    session.post levanta ClientError (probes POST nao sao esperadas neste contexto).
    """
    session = MagicMock()

    def _get(url, **kwargs):
        for key, resp in responses.items():
            if key in url:
                return resp
        # Nenhum mock correspondente — simula erro de rede
        raise aiohttp.ClientError("no mock for " + url)

    session.get = _get
    session.post = MagicMock(side_effect=aiohttp.ClientError("blocked"))
    return session


# ---------------------------------------------------------------------------
# TestDetectEngine — testa cada cenario de deteccao de plataforma
# ---------------------------------------------------------------------------

class TestDetectEngine:
    """Testes unitarios de detect_engine (api.routes_brands) com HTTP/browser mockado."""

    def test_shopify_detected_via_collections_json(self):
        """Shopify: collections.json retorna 200 com chave 'collections' → ('shopify', None)."""
        mock_resp = _make_mock_response(200, json_data={"collections": [{"id": 1}]})
        mock_session = _make_mock_session({"collections.json": mock_resp})
        with patch(
            "api.routes_brands.SessionManager.get_session",
            new=AsyncMock(return_value=mock_session),
        ):
            from api.routes_brands import detect_engine
            engine, html = asyncio.run(detect_engine("test.myshopify.com"))
        assert engine == "shopify"
        assert html is None

    def test_vtex_detected_via_category_tree(self):
        """VTEX: collections.json retorna 404; category/tree/1 retorna 200 → ('vtex', None)."""
        no = _make_mock_response(404)
        vtex = _make_mock_response(200)
        mock_session = _make_mock_session({
            "collections.json": no,
            "category/tree/1": vtex,
        })
        with patch(
            "api.routes_brands.SessionManager.get_session",
            new=AsyncMock(return_value=mock_session),
        ):
            from api.routes_brands import detect_engine
            engine, html = asyncio.run(detect_engine("www.aramis.com.br"))
        assert engine == "vtex"
        assert html is None

    def test_wake_commerce_detected_returns_wake(self):
        """SC-2 — Wake Commerce: probes de API falham; HTML contem fbitsstatic.net → ('wake', html).

        Apos o plan 30-01 (D-05), o branch fbitsstatic.net retorna o engine correto
        'wake' (antes retornava 'unknown'), evitando a auto-desativacao da regra D-04.
        A probe Wake roda ANTES do VTEX HTML (Pitfall 1), entao o browser nem e acionado.
        O refactor 40-02 adiciona o html ao retorno para reutilizacao em infer_brand_name.
        """
        no = _make_mock_response(404)
        home_html_text = '<script src="https://shop2gether.fbitsstatic.net/sf/bundle?type=js"></script>'
        html_wake = _make_mock_response(
            200,
            text_data=home_html_text,
        )
        mock_session = _make_mock_session({
            "collections.json": no,
            "category/tree/1": no,
            "shop2gether.com.br": html_wake,  # home page — fallback HTML probe
        })
        with patch(
            "api.routes_brands.SessionManager.get_session",
            new=AsyncMock(return_value=mock_session),
        ):
            from api.routes_brands import detect_engine
            engine, html = asyncio.run(detect_engine("www.shop2gether.com.br"))
        assert engine == "wake"
        assert html is not None  # HTML carried for name inference (D-01)

    def test_sfcc_detected_via_browser(self):
        """SC-1 — SFCC: HTTP probes 403/404; o HTML renderizado pelo browser contem
        'demandware.static' → ('sfcc', rendered_html).

        Caso Lacoste/HugoBoss: HTTP direto e 403 (sem marcadores), mas a home
        renderizada via Playwright expoe assets demandware. O seam BrowserManager.fetch_html
        e mockado (AsyncMock) — nenhum browser real e lancado.
        """
        blocked = _make_mock_response(403, text_data="<html><body>Access Denied</body></html>")
        no = _make_mock_response(404)
        mock_session = _make_mock_session({
            "collections.json": no,
            "category/tree/1": no,
            "lacoste.com.br": blocked,  # home — 403 sem marcadores VTEX/Wake/Shopify
        })
        rendered_sfcc = (
            '<html><head>'
            '<link rel="stylesheet" href="/on/demandware.static/-/Sites/default/dw1a2b/css/main.css">'
            '</head><body>Lacoste BR</body></html>'
        )
        with patch(
            "api.routes_brands.SessionManager.get_session",
            new=AsyncMock(return_value=mock_session),
        ), patch(
            _BROWSER_FETCH_TARGET,
            new=AsyncMock(return_value=rendered_sfcc),
        ):
            from api.routes_brands import detect_engine
            engine, html = asyncio.run(detect_engine("www.lacoste.com.br"))
        assert engine == "sfcc"
        assert html == rendered_sfcc  # rendered HTML carried for name inference (D-01)

    def test_zara_detected_without_sfcc_false_positive(self):
        """Zara/Inditex: rendered static.zara.net marker maps to engine='zara'.

        This also guards that the SFCC probe does not classify Zara as sfcc.
        """
        blocked = _make_mock_response(403, text_data="<html><body>Forbidden</body></html>")
        mock_session = _make_mock_session({
            "collections.json": blocked,
            "category/tree/1": blocked,
            "zara.com": blocked,  # home — 403 generico
        })
        rendered_generic = (
            '<html><head><link rel="stylesheet" href="https://static.zara.net/stylesheets/app.css">'
            '</head><body>ZARA</body></html>'
        )
        with patch(
            "api.routes_brands.SessionManager.get_session",
            new=AsyncMock(return_value=mock_session),
        ), patch(
            _BROWSER_FETCH_TARGET,
            new=AsyncMock(return_value=rendered_generic),
        ):
            from api.routes_brands import detect_engine
            engine, html = asyncio.run(detect_engine("www.zara.com"))
        assert engine == "zara"
        assert html == rendered_generic

    def test_all_probes_fail_returns_unknown(self):
        """SC-4 — nenhuma probe identifica plataforma: HTTP retorna 404/generico e o
        HTML renderizado pelo browser tambem nao tem marcador demandware → ('unknown', None).

        Apos o plan 30-01, o fallback incondicional para 'vtex' foi removido (D-01).
        O browser e mockado para HTML sem marcadores (hermetico, T-30-09).
        """
        no = _make_mock_response(404)
        empty_html = _make_mock_response(200, text_data="<html><body>generic page</body></html>")
        mock_session = _make_mock_session({
            "collections.json": no,
            "category/tree/1": no,
            "genericstore.com.br": empty_html,
        })
        with patch(
            "api.routes_brands.SessionManager.get_session",
            new=AsyncMock(return_value=mock_session),
        ), patch(
            _BROWSER_FETCH_TARGET,
            new=AsyncMock(return_value="<html><body>generic rendered</body></html>"),
        ):
            from api.routes_brands import detect_engine
            engine, html = asyncio.run(detect_engine("www.genericstore.com.br"))
        assert engine == "unknown"
        # html may be None (browser path) or the home HTML (HTTP path carried through)
        # — both are valid; the important thing is engine == "unknown"


# ---------------------------------------------------------------------------
# TestCreateBrandUnknown — integracao: create_brand com engine unknown (regra D-04)
# ---------------------------------------------------------------------------

class TestMarketplaceDomainDetection:
    """REGRESSÃO (monitor-marketplace-pendente Round 2, hypothesis_A):
    detect_engine deve resolver domínios de marketplace (ML/Amazon/Netshoes) para o
    engine correto ANTES das probes de plataforma — antes caíam em 'unknown' porque
    não respondem a collections.json/api/catalog_system/etc, quebrando o identify e o
    título do monitor. As strings retornadas têm que ser resolvíveis por EngineFactory
    (mercadolivre/amazon/netshoes)."""

    def test_detect_marketplace_engine_all_host_forms(self):
        """O helper puro casa todas as formas de host por sufixo de LABEL."""
        from api.routes_brands import detect_marketplace_engine

        cases = {
            # Mercado Livre — inclui o subdomínio produto. do teste ao vivo
            "produto.mercadolivre.com.br": "mercadolivre",
            "www.mercadolivre.com.br": "mercadolivre",
            "lista.mercadolivre.com.br": "mercadolivre",
            "mercadolivre.com.br": "mercadolivre",
            "mercadolibre.com": "mercadolivre",
            # Amazon
            "www.amazon.com.br": "amazon",
            "amazon.com.br": "amazon",
            "www.amazon.com": "amazon",
            # Netshoes
            "www.netshoes.com.br": "netshoes",
            "m.netshoes.com.br": "netshoes",
            "netshoes.com.br": "netshoes",
        }
        for host, expected in cases.items():
            assert detect_marketplace_engine(host) == expected, (
                f"host {host!r} deveria mapear para {expected!r}"
            )

    def test_detect_marketplace_engine_non_marketplace_returns_none(self):
        """Domínios de marca própria/desconhecidos → None (segue para as probes)."""
        from api.routes_brands import detect_marketplace_engine

        for host in [
            "www.aramis.com.br",
            "www.richards.com.br",
            "example.com",
            "",
        ]:
            assert detect_marketplace_engine(host) is None, host

    def test_detect_marketplace_engine_label_boundary_no_false_positive(self):
        """Sufixo de STRING (não de label) NÃO deve casar (anti-spoof)."""
        from api.routes_brands import detect_marketplace_engine

        # 'maliciousmercadolivre.com.br' termina com 'mercadolivre.com.br' como
        # substring, mas não como sufixo de label → não deve casar.
        assert detect_marketplace_engine("maliciousmercadolivre.com.br") is None
        assert detect_marketplace_engine("notamazon.com.br") is None

    def test_detect_engine_ml_subdomain_maps_to_engine_no_network(self):
        """detect_engine('produto.mercadolivre.com.br') → ('mercadolivre', None)
        sem NENHUM fetch de rede (o Step 0 resolve antes das probes)."""
        # SessionManager.get_session lança se for chamado: prova que não há I/O.
        with patch(
            "api.routes_brands.SessionManager.get_session",
            new=AsyncMock(side_effect=AssertionError("não deve haver fetch p/ marketplace")),
        ):
            from api.routes_brands import detect_engine
            engine, html = asyncio.run(detect_engine("produto.mercadolivre.com.br"))
        assert engine == "mercadolivre"
        assert html is None

    def test_detect_engine_amazon_maps_to_engine(self):
        """detect_engine('www.amazon.com.br') → ('amazon', None) sem rede."""
        with patch(
            "api.routes_brands.SessionManager.get_session",
            new=AsyncMock(side_effect=AssertionError("não deve haver fetch p/ marketplace")),
        ):
            from api.routes_brands import detect_engine
            engine, html = asyncio.run(detect_engine("www.amazon.com.br"))
        assert engine == "amazon"
        assert html is None

    def test_detect_engine_netshoes_maps_to_engine(self):
        """detect_engine('www.netshoes.com.br') → ('netshoes', None) sem rede."""
        with patch(
            "api.routes_brands.SessionManager.get_session",
            new=AsyncMock(side_effect=AssertionError("não deve haver fetch p/ marketplace")),
        ):
            from api.routes_brands import detect_engine
            engine, html = asyncio.run(detect_engine("www.netshoes.com.br"))
        assert engine == "netshoes"
        assert html is None

    def test_marketplace_engine_strings_resolve_in_factory(self):
        """As strings retornadas devem ser resolvíveis por EngineFactory.get_engine
        (contrato IDENTIFY→factory): o engine string casa o brand_key via
        normalize_brand_key."""
        from services.engines.factory import engine_factory
        from services.engines.mercado_livre_engine import MercadoLivreEngine
        from services.engines.amazon_engine import AmazonEngine
        from services.engines.netshoes_engine import NetshoesEngine

        assert isinstance(engine_factory.get_engine("mercadolivre"), MercadoLivreEngine)
        assert isinstance(engine_factory.get_engine("amazon"), AmazonEngine)
        assert isinstance(engine_factory.get_engine("netshoes"), NetshoesEngine)


class TestCreateBrandUnknown:
    """Regressao D-04: create_brand persiste marca 'unknown' com is_active=False."""

    def test_unknown_engine_brand_saved_inactive(self):
        """Marca com engine detectado como 'unknown' deve ser salva com is_active=False.

        Estrategia:
          - Mocka detect_engine para retornar 'unknown' diretamente
          - Mocka brand_service.add_brand para evitar I/O real
          - Mocka brand_service.set_active
          - Verifica que o brand retornado tem is_active=False e engine='unknown'
          - Nenhuma HTTPException deve ser lancada (D-04: nao e erro, e aviso)
        """
        from core.models import DynamicBrand, DynamicBrandCreate
        import api.routes_brands as routes_brands_module

        # Simula brand adicionado com is_active=True (antes do set_active)
        fake_added_brand = DynamicBrand(
            brand_key="shop2gether",
            brand_name="Shop2Gether",
            domain="www.shop2gether.com.br",
            engine="unknown",
            is_active=True,
        )
        # Simula brand depois do set_active(False) (regra D-04)
        fake_deactivated_brand = DynamicBrand(
            brand_key="shop2gether",
            brand_name="Shop2Gether",
            domain="www.shop2gether.com.br",
            engine="unknown",
            is_active=False,
        )

        brand_create_data = DynamicBrandCreate(
            brand_key="shop2gether",
            brand_name="Shop2Gether",
            domain="www.shop2gether.com.br",
            engine="auto",
        )

        # Patch detect_engine para retornar ("unknown", None) — tuple após refactor 40-02
        with patch.object(
            routes_brands_module,
            "detect_engine",
            new=AsyncMock(return_value=("unknown", None)),
        ):
            # Patch brand_service.add_brand para evitar I/O
            with patch.object(
                routes_brands_module.brand_service,
                "add_brand",
                return_value=fake_added_brand,
            ):
                with patch.object(
                    routes_brands_module.brand_service,
                    "set_active",
                    return_value=fake_deactivated_brand,
                    create=True,
                ):
                    result = asyncio.run(
                        routes_brands_module.create_brand(brand_create_data)
                    )

        assert result.engine == "unknown", (
            f"Expected engine='unknown', got '{result.engine}'"
        )
        assert result.is_active is False, (
            f"Expected is_active=False for unknown engine, got {result.is_active} (D-04)."
        )


# ---------------------------------------------------------------------------
# TestCreateBrandActive — SC-3: marcas sfcc/wake permanecem ATIVAS (regra D-04
# so desativa 'unknown'). Verifica a logica D-04 EXISTENTE sem alterar create_brand.
# ---------------------------------------------------------------------------

class TestCreateBrandActive:
    """SC-3: uma marca cujo engine detectado e sfcc/wake e salva is_active=True
    e NAO passa pelo branch de desativacao D-04 (que so trata 'unknown')."""

    def _run_create_brand_with_detected_engine(self, engine: str):
        """Dirige create_brand com detect_engine mockado para `engine`.

        Retorna (result, set_active_mock) para que o teste possa asserir que
        set_active NAO foi chamado (o branch D-04 'unknown' nao dispara).
        """
        from core.models import DynamicBrand, DynamicBrandCreate
        import api.routes_brands as routes_brands_module

        fake_added_brand = DynamicBrand(
            brand_key="lacoste",
            brand_name="Lacoste",
            domain="www.lacoste.com.br",
            engine=engine,
            is_active=True,
        )
        brand_create_data = DynamicBrandCreate(
            brand_key="lacoste",
            brand_name="Lacoste",
            domain="www.lacoste.com.br",
            engine="auto",
        )

        set_active_mock = MagicMock()
        with patch.object(
            routes_brands_module,
            "detect_engine",
            new=AsyncMock(return_value=(engine, None)),
        ):
            with patch.object(
                routes_brands_module.brand_service,
                "add_brand",
                return_value=fake_added_brand,
            ):
                with patch.object(
                    routes_brands_module.brand_service,
                    "set_active",
                    new=set_active_mock,
                    create=True,
                ):
                    result = asyncio.run(
                        routes_brands_module.create_brand(brand_create_data)
                    )
        return result, set_active_mock

    def test_sfcc_brand_stays_active(self):
        """SC-3: engine detectado 'sfcc' → marca permanece ativa; D-04 nao desativa."""
        result, set_active_mock = self._run_create_brand_with_detected_engine("sfcc")
        assert result.engine == "sfcc"
        assert result.is_active is True
        set_active_mock.assert_not_called()

    def test_wake_brand_stays_active(self):
        """SC-3: engine detectado 'wake' → marca permanece ativa; D-04 nao desativa."""
        result, set_active_mock = self._run_create_brand_with_detected_engine("wake")
        assert result.engine == "wake"
        assert result.is_active is True
        set_active_mock.assert_not_called()
