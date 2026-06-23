---
status: resolved
trigger: "netshoes ainda nao esta trazendo o produto que esta no site"
created: 2026-06-11
updated: 2026-06-11
---

# Debug Session: netshoes-produto-errado

## Symptoms
- expected: Produto exato "Camiseta Manga Curta New Basic Navy"
- actual: Apenas o produto "Camiseta Aramis Manga Curta Algodão Peruano" com Match de 94.1% aparece no card da Netshoes

## Investigations
1. Identificado que a busca Cross-Marketplace estava encontrando apenas o produto "Algodão Peruano".
2. O problema estava na formação da query em `api/routes_search.py`. A lógica de dedup da categoria não verificava corretamente strings multi-word.
3. Se o produto alvo for "Camiseta Manga Curta New Basic Navy", com categoria "Camiseta Manga Curta", a verificação `mapped_cat.lower() not in [t.lower() for t in tokens]` resultava em `True`.
4. Isso gerava uma `broad_q` duplicando a categoria: `"Camiseta Manga Curta Camiseta Manga Curta New Aramis"`.
5. Uma consulta tão restrita fazia com que o sistema de busca da Netshoes ocultasse o produto original e passasse a sugerir outros itens que correspondiam parcialmente via algoritmo de relevância, incluindo o modelo "Algodão Peruano", que era então baixado.
6. A similaridade de imagem entre as duas camisetas passava pela validação de Visão Computacional (95.6%), resultando em um final de 95.6% pro Algodão Peruano, preenchendo a vaga e exibindo o produto errado na UI.

## Resolution
Modificada a verificação da query `broad_q` no arquivo `api/routes_search.py` (linha 355-360) para checar a string usando `mapped_cat.lower() not in strict_q.lower()`.
Isso gera corretamente a query "Camiseta Manga Curta New Aramis", resultando na listagem correta pela Netshoes, na detecção e aprovação do item correspondente exato "Camiseta Aramis Manga Curta New Basic Navy" com match > 97%.
