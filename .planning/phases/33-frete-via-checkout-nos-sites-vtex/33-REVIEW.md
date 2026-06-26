---
phase: 33-frete-via-checkout-nos-sites-vtex
reviewed: 2026-06-26T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - backend/services/vtex_shipping.py
  - backend/tests/test_vtex_shipping.py
  - backend/core/models.py
  - backend/tests/test_search_shipping_contract.py
  - backend/services/vtex_api_scraper.py
  - backend/api/routes_search.py
  - backend/tests/test_vtex_api_client.py
  - frontend/src/api/client.ts
  - frontend/src/stores/searchStore.ts
  - frontend/src/App.tsx
  - frontend/src/App.css
findings:
  critical: 2
  warning: 3
  info: 3
  total: 8
status: issues_found
---

# Phase 33: Code Review Report

**Reviewed:** 2026-06-26
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Phase 33 wired VTEX checkout shipping simulation (`_fetch_shipping`), added `shipping_options` to the search models, exposed a `GET /search/config` endpoint, and plumbed the results through to the frontend. The core shipping parsing module (`vtex_shipping.py`) and the new test suites are well-constructed. The main problems are: a data-model semantic inversion that propagates a wrong price across the entire system (backend → frontend), an off-by-one scope bug inside `_fetch_shipping` that silently reads only one logistics carrier even when a product ships from multiple carriers, and two quality issues around the price display formula in the frontend.

---

## Critical Issues

### CR-01: `price_discount` field meaning is inverted — frontend displays the wrong "original price"

**File:** `backend/services/vtex_api_scraper.py:347-348`, `backend/services/vtex_api_scraper.py:862-863`, `frontend/src/App.tsx:1420`, `frontend/src/App.tsx:2390`

**Issue:** In both `parse_product_dict` (line 348) and the `search()` method (line 863), `price_discount` is set to `ListPrice - Price` (the *discount amount*, i.e., how much was taken off). But the model field `price_discount` in `SearchProductResult` (and `RawProductBronze`) is documented and used by the frontend as the *discounted/sale price*, not the amount saved.

The frontend renders the original price as `price_full + price_discount` (App.tsx line 1420: `R$ {(p.price_full + p.price_discount).toFixed(2)}`). When `price_discount` means "discount amount" this formula accidentally reconstructs the original `ListPrice` correctly only by coincidence — but the discount badge formula on line 1410 reads:

```
Math.round((p.price_discount / (p.price_full + p.price_discount)) * 100)
```

This divides the discount amount by the reconstructed list price to get a percentage, which is arithmetically correct for that formula. However, the `SearchProductResult` model docstring says nothing explicit about which convention holds, and `RawProductBronze` also defines `price_discount: Optional[float]` without clarifying the convention. The `model_validator` `calculate_landed_price` uses `price_discount` as:

```python
base_price = self.price_discount if self.price_discount is not None else self.price_full
```

This treats `price_discount` as a *sale price* — the validator selects it as `base_price` directly, not as an offset. If `price_discount = 100.0` (the discount amount, e.g. R$300 → R$200 saving), then `landed_price` is computed as `R$100.00 + shipping`, which is wildly wrong.

Concretely: a product with `Price=199.90` and `ListPrice=299.90` would produce `price_full=199.90`, `price_discount=100.00` (the difference). The `model_validator` would then set `landed_price = 100.00 + shipping_price`, understating the true cost by R$99.90. Every `landed_price` in search results is wrong for discounted products.

**Fix:** Choose one convention and apply it consistently. The safest fix given the model validator semantics ("base_price = price_discount if present") is to store the *sale price* in `price_discount`:

```python
# vtex_api_scraper.py — search() method (line ~860)
price_full = offer.get("Price", 0.0)
lp = offer.get("ListPrice", 0.0)
if lp > price_full:
    price_discount = price_full         # sale price
    price_full = lp                      # original price (list)
```

And update the frontend badge formula accordingly (the formula already handles this convention correctly: `price_discount / (price_full + price_discount)` is wrong for "sale price" semantics — it should be `(price_full - price_discount) / price_full`).

