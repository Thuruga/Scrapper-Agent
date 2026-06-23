---
status: passed
phase: 28-persist-ncia-da-busca-entre-abas
source: [28-VERIFICATION.md]
started: 2026-06-21
updated: 2026-06-22
---

## Current Test

[all tests passed — approved by user 2026-06-22]

## Tests

### 1. Critério #1 — Estado sobrevive à troca de aba (Comparativa)
expected: Iniciar busca Comparativa longa (muitas marcas); com spinner ativo, trocar para outra aba e voltar: spinner ainda ativo, query preenchida, selectedBrands preservados, busca NÃO reiniciada. Após conclusão: toast "Busca Comparativa concluída" + resultados visíveis.
result: passed

### 2. Critério #1 — Estado sobrevive à troca de aba (SKU)
expected: Iniciar busca por SKU; com spinner ativo, trocar de aba e voltar: targetSku preservado, loading ativo, busca NÃO reiniciada. Após conclusão: toast "Busca por SKU concluída" + resultados visíveis.
result: passed

### 3. Critério #2 — Toast de conclusão fora da aba
expected: Iniciar busca, navegar para outra aba antes de concluir. Toast de sucesso deve aparecer na aba atual (não na aba de busca). Ao voltar: resultados disponíveis.
result: passed

### 4. Critério #3 — Sem duplo-fetch + cancelamento correto
expected: DevTools › Network — iniciar busca, trocar aba, voltar → apenas 1 request POST /search. Cancelamento: iniciar busca A, antes de concluir iniciar busca B → request A = "Canceled", B prossegue, apenas toast de B aparece. Resultado exibido é de B, NÃO de A. (CR-01 corrigido em 9ff516e — este UAT confirma o comportamento em runtime.)
result: passed

### 5. Critério #4 — WS cleanup da CategoryPage
expected: DevTools › Console e Network › WS. Aba Categorias, iniciar varredura; com WS ativo, navegar para outra aba: nenhum log novo após a troca; Network › WS = "Closed".
result: passed

### 6. Regressão D-11 — preloadedJobId
expected: Reabrir busca salva do histórico (Comparativa e SKU): leva à aba correta, resultados reexibidos sem nova raspagem. Trocar de aba e voltar não recarrega histórico por cima de busca nova.
result: passed

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
