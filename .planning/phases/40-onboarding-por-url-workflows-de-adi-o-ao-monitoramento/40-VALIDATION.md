---
phase: 40
slug: onboarding-por-url-workflows-de-adi-o-ao-monitoramento
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-29
---

# Phase 40 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `40-RESEARCH.md` → ## Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (backend) |
| **Config file** | `backend/pytest.ini` / `pyproject.toml` (verify in Wave 0) |
| **Quick run command** | `cd backend && python -m pytest tests/test_brand_identify.py tests/test_url_utils.py tests/test_price_monitor.py -x` |
| **Full suite command** | `cd backend && python -m pytest tests/ -x` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick command above
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

> Task IDs assigned by the planner; rows mapped by requirement + behavior here so the planner
> can attach the right `<automated>` command to each task.

| Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| identify | 1 | UX-03 | T-40-V5 | `POST /brands/identify` is dry-run — returns engine+name, never writes brands.json | unit | `pytest tests/test_brand_identify.py -x` | ❌ W0 | ⬜ pending |
| identify | 1 | UX-03 | — | `infer_brand_name` resolves all 4 cases (JSON-LD → OG → `<title>` → domain) | unit | `pytest tests/test_brand_identify.py::test_infer_brand_name -x` | ❌ W0 | ⬜ pending |
| identify | 1 | UX-03 | T-40-SSRF | identify rejects non-http(s) scheme and RFC1918/private-IP hosts | unit | `pytest tests/test_brand_identify.py::test_identify_rejects_ssrf -x` | ❌ W0 | ⬜ pending |
| monitor-dedup | 1 | UX-04 | — | `normalize_url` drops utm_*/gclid/fbclid, keeps SKU query, lowercases host, strips www, forces https + no trailing slash | unit | `pytest tests/test_url_utils.py -x` | ❌ W0 | ⬜ pending |
| monitor-dedup | 2 | UX-04 | — | `start_monitor` on already-active url+brand → `already_active`, no new job_id | unit | `pytest tests/test_price_monitor.py::test_dedup_active -x` | ✅ extend | ⬜ pending |
| monitor-dedup | 2 | UX-04 | — | `start_monitor` on stopped url+brand → reactivates existing monitor | unit | `pytest tests/test_price_monitor.py::test_dedup_reactivate -x` | ✅ extend | ⬜ pending |
| marketplace-toggle | 2 | UX-05 | — | `cross_marketplace_service._active_engines()` excludes marketplace with `is_active=False` (next run) | unit | `pytest tests/test_cross_marketplace_service.py::test_inactive_marketplace_excluded -x` | ✅ extend | ⬜ pending |
| marketplace-toggle | 1 | UX-05 | — | `GET /brands/` returns mercado_livre/netshoes/amazon from brands.json (no runtime injection) | integration | `pytest tests/test_brand_active.py::test_marketplaces_in_brands_json -x` | ✅ extend | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_brand_identify.py` — UX-03: identify dry-run (no persistence) + `infer_brand_name` 4 cases + SSRF rejection
- [ ] `backend/tests/test_url_utils.py` — UX-04: `normalize_url` (tracking-param strip, SKU-query preservation, www/https/trailing-slash)
- [ ] Extend `backend/tests/test_price_monitor.py` — UX-04 dedup (already_active no-op, reactivate-stopped)
- [ ] Extend `backend/tests/test_cross_marketplace_service.py` — UX-05 (inactive marketplace excluded per-request)
- [ ] Extend `backend/tests/test_brand_active.py` — UX-05 (marketplaces live in brands.json, not runtime-injected)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Pre-filled confirmation form renders with editable name + engine override | UX-03 | Frontend rendering / interaction | Paste a brand URL in onboarding → form appears pre-filled → edit name → save |
| "Adicionar ao monitoramento" button present & wired on all 3 surfaces | UX-04 | Cross-surface UI presence | Click the button on comparative search, SKU search, and category monitor; confirm product appears in price monitors once |
| Marketplace toggles visible in settings & dim/exclude on disable | UX-05 | Visual + end-to-end search behavior | Toggle off a marketplace in settings → run cross-marketplace search → marketplace absent from results |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