Alternatively, if "discount amount" is the intended convention, fix `calculate_landed_price` in both models to use `price_full - (price_discount or 0)` as `base_price`, and update the frontend to show `price_full - price_discount` as the sale price and `price_full` as the strikethrough price.

---

### CR-02: `_fetch_shipping` only reads SLAs from `logisticsInfo[0]` — multi-item checkouts silently drop carriers

**File:** `backend/services/vtex_api_scraper.py:472`

**Issue:**

```python
logistics = data.get("logisticsInfo", [])
all_slas = logistics[0].get("slas", []) if logistics else []
```

The VTEX checkout simulation endpoint returns one `logisticsInfo` entry *per item* in the request. The code always sends exactly one item (line 455-458), so `logistics[0]` is the correct entry for that SKU — but `logisticsInfo[0].get("slas", [])` can still return an empty list if the VTEX response omits the `"slas"` key entirely (it is not guaranteed to be present when the carrier list is empty for other reasons). More importantly, this hard-index means if a future caller ever passes multiple items, all carriers for items 1..N are silently discarded.

Additionally, there is no guard for the case where `logisticsInfo` is present but its first entry is `None` or not a dict, which would raise `AttributeError` on `.get()`.

**Fix:**

```python
logistics = data.get("logisticsInfo") or []
# Flatten SLAs across all logisticsInfo entries (future-proof for multi-item)
all_slas: list = []
for entry in logistics:
    if isinstance(entry, dict):
        all_slas.extend(entry.get("slas") or [])
options = filter_and_sort_slas(all_slas)
```

---

## Warnings

### WR-01: `_fetch_shipping` timeout argument is 5 seconds with no `aiohttp.ClientTimeout` wrapper — `timeout` kwarg is silently ignored

**File:** `backend/services/vtex_api_scraper.py:468`

**Issue:**

```python
async with self.session.post(url, json=payload, timeout=5) as resp:
```

`aiohttp.ClientSession.post()` accepts a `timeout` parameter, but only if it is an `aiohttp.ClientTimeout` instance. When a bare integer `5` is passed, `aiohttp` raises a `ValueError` at construction time (aiohttp >= 3.8). In earlier versions the argument was silently ignored and the session-level timeout applied instead. This means the bounded retry logic (D-15) depends on a timeout that may not actually fire within 5 seconds — the whole-session timeout from `search()` (15s, line 913) would apply instead, making two slow attempts take up to 30 seconds before yielding `temporary_failure`.

**Fix:**

```python
from aiohttp import ClientTimeout
...
async with self.session.post(
    url, json=payload, timeout=ClientTimeout(total=5)
) as resp:
```

---

### WR-02: `search()` creates a new `aiohttp.ClientSession` that shadows `self.session`, then leaves `self.session` pointing to a closed session after returning

**File:** `backend/services/vtex_api_scraper.py:913-926`

**Issue:**

```python
async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
    self.session = session
    products, last_error = await _run_paging(category_path)
    ...
```

`search()` unconditionally overwrites `self.session` with a locally-scoped session, then exits the `async with` block which closes that session. After `search()` returns, `self.session` points to the now-closed session object. Any subsequent call on the same `VtexApiClient` instance (e.g., `get_product_by_url`) will use a closed session and raise `aiohttp.ClientConnectorError` or `RuntimeError: Session is closed`.

Additionally, if the caller already injected a session via the constructor (`VtexApiClient(brand_name=..., session=existing_session)`), that injected session is silently thrown away — the `_owns_session=False` guard in `__aenter__`/`__aexit__` is not respected in `search()`.

**Fix:** Move the `ClientSession` creation out of `search()` or use the async context manager pattern (`async with VtexApiClient(...) as client:`). The simplest fix is:

```python
# In search(): use self.session if already set, else create a local one
if self.session is None:
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
        self.session = session
        products, last_error = await _run_paging(...)
        # ... fallback ...
    self.session = None  # clear after use
else:
    products, last_error = await _run_paging(...)
```

