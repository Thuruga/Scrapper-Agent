---
phase: 45
slug: an-lise-de-sortimento
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-05
---

# Phase 45 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + frontend production build |
| **Config file** | `pytest.ini` with `testpaths = backend/tests` and `pythonpath = backend` |
| **Quick run command** | `python -m pytest backend/tests/test_sortiment_registry_service.py backend/tests/test_sortiment_snapshot_service.py backend/tests/test_sortiment_routes.py -q` |
| **Full suite command** | `python -m pytest` |
| **Estimated runtime** | Quick: under 20s after Wave 0; full suite: project dependent |

## Sampling Rate

- **After every task commit:** Run `python -m pytest backend/tests/test_sortiment_registry_service.py backend/tests/test_sortiment_snapshot_service.py backend/tests/test_sortiment_routes.py -q`
- **After every plan wave:** Run `python -m pytest` and `cd frontend && npm run build`
- **Before `$gsd-verify-work`:** Full backend suite and frontend build must be green
- **Max feedback latency:** 20 seconds for the Phase 45 quick suite after Wave 0

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 45-01-01 | 45-01 | 1 | SORT-01 | T-45-01 | One-way seed sync preserves operator-owned `enabled` state and defaults new rows to disabled | unit | `python -m pytest backend/tests/test_sortiment_registry_service.py -q` | missing - Wave 0 | pending |
| 45-01-02 | 45-01 | 1 | SORT-01 | T-45-02 / T-45-03 | Immutable snapshot/manifest helpers keep filenames safe and persist aggregate-only payloads with capped evidence | unit | `python -m pytest backend/tests/test_sortiment_registry_service.py -q` | missing - Wave 0 | pending |
| 45-02-01 | 45-02 | 2 | SORT-01 | T-45-06 / T-45-07 | Snapshot execution normalizes only `available_colors`, `available_sizes`, and `composition`, buckets dirty values as `não informado`, and returns truthful baseline/delta semantics | unit | `python -m pytest backend/tests/test_sortiment_snapshot_service.py -q` | missing - Wave 0 | pending |
| 45-02-02 | 45-02 | 2 | SORT-01 | T-45-04 / T-45-05 | Routes resolve persisted category identity server-side, manual runs stay overlap-safe, and the independent cron does not mutate monitor cadence or source JSON | integration | `python -m pytest backend/tests/test_sortiment_routes.py -q` | missing - Wave 0 | pending |
| 45-03-01 | 45-03 | 3 | SORT-01 | T-45-08 / T-45-09 / T-45-10 | Dedicated `Sortimento` page renders registry controls, explicit baseline state, and current distributions for exactly the three v1 dimensions without browser-side snapshot math | build/smoke | `cd frontend && npm run build` | existing build path | pending |

## Wave 0 Requirements

- [ ] `backend/tests/test_sortiment_registry_service.py` - stubs and red tests for separate registry sync, disabled-by-default seeding, and artifact helper contracts
- [ ] `backend/tests/test_sortiment_snapshot_service.py` - stubs and red tests for batch execution, `não informado` bucketing, manifest pointers, and baseline/delta assembly
- [ ] `backend/tests/test_sortiment_routes.py` - stubs and red tests for registry endpoints, manual run, dashboard reads, and overlap-safe scheduling boundaries
- [ ] Frontend build verification remains `npm run build`; no dedicated new frontend runner is required for this phase

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| One enabled sortiment category produces a real snapshot and dashboard payload against a live storefront | SORT-01 | Requires low-frequency live scraping and real attribute sparsity; not suitable for hermetic CI | Enable one registry row, trigger the manual run once, then confirm the dashboard shows latest snapshot metadata and either baseline state or deltas from the prior snapshot. |
| Sparse attributes remain truthful instead of fabricated | SORT-01 | Best checked with a real category where some products lack colors, sizes, or composition | Inspect one live snapshot/dashboard and confirm missing/dirty values appear under `não informado` rather than being dropped or synthesized. |
| Hugo Boss inherited risk is documented rather than masked | SORT-01 | Depends on upstream category-scan reliability from the pending Hugo Boss todo | If using Hugo Boss in UAT, record the result explicitly; if scans remain weak or zero, keep that as a known upstream risk and verify another working brand for acceptance. |

## Validation Sign-Off

- [x] All tasks have `<automated>` verify steps or manual-only justifications
- [x] Sampling continuity: no 3 consecutive tasks should run without automated verification
- [x] Wave 0 covers all missing Phase 45 test files
- [x] No watch-mode flags
- [x] Feedback latency target under 20s for the quick suite after Wave 0
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** ready for planning
