"""
Testes RED de deteccao de motor de plataforma (Phase 25, Wave 0 — COMP-02).

Cobertura:
  - TestDetectEngine: exercita detect_engine com sessoes HTTP mockadas
      1. Shopify via collections.json → "shopify"
      2. VTEX via category tree → "vtex"
      3. Wake Commerce (fbitsstatic.net) → "unknown"  (RED: hoje retorna "vtex")
      4. Todas as probes falham → "unknown"           (RED: hoje retorna "vtex")
  - TestCreateBrandUnknown: integração
      5. create_brand com engine detectado "unknown" → marca salva com
         engine="unknown" e is_active=False            (RED: hoje nao desativa)

Estes testes devem coletar sem erros de importacao e FALHAR (RED) contra o
codigo atual enquanto as implementacoes de Wave 1/2 nao existirem.
"""
import asyncio
import aiohttp
from unittest.mock import MagicMock, AsyncMock, patch

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
    """Testes unitarios de detect_engine (api.routes_brands) com HTTP mockado."""

    def test_shopify_detected_via_collections_json(self):
        """Shopify: collections.json retorna 200 com chave 'collections' → 'shopify'."""
        mock_resp = _make_mock_response(200, json_data={"collections": [{"id": 1}]})
        mock_session = _make_mock_session({"collections.json": mock_resp})
        with patch(
            "api.routes_brands.SessionManager.get_session",
            new=AsyncMock(return_value=mock_session),
        ):
            from api.routes_brands import detect_engine
            result = asyncio.run(detect_engine("test.myshopify.com"))
        assert result == "shopify"

    def test_vtex_detected_via_category_tree(self):
        """VTEX: collections.json retorna 404; category/tree/1 retorna 200 → 'vtex'."""
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
            result = asyncio.run(detect_engine("www.aramis.com.br"))
        assert result == "vtex"

    def test_wake_commerce_returns_unknown(self):
        """Wake Commerce: probes de API falham; HTML contem fbitsstatic.net → 'unknown'.

        RED: o codigo atual nao proba Wake — cai no fallback 'vtex' (L53).
        Esta falha e esperada ate a implementacao de Wave 1 (COMP-02 SC-1).
        """
        no = _make_mock_response(404)
        html_wake = _make_mock_response(
            200,
            text_data='<script src="https://shop2gether.fbitsstatic.net/sf/bundle?type=js"></script>',
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
            result = asyncio.run(detect_engine("www.shop2gether.com.br"))
        # Deve retornar "unknown" (Wake nao suportado); hoje retorna "vtex" → RED
        assert result == "unknown"

    def test_all_probes_fail_returns_unknown(self):
        """Nenhum probe identifica plataforma: todas as probes retornam 404 → 'unknown'.

        RED: o codigo atual retorna 'vtex' como fallback incondicional (L53).
        Esta falha e esperada ate a implementacao de Wave 1 (D-01).
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
        ):
            from api.routes_brands import detect_engine
            result = asyncio.run(detect_engine("www.genericstore.com.br"))
        # Deve retornar "unknown"; hoje retorna "vtex" → RED
        assert result == "unknown"


# ---------------------------------------------------------------------------
# TestCreateBrandUnknown — integracao: create_brand com engine unknown
# ---------------------------------------------------------------------------

class TestCreateBrandUnknown:
    """Testa que create_brand persiste marca com engine='unknown' e is_active=False.

    RED: o codigo atual nao trata o caso 'unknown' — marca e salva com is_active=True.
    Esta falha e esperada ate a implementacao de Wave 1 (D-04).
    """

    def test_unknown_engine_brand_saved_inactive(self):
        """Marca com engine detectado como 'unknown' deve ser salva com is_active=False.

        Estrategia:
          - Mocka detect_engine para retornar 'unknown' diretamente
          - Mocka brand_service.add_brand para evitar I/O real
          - Mocka brand_service.set_active (pode nao existir ainda — RED esperado)
          - Verifica que o brand retornado tem is_active=False e engine='unknown'
          - Nenhuma HTTPException deve ser lancada (D-04: nao e erro, e aviso)
        """
        from core.models import DynamicBrand, DynamicBrandCreate
        import api.routes_brands as routes_brands_module

        # Simula brand adicionado com is_active=True (comportamento atual)
        fake_added_brand = DynamicBrand(
            brand_key="shop2gether",
            brand_name="Shop2Gether",
            domain="www.shop2gether.com.br",
            engine="unknown",
            is_active=True,  # comportamento atual — ainda nao foi desativado
        )
        # Simula brand depois do set_active (esperado pos-Wave 1)
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

        # Patch detect_engine para retornar "unknown"
        with patch.object(
            routes_brands_module,
            "detect_engine",
            new=AsyncMock(return_value="unknown"),
        ):
            # Patch brand_service.add_brand para evitar I/O
            with patch.object(
                routes_brands_module.brand_service,
                "add_brand",
                return_value=fake_added_brand,
            ):
                # set_active nao existe ainda (sera criado no Wave 1).
                # Usa create=True para nao falhar no setup do patch.
                with patch.object(
                    routes_brands_module.brand_service,
                    "set_active",
                    return_value=fake_deactivated_brand,
                    create=True,  # permite patch mesmo quando atributo nao existe
                ):
                    result = asyncio.run(
                        routes_brands_module.create_brand(brand_create_data)
                    )

        # Pos-Wave 1: brand deve ter engine="unknown" e is_active=False
        assert result.engine == "unknown", (
            f"Expected engine='unknown', got '{result.engine}'"
        )
        assert result.is_active is False, (
            f"Expected is_active=False for unknown engine, got {result.is_active}. "
            "create_brand nao implementa D-04 ainda (RED esperado em Wave 0)."
        )
