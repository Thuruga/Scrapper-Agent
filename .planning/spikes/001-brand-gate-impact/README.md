---
spike: 001
name: brand-gate-impact
type: standard
validates: "Given os 71 result-sets cross reais, when aplico gate rígido de marca no lugar do ×0.50, then meço quantos itens saem e classifico em ganho-de-precisão vs perda-de-cobertura"
verdict: VALIDATED
related: [002]
tags: [search, relevance, brand]
---

# Spike 001: Impacto do Gate Rígido de Marca

## What This Validates
**Given** os 71 jobs `cross` reais em `data/search_history.json`, **when** se aplica um gate
rígido de marca (descartar item cujo título não contém a marca da query) no lugar da penalidade
suave `score * 0.50`, **then** medir quantos itens são removidos e classificá-los em
ganho-de-precisão (visual baixo) vs perda-de-cobertura (visual alto).

## Research
Sem dependências externas novas — reutiliza o `services.nlp_service` real (rapidfuzz, já no
projeto) e os scores CLIP já armazenados no histórico. Experimento offline e determinístico.

Prior art: o [spike de EAN](../../notes/spike-ean-sku-search.md) já invalidou a busca por EAN
(cobertura ruim) e listou o "filtro rígido pós-busca" (Opção 2) como alternativa — é exatamente
o que este spike mede.

## How to Run
```bash
python .planning/spikes/001-brand-gate-impact/experiment.py
```
Gera `REPORT.md` (tabelas) e imprime o resumo. Verificações pontuais rodadas inline (ver trilha).

## What to Expect
Contagem de itens que o gate rígido removeria, repartidos por bucket de score visual, mais
amostras reais de títulos por bucket e quebra por marketplace.

## Investigation Trail

### Iteração 1 — medição estrutural
Rodado o experimento sobre 1454 itens exibidos (71 jobs). Resultado: **95% dos itens exibidos
já contêm a marca** no título; só **5% (78 itens)** são brand-absent (o que o gate rígido
removeria). Dos 78: 4 com visual baixo (<60), 1 com visual alto (>=85), **73 ambíguos
(60–85)**, e **11 nomeiam um concorrente explícito** (ex: "...Piquet **Hering**").

### Iteração 2 — surpresa nos dados: histórico é anterior à penalidade de marca
O pior falso positivo (polo **Hering**) aparece com `text_match_score=88` armazenado. Se a
penalidade `×0.50` tivesse sido aplicada, seria ~44. Logo o **histórico salvo é anterior** ao
código atual da penalidade de marca. Recalculado ao vivo com o `nlp_service` atual:

| Título vs query oficial Aramis | Score de texto (vivo) |
|---|---|
| `...Piquet Hering` (marca ausente) | **40.9** (penalidade aplicada ✓) |
| `...Aramis` (marca presente) | 100.0 |
| `...Polo Masculina ... Azul` (genérico) | 21.2 |

→ A penalidade de marca **está viva e funcionando** no texto. Mas isso levantou a próxima
pergunta: 40.9 é suficiente para barrar?

### Iteração 3 — smoking gun: o gate visual desfaz a penalidade de marca
Passado o caso Hering pelos decision gates atuais (`relevance_gates.compute_final_match_score`)
com `text=40.9` e `img=85` (CLIP armazenado):

```
compute_final_match_score(40.9, 85.0) -> 85.0
cutoff com visão = 60.0  ->  Hering PASSA (85 >= 60)
```

A regra `if img >= HIGH_IMAGE_SCORE (85) and text >= MED_TEXT_FLOOR (40): return max(img, text)`
([relevance_gates.py:51](../../../services/relevance_gates.py)) **resgata o concorrente pelo
visual**, anulando a penalidade de marca. Um piquet polo da Hering "parece" um piquet polo da
Aramis para o CLIP → img alto → passa.

### Iteração 4 — "perda de cobertura" pelo proxy visual era ruído
O único item rotulado como perda-de-cobertura (`Sanders Soft Back Slip On`, img=88) é, na
verdade, **outro tênis de marca diferente** que só parece visualmente. Conclusão importante:
**visual alto NÃO significa "mesmo produto, marca omitida"** — significa "parece". Logo a
presença da marca é um sinal **independente e insubstituível** que o visual não reconstrói.

## Results

**Verdict: VALIDATED** — adotar o gate rígido de marca é justificado e de baixo risco de
cobertura, mas com nuances importantes.

**Evidências:**
1. **O gate é necessário porque a penalidade de texto é anulada pelo gate visual.** Caso real e
   reprodutível: polo Hering hoje → texto penalizado a 40.9 → mas final 85 via resgate visual →
   exibido. Só um filtro de marca *independente do score* (descartar brand-absent) elimina isso.
2. **Risco de cobertura é baixo na prática.** Entre os itens brand-absent exibidos, os de visual
   alto são dominados por concorrentes parecidos (Hering, Sanders), não por Aramis legítimo com
   marca omitida. Remover brand-absent não derruba produto Aramis genuíno de forma relevante.
3. **A marca é sinal independente do visual** — não dá para substituí-la por threshold de CLIP.

**Surpresas:**
- Histórico salvo é anterior à penalidade de marca (scores não refletem o código atual) →
  qualquer auditoria futura sobre esse JSON precisa recalcular ao vivo.
- O gate visual `max(img, text)` é o verdadeiro vilão dos falsos positivos de concorrente
  parecido, não a "leniência" da penalidade de texto.

**Limites / o que observar:**
- **Lever pequeno:** o gate só toca os ~5% brand-absent. Os 95% brand-present ainda contêm
  falso positivo de "Aramis errado" (modelo errado) e de seller que escreve "aramis"
  enganosamente. Isso fica para o Todo `reforcar-discriminacao-modelo`.
- `known_brands_for_detection` hoje = {aramis, reserva, tommy}. O gate só dispara se a query
  contém uma dessas. Para Aramis (caso principal) funciona; ampliar a lista se necessário.
- O gate deve ser aplicado como **filtro pós-score** (ou condicionar o resgate visual à presença
  de marca), não como mais um multiplicador — senão o gate visual continua anulando.

**Recomendação para o build:** implementar o gate de marca como filtro rígido **independente**
do score visual (ou tornar o resgate visual `if img>=85 and text>=40` **condicional à presença
da marca quando a query especifica marca conhecida**). É a correção de maior alavancagem para o
falso positivo "marca errada".
