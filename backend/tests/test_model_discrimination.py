"""
Testes de discriminação de modelo (Phase 23 — MODEL-01, MODEL-02, criterion 3, criterion 4, fallback).

Cobertura:
  - TestModelPenalty: exercita compute_final_match_score com o multiplicador HEAVY_WITH_BRAND=0.40
      3. (criterion 3 / anchor 3): candidato de modelo divergente (model_ratio≈0, mesma marca),
         com texto penalizado por HEAVY=0.40 e image=85, finaliza abaixo do cutoff 60 — o Gate 1
         não dispara porque texto_penalizado (88*0.40=35.2) < MED_TEXT_FLOOR(40).
      4. (criterion 4 / anchor 4): candidato de modelo+marca corretos (ratio>=0.75) não recebe
         penalidade e permanece no topo — não-regressão determinística via apply_visual_tiebreak.

  - TestVisualTiebreak: exercita o MESMO objeto de código apply_visual_tiebreak usado em produção
      1. (MODEL-01 / anchor 1): entre dois polos Aramis (modelo correto vs adjacente), o modelo
         correto (maior image_score) termina no topo de apply_visual_tiebreak.
      2. (MODEL-02 / anchor 2): dois candidatos Aramis com final_match_score dentro de uma janela
         de 10 pontos são reordenados pelo maior image_match_score — o visual atua como desempate,
         INCLUSIVE sobre o líder de texto da janela (Criterion 2 — "próximos => visual desempata").
      5. (fallback / anchor 5): VISUAL_TIEBREAK_ENABLED=False retorna ordem por (-final, preco);
         o mesmo para enabled=True mas todos image_match_score==0 — zero regressão.

  - TestVisualTiebreakBoundary: testes de regressão da CR-01 (bug de bucket-flooring). Exercitam
    as duas inversões reportadas no code review — devem FALHAR contra a implementação floored
    e PASSAR contra a chave de duas faixas corrigida.

  - TestVisualTiebreakRobustness: out-of-window genuíno, multi-marca (sanidade), lista vazia,
    chaves ausentes e window<=0.
"""
from services import relevance_gates
from services.cross_marketplace_service import apply_visual_tiebreak


# ---------------------------------------------------------------------------
# Fixtures base
# ---------------------------------------------------------------------------
# Modelo correto (Aramis, ratio alto, image alto)
_CORRECT_MODEL = {
    "titulo": "Polo Aramis Manga Curta Piquet Mescla Basica Marinho",
    "final_match_score": 86.0,
    "image_match_score": 92.0,
    "preco": 200.0,
}

# Modelo adjacente (Aramis, ratio baixo, image menor)
_ADJACENT_MODEL = {
    "titulo": "Polo Aramis Manga Curta Cotton Piquet Basic",
    "final_match_score": 85.0,
    "image_match_score": 72.0,
    "preco": 180.0,
}


