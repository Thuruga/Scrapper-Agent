---
phase: 38-ux-de-busca-monitoramento-quick-wins
reviewed: 2026-07-01T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - backend/core/models.py
  - backend/services/price_monitor_service.py
  - backend/tests/test_brand_active.py
  - backend/tests/test_category_monitor.py
  - backend/tests/test_price_monitor.py
  - frontend/src/App.css
  - frontend/src/App.tsx
findings:
  critical: 2
  warning: 6
  info: 5
  total: 13
status: issues_found
---

# Phase 38: Code Review Report

**Reviewed:** 2026-07-01T00:00:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Reviewed the backend price-monitor domain (`models.py`, `price_monitor_service.py`), their test coverage, and the frontend `App.tsx`/`App.css`. The backend monitor loop is generally careful (jitter, cancellation handling, structured logging, discount-aware change detection), but there are two correctness bugs: an unbounded exception `except Exception` swallows the wrong signal for `RawProductBronze` field validation, and the `available`/`is_stock` boolean at loop start can silently coerce `None` to `False` inside `PriceHistoryEntry`, misrepresenting stock in the history. On the frontend, `App.tsx` is a very large single file (3478 lines) with duplicated logic (CEP modal, shipping calculation, add-to-monitor) repeated near-verbatim between `SearchPage` and `CrossMarketplacePage`, several `any`-typed props that erase type safety, and at least one confirmed logic bug in the monitor price/discount rendering that will show an incorrect "original price" when `last_price_discount` is present but the record predates the discount-aware history (backward compatibility gap). Test files provide decent regression coverage for the discount and dedup logic but two of the older tests in `test_price_monitor.py` re-implement stale duplicated logic instead of calling the real `_monitor_loop`, so they can pass while the production code diverges.

## Critical Issues

### CR-01: `available_colors`/`available_sizes` comparison mutates state even when `sorted()` raises on mixed/None entries

**File:** `backend/services/price_monitor_service.py:211-217`
**Issue:** `sorted(config.available_colors) != sorted(current_colors)` assumes both lists contain only comparable, non-None strings. `product.available_colors` and `product.available_sizes` come from engine-scraped data (`current_colors = product.available_colors or []`), which is not guaranteed to be homogeneous — some engines (see `sfcc_parser.py`, `wake_engine.py`) can emit `None` entries or mixed types when parsing malformed markup. If `sorted()` raises `TypeError` (comparing `None` to `str`), this exception is caught by the broad `except Exception as e` at line 260, which then sets `last_status = "error"` for what is actually a data-quality issue in a single field, silently corrupting the price monitor's exposed status while the price and other fields as computed earlier in the `try` block (e.g. `config.last_status = "ok"` at line 176) get discarded because the exception unwinds before `_save_monitors()` at line 270 is skipped for that cycle. The net effect: a monitor with a valid, changed price can flip to `"error"` status with a confusing message purely because of a `None` in a color list, hiding the real price update from the user for a full cycle.
**Fix:**
```python
def _safe_sorted(values):
    return sorted(str(v) for v in values if v is not None)

if _safe_sorted(config.available_colors) != _safe_sorted(current_colors):
    has_change = True
    config.available_colors = current_colors

if _safe_sorted(config.available_sizes) != _safe_sorted(current_sizes):
    has_change = True
    config.available_sizes = current_sizes
```

### CR-02: Frontend monitor card shows a wrong "original price" strikethrough for legacy records once `last_price_discount` becomes stale/non-zero after a price rollback

