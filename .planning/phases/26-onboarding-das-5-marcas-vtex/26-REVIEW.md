---
phase: 26-onboarding-das-5-marcas-vtex
reviewed: 2026-06-19T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - tests/test_vtex_brand_onboarding_contract.py
  - scripts/onboard_vtex_brands.py
findings:
  critical: 1
  warning: 5
  info: 4
  total: 10
status: issues_found
---

# Phase 26: Code Review Report

**Reviewed:** 2026-06-19
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Reviewed the two new Phase 26 files at standard depth, cross-referencing the
service/engine layer they delegate to (`services/brand_service.py`,
`services/category_mapping.py`, `services/engines/vtex_engine.py`,
`services/engines/factory.py`, `api/routes_brands.py`, `core/models.py`).

The script is a well-structured orchestrator and the contract test is a faithful
offline pin of the COMP-01 final state. However there is one BLOCKER: the
contract test `test_mappings_persisted` does **not** actually exercise the
documented persistence/validation invariant — it pins a tautology and would pass
even if `update_mappings` silently dropped or corrupted mappings. Several WARNING
issues concern the script's auto-match correctness (slug-claim ordering causing
silent drops), an unguarded `discover_categories()` failure path, an unused
import, and a contract gap where the test never asserts the script's own
slug-validity guarantee.

No security vulnerabilities found (no injection sinks, no hardcoded secrets,
domains are constants, `detect_engine` already pins `allow_redirects=False`
upstream).

## Critical Issues

### CR-01: `test_mappings_persisted` validates a tautology, not the persistence contract

**File:** `tests/test_vtex_brand_onboarding_contract.py:88-112`
**Issue:** The test feeds two hand-built `CategoryMapping` objects (`canonical_slug="calcas"` and `"polos"`) directly into `svc.update_mappings(...)`, then asserts that the returned mappings are non-empty and that each `canonical_slug` is in `VALID_SLUGS`. But the slugs are hardcoded valid by the test author, and `update_mappings` (see `services/brand_service.py:226-232`) does a plain `self.brands[key].mappings = mappings` assignment with **no filtering or validation**. The assertion `m.canonical_slug in VALID_SLUGS` can therefore only fail if the test author typed an invalid slug — it does not test any behavior of the production code. The docstring claims this pins "update_mappings persiste os mapeamentos e todos os slugs sao validos", but nothing in the system under test enforces slug validity; the real guard against invalid slugs lives in `scripts/onboard_vtex_brands.py` (`auto_match` only emits `CANONICAL_KEYWORDS` slugs), which this test never invokes. The contract is unprotected: a regression in `auto_match` (or any caller that builds mappings with an off-vocabulary slug) would ship undetected.
**Fix:** Make the test exercise the script's actual slug-producing path, so the invariant is enforced by production code rather than the test fixture:
```python
from scripts.onboard_vtex_brands import auto_match

def test_mappings_persisted(self):
    svc = _make_service_with_vtex_brand()
    # Drive the real auto-match so the slug vocabulary is produced by the SUT
    categories = [
        {"name": "Calças Jeans", "rel_path": "/roupas/jeans"},
        {"name": "Polos", "rel_path": "/roupas/polos"},
    ]
    proposals = auto_match(categories)
    sample = [
        CategoryMapping(canonical_slug=slug, vtex_fq_path=path, label=label)
        for slug, path, label in proposals
    ]
    with unittest.mock.patch.object(svc, "_save"):
        brand = svc.update_mappings("levis", sample)

    assert len(brand.mappings) > 0
    for m in brand.mappings:
        assert m.canonical_slug in VALID_SLUGS, (
            f"auto_match produced off-vocabulary slug '{m.canonical_slug}'"
        )
```
Alternatively, if `update_mappings` is *intended* to reject invalid slugs, add that filtering to `brand_service.update_mappings` and assert a bad slug is dropped — the current test asserts neither end of the contract.

## Warnings

### WR-01: `auto_match` silently drops a category when its best-fit slug was already claimed

