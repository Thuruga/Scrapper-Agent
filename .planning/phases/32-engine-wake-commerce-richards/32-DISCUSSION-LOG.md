# Phase 32: Engine Wake Commerce — Richards - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-24
**Phase:** 32-Engine Wake Commerce — Richards
**Areas discussed:** Spike GO/NO-GO gate, Token config & failure, Engine scope (contract), GraphQL search shape

---

## Spike target store (Wave 0)

| Option | Description | Selected |
|--------|-------------|----------|
| Richards + Shop2gether fallback | Spike Richards first (real target); fall back to Shop2gether if Richards blocks the test. De-risks the gate against one store's quirks. | ✓ |
| Richards only | Test only against Richards. Cleanest signal, single point of failure for the gate. | |
| Shop2gether first | Prove the generic Wake flow on Shop2gether before touching Richards. | |

**User's choice:** Richards + Shop2gether fallback
**Notes:** SC-1 explicitly permits Richards OR Shop2gether — both are Wake stores. → D-01.

---

## Token acquisition strategy (runtime + spike)

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-extract + manual override | Auto-discover the public storefront token per store (zero-config); manual override when the site changes. Per-store by construction (SC-4). | ✓ |
| Operator configures explicitly | Operator finds and supplies the per-store token; engine just sends it. More friction. | |
| Auto-extract only | Discover token from storefront, no manual path. Brittle if Wake hides/rotates the token. | |

**User's choice:** Auto-extract + manual override
**Notes:** TCS-Access-Token is the public storefront token (shipped in page JS). → D-05.

---

## GO threshold (spike validated)

| Option | Description | Selected |
|--------|-------------|----------|
| ≥1 product w/ title+url+price | Minimal end-to-end proof via GraphQL+token. Gate, not a load test. | ✓ |
| ≥5 products for a real query | Stronger signal that term-search returns a usable set. | |
| You decide | Planner/spike sets a sensible bar. | |

**User's choice:** ≥1 product with title+url+price → D-02

---

## NO-GO behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Stop at gate, defer engine | Document NO-GO; defer WakeEngine to a follow-up phase. Gate by design. | ✓ |
| Escalate to me first | Surface evidence; user decides. | |
| Build engine anyway (flagged) | Proceed degraded despite NO-GO. Not recommended. | |

**User's choice:** Stop at gate, defer engine → D-03

---

## Manual override token storage

| Option | Description | Selected |
|--------|-------------|----------|
| Optional brand field in brands.json | Add e.g. `wake_access_token` alongside `vtex_account`/`review_store_id`. Public storefront token → committing an override is acceptable; usually empty (auto-extract resolves). | ✓ |
| Env var per brand | e.g. `WAKE_TOKEN_RICHARDS`; treats token as secret, more friction. | |
| You decide | Planner picks, respecting SC-4. | |

**User's choice:** Optional brand field in brands.json → D-06
**Notes:** brands.json is git-tracked; acceptable because the token is the public storefront token.

---

## Token failure surfacing

| Option | Description | Selected |
|--------|-------------|----------|
| At search time as BrandSearchResult.error | Captured by factory `_search_one` try/except; mirrors SFCC; onboarding decoupled. | ✓ |
| Block at onboarding | `create_brand` refuses a `wake` brand whose token can't be resolved. | |
| Both: warn early, hard-fail at search | Most informative; code in two places. | |

**User's choice:** At search time as BrandSearchResult.error → D-07
**Notes:** SC-4 — must not be silent 0 products.

---

## Engine contract scope

| Option | Description | Selected |
|--------|-------------|----------|
| Search-only + graceful stubs | Real search (catálogo+preço); discover_categories/get_catalog → []; calculate_shipping → None. Mirrors SFCC D-04/D-06/D-09; matches ROADMAP SC. | ✓ |
| Also real category monitoring | Implement real category discovery (SFCC D-05). Expands beyond SC-2/SC-3. | |
| Search-only now, categories gated | Attempt categories, fall back to stub (SFCC D-05/D-06 pattern). | |

**User's choice:** Search-only + graceful stubs → D-08

---

## GraphQL search shape

| Option | Description | Selected |
|--------|-------------|----------|
| Single GraphQL search query | One storefront search/productList query returns title+url+price — no per-product enrichment (unlike SFCC PDP). | ✓ |
| Search + detail-query fallback | Per-product detail query when fields missing. More robust, extra requests. | |
| You decide from spike | Spike findings determine whether enrichment is needed. | |

**User's choice:** Single GraphQL search query → D-10
**Notes:** Final field/query shape confirmed by the Wave 0 spike.

---

## Claude's Discretion

- Spike threshold above the ≥1 minimum; exact token field name (`wake_access_token` suggested); class/constant/marker names per repo conventions.
- Price unit/format from Wake's GraphQL (numeric via API; confirm in spike).
- Auto-extracted-token caching; concrete auto-extraction strategy (where the token appears in the page).
- Whether Richards is seeded into brands.json by the phase or onboarded via the UI by the operator.
- `only_in_stock` / `sort` / `max_results` handling (GraphQL-side vs client-side); exact `calculate_shipping` return shape.

## Deferred Ideas

- Wake category monitoring (real `discover_categories`/`get_catalog`) — follow-up (stubs this phase).
- Wake shipping/checkout — out of scope (`calculate_shipping` → None).
- Full WakeEngine if the spike returns NO-GO — deferred to a follow-up phase.
- Per-product detail-query enrichment — not used this phase (single-query, D-10).
- Reviewed-not-folded todo: *"Reforçar discriminação de modelo"* — about `nlp_service` SKU search, not the Wake engine (same call as Phases 30/31).
