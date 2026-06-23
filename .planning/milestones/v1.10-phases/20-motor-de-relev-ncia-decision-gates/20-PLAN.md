# Phase 20: Motor de Relevância - Decision Gates - Plan

**Goal:** Substituir o sistema de média linear rígida por uma árvore de decisão baseada em gates.

## Tasks

1. **[REL-01, REL-02, REL-03, REL-04] Implementar Árvore de Decisão no Score Final**
   - Arquivo: `services/cross_marketplace_service.py`
   - Ação: Na função local `run_visual_validation`, remover o cálculo linear estrito:
     ```python
     p["final_match_score"] = (
         p["text_match_score"] * relevance_settings.FINAL_TEXT_WEIGHT
         + p["image_match_score"] * relevance_settings.FINAL_IMAGE_WEIGHT
     )
     ```
     Substituir por:
     ```python
     t_score = p["text_match_score"]
     i_score = p["image_match_score"]

     if i_score >= 85.0 and t_score >= 40.0:
         p["final_match_score"] = max(i_score, t_score) # Ou um valor fixo alto que aprova
     elif t_score >= 85.0 and i_score >= 45.0:
         p["final_match_score"] = max(i_score, t_score)
     else:
         p["final_match_score"] = (
             t_score * relevance_settings.FINAL_TEXT_WEIGHT
             + i_score * relevance_settings.FINAL_IMAGE_WEIGHT
         )
     ```
   - Justificativa: Isso aplica os "Gates" solicitados. Se a imagem é muito parecida, somos lenientes no texto e vice versa.

2. **Verificação Local**
   - Ação: Executar um sanity check para validar que o arquivo python compila sem erros.
