---
status: complete
phase: 26-onboarding-das-5-marcas-vtex
source: [26-01-SUMMARY.md, 26-02-SUMMARY.md]
started: 2026-06-19T18:46:42Z
updated: 2026-06-19T18:46:42Z
---

## Current Test

[testing complete]

## Tests

### 1. Onboarding das 5 marcas VTEX com engine reconfirmada
expected: Rodar o script cadastra as 5 marcas com engine='vtex' reconfirmada por detect_engine, todas ativas; Austral resolvida (nunca 'unknown').
result: pass
observed: levis/calvinklein/zapalla/austral/trackfield -> engine=vtex (4 corrigidas de 'auto'->'vtex'), is_active=True. Austral resolveu direto em www.austral.com.br.

### 2. Busca ao vivo retorna produtos por marca
expected: Uma busca retorna produtos reais para cada uma das 5 marcas ([SMOKE] {marca}: >=1 produtos).
result: pass
observed: [SMOKE] levis 3, calvinklein 2, zapalla 3, austral 3, trackfield 3 (todas >=1).

### 3. De/para de categorias — somente masculino
expected: Cada marca tem mapeamento de slugs canonicos para caminhos VTEX relativos, SOMENTE masculino (sem feminino), infantil apenas da linha do menino; resolve_category_for_brands gera URLs validas.
result: pass
observed: 32 mappings persistidos (levis 7, CK 7, zapalla 7, austral 5, trackfield 6), 0 femininos/inativos; resolve_category_for_brands gera URLs validas. Omissoes corretas: trackfield sem 'camisas', austral sem 'polos'/'infantil'.

### 4. Idempotencia da re-execucao
expected: Re-rodar o script nao duplica marcas e pede confirmacao antes de sobrescrever mappings existentes (D-06).
result: pass
observed: Re-execucao manteve 13 marcas (sem duplicacao), disparou "mappings ja existem -> Sobrescrever?" nas 5 e preservou os mappings ao recusar.

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