**File:** `frontend/src/App.tsx:423-431`
**Issue:**
```tsx
{m.last_price_discount && m.last_price_discount > 0 ? (
  <span className="price-original" ...>
    R$ {(m.last_price + m.last_price_discount).toFixed(2)}
  </span>
) : null}
<div className="monitor-price-value">R$ {m.last_price.toFixed(2)}</div>
```
This assumes `last_price_discount` is always in sync with `last_price` (i.e., always represents the *current* discount delta on the *current* price). However, `price_monitor_service.py` (`_monitor_loop`, lines 182-186, 207-208) only updates `last_price_discount` when a **change** is detected (`has_change`). If a promo ends (discount becomes `0`/`None`) at the same cycle the underlying `price_full` also happens to be identical to a previously-discounted price (e.g., promo price becomes the new list price — a common retail pattern), `has_change` at the discount check (`config.last_price_discount != current_discount`) will still be true and correctly clear the discount. But if the monitor's persisted JSON on disk (`price_monitors.json`) was created/migrated before the `last_price_discount` field existed (the field is documented as "Phase 33 additive" for `ShippingInfo`, and this project has multiple backward-compat migration comments elsewhere), a record loaded via `PriceMonitorConfig(**config_dict)` in `load_monitors()` defaults `last_price_discount` to `None` and only ever gets a stale value once a discount actually reappears — at which point the arithmetic `last_price + last_price_discount` is correct. The actual bug is a UI data trust issue, not an arithmetic one: **there is no defensive check that `m.last_price_discount <= m.last_price`** (i.e., that the computed "original price" is sane). A malformed or negative discount value (which can occur if an engine returns a `price_discount` larger than expected due to a scraping glitch, since `price_monitor_service.py` line 182-186 only guards `> 0`, not an upper bound) will render a strikethrough price that is nonsensical without any client-side sanity check, misleading whoever is monitoring competitor prices — the core purpose of this feature.
**Fix:** Add a sanity bound before rendering the derived original price, and treat clearly wrong deltas as "no discount" rather than rendering garbage:
```tsx
{m.last_price_discount && m.last_price_discount > 0 && m.last_price_discount < m.last_price * 5 ? (
  <span className="price-original" ...>
    R$ {(m.last_price + m.last_price_discount).toFixed(2)}
  </span>
) : null}
```
(Bound value is illustrative — align with whatever the backend considers a sane discount ratio; alternatively validate/clamp `price_discount` server-side in the engines before it ever reaches `PriceMonitorConfig`.)

## Warnings

### WR-01: Broad `except Exception` in `_monitor_loop` conflates transport/logic errors with data-shape errors and can mask a growing class of failures

**File:** `backend/services/price_monitor_service.py:260-266`
**Issue:** The catch-all `except Exception as e` wraps everything from network failures (already handled by `product_data is None` earlier) to `ValidationError` (already handled explicitly at line 152) to any stray bug in the change-detection logic (sorting, `.lower()`, dict access). Because it stores only `str(e)[:200]`, a genuine regression in the diffing logic (like CR-01) is indistinguishable in the UI/logs from a transient scraping error. This weakens the "Bloqueado"/"Erro" signal the UI relies on to guide the user (see `App.tsx:432-441`, which branches only on `last_status in {'blocked','error'}` without surfacing *why*).
**Fix:** Narrow the except clause to expected exception types where possible, or at minimum log the exception type explicitly (`type(e).__name__`) so operators can distinguish "engine timeout" from "code bug in comparison logic" without reading server logs line by line:
```python
except Exception as e:
    logger.exception("Erro inesperado no monitor %s (%s): %s", job_id, config.brand, e)
    config.last_status = "error"
    config.last_error = f"{type(e).__name__}: {str(e)[:200]}"
```

### WR-02: `load_monitors()` reconstructs `PriceMonitorConfig` from disk without validating; a single malformed entry aborts loading of *all* monitors

**File:** `backend/services/price_monitor_service.py:29-40`
**Issue:** The `for job_id, config_dict in data.items(): self.monitors[job_id] = PriceMonitorConfig(**config_dict)` loop is wrapped in one `try/except` around the entire loop. If any single monitor's JSON is malformed (e.g., a `ValidationError` from Pydantic on one bad record — plausible given the file is hand-edited/migrated per `git status`, which shows `backend/data/price_monitors.json` as modified), the exception aborts the whole `for` loop, and **no monitors load at all**, including ones with perfectly valid data and active background tasks that should have resumed. This is a silent full-service degradation on next restart triggered by a single corrupt record.
**Fix:**
```python
def load_monitors(self):
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Erro ao ler arquivo de monitores do disco: {e}")
            return
        for job_id, config_dict in data.items():
            try:
                self.monitors[job_id] = PriceMonitorConfig(**config_dict)
                if self.monitors[job_id].active:
                    self.tasks[job_id] = asyncio.create_task(self._monitor_loop(job_id))
            except Exception as e:
                logger.error(f"Erro ao carregar monitor {job_id}: {e}")
```

### WR-03: `RawProductBronze.image_url_must_be_present` validator rejects missing images even though `_monitor_loop` explicitly strips `image_url` to work around this — fragile coupling

