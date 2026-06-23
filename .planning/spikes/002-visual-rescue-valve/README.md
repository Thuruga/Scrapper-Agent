---
spike: 002
name: visual-rescue-valve
type: standard
validates: "Given os itens que o gate rígido derrubaria, when adiciono uma válvula de resgate por image_match_score >= T, then meço quantos legítimos recupero sem readmitir ruído de marca errada"
verdict: INVALIDATED
related: [001]
tags: [search, relevance, vision]
---

# Spike 002: Válvula de Resgate Visual

## What This Validates
**Given** os itens brand-absent que o gate rígido de marca derrubaria, **when** adiciono uma
válvula que os resgata se `image_match_score >= T`, **then** medir quantos legítimos (Aramis com
marca omitida) recupero **sem** readmitir ruído de concorrente parecido.

## Research
Reutiliza os scores CLIP reais armazenados e o `nlp_service`. Offline e determinístico.
Construído logo após o Spike 001, que já sugeria que visual alto em item brand-absent =
concorrente parecido, não Aramis legítimo.

## How to Run
```bash
python .planning/spikes/002-visual-rescue-valve/experiment.py
```

## What to Expect
Varredura de thresholds T ∈ {80, 85, 90, 95} sobre os 78 itens brand-absent, contando
resgatados e a fração que nomeia concorrente explícito.

## Investigation Trail

### Iteração 1 — varredura de threshold
| T (img>=) | resgatados | nomeiam concorrente | % ruído explícito |
|---|---|---|---|
| 80 | 17 | 10 | **59%** |
| 85 | 1 | 1 | **100%** |
| 90 | 0 | 0 | — |
| 95 | 0 | 0 | — |

Não existe threshold que recupere legítimos sem readmitir ruído:
- **T baixo (80):** resgata 17 itens, dos quais **59% nomeiam um concorrente explícito**
  (ex: Hering). Os ~41% restantes são genéricos/sem-marca e não-verificáveis — e o Spike 001
  mostrou que "genérico de visual alto" tende a ser look-alike (ex: tênis Sanders, img 88), não
  Aramis. Ou seja, o resgate é majoritariamente ruído.
- **T alto (85+):** o único item resgatado é, ele próprio, um concorrente. A partir de 90,
  **nenhum** item brand-absent atinge o corte → a válvula não recupera nada útil.

## Results

**Verdict: INVALIDATED** — a válvula de resgate visual é uma armadilha. Não há ponto de operação
útil: ou ela readmite concorrentes (T baixo), ou não resgata nada (T alto).

**Por quê (a lição):** o `image_match_score` mede *parecença*, não *identidade de marca*. Dois
piquet polos parecem iguais para o CLIP independentemente da etiqueta. A marca é justamente o
sinal que distingue "mesmo produto" de "produto parecido" — e a válvula descarta esse sinal.
Tentar reconstruir identidade a partir de aparência é circular.

**Consequência para o build:**
- **Não** suavizar o gate rígido de marca (do Spike 001) com resgate visual. Confirma o
  requirement: o gate de marca deve ser independente e o resgate visual
  `if img>=85 and text>=40` deve ser **condicionado à presença de marca** quando a query
  especifica marca conhecida.
- O caminho para recuperar cobertura de Aramis-com-marca-omitida **não** é visual — teria de ser
  um sinal de identidade real (ID de catálogo do marketplace, seller oficial), que é a
  [research question](../../research/questions.md) em aberto.
