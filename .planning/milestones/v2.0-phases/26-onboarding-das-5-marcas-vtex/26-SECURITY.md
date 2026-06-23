---
phase: 26
slug: onboarding-das-5-marcas-vtex
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-19
---

# Phase 26 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Register authored at plan-time (both 26-01-PLAN.md and 26-02-PLAN.md carry `<threat_model>` blocks); each mitigation verified against the implementation on 2026-06-19.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| test harness → BrandManagerService | Contract test builds the service in-memory (`__new__`); all persistence sinks mocked | None — no external input reaches real persistence |
| operator stdin → script | `print_and_confirm` / overwrite gate read only y/n confirmations | Low-trust y/n; no free text persisted |
| script → detect_engine → remote storefront | Network responses classify the engine; untrusted remote HTML drives the engine label | Untrusted HTML (read-only classification) |
| script → brand_service → persistence (brands.json / Supabase) | New brand rows + category mappings written via the existing service layer | Brand records + relative category paths (internal) |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-26-01-IO | Tampering | contract test touching real brands.json / Supabase | mitigate | `_check_reload` is `MagicMock()` (test:54); `_save` only inside `patch.object(svc, "_save")` (test:117); service built via `__new__` with empty in-memory `brands`. Test runs fully offline. | closed |
| T-26-01-IMP | Tampering | broken import silently skipping coverage | mitigate | No non-existent `CANONICAL_SLUGS` import; `VALID_SLUGS` derived from `_RAW_CATEGORIES` (test:29, D-04 anchor). 7/7 contract tests collect and pass. | closed |
| T-26-02-DOM | Tampering | `domain` field on DynamicBrandCreate (V5 input validation) | mitigate | `DynamicBrandCreate.clean_domain` strips `http(s)://` + trailing `/` (core/models.py:216-218); domains come from the fixed D-01 `BRAND_TABLE`, not free operator input. | closed |
| T-26-02-ENG | Spoofing | engine label from remote storefront HTML | mitigate | Engine set ONLY from `detect_engine` reconfirmation (`brand.engine = detected`, script:261). The single `engine = "vtex"` literal (script:273) is inside the Austral branch entered only when `resolve_austral_domain()` returned a domain it confirmed via `detect_engine(candidate) == "vtex"`. No unconditional manual override (D-11). | closed |
| T-26-02-PATH | Tampering | `vtex_fq_path` path-traversal (e.g. `/../../etc`) | accept | Internal data, not an external request path; value derived from `urlparse(discovered_url).path` of the brand's own storefront tree — no traversal sink. See Accepted Risks Log. | closed |
| T-26-02-IDEM | Tampering | stale `engine`/`is_active` surviving re-run (upsert bug) | mitigate | After every `add_brand`, the script re-checks `detect_engine` and force-corrects `brand.engine` + `_save` (script:259-263); WR-05 fail-safe `set_active(False)` immediately after `add_brand`. Idempotency confirmed live 2026-06-19 (re-run: no duplication, 13 brands stable, mappings preserved). | closed |
| T-26-SC | Tampering | npm/pip/cargo supply-chain installs | mitigate | No package installs in this phase. Script imports are stdlib only (asyncio, re, unicodedata, sys, os, typing, urllib) plus internal modules (services.*, core.models). | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-26-01 | T-26-02-PATH | `vtex_fq_path` is internal data derived from `urlparse()` of the brand's own VTEX storefront tree; it is concatenated into an outbound scan URL, never used as a filesystem path or to resolve a server-side resource. No path-traversal sink exists. Low risk per RESEARCH Security Domain. | Operator (arthur.correia) | 2026-06-19 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-19 | 7 | 7 | 0 | Claude (gsd-secure-phase, plan-time register verified against implementation) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-19
