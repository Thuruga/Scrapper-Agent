---
phase: 30-detec-o-de-engine-sfcc-wake
plan: "01"
subsystem: engine-detection
tags: [sfcc, wake, detect-engine, browser-probe, playwright]
dependency_graph:
  requires: []
  provides: [detect_engine_wake, detect_engine_sfcc]
  affects: [backend/api/routes_brands.py]
tech_stack:
  added: []
  patterns: [lazy-import-inside-try, try-except-degrade, exclusive-marker-check]
key_files:
  modified:
    - backend/api/routes_brands.py
decisions:
  - "D-05: Wake branch returns 'wake' (not 'unknown') so create_brand persists it active"
  - "D-07: SFCC probe is last-resort — only fires after Shopify, VTEX, and HTML probes all fail"
  - "D-02: SFCC verdict uses exclusive asset hosts demandware.static / demandware.edgesuite.net, NOT bare 'demandware'"
  - "D-03: BrowserManager imported lazily inside try block so Playwright-absent startup does not break module load"
  - "D-04: SFCC probe degrades to 'unknown' on any exception — never crashes detect_engine"
metrics:
  duration: "10m"
  completed_date: "2026-06-23"
  tasks_completed: 2
  files_modified: 1
---

# Phase 30 Plan 01: Engine Detection — Wake Flip & SFCC Browser Probe Summary

**One-liner:** `detect_engine` now labels Wake domains as `"wake"` (fbitsstatic.net flip) and SFCC domains as `"sfcc"` via a last-resort Playwright render checking exclusive demandware asset hosts.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Flip the Wake branch to return "wake" | 53ec0ef | backend/api/routes_brands.py |
| 2 | Add the last-resort SFCC browser probe | ee15042 | backend/api/routes_brands.py |

## What Was Built

### Task 1 — Wake flip (D-05)

Changed the `fbitsstatic.net` branch inside `detect_engine` from `return "unknown"` to `return "wake"`. The probe structure, `logger.info` call, and ordering relative to VTEX HTML probe are unchanged. Wake-before-VTEX ordering (Pitfall 1) preserved.

### Task 2 — SFCC browser probe (D-01/D-02/D-03/D-07)

Inserted a new Step 6 immediately after the HTML-fallback `except` block and before the final `return "unknown"`. It:
- Lazily imports `BrowserManager` from `core.browser_manager` inside a `try` block (D-03)
- Calls `await BrowserManager.fetch_html(f"https://{domain}")` with defaults (no wait_selector)
- Checks lowercased rendered HTML for `demandware.static` OR `demandware.edgesuite.net` (D-02 exclusive markers)
- Returns `"sfcc"` on positive match with `logger.info`
- Catches any exception with `logger.debug` and falls through to `return "unknown"` (D-04)

## Verification

- `grep -nF 'return "wake"' backend/api/routes_brands.py` returns line 53 ✓
- `grep -nE 'demandware\.static|demandware\.edgesuite\.net' backend/api/routes_brands.py` (non-comment) returns line 79 ✓
- `python -c "import ast; ast.parse(...)"` — Syntax OK ✓
- Wake probe (line 51) before VTEX HTML probe (line 58) — ordering preserved ✓
- SFCC probe (lines 75-85) after HTML-fallback except (line 64-65), before final return (line 88) ✓

## Deviations from Plan

None — plan executed exactly as written.

## Threat Surface Scan

No new network endpoints or auth paths introduced. The SFCC probe reuses the existing BrowserManager infrastructure and fires only on the rare `POST /brands/` operator action (authenticated). All threat IDs (T-30-01..T-30-04) from the plan's threat model are covered by the implementation as designed:
- T-30-01 (Spoofing): exclusive asset-host markers used, not bare `demandware` ✓
- T-30-02 (SSRF): accepted residual risk for operator-trusted admin action ✓
- T-30-03 (DoS): probe is last-resort with bounded 30s timeout ✓
- T-30-04 (Tampering): entire probe in try/except Exception → degrade ✓

## Known Stubs

None — both engine labels are fully functional return values within detect_engine. The downstream engine implementations (SFCC Phase 31, Wake Phase 32) are intentionally deferred; brands labeled `"sfcc"` or `"wake"` will be active but guarded by the factory (D-09, plan 30-02).

## Self-Check: PASSED

- `backend/api/routes_brands.py` exists and contains both changes ✓
- Commit `53ec0ef` exists (Task 1 — Wake flip) ✓
- Commit `ee15042` exists (Task 2 — SFCC probe) ✓
