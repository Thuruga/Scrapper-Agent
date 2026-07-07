---
status: complete
phase: 33-frete-via-checkout-nos-sites-vtex
source: [33-VERIFICATION.md]
started: 2026-06-26T00:00:00Z
updated: 2026-06-26T00:00:00Z
---

## Current Test

[concluído — operador confirmou "Funcionando" em 2026-06-26]

## Nota de design (gap closure)

O UX original (CEP padrão visível + frete automático em toda busca) foi **revisado ao vivo**
após o UAT. Design final (commit 178126f):
- CEP é **opcional e sem valor padrão**.
- Com CEP preenchido **antes** da busca → frete de todos os produtos vem junto (inline).
- Sem CEP → busca traz só preços; cada produto VTEX tem botão **"Calcular Frete"** (cálculo
  de um único item) que abre um **modal de CEP** quando necessário.
- Detalhes do frete ficam **colapsados** (resumo + expandir/recolher todos / item a item).
- Busca por SKU segue a mesma lógica (botão + modal).
- Bug Foxton (e outras VTEX) corrigido: SLAs achatados de todas as entradas de `logisticsInfo`
  (CR-02) + `timeout` aiohttp corrigido (WR-01).

## Tests

### 1. Busca sem CEP exibe botão "Calcular Frete" por produto VTEX
expected: Sem CEP no campo, a busca traz só preços; cada produto VTEX mostra o botão "Calcular Frete"
result: passed

### 2. CEP preenchido antes da busca traz frete inline (colapsado)
expected: Com CEP válido no campo, a busca traz preços + frete de todos os produtos VTEX, colapsado
result: passed

### 3. Botão "Calcular Frete" sem CEP abre o modal e calcula um único produto
expected: Clicar em "Calcular Frete" sem CEP abre o modal; ao confirmar, calcula só aquele produto
result: passed

### 4. Produto VTEX (ex: Foxton) retorna opções reais de frete em reais
expected: Marcas VTEX trazem ≥1 modalidade de entrega com preço em reais (bug logisticsInfo[0] corrigido)
result: passed

### 5. Frete grátis exibido como "Frete Grátis" (verde), não "R$ 0,00"
expected: Opção gratuita mostra "Frete Grátis" em verde com CheckCircle2
result: passed

### 6. Colapsar/expandir frete (todos e item a item)
expected: Detalhes colapsados por padrão; "Expandir todos"/"Recolher todos" e chevron por card funcionam
result: passed

### 7. Estados sem entrega / falha temporária
expected: "Entrega indisponível para este CEP" (muted) e "Frete temporariamente indisponível" (âmbar, com "Tentar novamente")
result: passed

### 8. Busca por SKU segue a mesma lógica (botão + modal)
expected: "Calcular Frete" por item abre o modal de CEP quando não há CEP; calcula sob demanda
result: passed

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
