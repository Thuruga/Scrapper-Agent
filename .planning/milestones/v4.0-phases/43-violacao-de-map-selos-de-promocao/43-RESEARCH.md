# Phase 43: Violacao de MAP & Selos de Promocao - Research

**Researched:** 2026-07-04  
**Domain:** FastAPI/Pydantic search contracts, JSON-backed operator rules, promotion normalization, marketplace seller attribution, React settings/result surfaces  
**Confidence:** MEDIUM-HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

Fonte desta secao: distilled from `.planning/phases/43-violacao-de-map-selos-de-promocao/43-CONTEXT.md`.

### Locked Decisions

- D-01..D-04: MAP rules are JSON-backed in `backend/data/map_rules.json`, atomic-write only, with precedence `product > category > brand`.
- D-05..D-07: MAP violation is decided from the effective advertised product price only; `shipping_price` and `landed_price` are display context, not verdict inputs.
- D-08..D-10: marketplaces should prefer real seller extraction; first-party brand sites use the brand/storefront as the infractor fallback.
- D-11..D-15: `promotions` is additive, defaults to `[]`, preserves `raw_text`, and minimally supports `pix_discount`, `percentage_discount`, `bundle`, `installments`, `generic_badge`.
- D-16..D-20: phase should ship endpoint + minimal UI, reuse existing result cards/settings surfaces, and remain backward-compatible with search/history/export.

### Deferred Ideas

- No analytics/history dashboard for MAP over time.
- No verdict based on landed price.
- No requirement to perfectly normalize every promotion variant from every engine before shipping.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MAP-01 | Operator defines MAP by product/brand/category; results flag items below MAP and identify infractor. | Existing code already resolves effective product price, seller, brand metadata, and has JSON-backed operator settings patterns. |
| PROMO-01 | Extract structured offer/payment badges while preserving raw text when parse fails. | Current product/result contracts are additive and can accept a compact `promotions` list with defaults. |
</phase_requirements>

## Summary

Phase 43 should be planned as a **shared backend-domain phase plus a thin UI/operator phase**, not as a giant engine rewrite. The existing code already has the two key building blocks the feature needs:

1. **Price semantics are already explicit.** `resolve_effective_price` / `resolve_original_price` in `backend/core/models.py` distinguish effective sale price from full/risked price, which directly supports the locked MAP comparison rule.
2. **Operator configuration already uses JSON local persistence cleanly.** `backend/services/brand_service.py` provides the house pattern for validate-on-read plus atomic write/replace.

The main architectural wrinkle is that the project has **two result shapes**, not one:

- Brand search flows return `SearchProductResult` via `engine_factory.search_all_brands(...)`.
- Cross-marketplace flows return custom dict rows assembled by `cross_marketplace_service.py`.

That means MAP/promotion surfacing cannot be solved only by extending `SearchProductResult`; the planner must wire the same semantics into the cross-marketplace result builder and export path as well.

Promotion extraction is currently the least standardized area. The codebase has no shared `promotions` abstraction yet, and engine coverage is uneven. The safest path is to build a **pure parser/normalizer module first** and then feed it raw promotion hints from whichever engines already expose cheap source text. When normalization fails, `generic_badge + raw_text` still satisfies PROMO-01 without blocking the whole phase.

**Primary recommendation:** split Phase 43 into four waves:

1. backend contracts + pure services,
2. MAP rules CRUD API,
3. search/export/promotion wiring across result flows,
4. frontend rule-management and result badges.

## Project Constraints (from CLAUDE.md)

- Backstage coding-standards MCP should be consulted before code edits; that MCP tool is not available in this session, so planning should note `Backstage standards MCP unavailable; continue with in-repo patterns`.
- Never commit Backstage PAT or `.mcp.json` credentials.
- Use Conventional Commits with scope when clear.
- PR flow only; never commit directly to `main`.
- Favor Clean Code / refactoring.guru principles without over-engineering.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| MAP rule persistence and precedence | API / Backend | Local JSON storage | Rules are operator-defined configuration and already fit the project's JSON-backed service pattern. |
| MAP verdict computation | API / Backend | Shared pure service | Effective price, seller, and rule precedence are backend facts and should be deterministic before UI rendering/export. |
| Promotion normalization | API / Backend | Engine parsers / PDP enrichment | Regex/type inference should be centralized; engine-specific code should only supply raw hints when needed. |
| Result badges and rule management UI | Browser / Client | API / Backend | Frontend should remain a thin consumer of typed backend data and CRUD endpoints. |
| Export compatibility | API / Backend | Spreadsheet contract | Excel generation is owned by `routes_search.py` + `product_contract.py`; additive changes must remain there. |

