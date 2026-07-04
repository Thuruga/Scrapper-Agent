---
phase: 37
slug: paridade-de-atributos-fundacao-sqlite
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-03
---

# Phase 37 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pytest.ini` with `testpaths = backend/tests` and `pythonpath = backend` |
| **Quick run command** | `python -m pytest backend/tests/test_product_contract.py backend/tests/test_phase37_engine_contract.py backend/tests/test_export_search_contract.py -q` |
| **Full suite command** | `python -m pytest` |
| **Estimated runtime** | Quick: under 20s after Wave 0; full suite: project dependent |

## Sampling Rate

- **After every task commit:** run the Phase 37 quick suite.
- **After every plan wave:** run `python -m pytest`.
- **Before `/gsd-verify-work`:** full suite must be green.
- **Max feedback latency:** 20 seconds for the Phase 37 quick suite after Wave 0.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|-------------|--------|
| 37-W0-01 | 37-01 | 0 | PARID-01 | Canonical column order and fallback projection are deterministic | unit | `python -m pytest backend/tests/test_product_contract.py -q` | missing - Wave 0 | pending |
| 37-W0-02 | 37-01 | 0 | PARID-03 | Alias normalization is additive and preserves raw keys | unit | `python -m pytest backend/tests/test_product_contract.py::test_aliases_are_additive -q` | missing - Wave 0 | pending |
| 37-W0-03 | 37-02 | 0 | PARID-02 | Engine/parsers populate canonical fields or `None` without inventing data | characterization | `python -m pytest backend/tests/test_phase37_engine_contract.py -q` | missing - Wave 0 | pending |
| 37-W0-04 | 37-03 | 0 | PARID-01/PARID-02 | Comparative export and category exports share the same leading canonical columns | integration | `python -m pytest backend/tests/test_export_search_contract.py -q` | missing - Wave 0 | pending |

## Wave 0 Requirements

- [ ] `backend/tests/test_product_contract.py` covers canonical column order, `raw_title`/`raw_description` fallback, `product_code` null semantics, and additive aliases.
- [ ] `backend/tests/test_phase37_engine_contract.py` covers representative VTEX/Shopify/Wake/SFCC/Zara/marketplace payloads against the canonical contract.
- [ ] `backend/tests/test_export_search_contract.py` covers the three export surfaces using the same shared canonical leading columns.

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| One real comparative export shows fixed canonical columns in English | PARID-01 | Final confidence check on generated Excel | Run a comparative search export and verify the canonical column block appears first and consistently. |
| One category-scan export matches the same canonical leading columns | PARID-01/PARID-02 | Confirms orchestrator parity, not just route parity | Run a category export for a working brand and compare the leading columns with the comparative export. |
| A sparse engine leaves blanks instead of synthetic codes/attributes | PARID-02/D-03 | Best checked with a real sparse brand/page | Verify at least one sparse engine row has `product_code` blank when the source does not expose one. |

## Validation Sign-Off

- [x] All phase requirements have automated targets or manual-only justifications.
- [x] Wave 0 covers every new planned test file.
- [x] No watch-mode flags.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** ready for planning
