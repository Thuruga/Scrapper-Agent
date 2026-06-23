"""
Testes do gate de marca (Phase 22 — BRAND-01, BRAND-02, BRAND-03).

Cobertura:
  - TestBrandGate: exercita NLPService.brand_is_present diretamente
      1. Caso-âncora: polo Hering descartada numa busca Aramis (bug validado)
      2. Não-regressão: título com "aramis" passa
      3. No-op: query sem marca conhecida não remove nada
      4. Guarda de cor (HIGH-2): veredito de marca não muda com token de cor
      5. Independência do resgate visual (BRAND-02): compute_final_match_score
         resgata o item para 85, mas brand_is_present ainda o descarta
  - TestBrandGatePredicate: exercita o MESMO objeto de código usado em produção
      6. passes_brand_gate com enabled=True descarta o Hering (BRAND-02)
      7. passes_brand_gate com enabled=False mantém o Hering (BRAND-03)
  - (integração): o item Hering (final=85, preco=100) desaparece de
    produtos_filtrados quando enabled=True e aparece quando enabled=False;
    cutoff fixado em 60 explicitamente para provar que 85>=60 e a queda se
    deve à marca, não ao score.
"""
from services import relevance_gates
from services.cross_marketplace_service import passes_brand_gate
from services.nlp_service import nlp_service


# ---------------------------------------------------------------------------
# Constantes usadas em múltiplos testes
# ---------------------------------------------------------------------------
_OFFICIAL_ARAMIS = "Camisa Polo Aramis Masculina aramis"
_TITLE_HERING = "Camisa Polo Basica Masculina Manga Curta Em Piquet Hering"
_TITLE_ARAMIS = "Camisa Polo Aramis Masculina Piquet"
_OFFICIAL_NO_BRAND = "Camisa Polo Masculina Piquet"


# ---------------------------------------------------------------------------
# TestBrandGate — exercita brand_is_present
# ---------------------------------------------------------------------------
class TestBrandGate:
    def test_hering_polo_discarded_against_aramis_query(self):
        # Caso-âncora: query oficial Aramis vs título Hering — marca ausente → descartado
        assert nlp_service.brand_is_present(
            _OFFICIAL_ARAMIS,
            _TITLE_HERING,
        ) is False

    def test_aramis_title_passes(self):
        # Não-regressão: ~95% dos casos reais têm a marca no título
        assert nlp_service.brand_is_present(
            _OFFICIAL_ARAMIS,
            _TITLE_ARAMIS,
        ) is True

    def test_noop_when_query_has_no_known_brand(self):
        # Gate é no-op quando a query não especifica marca conhecida
        # (ex: "Camisa Polo Masculina Piquet" → não filtra nada)
        assert nlp_service.brand_is_present(
            _OFFICIAL_NO_BRAND,
            "Camisa Polo Hering",
        ) is True

    def test_brand_detection_unaffected_by_color_tokens(self):
        # Guarda de cor (HIGH-2): adicionar ou remover token de cor não muda o veredito
        # de marca. Por construção: known_brands_for_detection ∩ colors == ∅
        # (aramis/reserva/tommy não são cores), logo remove_colors é supérfluo aqui.
        result_with_color = nlp_service.brand_is_present(
            "Polo Aramis Azul aramis",
            "Polo Azul Aramis",
        )
        result_without_color = nlp_service.brand_is_present(
            "Polo Aramis aramis",
            "Polo Aramis",
        )
        assert result_with_color is True
        assert result_without_color is True
        # O veredito deve ser idêntico independentemente do token de cor
        assert result_with_color == result_without_color

    def test_independent_of_visual_rescue(self):
        # BRAND-02: prova que o filtro de marca é INDEPENDENTE do Gate 1 visual.
        # O Gate 1 visual de relevance_gates resgata text=40.9 + img=85 para final=85
        # (acima do cutoff 60) — MAS brand_is_present ainda descarta o item Hering.
        final_score = relevance_gates.compute_final_match_score(40.9, 85.0)
        assert final_score == 85.0, (
            f"Gate 1 visual deveria resgatar para 85, obteve {final_score}"
        )
        # Apesar do resgate visual, a marca está ausente → descartado
        assert nlp_service.brand_is_present(
            _OFFICIAL_ARAMIS,
            _TITLE_HERING,
        ) is False


# ---------------------------------------------------------------------------
# TestBrandGatePredicate — exercita passes_brand_gate (o mesmo objeto de produção)
# ---------------------------------------------------------------------------
class TestBrandGatePredicate:
    def test_passes_brand_gate_drops_hering_when_enabled(self):
        # Predicado real: flag True, query Aramis, título Hering → descartado (BRAND-02)
        assert passes_brand_gate(_TITLE_HERING, _OFFICIAL_ARAMIS, True) is False

    def test_brand_gate_disabled_keeps_item(self):
        # Predicado real: flag False → gate inativo, item mantido (BRAND-03)
        assert passes_brand_gate(_TITLE_HERING, _OFFICIAL_ARAMIS, False) is True

    def test_integration_hering_absent_enabled_present_disabled(self):
        # Integração (BRAND-02 anti-tautologia, MEDIUM):
        # Constrói produtos_filtrados com os MESMOS três predicados de produção,
        # chamando passes_brand_gate importado (sem reimplementar o predicado).
        # Cutoff fixado em 60 explicitamente para que 85 >= 60 seja verificável —
        # a queda do item Hering é atribuível à marca, não ao score.
        official_title = _OFFICIAL_ARAMIS

        todos_produtos = [
            # Item Hering: final=85, preco=100 — passa score/preço, cai no gate de marca
            {"titulo": _TITLE_HERING, "final_match_score": 85.0, "preco": 100.0},
            # Item Aramis: final=85, preco=120 — passa todos os predicados
            {"titulo": _TITLE_ARAMIS, "final_match_score": 85.0, "preco": 120.0},
        ]

        cutoff = 60  # fixado explicitamente; 85 >= 60 confirma que score não é o problema
        assert 85.0 >= cutoff, "Premissa violada: score do Hering deveria passar pelo cutoff"

        # Com gate ativo (enabled=True): Hering deve ser descartado
        filtrados_on = [
            p for p in todos_produtos
            if p["final_match_score"] >= cutoff
            and p["preco"] > 0
            and passes_brand_gate(p["titulo"], official_title, True)
        ]
        titulos_on = [p["titulo"] for p in filtrados_on]
        assert _TITLE_HERING not in titulos_on, "Hering deveria ser descartado com gate ativo"
        assert _TITLE_ARAMIS in titulos_on, "Aramis deveria permanecer com gate ativo"

        # Com gate desativado (enabled=False): Hering deve aparecer
        filtrados_off = [
            p for p in todos_produtos
            if p["final_match_score"] >= cutoff
            and p["preco"] > 0
            and passes_brand_gate(p["titulo"], official_title, False)
        ]
        titulos_off = [p["titulo"] for p in filtrados_off]
        assert _TITLE_HERING in titulos_off, "Hering deveria sobreviver com gate desativado"
        assert _TITLE_ARAMIS in titulos_off, "Aramis deveria permanecer com gate desativado"
