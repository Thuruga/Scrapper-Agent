"""
Testes da lógica pura do motor de relevância (services/relevance_gates.py).

Cobrem a régua de decisão (gates) de score, o ponto de corte, normalização,
deduplicação e seleção de buybox — antes sem nenhuma cobertura de teste.
"""
from types import SimpleNamespace

import pytest

from services import relevance_gates as rg


# ---------------------------------------------------------------------------
# compute_final_match_score — cada gate da régua de decisão
# ---------------------------------------------------------------------------
class TestFinalMatchScore:
    def test_strong_text_dominates(self):
        # t >= 90 -> max(t, i), mesmo com imagem fraca
        assert rg.compute_final_match_score(95.0, 30.0) == 95.0
        assert rg.compute_final_match_score(95.0, 99.0) == 99.0

    def test_strong_text_ignores_anti_waf_gate(self):
        # t >= 90 vence antes do gate anti-WAF (i == 0)
        assert rg.compute_final_match_score(95.0, 0.0) == 95.0

    def test_high_image_with_decent_text(self):
        # i >= 85 e t >= 40 -> max
        assert rg.compute_final_match_score(50.0, 90.0) == 90.0

    def test_high_text_with_medium_image(self):
        # t >= 85 e i >= 45 -> max
        assert rg.compute_final_match_score(88.0, 50.0) == 88.0

    def test_anti_waf_text_rescue(self):
        # i == 0 (download falhou) mas t >= 80 -> aprova pela nota de texto
        assert rg.compute_final_match_score(82.0, 0.0) == 82.0

    def test_anti_waf_does_not_apply_below_floor(self):
        # i == 0 e t < 80 -> média ponderada (não resgata)
        result = rg.compute_final_match_score(50.0, 0.0, text_weight=0.6, image_weight=0.4)
        assert result == pytest.approx(30.0)

    def test_weighted_average_fallback(self):
        result = rg.compute_final_match_score(70.0, 30.0, text_weight=0.6, image_weight=0.4)
        assert result == pytest.approx(70.0 * 0.6 + 30.0 * 0.4)

    def test_weighted_average_just_below_text_floor(self):
        # t=39 (<40) com i=90: nenhum gate de max se aplica -> ponderada
        result = rg.compute_final_match_score(39.0, 90.0, text_weight=0.6, image_weight=0.4)
        assert result == pytest.approx(39.0 * 0.6 + 90.0 * 0.4)

    def test_uses_configured_weights_by_default(self):
        from config import relevance_settings
        result = rg.compute_final_match_score(50.0, 50.0)
        expected = (
            50.0 * relevance_settings.FINAL_TEXT_WEIGHT
            + 50.0 * relevance_settings.FINAL_IMAGE_WEIGHT
        )
        assert result == pytest.approx(expected)


# ---------------------------------------------------------------------------
# compute_min_score_cutoff
# ---------------------------------------------------------------------------
class TestMinScoreCutoff:
    def test_requested_min_wins_when_higher(self):
        assert rg.compute_min_score_cutoff(70.0, has_vision=True) == 70.0

    def test_vision_floor_wins_when_higher(self):
        from config import relevance_settings
        result = rg.compute_min_score_cutoff(10.0, has_vision=True)
        assert result == relevance_settings.CROSS_MIN_SCORE_WITH_VISION

    def test_no_vision_uses_lower_floor(self):
        from config import relevance_settings
        result = rg.compute_min_score_cutoff(10.0, has_vision=False)
        assert result == relevance_settings.CROSS_MIN_SCORE_WITHOUT_VISION


# ---------------------------------------------------------------------------
# normalize_engine_products
# ---------------------------------------------------------------------------
class TestNormalizeEngineProducts:
    def _make_result(self, **overrides):
        defaults = dict(
            brand="Nike",
            product_name="Tênis Air",
            price_full=199.9,
            url="http://x/p",
            image_url="http://img/1.jpg",
            seller="LojaX",
        )
        defaults.update(overrides)
        return SimpleNamespace(products=[SimpleNamespace(**defaults)])

    def test_maps_fields(self):
        out = rg.normalize_engine_products(self._make_result(), "Amazon")
        assert out == [
            {
                "plataforma": "Nike",
                "titulo": "Tênis Air",
                "preco": 199.9,
                "url": "http://x/p",
                "imagem": "http://img/1.jpg",
                "seller": "LojaX",
            }
        ]

    def test_falls_back_to_platform_when_no_brand(self):
        out = rg.normalize_engine_products(self._make_result(brand=None), "Amazon")
        assert out[0]["plataforma"] == "Amazon"

    def test_seller_defaults_to_na(self):
        out = rg.normalize_engine_products(self._make_result(seller=None), "Amazon")
        assert out[0]["seller"] == "N/A"

    def test_price_zero_when_no_price(self):
        out = rg.normalize_engine_products(self._make_result(price_full=0.0), "Amazon")
        assert out[0]["preco"] == 0.0


