---
phase: 34
plan: 02
subsystem: banner-collector
tags: [playwright, carousel, ssrf, fixtures]
requires: [34-01]
provides: [desktop-banner-collector, carousel-traversal, viewport-evidence]
affects: [34-03, 34-04]
tech-stack:
  added: []
  patterns: [sequential-playwright, cooperative-cancellation, deterministic-browser-fixture]
key-files:
  created:
    - backend/services/banner_extraction_service.py
    - backend/tests/fixtures/banner_carousels.html
    - backend/tests/test_banner_extraction.py
  modified: []
key-decisions:
  - "Largest source and actual currentSrc are stored separately."
  - "Carousel traversal tolerates video-only rounds even without declared slide counts."
requirements-completed: [BANNER-01, BANNER-02, BANNER-03]
duration: 10 min
completed: 2026-06-23
---

# Phase 34 Plan 02: Production Banner Collector Summary

Production Playwright collector with 1366×768 hero detection, lazy/srcset/background support, video-aware traversal, original-byte storage, SSRF guards, and cooperative cancellation.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 34-02-01 | `6dd9fe1` | Promote validated prototype into service boundary |
| 34-02-02 | `15977b5` | Deterministic carousel fixture and security/traversal tests |

## Verification

`python -m pytest backend/tests/test_banner_extraction.py -q` — 4 passed.

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

Ready for 34-03 asynchronous job/API orchestration.

## Self-Check: PASSED

- All three key files exist.
- Collector and fixture commits are present.
- Image-after-video traversal passes with and without declared slide count.