---

### WR-03: `filter_and_sort_slas` does not protect against `pickupStoreInfo` being non-dict (e.g., `None` or a non-dict value from a malformed payload)

**File:** `backend/services/vtex_shipping.py:125`

**Issue:**

```python
pickup_info = sla.get("pickupStoreInfo", {}) or {}
```

The `or {}` coercion handles `None` and empty-dict correctly, but if `pickupStoreInfo` is a non-dict truthy value (e.g., a list, a string, or an unexpected nested object from a malformed VTEX response), `pickup_info.get("isPickupStore")` will raise `AttributeError` because non-dict objects do not have `.get()`. This falls outside the general `try/except` block — the exception would propagate out of `filter_and_sort_slas` uncaught, causing the entire SLA list to be lost for a product.

**Fix:**

```python
raw_pickup = sla.get("pickupStoreInfo")
pickup_info = raw_pickup if isinstance(raw_pickup, dict) else {}
```

---

## Info

### IN-01: `test_vtex_api_client.py` — `_FakeSession.post()` does not implement `async with` protocol; raises `AttributeError` on second attempt when a sequence item is a `_FakeResp`

**File:** `backend/tests/test_vtex_api_client.py:199-205`

**Issue:** `_FakeSession.post()` returns a `_FakeResp` object directly (not via `async with`). `_FakeResp` *is* an async context manager (`__aenter__`/`__aexit__`), so the production code `async with self.session.post(...) as resp:` works. However, when `_FakeSession` is constructed with a sequence and the sequence element is a raw `BaseException`, it raises immediately inside `post()` — this is the intended raise path. But the code comment says "Elementos que são exceções são levantados; demais são retornados" — it is correct for simple items. The issue is that `_CapturingSession.post()` in test `test_payload_carries_resolved_seller_not_hardcoded_1` returns a `_FakeResp` but is not an async context manager itself (it returns the object directly without wrapping). This works because `_FakeResp.__aenter__` returns `self`. However `_CapturingSession` has no `async with` guard of its own; relying on protocol duck-typing silently makes the test fragile if `post()` is ever called outside of `async with`. This is a minor test robustness issue, not a production bug.

**Fix:** Either document the contract explicitly or make `_FakeSession.post()` return a proper context manager wrapper that is consistent with `aiohttp`'s `_RequestContextManager`.

---

### IN-02: `routes_search.py` — `GET /search` endpoint does not record to search history

**File:** `backend/api/routes_search.py:230-258`

**Issue:** The `POST /search` endpoint records a history entry via `search_history_service.create_job()` and `update_job()`. The `GET /search` endpoint (convenience alias, lines 230-258) performs the same search but never records any history. Users who use the GET endpoint (e.g., from Swagger UI) will not see those searches in the history list. If both endpoints are considered equivalent, the GET endpoint should also record history, or its description should explicitly note it is history-less.

**Fix:** Either add the same history recording pattern as `POST /search` to the GET endpoint, or add a note in the endpoint description: `"Este endpoint de conveniência não registra no histórico de buscas."`.

---

### IN-03: Commented-out code block in `scrape_category_paged` (`vtex_api_scraper.py:627-634`)

**File:** `backend/services/vtex_api_scraper.py:627-634`

**Issue:** A multi-line block is commented out in production code:

```python
# Nao enviamos mais o total de produtos para evitar confusao de paridade
# total_produtos = int(res_header.split("/")[-1])
# log({
#     "type": "brand_stats",
#     "total_links": total_produtos,
#     "message": f"Total de produtos na categoria: {total_produtos}"
# })
```

The `total_produtos` and `stats_emitido` variables are still declared and assigned but never read meaningfully. Dead code and orphaned variables should be removed.

**Fix:** Remove the commented-out block, the `total_produtos = None` declaration (line 589), and the `stats_emitido = True` assignment (line 634). If the `stats_emitido` guard is still needed for the outer `if`, replace with a simpler `headers_read = True`.

---

_Reviewed: 2026-06-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
