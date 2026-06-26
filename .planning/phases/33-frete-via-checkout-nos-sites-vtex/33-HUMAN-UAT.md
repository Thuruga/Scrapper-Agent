---
status: partial
phase: 33-frete-via-checkout-nos-sites-vtex
source: [33-VERIFICATION.md]
started: 2026-06-26T00:00:00Z
updated: 2026-06-26T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. CEP padrão carrega no load e reseta no reload
expected: Campo "CEP de entrega" exibe o CEP padrão do backend (ex: "01310-100") ao abrir a página; ao recarregar, o campo reseta para o padrão (não para o último valor editado)
result: [pending]

### 2. CEP inválido (1-7 dígitos) bloqueia Comparar e Excel
expected: Digitar 3 dígitos e clicar em "Comparar" ou "Exportar Excel": botão não dispara a busca, foco vai para o campo CEP, inline error "Informe um CEP válido com 8 dígitos." aparece com ícone AlertTriangle
result: [pending]

### 3. Config com delay não sobrescreve CEP editado pelo usuário
expected: Editar o CEP antes da resposta do /search/config chegar (simular com network throttle ou DevTools): o valor digitado pelo usuário deve permanecer, sem overwrite silencioso
result: [pending]

### 4. Busca VTEX retorna opções de frete com preços em reais
expected: Buscar SKU de marca VTEX ativa (ex: Levi's, Calvin Klein) com CEP válido: cada card exibe seção "Entrega para {CEP}" com ≥1 opção de entrega, preço em "R$ X,XX"
result: [pending]

### 5. Frete grátis exibe "Frete Grátis" em verde (não "R$ 0,00")
expected: Para SKU com opção de frete grátis: linha exibe ícone CheckCircle2 + texto "Frete Grátis" em --success (verde), sem exibir "R$ 0,00"
result: [pending]

### 6. CEP sem cobertura exibe "Entrega indisponível" em cor muted (não vermelho)
expected: Buscar com CEP de área sem cobertura VTEX: exibe "Entrega indisponível para este CEP" com ícone MapPin em cor --text-muted (cinza), card permanece utilizável
result: [pending]

### 7. Falha temporária de frete exibe aviso âmbar; outros produtos não são afetados
expected: Simular timeout/erro no checkout de um SKU: card do produto afetado exibe "Frete temporariamente indisponível" com AlertTriangle âmbar; outros produtos na mesma busca exibem opções normalmente
result: [pending]

### 8. Histórico pré-Phase-33 renderiza via fallback legado sem crash
expected: Abrir aba "Histórico" e visualizar registros de buscas anteriores à Phase 33 (sem campo shipping_options): registros renderizam sem crash, exibindo o campo legacy shipping se disponível
result: [pending]

## Summary

total: 8
passed: 0
issues: 0
pending: 8
skipped: 0
blocked: 0

## Gaps