## Standard Stack

| Library | Purpose | Why Standard |
|---------|---------|--------------|
| FastAPI | CRUD routes for MAP rules and search response transport | Existing API layer already uses FastAPI routers with API-key protection. |
| Pydantic v2 | Additive rule/promotion/violation models | Existing `core/models.py` is already the canonical contract seam. |
| Python stdlib `json` + `Path` | JSON-backed MAP rule persistence | Existing services use local JSON stores and atomic replace. |
| React + Vite | Minimal operator management and result badges | Existing frontend already has `SettingsPage`, modals, and result-card badge patterns. |

## Package Legitimacy Audit

No new package installs are recommended for Phase 43. The phase can be implemented with the existing FastAPI/Pydantic/React stack and local JSON persistence patterns.

## Architecture Patterns

### System Architecture Diagram

```text
Operator -> MAP rules UI / API
  -> routes_map_rules.py
  -> map_rules_service.py
  -> backend/data/map_rules.json

Search or cross-marketplace result
  -> engine/search result + optional enrichment
  -> map_evaluator_service.py resolves effective price + applicable rule + infractor
  -> promotion_parser.py normalizes raw badge/payment strings
  -> response payload gains promotions[] + map metadata
  -> frontend renders badges / export writes additive columns or serialized text
```

### Recommended Project Structure

```text
backend/
├── api/
│   ├── routes_map_rules.py
│   └── routes_search.py                # response/export wiring
├── core/models.py                      # additive models/fields
├── services/
│   ├── map_rules_service.py            # JSON CRUD + precedence helpers
│   ├── map_evaluator_service.py        # effective price + applicable rule + violation
│   └── promotion_parser.py             # pure normalization of raw promotion hints
└── tests/
    ├── test_map_rules_service.py
    ├── test_map_rules_routes.py
    ├── test_map_evaluator_service.py
    └── test_phase43_search_contract.py

frontend/
├── src/api/client.ts                   # typed MAP rules client
└── src/App.tsx                         # settings panel + result badges
```

### Pattern 1: Atomic JSON Config Service

**What:** Persist operator-editable JSON using load/validate + temp-file replace.  
**Analog:** `backend/services/brand_service.py`

**Use for:** `map_rules_service.py`

### Pattern 2: Pure Extraction/Normalization Module

**What:** Keep text parsing separate from I/O and UI.  
**Analog:** `backend/services/engines/seller_extraction.py`

**Use for:** `promotion_parser.py`

### Pattern 3: Pure Verdict Service Over Existing Contracts

**What:** Accept product-like dict/model, resolve effective price, apply deterministic rules, return additive metadata.  
**Analog:** `backend/services/stock_summary_service.py` and `backend/services/shipping/base.py`

**Use for:** `map_evaluator_service.py`

### Pattern 4: Incremental Settings Surface

**What:** Extend `SettingsPage` with another management card/modal instead of building a new screen.  
**Analog:** brand management in `frontend/src/App.tsx`

**Use for:** MAP rules CRUD UI.

## Risks and Open Questions for Planning

### Confirmed Risks

- **Dual result contracts:** `SearchProductResult` and cross-marketplace dict rows must both be updated.
- **Promotion hint availability varies by engine:** some engines expose enough text cheaply; others may only support `raw_text` fallbacks at first.
- **Seller semantics differ:** marketplaces may have a real seller, a marketplace default seller, or only brand/storefront identity.

### Planning Recommendations

- Treat `promotions` normalization as **best-effort but never empty by omission when raw text exists**.
- Keep MAP rules API independent of search flows so the operator UI can be built and tested in isolation.
- Reuse `resolve_effective_price` rather than duplicating price math in routes or the frontend.
- Prefer a small number of additive top-level response fields for MAP (`map_violation`, `map_price_floor`, `map_rule_scope`, `map_infractor`) over deeply nested opaque blobs.

## Recommended Wave Split

| Plan | Focus | Output |
|------|-------|--------|
| 43-01 | Contracts + pure backend services | New models/fields, JSON rule service, pure evaluator/parser |
| 43-02 | MAP rules API | CRUD routes, router registration, route tests |
| 43-03 | Search/export/promotion backend wiring | Search/cross/export MAP metadata and promotions flow |
| 43-04 | Frontend operator/result surfaces | Settings UI, result badges, typed client, build verification |

## No-Browse Note

This research was grounded in the local repository and current workspace state. No external dependency/package/library decision required web research for this phase.