**File:** `backend/core/models.py:158-163`, `backend/services/price_monitor_service.py:146-149`
**Issue:** `RawProductBronze` enforces `image_url` as mandatory via a `field_validator` that raises `ValueError` for `None`/empty/`"None"`. `price_monitor_service.py` works around this by manually popping `image_url` from the payload dict before validation (with an explanatory comment), because the monitor's PDP scrape may legitimately lack an image. This is a correct workaround today, but it is a landmine for any *other* future caller of `RawProductBronze.model_validate` (e.g., category monitor scans, bulk scrape ingestion) that doesn't know to replicate this same pop — they will get spurious `ValidationError`s any time an image is missing, and the failure mode (silently dropped product / swallowed exception, depending on the caller) is easy to miss. The validator's "always required" contract has effectively already been falsified by one legitimate use case.
**Fix:** Either loosen `image_url` to `Optional[str]` on the model (removing the hard requirement, since it is not universally true) and enforce "image required" only at the ingestion boundaries that actually need it (e.g., a stricter `CatalogProductBronze` subtype used for bulk scraping), or centralize the "sanitize missing image" step inside a shared helper/model validator (`mode="before"`) so every caller gets the same tolerant behavior instead of relying on call-site knowledge.

### WR-04: `test_price_monitor_recording_change` and `test_price_monitor_no_change` re-implement the change-detection logic inline instead of exercising `_monitor_loop`

**File:** `backend/tests/test_price_monitor.py:8-100`
**Issue:** These two tests manually duplicate the "if config.last_price != product.price_full: append history" logic inline in the test body rather than calling `service._monitor_loop(job_id)` (as the later tests in the same file correctly do, e.g. `test_monitor_uses_get_pdp_product_not_get_product_details`). Because the real `_monitor_loop` has since evolved to include discount-aware comparison, color/size diffing, and the `get_pdp_product` path (not `get_product_details`, which these two tests still mock), these two tests exercise dead/stale logic that no longer matches production behavior. They will keep passing even if the real `_monitor_loop` regresses on basic price-change detection, giving false confidence.
**Fix:** Rewrite both tests to call `await service._monitor_loop(job_id)` with `get_pdp_product` mocked and `asyncio.sleep` patched to stop after one iteration, following the pattern already established by `test_monitor_uses_get_pdp_product_not_get_product_details` later in the same file. This also removes the now-unused `get_product_details` mock path in these two tests, which is no longer representative of the real code path.

### WR-05: `domainMatchesBrand`/`normalizeDomain` duplicate CEP/shipping/add-to-monitor logic exist twice with copy-paste drift risk between `SearchPage` and `CrossMarketplacePage`

**File:** `frontend/src/App.tsx:1366-1379` (SearchPage `handleAddToMonitor`) and `frontend/src/App.tsx:2037-2050` (CrossMarketplacePage `handleAddToMonitor`); also the CEP modal JSX at `1919-1965` vs `2563-2609`
**Issue:** `handleAddToMonitor` is defined identically (same body, same toast messages) in both `SearchPage` and `CrossMarketplacePage`. The CEP-confirmation modal markup (`modal-overlay`/`modal-content` with CEP input, error rendering, confirm/cancel buttons) is also duplicated nearly verbatim between the two pages, differing only in which confirm handler (`confirmCep` vs `confirmCepCross`) is wired up. This is not a functional bug today, but any future fix to one copy (e.g., escape-key-to-close, focus trap, a11y improvement, or a wording change) is likely to be applied to only one of the two call sites, silently reintroducing the same defect in the other page — this has already nearly happened once, since the CEP modal in `SearchPage` supports `Enter`-to-confirm (`onKeyDown` at line 1951) with the same pattern duplicated at line 2595, but there's no shared component enforcing that parity.
**Fix:** Extract a shared `useAddToMonitor()` hook and a shared `<CepModal open onConfirm onClose value onChange error inputRef />` component used by both pages, eliminating the duplicated JSX/logic and making future fixes apply uniformly.

### WR-06: `App.tsx` mixes `any` typing pervasively across props/state (`brands: any[]`, `results: any`, `item: any`, etc.), eliminating compile-time safety for a file this large

**File:** `frontend/src/App.tsx` — pervasive, e.g. lines 217, 491, 1023, 1218, 1970-1971, 2729
**Issue:** Nearly every component prop and most local state in this 3478-line file is typed `any` (the file even opens with `/* eslint-disable @typescript-eslint/no-explicit-any */` at line 1, disabling the lint rule wholesale rather than fixing individual violations). This means TypeScript provides no protection against the exact class of bug found in CR-02 (accessing `.last_price_discount` on a possibly-`undefined` shape) or typos in property access (e.g., `product.comments` vs `product.review_comments`, both of which are defensively checked at runtime in `productReviewComments` at line 2714-2718 — a tell that the shape is not trusted even by the code that consumes it). For a file of this size and complexity, blanket `any` usage substantially raises the maintenance cost of every future change.
**Fix:** At minimum, define shared interfaces for `Brand`, `Monitor`, `SearchResult`, `CrossMarketplaceItem` (many of these already have implicit shapes documented in `backend/core/models.py` — e.g. `SearchProductResult`, `PriceMonitorConfig`) and progressively replace `any` with these types, removing the file-wide eslint-disable once violations are addressed.