# ---------------------------------------------------------------------------
# TestModelPenalty — verifica que o multiplicador HEAVY_WITH_BRAND=0.40 do Plan 01
#                    derruba candidatos de modelo divergente abaixo do cutoff
# ---------------------------------------------------------------------------
class TestModelPenalty:
    def test_model_ratio_zero_below_cutoff_with_high_image(self):
        # Criterion 3 / anchor 3: candidato de modelo divergente com mesma marca,
        # model_ratio≈0 → texto penalizado por HEAVY_WITH_BRAND=0.40.
        # raw_blend=88 → penalizado=88*0.40=35.2 < MED_TEXT_FLOOR(40) → Gate 1 não dispara.
        # Weighted: 35.2*0.60 + 85.0*0.40 = 21.12 + 34.0 = 55.12 < 60 (cutoff).
        text_penalizado_88 = 88.0 * 0.40   # = 35.2 — abaixo de MED_TEXT_FLOOR(40)
        final_88 = relevance_gates.compute_final_match_score(text_penalizado_88, 85.0)
        assert final_88 < 60.0, (
            f"Candidato de modelo divergente (raw=88, heavy=0.40, img=85) deveria ficar "
            f"abaixo do cutoff 60 com Gate 1 bloqueado, obteve {final_88}"
        )

        # Robustez: raw=90 também deve ficar abaixo do cutoff com heavy=0.40
        text_penalizado_90 = 90.0 * 0.40   # = 36.0 < 40 → Gate 1 não dispara
        final_90 = relevance_gates.compute_final_match_score(text_penalizado_90, 90.0)
        assert final_90 < 60.0, (
            f"Candidato de modelo divergente (raw=90, heavy=0.40, img=90) deveria ficar "
            f"abaixo do cutoff 60 com Gate 1 bloqueado, obteve {final_90}"
        )

    def test_correct_model_unaffected_by_penalty(self):
        # Criterion 4 / anchor 4: candidato de modelo+marca corretos (ratio>=0.75) não recebe
        # penalidade — apply_visual_tiebreak mantém o modelo correto no topo.
        correct = {
            "titulo": "Polo Aramis Manga Curta Piquet Marinho",
            "final_match_score": 91.0,
            "image_match_score": 92.0,
            "preco": 200.0,
        }
        adjacent = {
            "titulo": "Polo Aramis Manga Curta Cotton Piquet",
            "final_match_score": 82.0,
            "image_match_score": 75.0,
            "preco": 180.0,
        }
        # correto final=91/img=92 vs adjacente final=82/img=75 (ambos in-window de top=91):
        # o correto vence no cohort por -image. Sem penalidade indevida ao modelo correto.
        result = apply_visual_tiebreak(
            [adjacent, correct],   # adjacente primeiro — testando reordenação
            window=10.0,
            enabled=True,
        )
        assert result[0] is correct, (
            "Modelo correto (final=91, maior image) deve permanecer no topo — "
            "nenhuma penalidade aplicada a candidatos de ratio>=0.75"
        )


# ---------------------------------------------------------------------------
# TestVisualTiebreak — exercita apply_visual_tiebreak (o mesmo objeto de produção)
# ---------------------------------------------------------------------------
class TestVisualTiebreak:
    def test_correct_model_ranks_above_adjacent(self):
        # Anchor 1 (MODEL-01): dois polos Aramis (modelo correto vs adjacente) dentro
        # da janela de 10 pontos — o modelo correto (maior image_score) termina no topo.
        correct = {
            "titulo": "Polo Aramis Manga Curta Piquet Mescla Basica Marinho",
            "final_match_score": 86.0,
            "image_match_score": 90.0,
            "preco": 200.0,
        }
        adjacent = {
            "titulo": "Polo Aramis Manga Curta Cotton Piquet Basic",
            "final_match_score": 85.0,
            "image_match_score": 68.0,
            "preco": 180.0,
        }
        result = apply_visual_tiebreak([adjacent, correct], window=10.0, enabled=True)
        assert result[0] is correct, (
            "MODEL-01: modelo correto (maior image_score) deve ficar no topo entre "
            "candidatos da mesma marca dentro da janela de ambiguidade"
        )

    def test_promotes_higher_image_within_window(self):
        # Anchor 2 (MODEL-02): dois candidatos Aramis com final_match_score dentro de
        # 10 pontos (86 vs 85) são reordenados pelo maior image_match_score (92 vs 72).
        correct_model = _CORRECT_MODEL   # final=86, img=92
        wrong_model = _ADJACENT_MODEL    # final=85, img=72
        result = apply_visual_tiebreak([wrong_model, correct_model], window=10.0, enabled=True)
        assert result[0] is correct_model, (
            "MODEL-02: candidato com maior image_match_score deve subir ao topo "
            "quando os scores de texto estão dentro da janela de ambiguidade"
        )

    def test_text_leader_overtaken_by_visual_within_window(self):
        # Criterion 2 (forma forte): o LÍDER de texto da janela PODE ser ultrapassado pelo
        # visual. leader final=90/img=40 vs challenger final=84/img=95 (gap 6 ≤ 10, mesma marca).
        # "Textos próximos => o de maior similaridade visual fica acima" — challenger vence,
        # apesar de ter texto MENOR. (Falharia se o visual fosse mera confirmação pós-texto.)
        leader = {
            "titulo": "Polo Aramis Manga Curta Piquet Basica",
            "final_match_score": 90.0,
            "image_match_score": 40.0,
            "preco": 210.0,
        }
        challenger = {
            "titulo": "Polo Aramis Manga Curta Piquet Mescla Marinho",
            "final_match_score": 84.0,
            "image_match_score": 95.0,
            "preco": 190.0,
        }
        result = apply_visual_tiebreak([leader, challenger], window=10.0, enabled=True)
        assert result[0] is challenger, (
            "MODEL-02: dentro da janela de ambiguidade, o candidato de maior image_score "
            "(challenger, final=84/img=95) deve ultrapassar o líder de texto "
            "(final=90/img=40) — o visual é DESEMPATE, não confirmação"
        )

    def test_fallback_when_disabled(self):
        # Anchor 5 (fallback): VISUAL_TIEBREAK_ENABLED=False → ordem por (-final, preco),
        # idêntico ao comportamento atual do .sort() in-place.
        a = {"titulo": "Polo Aramis A", "final_match_score": 85.0, "image_match_score": 90.0, "preco": 100.0}
        b = {"titulo": "Polo Aramis B", "final_match_score": 88.0, "image_match_score": 70.0, "preco": 100.0}
        # enabled=False: ordenação por -final → b(88) antes de a(85)
        result_disabled = apply_visual_tiebreak([a, b], window=10.0, enabled=False)
        assert result_disabled[0] is b, (
            "Fallback (enabled=False): ordenação por -final_match_score — b(88) deve vir antes de a(85)"
        )

        # enabled=True mas TODOS image_match_score==0 → mesma ordem de fallback por texto
        a_no_img = {"titulo": "Polo Aramis A", "final_match_score": 85.0, "image_match_score": 0.0, "preco": 100.0}
        b_no_img = {"titulo": "Polo Aramis B", "final_match_score": 88.0, "image_match_score": 0.0, "preco": 100.0}
        result_no_img = apply_visual_tiebreak([a_no_img, b_no_img], window=10.0, enabled=True)
        assert result_no_img[0] is b_no_img, (
            "Fallback (todos image==0): ordenação por -final_match_score — b(88) antes de a(85)"
        )


