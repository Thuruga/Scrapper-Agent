---
phase: 42-frete-para-marketplaces-matriz-multi-regional
reviewed: 2026-07-02T00:00:00Z
depth: standard
files_reviewed: 20
files_reviewed_list:
  - backend/config.py
  - backend/services/engines/amazon_engine.py
  - backend/services/engines/mercado_livre_engine.py
  - backend/services/shipping/amazon.py
  - backend/services/shipping/base.py
  - backend/services/shipping/mercado_livre.py
  - backend/services/shipping/netshoes.py
  - backend/services/shipping/resolver.py
  - backend/services/shipping/regional_matrix.py
  - backend/api/routes_search.py
  - backend/services/cross_marketplace_service.py
  - backend/services/relevance_gates.py
  - backend/data/cep_matrix.json
  - backend/data/shipping_matrix_cache.json
  - .gitignore
  - frontend/src/App.css
  - frontend/src/App.tsx
  - frontend/src/api/client.ts
  - backend/tests/test_marketplace_shipping.py
  - backend/tests/test_shipping_engines.py
  - backend/tests/test_shipping_resolver.py
  - backend/tests/test_non_vtex_shipping_route.py
  - backend/tests/test_shipping_regional_matrix.py
  - backend/tests/test_cross_marketplace_service.py
findings:
  critical: 2
  warning: 6
  info: 4
  total: 12
status: issues_found
---

# Phase 42: Code Review Report

**Reviewed:** 2026-07-02T00:00:00Z
**Depth:** standard
**Files Reviewed:** 24 (test files reviewed for reliability only, per scope rules)
**Status:** issues_found

## Summary

Phase 42 adds a multi-regional shipping matrix (`regional_matrix.py`), wires
`AmazonShipping`/`MercadoLivreShipping`/`NetshoesShipping` providers behind the
existing `BaseShipping` contract, and surfaces delivery-time/blocked-state data
through `cross_marketplace_service` into the frontend. The design (guarded
on-demand trigger, per-region error isolation, TTL cache, CEP-domain allow-list)
is sound and the unit-test coverage for the new orchestrator is solid.

However, the on-disk shipping-matrix cache has a plaintext-JSON read-modify-write
race that will silently lose data under concurrent on-demand requests, and the
`.gitignore` pattern for the cache file means every developer/CI run's live
network responses (including timestamps) get committed to the repository.
There is also a real regression risk in `MercadoLivreEngine._fetch_shipping_options`:
the "worst case" price selection logic ignores its own free-shipping check,
so a genuinely free ML shipping option can still be reported as paid at the
highest listed price. Several other issues (duplicate `requestMatrix`/
`ShippingMatrixModal` logic between two pages, brand-domain matching against an
empty string, unreachable dead code) round out the list below.

## Critical Issues

### CR-01: `_fetch_shipping_options` can report a paid price for a marketplace that has a free option

**File:** `backend/services/engines/mercado_livre_engine.py:799-816`
**Issue:** The method computes `is_free = any(opt.get("cost") == 0 for opt in options)` correctly, but then computes `shipping_price = 0.0 if is_free else highest_price`. That looks right at first glance — but note `highest_price = max(prices)` is computed unconditionally over **all** returned options, including any zero-cost one. If the ML API returns e.g. `[{"cost": 0.0}, {"cost": 29.90}]` (free "normal" tier + paid "express" tier — a very common real-world ML pattern for reference-priced sellers), `is_free` is `True`, so the code does correctly report `shipping_price = 0.0`. That part is fine.

  The actual bug is the reverse: when NONE of the options are free (`is_free = False`), the code reports `highest_price` (the *most expensive* shipping tier) as "the" shipping price, unconditionally — even when a cheaper tier exists (e.g. `[{"cost": 12.90}, {"cost": 39.90}]`). This is called out in the code's own comment as an explicit choice ("assume highest for ranges/options to be safe"), but it directly contradicts `services/shipping/base.py::sorted_shipping_options`, which sorts by ascending price and is used everywhere else in the shipping pipeline (`AmazonShipping`, `NetshoesShipping`, `MercadoLivreShipping.calculate`) to select the **cheapest** option as `shipping_options[0]`. The result: the regional matrix and the on-demand `/calculate-shipping-brand` route for Mercado Livre will systematically show inflated shipping costs (worst-case) while every other provider shows the cheapest, giving inconsistent and misleading pricing across marketplaces in the same UI (the matrix modal and the comparison table).
