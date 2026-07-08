---
phase: 41-abstracao-de-frete-marcas-nao-vtex
plan: 01
subsystem: spike
tags: [shipping, shopify, wake, live-probe]

provides:
  - ".planning/spikes/011-non-vtex-shipping/experiment.py"
  - ".planning/spikes/011-non-vtex-shipping/REPORT.md"
  - "GO verdict for Shopify/Buckman via Shopify Ajax Cart shipping rates"
  - "GO verdict for Wake/Richards via Storefront GraphQL shippingQuotes"

requirements-completed: [FRET-07]
completed: 2026-06-29T21:43:08Z
---

# Phase 41 Plan 01: Spike 011 Summary

Spike 011 proved both non-VTEX targets can return real shipping through public storefront paths.

## Results

- Shopify/Buckman: GO. `products.json` exposed variant id; isolated cart flow returned `shipping_rates[]` twice.
- Wake/Richards: GO. REST quote endpoint returned 401 with storefront token, but public Storefront GraphQL exposed and accepted `shippingQuotes(cep, productVariantId, quantity)` twice.
- VTEX remains outside the new abstraction.
- SFCC remains unsupported.

## Evidence

- `.planning/spikes/011-non-vtex-shipping/experiment.py` compiles and reruns both probes.
- `.planning/spikes/011-non-vtex-shipping/REPORT.md` records product URL, response signature, options and implementation decisions.

## Verification

```powershell
python -m py_compile .planning/spikes/011-non-vtex-shipping/experiment.py
python .planning/spikes/011-non-vtex-shipping/experiment.py --provider all --write-report
```

