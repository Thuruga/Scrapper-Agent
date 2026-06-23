---
status: resolved
phase: 26-onboarding-das-5-marcas-vtex
source: [26-VERIFICATION.md]
started: 2026-06-19T14:12:47Z
updated: 2026-06-19T18:46:42Z
---

## Current Test

[complete]

## Tests

### 1. Live onboarding run of the 5 VTEX brands
expected: |
  Run `python scripts/onboard_vtex_brands.py` once with network access.
  Each of the 5 brands (levis, calvinklein, zapalla, austral, trackfield) prints
  engine=vtex after detect_engine reconfirmation. The de/para (auto-match) review
  prompt appears per brand and persists mappings only after operator confirmation.
  `[SMOKE] {brand}: >=1 produtos` for all 5 (Austral resolves via a www/no-www/secure
  variant — never left "unknown"). Re-run shows no duplication and the
  mappings-already-exist prompt (D-06 idempotency).
result: passed — Executado ao vivo em 2026-06-19.
  - engine: as 5 marcas reconfirmadas como engine=vtex via detect_engine
    (calvinklein/zapalla/austral/trackfield corrigidas de 'auto'->'vtex'; levis ja vtex).
    Austral resolveu direto em www.austral.com.br (sem precisar de variante).
  - is_active=True nas 5; persistido via dev brands.json (D-08).
  - busca ao vivo retornou produtos para todas: levis 3, calvinklein 2, zapalla 3,
    austral 3, trackfield 3 (criterio 1 / D-10a satisfeito, >=1 cada).
  - de/para revisado pelo operador e ajustado para a regra de negocio: SOMENTE
    categorias masculinas (nunca femininas) e infantil somente da linha do menino.
    32 mappings persistidos via update_mappings (levis 7, calvinklein 7, zapalla 7,
    austral 5, trackfield 6). Omissoes corretas: trackfield sem 'camisas' (marca
    atletica), austral sem 'polos'/'infantil'.
  - auto_match endurecido (commit 8780b1e): genero-consciente + correcao do bug
    do token 'mini'; teste de regressao test_auto_match_masculine_only adicionado.

## Summary

total: 1
passed: 1
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
