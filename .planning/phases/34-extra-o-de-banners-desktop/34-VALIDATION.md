---
phase: 34
slug: extra-o-de-banners-desktop
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-23
---

# Phase 34 — Validation Strategy

> Per-phase validation contract for desktop banner extraction.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + TypeScript compiler/ESLint |
| **Config file** | `pytest.ini`, `frontend/eslint.config.js`, `frontend/tsconfig.json` |
| **Quick run command** | `python -m pytest backend/tests/test_banner_models.py backend/tests/test_banner_storage.py backend/tests/test_banner_extraction.py backend/tests/test_banner_routes.py -q` |
| **Full suite command** | `python -m pytest backend/tests -q` then `npm run lint && npm run build` in `frontend` |
| **Estimated runtime** | ~120 seconds |

## Sampling Rate

- **After every task commit:** run the task's targeted command.
- **After every plan wave:** run all banner tests plus the frontend build when applicable.
- **Before `/gsd-verify-work`:** full backend suite, frontend lint/build, and manual live-site smoke must be green.
- **Max feedback latency:** 120 seconds.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 34-01-01 | 01 | 1 | BANNER-02 | T-34-01 | Paths derive only from digest and allowlisted extension | unit | `python -m pytest backend/tests/test_banner_models.py backend/tests/test_banner_storage.py -q` | yes | green |
| 34-01-02 | 01 | 1 | BANNER-04 | T-34-02 | Atomic immutable approval, retention and orphan cleanup | unit | `python -m pytest backend/tests/test_banner_storage.py -q` | yes | green |
| 34-02-01 | 02 | 2 | BANNER-01, BANNER-02, BANNER-03 | T-34-03 | Only registered HTTP(S) page-discovered assets are fetched | unit | `python -m pytest backend/tests/test_banner_extraction.py -q` | yes | green |
| 34-02-02 | 02 | 2 | BANNER-01, BANNER-03 | T-34-02 | Limits and cancellation bound browser/file work | browser fixture | `python -m pytest backend/tests/test_banner_extraction.py -q` | yes | green |
| 34-03-01 | 03 | 3 | BANNER-01, BANNER-04 | T-34-04 | Authenticated job-scoped state and cancel flags | API unit | `python -m pytest backend/tests/test_banner_routes.py -q` | yes | green |
| 34-03-02 | 03 | 3 | BANNER-04 | T-34-04 | Partial/cancelled runs cannot enter history | API unit | `python -m pytest backend/tests/test_banner_routes.py -q` | yes | green |
| 34-04-01 | 04 | 4 | BANNER-01, BANNER-04 | T-34-05 | Late events cannot overwrite a newer job | compile/lint | `npm run lint && npm run build` | existing infrastructure | green |
| 34-04-02 | 04 | 4 | BANNER-01, BANNER-04 | — | Accessible states expose selection, stop, review and history | compile/lint | `npm run lint && npm run build` | existing infrastructure | green |
| 34-04-03 | 04 | 4 | BANNER-01..04 | — | Full vertical contract remains integrated | regression | `python -m pytest backend/tests -q; cd frontend; npm run lint; npm run build` | existing infrastructure | green with unrelated Phase 30 test debt noted |

## Wave 0 Requirements

Existing pytest, TypeScript, ESLint, Vite, Playwright and fixture infrastructure cover all phase requirements. Test files are delivered in their owning implementation tasks so each behavior is introduced with its executable proof.

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Detect every current desktop carousel slide on all 13 active brands | BANNER-01, BANNER-03 | Retail campaigns, WAFs and DOMs change externally | Run all active brands at 1366×768; compare gallery with per-brand viewport captures and approve only real hero slides. |
| Visual quality and interaction of the dedicated tab | BANNER-01, BANNER-04 | Requires browser-level visual judgment | Check all-selected default, toggle brands, progress, stop, review, immutable approval, reopen and deletion. |

## Validation Sign-Off

- [x] All tasks have automated verification.
- [x] Sampling continuity has no three consecutive tasks without automated feedback.
- [x] Existing infrastructure covers Wave 0.
- [x] No watch-mode flags.
- [x] Feedback latency target is below 120 seconds.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** approved 2026-06-23
