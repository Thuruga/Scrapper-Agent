---
status: complete
phase: 40-onboarding-por-url-workflows-de-adi-o-ao-monitoramento
source: [40-05-SUMMARY.md]
started: 2026-07-06T00:00:00Z
updated: 2026-07-08T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Flow 1 — UX-03 identify-first monitor (reworked)

expected: Pasting a product URL whose domain matches a registered brand auto-identifies the brand, starts the monitor, shows a success toast, and resubmitting the same URL shows a dedup toast instead of a duplicate. Pasting a URL for an unregistered domain reveals the manual brand select instead of dead-ending.
result: passed - operator confirmed live during v4.0 milestone close (2026-07-08).

### 2. Flow 2 — UX-04 add-to-monitor (3 surfaces)

expected: Add-to-monitor button works from comparative search, SKU search, and category monitor, with dedup toasts on repeat.
result: passed - previously approved, unchanged by the Flow 1 rework.

### 3. Flow 3 — UX-05 marketplace toggles

expected: Virtual marketplace toggles (Mercado Livre, Netshoes, Amazon) are respected by cross-marketplace search.
result: passed - previously approved, unchanged by the Flow 1 rework.

## Summary

total: 3
passed: 3
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

None.
