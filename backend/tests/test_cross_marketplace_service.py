"""
Testes de caracterizacao de CrossMarketplaceService.compare_product.

Travam o comportamento OBSERVAVEL do orquestrador cross-marketplace ANTES do
refactor de Workstream 1 (extracao de compare_product em metodos/funcoes puras).
Hoje so existem testes das funcoes puras isoladas (gates, tiebreak); nao havia
nenhum teste end-to-end do pipeline. Estes testes sao a rede de seguranca: o
refactor deve mante-los verdes sem mudar nenhuma assercao.

Estrategia (deterministico, zero rede / zero IA):
  - Engines injetados via _inject_engines(service, engines_dict): seta _by_display
    (usado por _enrich_pdp_and_shipping) e substitui _active_engines() para
    retornar o mesmo dict (usado por _fetch_all_engines). Nao depende de brands.json
    no disco — testes hermeticos.
  - ``target_sku=None`` => caminho text-only (vision_active=False): VTEXEngine e
    image_ai_service NUNCA sao importados/usados (estao dentro do ``if target_sku``).
  - ``nlp_service.calculate_text_score`` e ``brand_is_present`` monkeypatchados
    para scores/marca deterministicos (sem depender do vocab real nem de .env).
  - ``relevance_settings`` fixado explicitamente (mutavel: model_config sem frozen),
    para o teste nao depender de overrides de .env.
  - ``compare_product`` e async; dirigido via ``asyncio.run`` (o projeto nao tem
    pytest-asyncio configurado).

Casos:
  1. Happy path text-only: 2 plataformas com match estrito + 1 vazia (vira erro).
     Trava o shape do dict de retorno, os scores, o buybox no mais barato, o
     landed_price (preco + frete) e as metricas.
  2. Fallback de similares (S1): plataforma sem a marca buscada (brand gate falha)
     mas com final >= CROSS_SIMILAR_MIN_SCORE vira ``is_similar``; o buybox e o
     cheapest_price ficam RESTRITOS ao match estrito (o nucleo do comportamento S1).
  3. Excecao de motor: vira entrada em ``errors`` sem derrubar o pipeline.
  4. Inactive marketplace excluded (UX-05/D-11): marketplace marcado is_active=False
     nao entra em _active_engines() e portanto nao aparece na busca.
"""
import asyncio
import unittest.mock

from config import relevance_settings
from services.cross_marketplace_service import CrossMarketplaceService
from services.nlp_service import nlp_service


_EMPTY_REASON = "Nenhum resultado encontrado (possível bloqueio ou sem estoque)"


class FakeEngine:
    """Motor falso: retorna resultados de busca pre-definidos, sem rede."""

    def __init__(self, search_result, *, details_by_url=None, shipping_by_url=None, raise_exc=None):
        self._search_result = search_result
        self._details = details_by_url or {}
        self._shipping = shipping_by_url or {}
        self._raise = raise_exc

    async def search(self, query, max_results, **kwargs):
        if self._raise is not None:
            raise self._raise
        return self._search_result

    async def get_product_details(self, url):
        return self._details.get(url)

    async def calculate_shipping(self, p, zipcode):
        return self._shipping.get(p.get("url"))


def _inject_engines(service: CrossMarketplaceService, engines_dict: dict) -> CrossMarketplaceService:
    """Inject a {display_name: FakeEngine} dict into a CrossMarketplaceService for testing.

    Sets _by_display (for _enrich_pdp_and_shipping) and monkey-patches _active_engines
    to return the same dict (for _fetch_all_engines).  Tests remain hermetic — they do
    not touch brands.json on disk or the real brand_service singleton.

    Returns the service for chaining convenience.
    """
    service._by_display = dict(engines_dict)
    service._active_engines = lambda: dict(engines_dict)  # type: ignore[method-assign]
    return service


def _prod(plataforma, titulo, preco, url, imagem="http://img/x.jpg", seller="Loja"):
    return {
        "plataforma": plataforma,
        "titulo": titulo,
        "preco": preco,
        "url": url,
        "imagem": imagem,
        "seller": seller,
    }


