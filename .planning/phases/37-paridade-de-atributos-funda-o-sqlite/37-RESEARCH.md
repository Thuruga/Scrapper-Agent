# Phase 37: Paridade de Atributos & Fundaçao SQLite - Research

**Researched:** 2026-07-03  
**Domain:** canonical product contract, engine attribute parity, Excel export normalization  
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 [canonical export contract]:** The required canonical fields are `brand`, `url`, `price_full`, `price_discount`, `product_name`, `product_description`, `composition`, `available_colors`, `available_sizes`, `product_code`, `category`, `rating`, and `review_count`.
- **D-02 [minimum success bar]:** Phase success is parity of those fields across engines and fixed Excel columns, not a broader schema rewrite.
- **D-03 [product_code semantics]:** `product_code` is the commercial code visible on PDP/listing. If the source does not expose one clearly, it must stay `null`.
- **D-04 [missing source data]:** Missing required fields must not invalidate a product; blanks/`null` are acceptable when the source does not expose the value.
- **D-05 [Excel is the main surface]:** Export must use the canonical English contract with fixed columns and blanks for missing data.
- **D-06 [scope boundary]:** Keep the system behavior otherwise unchanged. No UX expansion, no new operator flows, no new reporting feature.
- **D-07 [compatibility]:** Standardization must be additive and backward-compatible with the current code paths.
- **D-08 [SQLite removed]:** SQLite, analytics persistence, and `analytics.db` are explicitly out of scope for this phase and out of the project.
- **D-09 [coverage report removed]:** No coverage report endpoint/log/export belongs to this phase.
- **D-10 [mapping freedom]:** Canonical names may be guaranteed in shared helpers and export boundaries so long as the final extraction/export contract is uniform.

### Codex's Discretion

- Exact module name and seam for the shared canonicalization helper.
- Whether each engine writes canonical fields directly or contributes raw/source data that a shared projector normalizes before export.
- How to split the execution across rich engines (VTEX/Shopify) and sparse ones (Wake/SFCC/Zara/marketplaces), as long as the exported shape is uniform.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Planning interpretation |
|----|-------------|-------------------------|
| PARID-01 | Unique canonical product vocabulary across brands/engines | Centralize one canonical export contract and one alias map shared by all export paths. |
| PARID-02 | Engines populate the canonical field set for deficient brands | Fill or derive the canonical fields where the source exposes them, with `null` allowed when absent. |
| PARID-03 | Divergent source names are normalized additively | Preserve raw/source bags and add canonical keys via helper logic or additive engine fields. |
| PARID-04 | Legacy milestone wording mentions a coverage report | Reinterpreted by `37-CONTEXT.md`: phase ends at canonical export parity; no new report is planned. |
</phase_requirements>

## Summary

The current code already has most of the raw ingredients for Phase 37, but the contract is split across three layers: `RawProductBronze` uses `raw_title`/`raw_description`, the search UI uses `SearchProductResult.product_name`, and the Excel exporters flatten `specifications` opportunistically with no fixed canonical column order. The highest-leverage seam is a shared backend helper that projects a product into a fixed canonical export row while preserving the existing model contracts and raw bags.

VTEX is the richest reference implementation today: it already extracts `composition`, colors, sizes, category, ratings, and a populated `specifications` bag. Shopify is partially rich, Wake exposes core commerce fields plus shipping identifiers but very little attribute detail, SFCC and Zara currently return mostly title/price/image with sparse attributes, and the marketplace engines largely stop at search-card data. That means Phase 37 should not try to force identical extraction depth everywhere; instead it should enforce identical field names and blanks semantics everywhere.

The main regression risk is duplicated export logic. `backend/api/routes_search.py`, `backend/services/orchestrator.py`, and `backend/services/orchestrator_multi.py` each build Excel rows independently and each expands `specifications` ad hoc. If we only fix one path, the user will still see column drift depending on which export surface they use. A shared canonical export helper must therefore be consumed by all three export routes.

**Primary recommendation:** implement Phase 37 around a new shared module such as `backend/services/product_contract.py` that owns:

- ordered canonical export columns
- additive alias normalization for `specifications`
- fallback projection from `raw_title`/`raw_description` to `product_name`/`product_description`
- safe `product_code` extraction rules
- one row-builder used by every Excel/export path

## Architecture Findings

### Current Strong Seams

- `backend/core/models.py`
  - `RawProductBronze` already carries `composition`, `available_colors`, `available_sizes`, `category`, `rating`, `review_count`, and a raw `specifications` bag.
  - `SearchProductResult` already uses `product_name`, which is a useful downstream canonical label.
- `backend/services/engines/base_engine.py`
  - `validate_single` / `validate_and_filter` provide one shared point to keep additive fields backward-compatible.
- `backend/api/routes_search.py`
  - the comparative export already gathers full PDP product dicts and is the most direct Excel seam.
