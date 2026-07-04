---
phase: 43-violacao-de-map-selos-de-promocao
plan: 01
subsystem: backend-contract
tags: [pydantic, pytest, json, map, promotions]
requirements-completed: [MAP-01, PROMO-01]
completed: 2026-07-04
---

# Phase 43 Plan 01 Summary

Shared backend foundations for MAP and promotions were implemented.

## Accomplishments

- Added additive `PromotionInfo` and `MapRule` contracts plus MAP/promotion fields on product models.
- Created `map_rules_service.py` with atomic JSON persistence and product > category > brand precedence.
- Created `map_evaluator_service.py` for effective-price MAP verdicts and infractor fallback semantics.
- Created `promotion_parser.py` for pix, percentage, bundle, installments, generic badge, and discount-derived promotion helpers.
- Added unit coverage for backward compatibility, rule CRUD helpers, precedence, URL matching, MAP price basis, seller default semantics, and promotion parsing.

## Verification

- `cd backend && python -m pytest tests/test_map_rules_service.py tests/test_map_evaluator_service.py -x -q` -> 14 passed

## Deviations

- Execution was inline rather than delegated to subagents because this Codex thread's subagent policy only permits spawning when the user explicitly asks for delegation.