**Fix:**
```python
# Report the cheapest paid option, consistent with sorted_shipping_options()
# used by every other provider (Amazon/Netshoes) and by ShippingCalculation.
cheapest_price = min(prices) if prices else 0.0
shipping_price = 0.0 if is_free else cheapest_price
```

### CR-02: Shipping-matrix cache read-modify-write is not concurrency-safe and can lose or corrupt entries

**File:** `backend/services/shipping/regional_matrix.py:59-71, 110-167`
**Issue:** `calculate_regional_matrix` loads the entire cache file into memory (`_load_cache`), mutates the in-memory dict per region, and writes the **whole file** back once at the end (`_save_cache`) with a plain `path.write_text(...)` — no file lock, no atomic rename, no compare-and-swap. If two `/search/calculate-shipping-matrix` requests for different products run concurrently (very plausible: nothing serializes requests, and `asyncio.gather`/multiple browser tabs can easily trigger this), both read the same initial cache snapshot, and whichever request finishes last overwrites the file, silently discarding the other request's cache entries. Given `SHIPPING_MATRIX_CACHE_TTL_SECONDS` defaults to 6h, lost entries mean unnecessary re-fetches (functional degradation, not data loss of business value) — but a torn write (crash/kill mid `write_text`) can also leave `shipping_matrix_cache.json` as invalid JSON, and `_load_cache` swallows `JSONDecodeError` by returning `{}`, silently discarding the **entire** existing cache the next time it's read.
**Fix:**
```python
def _save_cache(path: Path, cache: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_path.replace(path)  # atomic on POSIX and Windows (same filesystem)
```
This fixes torn writes but not the lost-update race between concurrent requests;
consider a per-process `asyncio.Lock` (or per-cache-file lock) around the
load-mutate-save sequence in `calculate_regional_matrix` if concurrent matrix
requests are expected in practice.

## Warnings

### WR-01: `.gitignore` allowlist commits the shipping-matrix cache (including timestamps and possibly stale prices) to version control

**File:** `.gitignore:20`, `backend/data/shipping_matrix_cache.json`
**Issue:** The blanket `*.json` ignore rule is explicitly overridden with `!/backend/data/shipping_matrix_cache.json`, meaning this file — which is runtime-generated cache data, mutated by every on-demand matrix call, containing epoch timestamps and live-scraped shipping prices — is tracked in git. Every developer/CI run that exercises this endpoint will produce a diff on this file, causing noisy commits and merge conflicts, and it commits ephemeral pricing data (which can go stale or be scraped from a specific IP/session) into permanent history. Compare with `.planning/*.json` (explicitly allow-listed for planning content) — this looks like the same allowlist pattern was applied to a cache file by mistake, or without considering it's runtime state, not configuration.
**Fix:** Remove `!/backend/data/shipping_matrix_cache.json` from `.gitignore` (let it fall under the general `*.json` ignore) and commit only an empty placeholder or `.gitkeep` if the directory must exist on checkout. If the file needs to ship with seed data for tests, use a `*.example.json` fixture instead of the live cache path.

### WR-02: Duplicate `requestMatrix`, `ShippingMatrixModal` wiring, and CEP-matrix state between `SearchPage` and `CrossMarketplacePage`

**File:** `frontend/src/App.tsx:1383-1389, 1627-1640` and `frontend/src/App.tsx:2202-2208 (approx), 2414-2427`
**Issue:** The `matrixModal` state shape, `requestMatrix` async handler, and the loading/error-handling logic are byte-for-byte duplicated between `SearchPage` and the cross-marketplace page component. Any future fix (e.g. the race-condition guard using `prev.productUrl === product.url`, or new error handling) must be applied in two places, and it's easy to fix one and forget the other — a classic drift risk. `ShippingMatrixModal` itself is already correctly extracted as a shared component; the state/handler logic around it was not.
**Fix:** Extract a `useShippingMatrix()` hook (or a small class/module) encapsulating `matrixModal` state + `requestMatrix`, and use it from both pages:
```ts
function useShippingMatrix() {
  const [matrixModal, setMatrixModal] = useState<MatrixModalState>({ open: false, brandKey: '', productUrl: '', loading: false, regions: [] });
  const requestMatrix = async ({ brandKey, product }: { brandKey: string; product: any }) => { /* shared body */ };
  return { matrixModal, requestMatrix, closeMatrix: () => setMatrixModal(m => ({ ...m, open: false })) };
}
```

