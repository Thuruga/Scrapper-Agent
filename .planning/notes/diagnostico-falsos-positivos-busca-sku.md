---
title: Diagnóstico - Falsos positivos na busca por SKU (precisão do match)
date: 2026-06-13
context: Exploração sobre melhorar o sistema de busca (SKU + comparativa). Objetivo confirmado da busca = encontrar o MESMO produto Aramis revendido por terceiros (ML/Amazon/Netshoes) para comparação de preço/buybox. Concorrente de outra marca = falso positivo a eliminar.
---

# Diagnóstico: Falsos positivos na busca por SKU

## Objetivo da busca (confirmado nesta exploração)
A busca comparativa serve para encontrar o **mesmo produto Aramis** sendo revendido por
terceiros, para comparar preço/buybox. **Não** é benchmark de concorrentes — produto de
outra marca (Hering, Reserva) é lixo a ser eliminado, não alvo.

Prioridade declarada: **precisão > cobertura** ("mostrar menos, mas ter certeza").

## Dois tipos de falso positivo (ocorrem com frequência parecida)

### 1. Marca errada (tipo de peça certo, marca errada)
- **Causa-raiz:** [`_apply_brand_penalty`](../../services/nlp_service.py) é uma penalidade
  **suave e multiplicativa** — quando a query especifica marca conhecida e o título do
  marketplace não a contém, o score apenas é multiplicado por `0.50` (cortado pela metade).
- **Efeito:** um título de concorrente com similaridade textual ~95% sobrevive a ~47% —
  perto da régua de corte, às vezes passando.
- **Direção de correção:** transformar o desconto em **gate rígido configurável** — quando a
  query especifica marca conhecida, título sem a marca é **descartado**, não penalizado.
  (É a "Opção 2" pendente do [spike de EAN](spike-ean-sku-search.md).)

### 2. Aramis errado (marca certa, modelo/linha errada)
- **Causa-raiz A:** [`_apply_model_word_penalty`](../../services/nlp_service.py) existe, mas é
  multiplicativo e brando — não é decisivo o suficiente para separar duas polos Aramis
  diferentes.
- **Causa-raiz B (estrutural):** o sinal visual CLIP só roda nos **top-N candidatos já
  selecionados pelo texto** ([`cross_marketplace_service.py` top_candidates](../../services/cross_marketplace_service.py)).
  Se o texto já elegeu o modelo errado, o visual nem entra para corrigir — ele confirma, não
  reordena o conjunto.
- **Direção de correção:** model-words mais decisivas + promover o sinal visual como
  desempate de "mesmo produto" (e não só como filtro pós-texto).

## Trade-off central
Ambas as correções apertam a precisão à custa de **cobertura** (mais falsos negativos). O
spike de EAN já mostrou que cobertura nos marketplaces de moda é frágil. O quanto o gate
rígido custa em cobertura **só se sabe medindo em buscas reais** — daí o spike associado.

## Próximos passos derivados
- Spike: gate rígido de marca medindo impacto em cobertura em buscas reais. Ver
  [spike brief](spike-gate-rigido-marca-brief.md).
- Todo: reforçar discriminação de modelo (model-words + visual como desempate).
- Research: existe sinal de identidade de produto confiável além do EAN?