def _pin_settings(monkeypatch):
    """Fixa os hiperparametros relevantes para o pipeline ser deterministico."""
    monkeypatch.setattr(relevance_settings, "BRAND_GATE_ENABLED", True)
    monkeypatch.setattr(relevance_settings, "CROSS_SIMILAR_FALLBACK_ENABLED", True)
    monkeypatch.setattr(relevance_settings, "CROSS_SIMILAR_MIN_SCORE", 15.0)
    monkeypatch.setattr(relevance_settings, "CROSS_MIN_SCORE_WITHOUT_VISION", 55.0)
    monkeypatch.setattr(relevance_settings, "CROSS_MIN_SCORE_WITH_VISION", 60.0)
    monkeypatch.setattr(relevance_settings, "CROSS_MAX_RESULTS_PER_ENGINE", 30)
    monkeypatch.setattr(relevance_settings, "CROSS_MAX_RESULTS_PER_PLATFORM_FINAL", 10)
    monkeypatch.setattr(relevance_settings, "VISUAL_TIEBREAK_ENABLED", True)
    monkeypatch.setattr(relevance_settings, "VISUAL_TIEBREAK_TEXT_WINDOW", 10.0)
    monkeypatch.setattr(relevance_settings, "ENGINE_DEFAULT_TIMEOUT_SECONDS", 30.0)
    monkeypatch.setattr(relevance_settings, "ML_TIMEOUT_PLAYWRIGHT_SECONDS", 100.0)


def _patch_nlp(monkeypatch, scores):
    """scores: dict titulo->[0..1]. Marca presente sse 'aramis' no titulo."""
    monkeypatch.setattr(
        nlp_service, "calculate_text_score", lambda official, market: scores.get(market, 0.0)
    )
    monkeypatch.setattr(
        nlp_service, "brand_is_present", lambda official, market: "aramis" in market.lower()
    )