### WR-03: `is_url_allowed_for_brand` silently denies (rather than erroring) when the brand has no domain configured

**File:** `backend/services/shipping/base.py:68-80`
**Issue:** `brand_domain()` returns `""` for a brand with no `domain` field, and `is_url_allowed_for_brand` returns `False` whenever `expected` is empty. This is defensively safe (no domain → nothing is "allowed"), but it means a misconfigured brand (missing `domain` in `brands.json`) fails with the generic `"URL do produto nao pertence ao dominio da marca"` message from every shipping route (`/calculate-shipping-brand`, `/calculate-shipping-matrix`) — which is misleading for an operator debugging why shipping suddenly "doesn't work" for a brand, since the real problem is a data/config gap, not a URL mismatch.
**Fix:** Distinguish the two cases in the route layer (or add a dedicated check) so a brand with no configured domain returns a clearer 400/422 message, e.g. `"Marca '{brand_key}' nao possui dominio configurado."`, instead of reusing the URL-mismatch copy.

### WR-04: `MercadoLivreShipping`/`AmazonShipping`/`NetshoesShipping.calculate` are near-identical copy-paste (only the BLOCKED-vs-TEMPORARY_FAILURE branch differs)

**File:** `backend/services/shipping/amazon.py:32-95`, `backend/services/shipping/mercado_livre.py:32-88`, `backend/services/shipping/netshoes.py:33-92`
**Issue:** All three provider classes repeat: CEP normalization + error handling, URL allow-list check, `try/except` around `engine.calculate_shipping_advanced`, and building a single `ShippingInfo` from the same four dict keys (`shipping_price`, `is_free_shipping`, `estimated_delivery_days`, `delivery_raw_text`). The only functional difference across the three is what happens when `result` is falsy (Netshoes maps to `BLOCKED`, the others to `TEMPORARY_FAILURE`) and the log tag. This isn't a correctness bug today, but it's the same "fix one, forget the other two" risk as WR-02 — e.g. CR-01's sibling bug in `MercadoLivreEngine` would have been easier to reason about, and a future 4th marketplace shipping provider is highly likely to inherit any latent bug that isn't shared.
**Fix:** Extract a shared helper in `base.py`, e.g. `async def calculate_via_engine(engine, product, zipcode, brand, *, empty_result_state) -> ShippingCalculation`, parameterized by the state to use on a falsy engine result, and have all three thin providers call it.

### WR-05: `apply_shipping_calculation` and the shipping providers disagree on the free-shipping predicate

**File:** `backend/services/shipping/base.py:109-113` vs `backend/services/shipping/amazon.py:89`, `mercado_livre.py:82`, `netshoes.py:86`
**Issue:** The providers build `ShippingInfo(..., is_free_shipping=is_free or price == 0.0)`. Later, `apply_shipping_calculation` (used by `/calculate-shipping-brand`) recomputes free-ness independently as `primary.price == 0.0 or primary.is_free_shipping is True`. These two formulas are logically equivalent given how `is_free_shipping` is constructed upstream, but the duplication means a future change to one predicate (e.g. adding a tolerance for near-zero float prices) must be mirrored in the other or the two code paths will silently diverge on edge cases like `price=None` combined with `is_free=True` (both formulas currently treat this as free, but for different reasons — `is_free` for the provider-computed flag, `is_free_shipping is True` for the reconstructed check).
**Fix:** Compute `is_free_shipping` once (e.g. a `ShippingInfo.is_free` property or a shared `def is_free(...)` helper) and use it consistently in both the provider construction and `apply_shipping_calculation`.

### WR-06: `calculate_regional_matrix` recomputes `identity` once per call but doesn't guard against `cep_list` containing duplicate CEPs