**File:** `scripts/onboard_vtex_brands.py:67-83`
**Issue:** The `seen_slugs` guard is *inside* the slug loop (`if slug in seen_slugs: continue`). When a category's only matching slug has already been claimed by an earlier category, the inner loop falls through without appending anything and the category is silently discarded. Worse, because the guard skips the matched slug and keeps iterating, a category can be diverted onto a *different* (later, broader) slug than its true best match — e.g. a "Jaquetas" page could be skipped while a generic "Blusas" page earlier claimed `jaquetas` via the broad `"blusa"` keyword (line 53). The first-match-wins behavior is order-dependent on VTEX's category tree, which is not deterministic across brands. Result: a real category that should map to a canonical slug can be omitted from the de/para with no warning at this layer (only the aggregate "[SEM MATCH]" notice in `print_and_confirm` surfaces it, and only if the slug ends up totally unmapped).
**Fix:** Decide the intended semantics explicitly. If "first category wins a slug" is intended, skip the *category* once any slug matches (move the dedup to the category level and `break`), and log dropped candidates:
```python
def auto_match(categories):
    proposals = []
    seen_slugs = set()
    for item in categories:
        norm = normalize(item["name"])
        for slug, keywords in CANONICAL_KEYWORDS.items():
            if any(kw in norm for kw in keywords):
                if slug in seen_slugs:
                    # already mapped by an earlier category — skip silently is OK,
                    # but do not let this category fall through to a worse slug
                    break
                proposals.append((slug, item["rel_path"], item["name"]))
                seen_slugs.add(slug)
                break
    return proposals
```
The key change is `break` (not `continue`) when `slug in seen_slugs`, so a category that best-matches an already-claimed slug is not re-routed to an inferior one.

### WR-02: `discover_and_match` crashes on categories with a missing/None `path`

**File:** `scripts/onboard_vtex_brands.py:200-203`
**Issue:** `urlparse(item["path"])` assumes every flattened category dict has a `path` key. `VTEXEngine._flatten_vtex_tree` (`services/engines/vtex_engine.py:40-53`) only appends nodes where both `name` and `url` are truthy, so `path` is normally present — but the contract is not enforced here, and `urlparse(None)` raises `TypeError`, aborting the entire onboarding loop for that brand mid-run (after the brand was already activated). A single malformed node from the live VTEX tree would crash the script with an unhandled exception, contradicting the "re-executavel / nao falha" design intent.
**Fix:** Defensively default and skip empty paths:
```python
for item in raw:
    item["rel_path"] = urlparse(item.get("path") or "").path
```
`auto_match` already only produces proposals from matched names, and `persist_mappings` already filters non-`/` paths (line 237-241), so an empty `rel_path` is then safely dropped.

### WR-03: `discover_categories()` failure (empty list) is indistinguishable from "site has no categories"

**File:** `scripts/onboard_vtex_brands.py:193-203`, `289-296`
**Issue:** `VTEXEngine.discover_categories()` returns `[]` both when the brand is not found and when `VtexApiClient.fetch_categories` fails/returns nothing (`vtex_engine.py:29-37`). The script treats an empty `proposals` only as "[WARN] nenhum mapping auto-matched" (line 284) and still appends the brand to `onboarded` (line 286) and runs the smoke test. A brand whose category discovery failed entirely is therefore reported as successfully onboarded with zero mappings — a misleading success signal for an operator-facing seed script. Combined with the smoke test swallowing all exceptions (line 295), a brand can be flagged "Onboardadas" while having no mappings and zero smoke results.
**Fix:** Distinguish "discovery returned nothing" from "matched nothing", and do not mark a brand as fully onboarded when it has no persisted mappings:
```python
raw = await discover_and_match(svc, brand_key)
if not raw:
    print(f"[WARN] {brand_key}: discover_categories vazio — possivel falha de rede/dominio.")
    skipped.append(brand_key)
    continue
```
(or report a third "partial" bucket so the final summary is honest).

### WR-04: Idempotency "[s/N]" prompt re-runs discovery even when operator declined to overwrite