# ---------------------------------------------------------------------------
# dedup_results
# ---------------------------------------------------------------------------
class TestDedupResults:
    def _r(self, marketplace, url, price=10.0):
        return {"marketplace": marketplace, "url": url, "price": price, "variant_count": 1}

    def test_collapses_same_marketplace_url(self):
        out = rg.dedup_results([
            self._r("Amazon", "http://a/1"),
            self._r("Amazon", "http://a/1"),
            self._r("Amazon", "http://a/1"),
        ])
        assert len(out) == 1
        assert out[0]["variant_count"] == 3

    def test_keeps_distinct_urls(self):
        out = rg.dedup_results([
            self._r("Amazon", "http://a/1"),
            self._r("Amazon", "http://a/2"),
        ])
        assert len(out) == 2

    def test_same_url_different_marketplace_not_collapsed(self):
        out = rg.dedup_results([
            self._r("Amazon", "http://a/1"),
            self._r("Netshoes", "http://a/1"),
        ])
        assert len(out) == 2

    def test_empty_urls_never_collapse(self):
        out = rg.dedup_results([
            self._r("Amazon", ""),
            self._r("Amazon", ""),
        ])
        assert len(out) == 2


# ---------------------------------------------------------------------------
# mark_buybox_winner
# ---------------------------------------------------------------------------
class TestBuyboxWinner:
    def test_cheapest_wins(self):
        results = [
            {"price": 30.0, "is_buybox_winner": False},
            {"price": 10.0, "is_buybox_winner": False},
            {"price": 20.0, "is_buybox_winner": False},
        ]
        rg.mark_buybox_winner(results)
        assert results[1]["is_buybox_winner"] is True
        assert sum(1 for r in results if r["is_buybox_winner"]) == 1

    def test_empty_list_is_safe(self):
        assert rg.mark_buybox_winner([]) == []


# ---------------------------------------------------------------------------
# select_top_candidates_per_platform (extraído de compare_product — WS1)
# ---------------------------------------------------------------------------
class TestSelectTopCandidates:
    def test_groups_sorts_and_caps_per_platform(self):
        produtos = [
            {"plataforma": "A", "text_match_score": 10.0},
            {"plataforma": "A", "text_match_score": 90.0},
            {"plataforma": "A", "text_match_score": 50.0},
            {"plataforma": "B", "text_match_score": 70.0},
        ]
        out = rg.select_top_candidates_per_platform(produtos, max_per_engine=2)
        a = [p["text_match_score"] for p in out if p["plataforma"] == "A"]
        b = [p["text_match_score"] for p in out if p["plataforma"] == "B"]
        assert a == [90.0, 50.0]  # ordenado por -text e cortado em 2
        assert b == [70.0]


# ---------------------------------------------------------------------------
# apply_similar_fallback (S1, extraído de compare_product — WS1)
# ---------------------------------------------------------------------------
class TestApplySimilarFallback:
    def test_recovers_zeroed_platform_as_similar(self):
        estrito_net = {"plataforma": "Netshoes", "final_match_score": 90.0, "preco": 100.0}
        bruto_amz = {"plataforma": "Amazon", "final_match_score": 30.0, "preco": 50.0}
        produtos_filtrados = [estrito_net]
        todos = [estrito_net, bruto_amz]

        out, used = rg.apply_similar_fallback(
            produtos_filtrados, todos, enabled=True, min_score=15.0
        )
        assert used is True
        assert bruto_amz in out
        assert bruto_amz["_is_similar"] is True
        # Netshoes (match estrito) não é marcado como similar
        assert "_is_similar" not in estrito_net

    def test_disabled_is_noop(self):
        produtos_filtrados = [{"plataforma": "Netshoes", "final_match_score": 90.0, "preco": 100.0}]
        todos = produtos_filtrados + [{"plataforma": "Amazon", "final_match_score": 30.0, "preco": 50.0}]
        out, used = rg.apply_similar_fallback(produtos_filtrados, todos, enabled=False)
        assert used is False
        assert len(out) == 1

    def test_below_min_score_not_recovered(self):
        estrito = {"plataforma": "Netshoes", "final_match_score": 90.0, "preco": 100.0}
        fraco = {"plataforma": "Amazon", "final_match_score": 10.0, "preco": 50.0}
        out, used = rg.apply_similar_fallback([estrito], [estrito, fraco], enabled=True, min_score=15.0)
        assert used is False
        assert fraco not in out


# ---------------------------------------------------------------------------
# cap_results_per_platform (extraído de compare_product — WS1)
# ---------------------------------------------------------------------------
class TestCapResultsPerPlatform:
    def test_caps_preserving_order(self):
        produtos = [
            {"plataforma": "A", "id": 1},
            {"plataforma": "A", "id": 2},
            {"plataforma": "A", "id": 3},
            {"plataforma": "B", "id": 4},
        ]
        out = rg.cap_results_per_platform(produtos, max_per_platform=2)
        assert [p["id"] for p in out] == [1, 2, 4]


# ---------------------------------------------------------------------------
# build_formatted_results (extraído de compare_product — WS1)
# ---------------------------------------------------------------------------
class TestBuildFormattedResults:
    def test_landed_price_with_and_without_shipping(self):
        produtos = [
            {
                "plataforma": "Netshoes", "titulo": "Polo", "preco": 100.0, "url": "u1",
                "imagem": "i1", "seller": "S", "text_match_score": 92.0,
                "image_match_score": 0.0, "final_match_score": 92.0, "shipping_price": 20.0,
            },
            {
                "plataforma": "Amazon", "titulo": "Polo2", "preco": 80.0, "url": "u2",
                "final_match_score": 85.0, "_is_similar": True,
            },
        ]
        out = rg.build_formatted_results(produtos)
        assert out[0]["landed_price"] == 120.0  # preço + frete
        assert out[0]["match_score"] == 92.0    # alias de final_match_score
        assert out[0]["is_similar"] is False
        assert out[1]["landed_price"] == 80.0    # sem frete -> só o preço
        assert out[1]["seller"] == "N/A"         # default quando ausente
        assert out[1]["is_similar"] is True
