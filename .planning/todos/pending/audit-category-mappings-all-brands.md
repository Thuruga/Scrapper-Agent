---
created: 2026-06-29
area: backend (category_mapping / onboarding) + frontend (category UI)
source: operator low-confidence in displayed categories — ALL brands (2026-06-29)
priority: medium
resolves_phase:
---

# Audit category-mapping accuracy across ALL brands

The operator does not fully trust the categories shown in the monitor/search UI **for
all brands**, not just Hugo Boss. During Phase 39 the `auto_match` matcher was caught
mapping canonical `calcas` → "Calçados" (footwear) for Hugo Boss — an accent / word-
boundary collision ("calça" ~ "calçados"). The same matcher and the hardcoded
`_RAW_CATEGORIES` feed every brand's category mappings, so similar mismatches likely
exist for other brands too.

## What to check
- For each brand in `brands.json` that has `mappings`, scan each mapped `vtex_fq_path`
  (or engine equivalent) and confirm the returned products actually match the canonical
  label — protects banana-com-banana comparison integrity.
- Review the hardcoded `_RAW_CATEGORIES` in `category_mapping.py` (aramis / reserva /
  tommy) and the dynamic `brand.mappings` for wrong or stale paths.
- Reconcile `get_canonical_categories()` so the UI only offers, per brand, categories
  that truly resolve AND return products (drop empty/dead category pages — e.g. Hugo
  Boss `/masculino/roupas/polos` renders an empty page on the brand's own site).

## Root cause to fix
- Make `auto_match` (scripts/onboard_vtex_brands.py) accent- and word-boundary-aware so
  discovery proposals are correct and reproducible. See
  `hugoboss-vtex-io-category-scan.md` → "auto_match accent collision".

Deferred by operator ("fica pra depois"). NOT blocking Phase 39 — Hugo Boss category
monitoring works; this is a data-quality audit across the existing brand mappings.