class TestCompareProductCharacterization:
    STRICT = "Camisa Polo Aramis Masculina"
    BROAD = "camisa polo"

    def test_happy_path_text_only(self, monkeypatch):
        _pin_settings(monkeypatch)
        net_title = "Camisa Polo Aramis Azul"
        amz_title = "Camisa Polo Aramis Preta"
        _patch_nlp(monkeypatch, {net_title: 0.92, amz_title: 0.85})

        service = _inject_engines(CrossMarketplaceService(), {
            "Mercado Livre": FakeEngine([]),  # vazio -> erro
            "Netshoes": FakeEngine(
                [_prod("Netshoes", net_title, 100.0, "http://net/1")],
                shipping_by_url={"http://net/1": {"is_free_shipping": False, "shipping_price": 20.0}},
            ),
            "Amazon": FakeEngine(
                [_prod("Amazon", amz_title, 80.0, "http://amz/1")]
            ),  # sem frete -> None
        })

        result = asyncio.run(
            service.compare_product(
                broad_query=self.BROAD,
                strict_query=self.STRICT,
                target_sku=None,
                min_score=70.0,
                zipcode="01001000",
            )
        )

        # ---- contrato de topo ----
        assert result["status"] == "success"
        assert result["vision_active"] is False
        assert result["similar_fallback"] is False
        assert result["target_sku"] == "N/A"
        assert result["search_query"] == self.STRICT

        # ---- plataforma vazia vira erro ----
        reasons = {(e["marketplace"], e["reason"]) for e in result["errors"]}
        assert ("Mercado Livre", _EMPTY_REASON) in reasons

        # ---- resultados ----
        results = result["results"]
        assert len(results) == 2
        # ordem: tiebreak sem imagem cai em sorted(-final, preco) -> Netshoes(92) antes de Amazon(85)
        assert [r["marketplace"] for r in results] == ["Netshoes", "Amazon"]

        by_mp = {r["marketplace"]: r for r in results}
        net, amz = by_mp["Netshoes"], by_mp["Amazon"]

        assert net["text_match_score"] == 92.0
        assert net["image_match_score"] == 0.0
        assert net["final_match_score"] == 92.0
        assert net["match_score"] == 92.0  # alias de compatibilidade
        assert net["price"] == 100.0
        assert net["shipping_price"] == 20.0
        assert net["landed_price"] == 120.0
        assert net["is_similar"] is False
        assert net["is_buybox_winner"] is False
        assert net["variant_count"] == 1

        assert amz["final_match_score"] == 85.0
        assert amz["price"] == 80.0
        assert amz["shipping_price"] is None
        assert amz["landed_price"] == 80.0  # sem frete -> landed == price
        assert amz["is_similar"] is False
        assert amz["is_buybox_winner"] is True  # mais barato entre os estritos

        # ---- metricas ----
        assert result["metrics"]["total_found_strict"] == 2
        assert result["metrics"]["cheapest_price"] == 80.0

    def test_similar_fallback_per_platform_s1(self, monkeypatch):
        _pin_settings(monkeypatch)
        net_title = "Camisa Polo Aramis Azul"      # tem a marca -> match estrito
        amz_title = "Camisa Polo Hering Preta"      # SEM a marca -> brand gate falha
        # Netshoes final 90 (>=70 estrito); Amazon final 30 (<70 estrito, >=15 similar)
        _patch_nlp(monkeypatch, {net_title: 0.90, amz_title: 0.30})

        service = _inject_engines(CrossMarketplaceService(), {
            "Mercado Livre": FakeEngine([]),  # vazio
            "Netshoes": FakeEngine([_prod("Netshoes", net_title, 100.0, "http://net/1")]),
            "Amazon": FakeEngine([_prod("Amazon", amz_title, 50.0, "http://amz/1")]),
        })

        result = asyncio.run(
            service.compare_product(
                broad_query=self.BROAD,
                strict_query=self.STRICT,
                target_sku=None,
                min_score=70.0,
                zipcode="01001000",
            )
        )

        assert result["similar_fallback"] is True
        by_mp = {r["marketplace"]: r for r in result["results"]}
        assert set(by_mp) == {"Netshoes", "Amazon"}
        net, amz = by_mp["Netshoes"], by_mp["Amazon"]

        # Netshoes e o match estrito; Amazon entra como similar
        assert net["is_similar"] is False
        assert amz["is_similar"] is True
        assert amz["price"] == 50.0  # similar e exibido com seu preco

        # NUCLEO S1: buybox e cheapest sao restritos ao match estrito.
        # Amazon (50) e mais barato, MAS por ser similar nao pode vencer a buybox
        # nem definir o cheapest_price.
        assert net["is_buybox_winner"] is True
        assert amz["is_buybox_winner"] is False
        assert result["metrics"]["cheapest_price"] == 100.0  # NAO 50 -> prova a exclusao

    def test_engine_exception_recorded(self, monkeypatch):
        _pin_settings(monkeypatch)
        net_title = "Camisa Polo Aramis Azul"
        _patch_nlp(monkeypatch, {net_title: 0.90})

        service = _inject_engines(CrossMarketplaceService(), {
            "Mercado Livre": FakeEngine([]),
            "Netshoes": FakeEngine([_prod("Netshoes", net_title, 100.0, "http://net/1")]),
            "Amazon": FakeEngine([], raise_exc=RuntimeError("boom")),
        })

        result = asyncio.run(
            service.compare_product(
                broad_query=self.BROAD,
                strict_query=self.STRICT,
                target_sku=None,
                min_score=70.0,
                zipcode="01001000",
            )
        )

        reasons = {(e["marketplace"], e["reason"]) for e in result["errors"]}
        assert ("Amazon", "boom") in reasons
        # o pipeline sobrevive e ainda retorna o match estrito da Netshoes
        assert any(r["marketplace"] == "Netshoes" for r in result["results"])
        assert result["status"] == "success"


