---
phase: quick-260615-dkc
plan: "01"
subsystem: seller-extraction
tags: [seller, marketplace, tdd, refactor, cross-marketplace]
dependency_graph:
  requires: []
  provides:
    - services/engines/seller_extraction.py (MARKETPLACE_DEFAULT_SELLER, ALL_DEFAULT_SELLERS, is_marketplace_default, parse_ml_seller_from_html, parse_amazon_seller_from_html)
  affects:
    - services/engines/mercado_livre_engine.py (get_product_details, _run_playwright_pdp)
    - services/engines/amazon_engine.py (get_product_details)
    - services/cross_marketplace_service.py (_enrich_pdp_and_shipping)
tech_stack:
  added:
    - services/engines/seller_extraction.py (BeautifulSoup + regex, no network I/O)
  patterns:
    - Pure-function extractor: HTML-in / Optional[str]-out, no side effects
    - Precedence guard: is_marketplace_default() prevents PDP default overwriting real listing seller
    - TDD RED/GREEN per task (test commit before impl commit)
key_files:
  created:
    - services/engines/seller_extraction.py
    - tests/test_seller_extraction.py
  modified:
    - services/engines/mercado_livre_engine.py
    - services/engines/amazon_engine.py
    - services/cross_marketplace_service.py
    - tests/test_cross_marketplace_service.py
decisions:
  - "LOCKED: marketplace name is the fallback when PDP exposes no third-party seller; no neutral label introduced"
  - "ALL_DEFAULT_SELLERS is a normalized set (NFD + ascii-ignore + lower) covering all known marketplace defaults, so a default from any marketplace cannot be mistaken for a real seller"
  - "Extractors return None (not the default string) — callers apply the fallback: parse_X_from_html(html) or MARKETPLACE_DEFAULT_SELLER[mp]"
  - "PDP exception log upgraded from logger.debug to logger.warning for operational visibility"
metrics:
  duration: "~25 minutes"
  completed: "2026-06-15"
  tasks_completed: 3
  files_changed: 6
---

# Quick Task 260615-dkc: Seller Extraction Robustness Summary

## One-liner

Pure `seller_extraction` module with multi-selector CSS+JSON-state extractors for ML/Amazon and a precedence guard that prevents PDP marketplace-defaults from overwriting real listing sellers.

## What Was Built

### Task 1 — New module `services/engines/seller_extraction.py` (TDD)

- `MARKETPLACE_DEFAULT_SELLER`: map `{marketplace_name -> default_seller_name}` for ML, Amazon, Netshoes.
- `ALL_DEFAULT_SELLERS`: normalized frozenset of all known defaults (NFD + ascii-ignore + lower), enabling cross-marketplace default detection.
- `is_marketplace_default(seller, marketplace=None) -> bool`: returns True for None, empty/whitespace, or any normalized string matching a known default. Used as the precedence predicate.
- `parse_ml_seller_from_html(html) -> Optional[str]`: tries 5 CSS selectors in order (`.ui-pdp-seller__link-trigger span`, `.ui-pdp-seller__link-trigger-button span`, `.ui-pdp-seller__header__title`, `.ui-pdp-action-modal__link span`, `a[href*="/loja/"]`) then falls back to JSON-state regex (`official_store_name`, `seller.nickname/name`, `store_name`). Strips prefixes "Vendido por"/"por"/"Loja oficial". Never returns a default-matching string.
- `parse_amazon_seller_from_html(html) -> Optional[str]`: tries `#sellerProfileTriggerId`, `#merchant-info a`, `#merchant-info` text, `#tabular-buybox` sibling, modern offer blocks. Strips prefixes. Never returns a default-matching string.
- 34 offline tests covering all extractors and `is_marketplace_default`.

### Task 2 — Wire extractors in ML and Amazon engines

- `mercado_livre_engine.py`: imported `parse_ml_seller_from_html` and `MARKETPLACE_DEFAULT_SELLER`. Replaced two duplicate inline selector blocks (in `get_product_details` and `_run_playwright_pdp`) with `parse_ml_seller_from_html(html) or MARKETPLACE_DEFAULT_SELLER["Mercado Livre"]`. Removed orphaned local imports (`from bs4 import BeautifulSoup`, `import re`) from `_run_playwright_pdp`. Playwright gate `"ui-pdp-seller" in response.text` preserved.
- `amazon_engine.py`: imported `parse_amazon_seller_from_html` and `MARKETPLACE_DEFAULT_SELLER`. Replaced inline selector block in `get_product_details` with `parse_amazon_seller_from_html(response.text) or MARKETPLACE_DEFAULT_SELLER["Amazon"]`.

### Task 3 — Precedence fix in `_enrich_pdp_and_shipping` + warning logging

- `cross_marketplace_service.py`: imported `is_marketplace_default`. In `fetch_pdp_seller_and_shipping`, replaced the unconditional `p["seller"] = details["seller"]` with precedence logic:
  - PDP seller is real (not `is_marketplace_default`) → overwrites `p["seller"]`
  - PDP seller is a default (or None/empty) → `p["seller"]` unchanged (listing value preserved)
- PDP exception handler upgraded from `logger.debug` to `logger.warning`.
- 4 new test cases in `tests/test_cross_marketplace_service.py` (`TestSellerPrecedence`): PDP-real overwrites listing-default; PDP-default preserves listing-real; PDP-exception preserves seller; PDP-real overwrites listing-default (common case).

## Verification Results

```
tests/test_seller_extraction.py     34 passed
tests/test_cross_marketplace_service.py  13 passed  (9 existing + 4 new)
tests/test_netshoes_engine.py        6 passed
Total target suite: 47 passed, 0 failed
```

All module imports clean:
```
python -c "import services.engines.mercado_livre_engine, services.engines.amazon_engine, services.engines.netshoes_engine, services.cross_marketplace_service"
# → OK (no errors)
```

No neutral label `"Vendedor não identificado"` introduced (grep confirmed).

## Commits

| Hash    | Type | Description |
|---------|------|-------------|
| 7b35cbd | test | add failing tests for seller_extraction module (RED) |
| 64d7459 | feat | implement seller_extraction pure module (GREEN) |
| d1f24af | feat | wire robust seller extractors in ML and Amazon engines |
| 0deb555 | test | add failing precedence tests for seller enrichment (RED) |
| 717beb9 | feat | fix seller precedence in _enrich_pdp_and_shipping (GREEN) |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All seller paths either resolve to a real extractor result or fall back to the marketplace name constant (LOCKED decision).

## Threat Flags

None. This plan adds no new network endpoints, auth paths, file access patterns, or schema changes. The `seller_extraction` module is pure (no I/O); the engines already had network access; `cross_marketplace_service` already called the engines.

## Self-Check

- [x] `services/engines/seller_extraction.py` exists
- [x] `tests/test_seller_extraction.py` exists
- [x] Commits 7b35cbd, 64d7459, d1f24af, 0deb555, 717beb9 exist
- [x] 47 target-suite tests pass
- [x] No neutral label introduced
