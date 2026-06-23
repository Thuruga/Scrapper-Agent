# Melhorar UI do Monitoramento

**Descrição:** 
O modal de Produtos em Monitoramento está exibindo apenas "R$" e nenhum nome, pois no frontend as chaves acessadas foram `p.name` e `p.price`, enquanto o modelo retornado pela API `RawProductBronze` utiliza `p.raw_title`, `p.price_full` e `p.price_discount`. 
O objetivo é arrumar esses mapeamentos e melhorar a UI para mostrar também se o produto está com desconto (destacando o preço antigo vs o novo).

**Passos:**
1. Modificar `App.tsx` na renderização do `monitorProducts`.
2. Trocar `p.name` por `p.raw_title`.
3. Adicionar lógica visual para quando há `p.price_discount` (exibir de R$ XX por R$ YY).
4. Usar `p.price_full` como preço atual ou usar `price_full - price_discount` se tiver desconto.
5. Melhorar o design do card do produto no modal.