class TestSellerPrecedence:
    """
    Testa a regra de precedencia seller listagem vs PDP em _enrich_pdp_and_shipping.

    Regra esperada (Task 3):
      - PDP retorna seller real → sobrescreve (independente do seller da listagem)
      - PDP retorna default do marketplace → NÃO sobrescreve seller real da listagem
      - PDP lança exceção → seller da listagem é preservado; pipeline não quebra
      - PDP retorna seller real e listagem tinha default → seller final = PDP (caso comum)
    """

    STRICT = "Camisa Polo Aramis Masculina"
    BROAD = "camisa polo"
    TITLE = "Camisa Polo Aramis Azul"

    def _run(self, monkeypatch, listing_seller, pdp_seller):
        """Executa compare_product com um produto de Netshoes e retorna o seller final."""
        _pin_settings(monkeypatch)
        _patch_nlp(monkeypatch, {self.TITLE: 0.90})

        url = "http://net/1"
        details = {"seller": pdp_seller} if pdp_seller is not None else None

        service = _inject_engines(CrossMarketplaceService(), {
            "Mercado Livre": FakeEngine([]),
            "Amazon": FakeEngine([]),
            "Netshoes": FakeEngine(
                [_prod("Netshoes", self.TITLE, 100.0, url, seller=listing_seller)],
                details_by_url={url: details} if details is not None else {},
            ),
        })

        result = asyncio.run(
            service.compare_product(
                broad_query=self.BROAD,
                strict_query=self.STRICT,
                target_sku=None,
                min_score=70.0,
                zipcode="01001000",
            )
        )
        by_mp = {r["marketplace"]: r for r in result["results"]}
        return by_mp.get("Netshoes", {}).get("seller")

    def test_pdp_real_seller_overwrites_listing_default(self, monkeypatch):
        """PDP retorna lojista real "Shoestime", listagem tinha "Amazon" (default) → Shoestime."""
        seller = self._run(monkeypatch, listing_seller="Amazon", pdp_seller="Shoestime")
        assert seller == "Shoestime"

    def test_pdp_default_does_not_overwrite_listing_real_seller(self, monkeypatch):
        """PDP retorna "Amazon" (default), listagem tinha "Loja Real" → Loja Real (não regride)."""
        seller = self._run(monkeypatch, listing_seller="Loja Real", pdp_seller="Amazon")
        assert seller == "Loja Real"

    def test_pdp_exception_preserves_listing_seller(self, monkeypatch):
        """PDP lança exceção → seller permanece o da listagem; pipeline não quebra."""
        _pin_settings(monkeypatch)
        _patch_nlp(monkeypatch, {self.TITLE: 0.90})

        url = "http://net/1"

        class RaisingEngine(FakeEngine):
            async def get_product_details(self, u):
                raise RuntimeError("pdp offline")

        service = _inject_engines(CrossMarketplaceService(), {
            "Mercado Livre": FakeEngine([]),
            "Amazon": FakeEngine([]),
            "Netshoes": RaisingEngine(
                [_prod("Netshoes", self.TITLE, 100.0, url, seller="Loja Da Listagem")],
            ),
        })

        result = asyncio.run(
            service.compare_product(
                broad_query=self.BROAD,
                strict_query=self.STRICT,
                target_sku=None,
                min_score=70.0,
                zipcode="01001000",
            )
        )
        assert result["status"] == "success"
        by_mp = {r["marketplace"]: r for r in result["results"]}
        assert by_mp["Netshoes"]["seller"] == "Loja Da Listagem"

    def test_pdp_real_seller_overwrites_listing_when_listing_was_default(self, monkeypatch):
        """PDP retorna seller real e listagem tinha o default → seller final = o da PDP (caso comum)."""
        seller = self._run(monkeypatch, listing_seller="Netshoes", pdp_seller="Shoestime")
        assert seller == "Shoestime"


