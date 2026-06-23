---
phase: 26-onboarding-das-5-marcas-vtex
plan: "02"
subsystem: scripts
tags: [vtex, onboarding, idempotent, seed-script, dual-persistence]
dependency_graph:
  requires:
    - "tests/test_vtex_brand_onboarding_contract.py (26-01) — contract the script satisfies"
    - "services/brand_service.py — add_brand, set_active, update_mappings, _save"
    - "services/engines/vtex_engine.py — discover_categories"
    - "api/routes_brands.py — detect_engine"
  provides:
    - "scripts/onboard_vtex_brands.py — idempotent seed orchestrator for 5 VTEX brands (COMP-01)"
  affects:
    - "data/brands.json (dev path) / Supabase (prod path) — via brand_service._save"
tech_stack:
  added: []
  patterns:
    - "asyncio.run(main()) entry-point (mirrors scripts/validate_clip.py)"
    - "detect_engine reconfirmation after add_brand (defuses upsert idempotency bug)"
    - "urlparse(item['path']).path to extract relative vtex_fq_path from full URL"
    - "AUSTRAL_DOMAIN_CANDIDATES retry loop until detect_engine == 'vtex' (D-11)"
    - "print_and_confirm stdin gate before persist_mappings (D-09)"
key_files:
  created:
    - scripts/onboard_vtex_brands.py
  modified: []
decisions:
  - "Script imports detect_engine from api.routes_brands INSIDE onboard_brand (avoids heavy import-time side effects; mirrors PATTERNS.md)"
  - "engine='vtex' assigned ONLY when detect_engine reconfirms it — never hardcoded (D-11 invariant enforced)"
  - "Full script written atomically in Task 1 commit (both tasks verified in same commit; no behavioral regression)"
metrics:
  duration: "12m"
  completed: "2026-06-19"
  tasks: 2
  files: 1
---

# Phase 26 Plan 02: VTEX Brand Onboarding Script Summary

Idempotent seed orchestrator `scripts/onboard_vtex_brands.py` for the 5 VTEX competitor brands (Levi's, Calvin Klein, Zapalla, Austral, Track & Field) — delegates entirely to existing service/engine layer with engine reconfirmation, Austral domain retry, auto-match human review gate, and dual-persistence via brand_service.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Script skeleton — engine reconfirmation, idempotency fix, Austral retry | 8166e66 | scripts/onboard_vtex_brands.py |
| 2 | Category discovery, auto-match + human review, relative-path mappings, dual persistence, live smoke | 8166e66 | scripts/onboard_vtex_brands.py (same commit — script written complete) |

## Verification Results

- `python -c "import ast; ast.parse(...); print('parse-ok')"` → **parse-ok**
- `python -m pytest tests/test_vtex_brand_onboarding_contract.py -q` → **6 passed**
- `python -m pytest tests/ -q` → **162 passed, 1 pre-existing failure** (test_ocr_service.py cv2/easyocr env incompatibility — identical to baseline from 26-01-SUMMARY.md, unrelated to this plan)
- Manual (D-10a): deferred to operator — run `python scripts/onboard_vtex_brands.py` with network once ready

## Deviations from Plan

### Auto-implemented

**1. [Scope] Tasks 1 and 2 implemented in a single write**
- **Found during:** Task 1 implementation
- **Reason:** The plan's two-task split describes an incremental build, but the final script design was clear from reading all source files. Writing both tasks atomically avoided a partial-state commit that would have been syntactically incomplete (Task 1's `main()` had a TODO hook for Task 2 functions that were already designed).
- **Impact:** Single commit 8166e66 covers both tasks. All acceptance criteria for both tasks verified and passing before commit.
- **Acceptance criteria satisfied:** All Task 1 and Task 2 criteria verified via automated checks and test suite.

## Known Stubs

None — script delegates to real service/engine layer. No hardcoded mock data flows through any rendering path. `BRAND_TABLE` contains production-verified domains (D-01).

## Threat Flags

None — no new network endpoints, auth paths, or schema changes. Script writes only through existing `brand_service._save` / `update_mappings` (boundary already present). `T-26-02-DOM`, `T-26-02-ENG`, `T-26-02-PATH`, `T-26-02-IDEM` all mitigated per threat model:
- Domain tampering: `DynamicBrandCreate.clean_domain` validator strips scheme/slash
- Engine spoofing: `engine="vtex"` only from `detect_engine` reconfirmation
- Path traversal: `urlparse(url).path` extracts only the path component
- Stale engine upsert: script calls `detect_engine` + `_save` after every `add_brand`

## Self-Check: PASSED

- scripts/onboard_vtex_brands.py — FOUND
- Commit 8166e66 — FOUND (git log confirms)
- `def onboard_brand(` — PRESENT
- `async def resolve_austral_domain(` — PRESENT
- `def auto_match(` — PRESENT
- `async def discover_and_match(` — PRESENT
- `def print_and_confirm(` — PRESENT
- `def persist_mappings(` — PRESENT
- `CANONICAL_KEYWORDS` with exactly 7 slugs (camisas, polos, camisetas, calcas, bermudas, jaquetas, infantil) — CONFIRMED
- `urlparse(item["path"]).path` in discover_and_match — CONFIRMED
- `engine="vtex"` only inside detect-engine-guarded branch — CONFIRMED
- `services/category_mapping.py` unmodified — CONFIRMED
- Contract tests 6/6 passing — CONFIRMED
- Full suite 162 passed, 1 pre-existing failure (unchanged from baseline) — CONFIRMED
