---
phase: 25-funda-o-de-motores
plan: "01"
subsystem: engine-detection
tags: [detect_engine, wake-commerce, unknown-fallback, security, auto-deactivate]
dependency_graph:
  requires: ["25-00", "25-02"]
  provides: ["detect_engine-hardened", "create_brand-unknown-branch"]
  affects: ["api/routes_brands.py"]
tech_stack:
  added: []
  patterns: ["allow_redirects=False on outbound probe", "engine-unknown auto-deactivate via set_active"]
key_files:
  created: []
  modified:
    - api/routes_brands.py
decisions:
  - "D-01: Final fallback replaced with return 'unknown' — no unconditional VTEX assumption"
  - "D-02: Wake probe on fbitsstatic.net inserted before VTEX HTML check"
  - "D-03: Total probe failure treated as inconclusive → 'unknown'"
  - "D-04: Unknown engine → brand persisted inactive via set_active(brand_key, False)"
  - "T-25-01-SR: allow_redirects=False on home-page HTML GET prevents redirect spoofing"
metrics:
  duration: "~8m"
  completed: "2026-06-18T18:30:00Z"
  tasks_completed: 2
  files_modified: 1
---

# Phase 25 Plan 01: Harden detect_engine (unknown fallback + Wake probe + auto-deactivate) Summary

**One-liner:** Hardened `detect_engine` with `fbitsstatic.net` Wake probe before VTEX HTML check, `return "unknown"` fallback for all inconclusive probes, and `create_brand` auto-deactivates unknown-engine brands via `set_active`.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Harden detect_engine — unknown fallback + Wake probe + redirect-safe probes | eec59c5 | api/routes_brands.py |
| 2 | create_brand auto-deactivates unknown engine (D-04) | 075c206 | api/routes_brands.py |

## What Was Built

**Task 1 — detect_engine hardening:**

The detection function now follows a strict 6-step order:

1. Shopify API probe (`/collections.json` → 200 + `collections` key) — unchanged
2. VTEX API probe (`/api/catalog_system/pub/category/tree/1` → 200) — unchanged
3. (NEW) Wake Commerce HTML probe: `fbitsstatic.net` in HTML → `"unknown"` + info log
4. (HARDENED) VTEX HTML: only `vtexassets.com` OR `vtexcommercestable.com`; removed loose `"vtex" in html_lower`
5. Shopify HTML: `cdn.shopify.com` OR `window.shopify` — unchanged
6. Final fallback: `return "unknown"` (was `return "vtex"`)

Security mitigation T-25-01-SR applied: `allow_redirects=False` on the home-page HTML GET prevents a malicious redirect from pointing detection at an attacker-controlled domain.

**Task 2 — create_brand D-04 branch:**

After `add_brand`, if `saved.engine == "unknown"`, calls `brand_service.set_active(saved.brand_key, False)` and returns the deactivated brand. Returns HTTP 200 — not an error. The chokepoint `list_brands(active_only=True)` in Plan 02 excludes these inactive brands from search.

## Verification

```
python -m pytest tests/test_engine_detection.py tests/test_brand_active.py -x -q
12 passed in 1.32s
```

All COMP-02 test cases turned GREEN:
- `test_shopify_detected_via_collections_json` — green (no regression)
- `test_vtex_detected_via_category_tree` — green (no regression)
- `test_wake_commerce_returns_unknown` — RED → GREEN (D-02)
- `test_all_probes_fail_returns_unknown` — RED → GREEN (D-01/D-03)
- `test_unknown_engine_brand_saved_inactive` — RED → GREEN (D-04)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — Wake Commerce is intentionally unsupported this milestone. The `"unknown"` return for Wake is the correct behavior, not a stub. The deferred item `COMP-FUT-01` tracks the future Wake engine.

## Threat Flags

No new threat surface introduced. Threat mitigations T-25-01-SR (allow_redirects=False) and T-25-01-WK (remove loose vtex substring, add Wake probe) were applied as planned.

## Self-Check: PASSED

- [x] `api/routes_brands.py` modified and committed (eec59c5, 075c206)
- [x] Commit eec59c5 exists: `feat(25-01): harden detect_engine`
- [x] Commit 075c206 exists: `feat(25-01): create_brand auto-deactivates unknown engine brands (D-04)`
- [x] `detect_engine` no longer contains `return "vtex"` as final fallback
- [x] `detect_engine` no longer contains loose `"vtex" in html_lower`
- [x] `detect_engine` contains `fbitsstatic.net` check before `vtexassets.com` check
- [x] `create_brand` calls `brand_service.set_active(saved.brand_key, False)` for unknown engine
- [x] All 12 tests pass (5 in test_engine_detection.py + 7 in test_brand_active.py)