class TestEnrichDeliveryTimeAndBlockedState:
    """
    Task 1 (42-03, FRET-08/FRET-09 backend surfacing):
    _enrich_pdp_and_shipping deve surfacear delivery-time (prazo) quando o
    engine retorna essas chaves, e marcar p["_shipping_state"] = "blocked"
    quando o engine retorna None para um marketplace bloqueado (Netshoes),
    SEM jamais fixar um shipping_price=0.0 falso nesse caso. O caminho de
    frete gratis existente nao pode regredir.
    """

    STRICT = "Camisa Polo Aramis Masculina"
    BROAD = "camisa polo"
    TITLE = "Camisa Polo Aramis Azul"

    def _run(self, monkeypatch, shipping_result):
        _pin_settings(monkeypatch)
        _patch_nlp(monkeypatch, {self.TITLE: 0.90})

        url = "http://net/1"
        service = _inject_engines(CrossMarketplaceService(), {
            "Mercado Livre": FakeEngine([]),
            "Amazon": FakeEngine([]),
            "Netshoes": FakeEngine(
                [_prod("Netshoes", self.TITLE, 100.0, url)],
                shipping_by_url={url: shipping_result},
            ),
        })

        result = asyncio.run(
            service.compare_product(
                broad_query=self.BROAD,
                strict_query=self.STRICT,
                target_sku=None,
                min_score=70.0,
                zipcode="01001000",
            )
        )
        by_mp = {r["marketplace"]: r for r in result["results"]}
        return by_mp["Netshoes"]

    def test_enrich_surfaces_delivery_time(self, monkeypatch):
        """Quando o engine retorna chaves de prazo, elas sao surfaceadas no produto."""
        item = self._run(monkeypatch, {
            "is_free_shipping": False,
            "shipping_price": 20.0,
            "estimated_delivery_days": 5,
            "delivery_raw_text": "Chega em ate 5 dias uteis",
        })
        assert item["estimated_delivery_days"] == 5
        assert item["shipping_raw_text"] == "Chega em ate 5 dias uteis"
        assert item["shipping_price"] == 20.0

    def test_enrich_surfaces_blocked_state(self, monkeypatch):
        """None (Netshoes bloqueado) vira _shipping_state='blocked', nunca frete 0.0 falso."""
        item = self._run(monkeypatch, None)
        assert item["_shipping_state"] == "blocked"
        assert item.get("shipping_price") is None

    def test_enrich_free_shipping_still_works(self, monkeypatch):
        """Regressao: resultado de frete gratis existente continua funcionando."""
        item = self._run(monkeypatch, {"is_free_shipping": True, "shipping_price": 0.0})
        assert item["is_free_shipping"] is True
        assert item["shipping_price"] == 0.0
        assert item.get("_shipping_state") != "blocked"

    def test_enrich_none_from_unimplemented_engine_is_not_labeled_blocked(self, monkeypatch):
        """Amazon Tier 2 e um stub que sempre retorna None (nao uma tentativa real
        de calculo bloqueada por anti-bot). Rotular isso como 'blocked' seria uma
        alegacao falsa exibida ao operador (achado da verificacao goal-backward
        da Phase 42). Engines com SHIPPING_TIER2_BLOCKS_ON_NONE=False (Amazon)
        nao devem setar _shipping_state='blocked' quando calculate_shipping()
        retorna None."""

        class UnimplementedTier2Engine(FakeEngine):
            SHIPPING_TIER2_BLOCKS_ON_NONE = False

        _pin_settings(monkeypatch)
        _patch_nlp(monkeypatch, {self.TITLE: 0.90})

        url = "http://amz/1"
        service = _inject_engines(CrossMarketplaceService(), {
            "Mercado Livre": FakeEngine([]),
            "Netshoes": FakeEngine([]),
            "Amazon": UnimplementedTier2Engine(
                [_prod("Amazon", self.TITLE, 100.0, url)],
                shipping_by_url={url: None},
            ),
        })

        result = asyncio.run(
            service.compare_product(
                broad_query=self.BROAD,
                strict_query=self.STRICT,
                target_sku=None,
                min_score=70.0,
                zipcode="01001000",
            )
        )
        by_mp = {r["marketplace"]: r for r in result["results"]}
        item = by_mp["Amazon"]
        assert item.get("_shipping_state") != "blocked"