- `backend/services/orchestrator.py` and `backend/services/orchestrator_multi.py`
  - both already normalize list fields and expand `specifications`, making them natural adopters of a shared export projection.

### Current Gaps

- No shared canonical column order exists.
- No shared alias map exists for `specifications`.
- No product model field currently captures `product_code`.
- Engine richness is uneven:
  - VTEX: strong
  - Shopify: medium
  - Wake: low on attributes
  - SFCC/Zara: sparse
  - Amazon/Mercado Livre/Netshoes: sparse and search-oriented

## Recommended Shape

### Canonical Contract Helper

Create a small backend module, for example:

```text
backend/services/product_contract.py
  - CANONICAL_PRODUCT_COLUMNS
  - CANONICAL_SPEC_ALIASES
  - normalize_specifications_aliases(specs)
  - build_canonical_product_row(product_like)
  - canonical_export_dataframe(products)
```

This lets the phase standardize the final contract without forcing a disruptive rename of `RawProductBronze.raw_title` or `raw_description`.

### Additive Model Adjustment

Add `product_code: Optional[str] = None` to `RawProductBronze`. This is the one canonical field that does not already have a dedicated typed home in the bronze model.

### Engine Strategy

- Rich engines should populate typed fields first, then additive canonical aliases into `specifications` when the source names differ.
- Sparse engines should remain valid with blanks, but should still emit the canonical keys where extraction is possible without inventing data.
- Marketplace engines should not fake `product_code`, `composition`, or `category`.

### Export Strategy

All Excel-producing paths should call the same shared projector and the same fixed canonical column list. Any extra raw/spec columns can be appended after the canonical block, but the first contract columns must be stable.

## Common Pitfalls

### Pitfall 1: Breaking `price_discount` Semantics

`price_discount` in this codebase is already a discount delta, not the final discounted selling price. Phase 37 must preserve that semantic everywhere instead of reinterpreting it during export.

### Pitfall 2: Faking `product_code`

Using internal IDs such as marketplace item IDs, Wake shipping IDs, or VTEX SKU IDs as `product_code` would violate the user's decision. Only visible commercial codes should populate this field.

### Pitfall 3: Solving Only One Export Surface

If only `routes_search.py` is normalized, category-scan Excel outputs will still drift. All three exporters need the same helper.

### Pitfall 4: Overwriting Raw `specifications`

Alias normalization must be additive. Raw source keys like `Cor2`, `Corte`, or `Composição do produto` still need to survive for debugging and future phases.

### Pitfall 5: Forcing Canonical Fields Into Search UI Before They Are Needed

The user did not ask for UI changes. The safest plan is to normalize the contract for engine payloads and exports first, then keep UI exposure unchanged unless an existing path already serializes the field.

## Validation Architecture

| Requirement | Quick automated proof | Notes |
|-------------|-----------------------|-------|
| PARID-01 | `python -m pytest backend/tests/test_product_contract.py -q` | Locks canonical column order, fallback projection, and alias normalization. |
| PARID-02 | `python -m pytest backend/tests/test_phase37_engine_contract.py -q` | Uses engine/parser characterization fixtures to prove field parity behavior. |
| PARID-03 | `python -m pytest backend/tests/test_product_contract.py::test_aliases_are_additive -q` | Ensures canonical aliases are added without deleting raw keys. |
| PARID-01/PARID-02 export surface | `python -m pytest backend/tests/test_export_search_contract.py -q` | Proves comparative export and category exports use the same canonical leading columns. |

## Recommended Plan Split

### Plan 37-01

Shared canonical contract and Wave-0 tests.

### Plan 37-02

Engine- and parser-level parity work, prioritizing the brands explicitly called out in context/roadmap.

### Plan 37-03

Unify Excel/export behavior across comparative search and category scan orchestrators.

## Environment Availability

| Dependency | Available | Notes |
|------------|-----------|-------|
| Python | yes | Use `python -m pytest` because the bare `pytest` entry point may not be on PATH. |
| pytest | yes | Existing backend suite is active in `backend/tests`. |
| pandas/openpyxl | yes | Already used by all current Excel export paths. |
| Playwright | yes | Not required for Phase 37's core work unless live engine verification is added later. |

## Open Questions (Resolved for Planning)

1. **Should Phase 37 still build SQLite foundations?**  
   No. `37-CONTEXT.md` explicitly removes SQLite from this phase and from the project.

2. **Does PARID-04 still require a coverage report?**  
   No. The executable interpretation is contract parity and fixed Excel output only.

3. **Do canonical names need to replace internal model names?**  
   No. Planning assumes canonical names can live in shared helpers/export boundaries so long as the user-facing output contract is uniform.

## Metadata

**Confidence breakdown:**

- code seams: HIGH
- export-path understanding: HIGH
- engine richness/parity estimate: MEDIUM-HIGH
- risk of hidden dependency outside inspected files: MEDIUM

**Valid until:** 2026-07-10 unless major export or engine refactors land first.