## Info

### IN-01: `App.tsx` is a single 3478-line file containing 10+ page components, which is difficult to navigate and review

**File:** `frontend/src/App.tsx`
**Issue:** `MonitorPage`, `CategoryPage`, `HistoryList`, `BannersPage`, `SearchPage`, `CrossMarketplacePage`, `SettingsPage`, `MonitoredCategoriesPage`, plus several shared components (`SidebarItem`, `GlassCard`, `StatusBanner`, `PriceChart`, `ProtectedBannerImage`) all live in one file.
**Fix:** Split into per-page files under `frontend/src/pages/` and per-component files under `frontend/src/components/`, keeping `App.tsx` as the router/layout shell only. Out of scope for this phase's "quick wins" framing, but worth tracking as tech debt given the file's growth trajectory (2555 lines added in this diff alone).

### IN-02: Magic numbers for polling/attempt limits are hardcoded without a single source of truth comment explaining the trade-off

**File:** `frontend/src/App.tsx:65-66`
**Issue:** `AUTO_SWEEP_POLL_MS = 5000` and `AUTO_SWEEP_MAX_ATTEMPTS = 20` (giving a 100s timeout) are reasonable but undocumented constants — no comment ties these values to a UX requirement (e.g., "typical scan takes under 60s, so 100s gives headroom"). A future change to typical scan duration could silently break the auto-sweep UX without anyone noticing why.
**Fix:** Add a one-line comment justifying the timeout budget, e.g. `// 20 * 5s = 100s ceiling — covers p95 scan duration with headroom (see PHASE-38 UX-08 notes)`.

### IN-03: `stockDepthDisplayValue`, `reviewCommentDisplayText`, and similar helper functions duplicate `?? '-'` / fallback-chain patterns without shared typing

**File:** `frontend/src/App.tsx:2688-2727`
**Issue:** These are small, correct helpers, but they take `product: any` / `comment: any` and manually probe multiple possible field names at runtime (`comment.title || comment.text || ...`), which suggests the underlying API contract for `review_comments` is not fully settled/typed. This is consistent with WR-06 but called out separately since it is a good candidate for locking down a typed `ReviewComment` interface mirroring the backend's `ReviewComment` Pydantic model (`backend/core/models.py:50-60`) to eliminate this runtime guessing.
**Fix:** Import/mirror `ReviewComment` fields as a TS interface and use it for `productReviewComments`/`reviewCommentDisplayText` parameters.

### IN-04: `DynamicBrandCreate.clean_domain` validator does not defend against `None` explicitly documented, but the type allows falsy values only implicitly

**File:** `backend/core/models.py:343-348`
**Issue:** The `mode="before"` validator does `if v: return v.replace(...)`, else `return v` — meaning if `v` is `None` (despite `domain: str` being declared non-Optional), it silently passes `None` through instead of raising a clear validation error at this stage; Pydantic will eventually reject it, but the error message will point at the field type mismatch rather than at this validator, making debugging slightly more roundabout.
**Fix:** This is minor/cosmetic; no action required unless brand-creation validation errors become a support burden. Consider `if v is None: raise ValueError("domain é obrigatório")` for a clearer message.

### IN-05: `test_category_monitor.py`'s `_fake_bulk_scrape` closes over `products` without exhaustion/reuse guards

**File:** `backend/tests/test_category_monitor.py:18-23`
**Issue:** `_fake_bulk_scrape` returns a fresh async generator function each call, which is fine for single-use in this test file, but the helper's docstring/name doesn't make explicit that calling the returned `_gen` more than once (e.g., if `run_category_scan` were changed to retry or call `run_bulk_scrape` twice) would still work correctly since it's a generator *function*, not a generator instance — this is actually correct here, just worth a one-line comment for future maintainers who might assume otherwise given the closure captures a mutable-looking `products` parameter.
**Fix:** No functional change needed; optionally add a short comment: `# Returns a fresh generator function; safe to call multiple times, each yields the same fixed list.`

---

_Reviewed: 2026-07-01T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