class TestInactiveMarketplaceExcluded:
    """UX-05 / D-11: deactivating a marketplace excludes it from the NEXT search.

    Testa que _active_engines() exclui engines cujo brand_key esta inativo em
    brands.json, e inclui apenas os ativos — sem restart de servidor (per-request).
    """

    STRICT = "Camisa Polo Aramis Masculina"
    BROAD = "camisa polo"

    def test_inactive_marketplace_excluded(self, monkeypatch):
        """Marketplace marcado is_active=False nao aparece na busca cross-marketplace.

        Estrategia: patch brand_service.list_brands para retornar apenas 'mercadolivre'
        e 'netshoes' como ativos (amazon inativo). Verifica que _active_engines() nao
        retorna a engine Amazon e que compare_product nao produz resultados da Amazon.
        """
        _pin_settings(monkeypatch)
        net_title = "Camisa Polo Aramis Azul"
        _patch_nlp(monkeypatch, {net_title: 0.90})

        # Simula brands.json com amazon marcado is_active=False
        from core.models import DynamicBrand
        from services import cross_marketplace_service as cms_module

        fake_active_brands = [
            DynamicBrand(
                # Valor de produção em brands.json é "mercado_livre" (COM underscore).
                # O fix normaliza esta chave para "mercadolivre" (chave do _ENGINE_MAP);
                # usar o valor real aqui fixa a regressão do BUG 2.
                brand_key="mercado_livre",
                brand_name="Mercado Livre",
                domain="mercadolivre.com.br",
                engine="mercadolivre",
                is_active=True,
            ),
            DynamicBrand(
                brand_key="netshoes",
                brand_name="Netshoes",
                domain="netshoes.com.br",
                engine="netshoes",
                is_active=True,
            ),
            # amazon OMITIDA → is_active=False
        ]

        # Patch brand_service.list_brands dentro do modulo cross_marketplace_service
        monkeypatch.setattr(
            cms_module.brand_service,
            "list_brands",
            lambda active_only=False: fake_active_brands if active_only else fake_active_brands,
        )

        service = CrossMarketplaceService()

        # _active_engines() deve retornar apenas Mercado Livre e Netshoes
        active = service._active_engines()
        assert "Mercado Livre" in active, "_active_engines deve incluir Mercado Livre (ativo)"
        assert "Netshoes" in active, "_active_engines deve incluir Netshoes (ativo)"
        assert "Amazon" not in active, "_active_engines NAO deve incluir Amazon (inativo)"

        # Substitui as instancias reais por FakeEngines controlaveis p/ a busca
        service._engine_instances["mercadolivre"] = FakeEngine([])  # ML sem resultados
        service._engine_instances["netshoes"] = FakeEngine(
            [_prod("Netshoes", net_title, 100.0, "http://net/1")]
        )
        service._engine_instances["amazon"] = FakeEngine(
            [_prod("Amazon", "Camisa Polo Aramis", 90.0, "http://amz/1")]
        )
        # Reconstroi _by_display apos trocar instancias
        service._by_display = {
            display: service._engine_instances[key]
            for key, (display, _) in cms_module._ENGINE_MAP.items()
        }

        result = asyncio.run(
            service.compare_product(
                broad_query=self.BROAD,
                strict_query=self.STRICT,
                target_sku=None,
                min_score=70.0,
                zipcode="01001000",
            )
        )

        marketplaces_in_results = {r["marketplace"] for r in result["results"]}
        assert "Amazon" not in marketplaces_in_results, (
            f"Amazon (inativa) nao deve aparecer nos resultados. Obtidos: {marketplaces_in_results}"
        )
        assert "Netshoes" in marketplaces_in_results, (
            f"Netshoes (ativa) deve aparecer nos resultados. Obtidos: {marketplaces_in_results}"
        )

    def test_active_marketplace_included(self, monkeypatch):
        """Marketplace marcado is_active=True aparece na busca (nao e excluido).

        Confirmacao positiva: quando todos os 3 marketplaces estao ativos,
        _active_engines() retorna todos os 3 engines.
        """
        from core.models import DynamicBrand
        from services import cross_marketplace_service as cms_module

        # _ENGINE_MAP usa a chave canônica "mercadolivre" (sem underscore), mas o
        # brand_key REAL de produção em brands.json é "mercado_livre" (com underscore).
        # Mapeamos as chaves do _ENGINE_MAP para os brand_keys de produção para que a
        # fixture reflita a realidade e fixe a regressão do BUG 2.
        _PRODUCTION_BRAND_KEY = {"mercadolivre": "mercado_livre"}
        fake_all_active = [
            DynamicBrand(
                brand_key=_PRODUCTION_BRAND_KEY.get(key, key),
                brand_name=display,
                domain=f"{key}.com.br",
                # O campo engine é incidental — _active_engines chaveia por brand_key.
                engine=key,
                is_active=True,
            )
            for key, (display, _) in cms_module._ENGINE_MAP.items()
        ]

        monkeypatch.setattr(
            cms_module.brand_service,
            "list_brands",
            lambda active_only=False: fake_all_active,
        )

        service = CrossMarketplaceService()
        active = service._active_engines()

        assert len(active) == 3, f"Esperado 3 engines ativos, obtido {len(active)}: {list(active)}"
        assert set(active.keys()) == {"Mercado Livre", "Netshoes", "Amazon"}
        # Regressão BUG 2: Mercado Livre (brand_key "mercado_livre") deve estar ativo.
        assert "Mercado Livre" in active, (
            "_active_engines deve incluir Mercado Livre quando o brand_key de produção "
            "'mercado_livre' está ativo (normalização para 'mercadolivre')"
        )