**File:** `backend/services/shipping/regional_matrix.py:119-166`
**Issue:** If `cep_matrix.json` were ever edited to contain a duplicate `cep` value (operator-editable per the module docstring), the loop would call the provider (or hit cache) twice for the same `(identity, cep)` key, append two near-identical entries to `results`, and the second write to `cache[key]` would just overwrite the first — wasted provider calls and a `results` list with a duplicate region row. Today's `cep_matrix.json` has 5 distinct CEPs so this can't happen in practice, but the module explicitly documents the file as "operator-editable," so this is a latent foot-gun with no test or validation guarding it.
**Fix:** Add an assertion/validation in `load_cep_matrix()` (or at the top of `calculate_regional_matrix`) that CEPs are unique, e.g. `assert len({r["cep"] for r in cep_list}) == len(cep_list)`, failing fast with a clear error instead of silently duplicating work/results.

## Info

### IN-01: `_extract_pdp_price` / Amazon price regex only matches prices with a decimal point already inserted by the earlier `.replace(",", ".")`

**File:** `backend/services/engines/amazon_engine.py:254-273`
**Issue:** Not a Phase 42 change, but exercised indirectly by the new shipping flows that depend on Amazon's PDP price extraction being correct for `landed_price` math. `_price_from_tag_text` strips thousands separators and swaps `,`→`.`, then requires `\d+\.\d+` — a price with no cents (e.g. "R$ 1.299" with no `,XX` suffix) after the replace becomes `1299` (no dot) and the regex fails to match, silently dropping a valid price. Low priority since Brazilian retail prices almost always include cents, but worth a defensive fallback given `_parse_pdp_html` treats `price_full is None` as "no product" (line 159).
**Fix:** Add a fallback branch: `match = re.search(r"\d+\.\d+", raw) or re.search(r"\d+", raw)`, treating an integer match as whole reais.

### IN-02: `_fetch_shipping_options` variable name `highest_price` no longer reflects the fix suggested in CR-01, and the surrounding comments contradict each other

**File:** `backend/services/engines/mercado_livre_engine.py:799-809`
**Issue:** The three consecutive comments ("user context: assume highest...", "But if free shipping is an option...", "Actually, ML usually returns 1-2 options...") read like an unresolved internal debate left in the code, which makes intent hard to verify during review and increases the chance the "highest wins" logic (CR-01) ships unnoticed in future edits.
**Fix:** Once CR-01 is fixed, delete the exploratory comments and replace with a single sentence documenting the final decision and why (matching the `sorted_shipping_options` convention).

### IN-03: `AmazonEngine.calculate_shipping` (Tier 2, listing-level) is a permanent no-op that silently returns `None`

**File:** `backend/services/engines/amazon_engine.py:471-478`
**Issue:** Every call site that uses the Tier-2 `calculate_shipping` (as opposed to `calculate_shipping_advanced`) for Amazon — e.g. `cross_marketplace_service._enrich_pdp_and_shipping` — will always get `None` back and mark `p["_shipping_state"] = "blocked"` for Amazon products, even though Amazon is not actually anti-bot-blocked in the same sense as Netshoes; it's just unimplemented. This mislabels the marketplace state in the cross-marketplace UI ("Bloqueado (anti-bot)" badge) for a case that's really "not implemented," which could mislead an operator into thinking Amazon needs a proxy fix when the code path is intentionally stubbed.
**Fix:** Either implement Tier-2 Amazon shipping via the same `calculate_shipping_advanced` path (Playwright), or have `_enrich_pdp_and_shipping` distinguish "engine returned None because unsupported" from "engine returned None because blocked" via a sentinel/exception rather than conflating both into `_shipping_state = "blocked"`.

### IN-04: `NLP_MODEL_PENALTY_*` / relevance settings docstrings reference Phase 23 decisions inline in `config.py`, mixed with Phase 42 additions — no functional issue, but growing config-file cohesion smell

**File:** `backend/config.py:277-333` vs `backend/config.py:155-163`
**Issue:** Not a bug, but noting for maintainability: `config.py` is accumulating phase-specific historical rationale as inline comments/descriptions (Phase 23, Phase 42, Phase 44 markers). This is useful today but as more phases land, `Settings`/`RelevanceSettings` will keep growing as an undifferentiated bag of flags with embedded changelog prose. Consider, in a future phase, splitting settings into logically grouped modules (e.g. `config/shipping.py`, `config/relevance.py`) once the single-file docstring history becomes unwieldy.
**Fix:** No action required for Phase 42; flagged for awareness only.

---

_Reviewed: 2026-07-02T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