# ---------------------------------------------------------------------------
# TestVisualTiebreakBoundary — regressão da CR-01 (bug de bucket-flooring).
# Estes dois testes FALHAM contra a implementação floored e PASSAM contra a
# chave de duas faixas (-top, -image) corrigida.
# ---------------------------------------------------------------------------
class TestVisualTiebreakBoundary:
    def test_in_window_not_demoted_below_out_of_window_across_bucket(self):
        # CR-01 inversão (a): in-window com final MAIOR não pode cair abaixo de um
        # out-of-window com final MENOR só por estar num bucket inferior.
        # top=92, window=10. B in-window (final=89, gap 3). A out-of-window (final=81, gap 11>10).
        # Implementação floored: A=(0,-81), B=(0,floor(89/10)*10=80,-img) -> -81 < -80 -> A acima de B (BUG).
        top = {"titulo": "Polo Aramis Premium", "final_match_score": 92.0, "image_match_score": 85.0, "preco": 300.0}
        b_in = {"titulo": "Polo Aramis Piquet Mescla", "final_match_score": 89.0, "image_match_score": 20.0, "preco": 250.0}
        a_out = {"titulo": "Polo Aramis Cotton Basic", "final_match_score": 81.0, "image_match_score": 99.0, "preco": 150.0}
        result = apply_visual_tiebreak([a_out, b_in, top], window=10.0, enabled=True)
        assert result.index(b_in) < result.index(a_out), (
            "CR-01(a): candidato in-window (final=89) deve ficar acima do out-of-window "
            f"(final=81) apesar do bucket — ordem obtida: {[r['final_match_score'] for r in result]}"
        )
        # E o out-of-window de imagem alta (99) NÃO é promovido para dentro do cohort:
        assert result[-1] is a_out, (
            "CR-01(a): out-of-window (gap>window) com image alta não deve ser promovido ao cohort"
        )

    def test_visual_decides_across_bucket_boundary(self):
        # CR-01 inversão (b): dois candidatos in-window straddling uma fronteira de bucket
        # devem ser desempatados por IMAGE, não pela linha de grade.
        # G final=80.0/img=10, H final=79.9/img=99 (mesma marca, top=80.0, ambos in-window).
        # Implementação floored: G bucket=80, H bucket=70 -> G(img=10) vencia H(img=99) (BUG).
        g = {"titulo": "Polo Aramis Modelo G", "final_match_score": 80.0, "image_match_score": 10.0, "preco": 100.0}
        h = {"titulo": "Polo Aramis Modelo H", "final_match_score": 79.9, "image_match_score": 99.0, "preco": 100.0}
        result = apply_visual_tiebreak([g, h], window=10.0, enabled=True)
        assert result[0] is h, (
            "CR-01(b): com textos a 0.1 de distância (mesmo cohort), o maior image_score "
            "(H, img=99) deve vencer — o desempate visual não pode morrer numa fronteira de bucket"
        )