**File:** `scripts/onboard_vtex_brands.py:174-186`, `276-285`
**Issue:** When mappings already exist and the operator answers anything but `s`, `onboard_brand` returns the brand (line 184) — but `main` then unconditionally calls `discover_and_match` (line 277) and prompts the operator *again* via `print_and_confirm` to re-persist. The "don't overwrite" decision at step 6 is effectively ignored: the operator is asked a second time and, if they confirm the second prompt, the existing mappings are overwritten anyway. The two confirmation gates are not coordinated, defeating the D-06 idempotency guard.
**Fix:** Return a sentinel from `onboard_brand` indicating "keep existing mappings, skip discovery", and honor it in `main`:
```python
# in onboard_brand, when operator declines overwrite:
if ans != "s":
    brand._skip_mappings = True   # or return a (brand, skip=True) tuple
    return brand
...
# in main:
if getattr(brand, "_skip_mappings", False):
    onboarded.append(brand_key)
    continue
```
Prefer an explicit return contract (e.g. a small dataclass/namedtuple) over a dunder attribute on a Pydantic model.

### WR-05: `engine="auto"` passed to `add_brand` is never resolved by `add_brand`

**File:** `scripts/onboard_vtex_brands.py:128-137`
**Issue:** The comment at line 119/135 says `DynamicBrandCreate(engine='auto') -> add_brand` and references the route's upsert behavior, but `brand_service.add_brand` (`services/brand_service.py:188-198`) never calls `detect_engine` — only the `create_brand` *route* does (`api/routes_brands.py:76-78`). So after `add_brand`, a newly created brand is persisted with the literal string `engine="auto"`, not a detected engine. The script does recover at step 2 (lines 140-145) by calling `detect_engine` and saving — so the end state is correct — but the intermediate persisted state contains `engine="auto"`, which `EngineFactory.get_engine` (`factory.py:42-45`) would resolve to `VTEXEngine` for any non-`shopify` value. If the script aborts between `add_brand` and the step-2 correction (e.g. network error in `detect_engine`), a non-VTEX brand is left persisted as `engine="auto"` and **active by default** (`DynamicBrand.is_active` defaults to `True`, `core/models.py:232`), since `add_brand` does not deactivate. That is a stale-state hazard the script's own comments claim to "defuse".
**Fix:** Either reuse the route's `create_brand` flow (which resolves `auto` and deactivates `unknown`), or set the brand inactive immediately after `add_brand` until engine is reconfirmed:
```python
brand = svc.add_brand(data)
svc.set_active(brand_key, False)   # fail-safe: inactive until engine reconfirmed
```

## Info

### IN-01: Unused import `engine_factory`-adjacent — `engine_factory` is used, but verify no dead imports

**File:** `scripts/onboard_vtex_brands.py:21`
**Issue:** `from services.engines.factory import engine_factory` is used only in the smoke block (line 290). `from services.engines.vtex_engine import VTEXEngine` (line 20) is used in `discover_and_match`. Both are live. No dead import here — flagged only to record that imports were checked. (No action required.)
**Fix:** None.

### IN-02: Test fixture hardcodes `brand_name`/`domain` regardless of `brand_key`

**File:** `tests/test_vtex_brand_onboarding_contract.py:52-59`
**Issue:** `_make_service_with_vtex_brand` accepts a `brand_key` parameter but always sets `brand_name="Levi's"` and `domain="www.levi.com.br"`. If a future test passes a different `brand_key`, the brand metadata will be inconsistent. Harmless today (only "levis" is used) but a latent footgun.
**Fix:** Derive or parameterize `brand_name`/`domain` from `brand_key`, or document that the factory is Levi's-specific.

### IN-03: Bare-ish broad exception in smoke test swallows real errors

**File:** `scripts/onboard_vtex_brands.py:295-296`
**Issue:** `except Exception as exc:` (annotated `# noqa: BLE001`) prints the error but the brand is already counted as onboarded. Acceptable for a non-blocking smoke per D-10, but combined with WR-03 it hides discovery/search failures behind a "success" report.
**Fix:** Already noqa-acknowledged; consider logging the exception type for diagnosability. No blocking action.

### IN-04: `print(f"...")` f-string with no placeholders

**File:** `scripts/onboard_vtex_brands.py:299`
**Issue:** `print(f"Onboarding concluido.")` uses an f-string with no interpolation. Cosmetic.
**Fix:** Drop the `f` prefix: `print("Onboarding concluido.")`.

---

_Reviewed: 2026-06-19_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