# ---------------------------------------------------------------------------
# TestVisualTiebreakRobustness — out-of-window genuíno, multi-marca, edge cases
# ---------------------------------------------------------------------------
class TestVisualTiebreakRobustness:
    def test_genuine_out_of_window_not_promoted_by_image(self):
        # Substitui o antigo test_out_of_window_candidate_not_demoted (cuja premissa era
        # inválida: final=92 vs 86 com window=10 são AMBOS in-window de top=92).
        # Out-of-window GENUÍNO: top=92, out final=75 (gap 17 > 10) com image=99.
        # O out-of-window NÃO deve ser promovido ao cohort apesar da imagem alta.
        top = {"titulo": "Polo Aramis Piquet Marinho", "final_match_score": 92.0, "image_match_score": 50.0, "preco": 200.0}
        out = {"titulo": "Polo Aramis Outro Modelo", "final_match_score": 75.0, "image_match_score": 99.0, "preco": 150.0}
        result = apply_visual_tiebreak([out, top], window=10.0, enabled=True)
        assert result[0] is top, (
            "Out-of-window (gap=17 > window=10) com image=99 não deve ultrapassar o cohort "
            "in-window (top final=92) — fora da janela de ambiguidade o visual não desempata"
        )

    def test_multi_brand_sanity_deterministic_order(self):
        # Sanidade multi-marca (cenário de rollback com brand gate desativado): sem crash,
        # ordem determinística, cohort da marca de maior top-score primeiro.
        aramis = {"titulo": "Polo Aramis Piquet", "final_match_score": 90.0, "image_match_score": 50.0, "preco": 200.0}
        reserva = {"titulo": "Camisa Reserva Basica", "final_match_score": 88.0, "image_match_score": 95.0, "preco": 180.0}
        result = apply_visual_tiebreak([reserva, aramis], window=10.0, enabled=True)
        assert result[0] is aramis, (
            "Multi-marca: o cohort da marca de maior top-score (aramis, top=90) deve vir "
            "antes do cohort de menor top-score (reserva, top=88) — ordem determinística"
        )

    def test_empty_list_returns_empty(self):
        assert apply_visual_tiebreak([], window=10.0, enabled=True) == []

    def test_missing_keys_do_not_crash(self):
        # Candidatos com chaves ausentes não devem levantar exceção (defaults via .get).
        with_img = {"titulo": "Polo Aramis A", "final_match_score": 85.0, "image_match_score": 90.0, "preco": 100.0}
        sparse = {"titulo": "Polo Aramis B", "final_match_score": 80.0}  # sem image/preco
        result = apply_visual_tiebreak([sparse, with_img], window=10.0, enabled=True)
        assert len(result) == 2 and with_img in result and sparse in result

    def test_window_zero_degrades_to_text_order(self):
        # window<=0: apenas o próprio top fica no cohort; sem divisão por zero (sem flooring).
        top = {"titulo": "Polo Aramis Top", "final_match_score": 90.0, "image_match_score": 10.0, "preco": 100.0}
        lower = {"titulo": "Polo Aramis Lower", "final_match_score": 85.0, "image_match_score": 99.0, "preco": 100.0}
        result = apply_visual_tiebreak([lower, top], window=0.0, enabled=True)
        assert result[0] is top, (
            "window=0: só o top (gap 0) fica no cohort; o de final menor não é promovido por image"
        )
