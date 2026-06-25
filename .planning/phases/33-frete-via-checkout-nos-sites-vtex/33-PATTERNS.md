# Phase 33: Frete via Checkout nos Sites VTEX - Pattern Map

**Mapped:** 2026-06-25
**Files analyzed:** 10 (3 new, 7 modified)
**Analogs found:** 10 / 10

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/services/vtex_shipping.py` (NEW) | service (pure helper) | transform | inline parsing in `vtex_api_scraper.py:444-465`; pure-helper module style of `services/vtex_parsing.py` | role-match |
| `backend/core/models.py` (EDIT) | model | transform | existing `ShippingInfo` / `SearchProductResult` in same file | exact |
| `backend/services/vtex_api_scraper.py` (EDIT) | service | request-response (+ retry) | `_fetch_shipping` (self, 431-470) + retry loop in `_request_json` (228-282) | exact |
| `backend/api/routes_search.py` (EDIT) | route | request-response | GET `search_products_get` (214-248) for config endpoint; POST serialize at 190-204 | exact |
| `backend/tests/test_vtex_shipping.py` (NEW) | test | n/a | pure-fn assertions in `test_vtex_api_client.py:158-194` | role-match |
| `backend/tests/test_search_shipping_contract.py` (NEW) | test | n/a | `_FakeResp`/`_FakeSession` in `test_vtex_api_client.py:128-154` | exact |
| `frontend/src/api/client.ts` (EDIT) | client | request-response | `static search` (83-88) | exact |
| `frontend/src/stores/searchStore.ts` (EDIT) | store | event-driven | `useSearchStore` slice + `setSearch` (72-99) | exact |
| `frontend/src/App.tsx` (EDIT) | component | request-response | single `p.shipping` render (1349-1357); CEP input (1204-1223) | exact |
| `frontend/src/App.css` (EDIT) | config (styles) | n/a | existing `.product-meta` classes | role-match |

## Pattern Assignments

### `backend/services/vtex_shipping.py` (NEW — pure helpers, transform)

**Analog:** the inline SLA logic in `vtex_api_scraper.py:444-465` to be extracted, plus the pure-module convention of `backend/services/vtex_parsing.py` (module of stateless functions, no `self`, no I/O).

**Current inline logic to lift into pure functions** (`vtex_api_scraper.py:444-465`):
```python
slas = logisticsInfo[0].get("slas", [])
if slas:
    cheapest = min(slas, key=lambda x: x.get("price", 0))   # PITFALL: no pickup filter before min()
    price = cheapest.get("price", 0) / 100                  # cents -> reais
    estimate = cheapest.get("shippingEstimate", "")
    m = re.search(r'\d+', estimate)                         # PITFALL: drops the unit (bd/d/h/m)
    if m:
        delivery_days = int(m.group())
    status = "Grátis" if price == 0 else "Disponível"        # PITFALL: price==0 vs price is None
```

**Build these deterministic, HTTP-free helpers (names = planner discretion):**
- `parse_estimate(shippingEstimate) -> (value, unit, sort_seconds, display_text)` — keep unit; map `bd`→"Até X dias úteis", `d`→"Até X dias", `h`→"Até X horas", `m`→"Até X minutos" (RESEARCH §Official VTEX Contract, units `m/h/bd/d`).
- `filter_and_sort_slas(slas) -> List[option]` — keep only `deliveryChannel == "delivery"`; defensively drop `pickupStoreInfo.isPickupStore is True` and non-empty `pickupPointId`; sort by `price` asc then estimate-duration asc (D-10); discard malformed entries (D-16).
- `select_candidate(items) -> (sku_id, seller_id)` — pair SKU with the seller of the available offer (replaces hardcoded `seller="1"`).
- `classify_result(...) -> state` — `available` | `unavailable_for_cep` | `temporary_failure` per RESEARCH state matrix.

**Free-shipping rule (D-02 / pitfall 3):** use explicit `price is None` vs `price == 0.0`. `0.0` = Frete Grátis; `None` = não calculado. Never treat `0` as missing.

---

### `backend/core/models.py` (EDIT — model, additive)

**Analog:** existing `ShippingInfo` (13-25) and `SearchProductResult` (95-133) in the same file.

**Existing contract to preserve** (13-25, 114-118):
```python
class ShippingInfo(BaseModel):
    price: float | None = Field(default=None, ...)   # 0.0 == grátis
    status: str = Field(default="Disponível", ...)
    estimated_delivery_days: int | None = None
    raw_text: str | None = Field(default=None, ...)
# SearchProductResult:
    shipping: ShippingInfo | None = None
    is_free_shipping: bool = False
    shipping_price: Optional[float] = None
    landed_price: Optional[float] = None
```

**Additive evolution (RESEARCH Data Contract; pitfall 6/7):**
- Extend `ShippingInfo` with service identity (`name`/`service_id`) + parsed estimate metadata (unit, display text). Keep all existing fields.
- Add `shipping_options: List[ShippingInfo] = Field(default_factory=list)` to `SearchProductResult`.
- Keep `shipping` = cheapest valid option; keep `shipping_price` / `is_free_shipping` derived from that primary option (FRET-05 + export/history consumers).
- Errors / no-delivery → `shipping_options=[]` and put state in `shipping.status`.
- Do NOT remove `landed_price` or its `@model_validator calculate_landed_price` (120-133) — global removal is deferred (D-08).

**Pattern to copy:** field declaration style with `Field(default_factory=list)` (see 41-42, 111-112); the `@model_validator(mode="after")` shape at 120-133.

---

### `backend/services/vtex_api_scraper.py` (EDIT — service, request-response + bounded retry)

**Analog A — current shipping call** (`_fetch_shipping`, 431-470): the seam to expand. It must (a) build `items` with the selected `(sku_id, seller_id)` instead of hardcoded `"1"` (435), (b) call the new pure parser, (c) populate `shipping_options` + primary `shipping`, (d) absorb its own exceptions so `asyncio.gather` siblings survive (current behavior at 468-470 + caller at 821-822).

**SKU+seller selection seam** (758-810): today `sku_id = items[0].get("itemId")` (764) and a separate seller scan for price (769-779). Pair them — pass the selected seller into `_fetch_shipping`.

**Analog B — bounded retry pattern** (`_request_json`, 228-282):
```python
for attempt in range(settings.MAX_RETRIES):
    try:
        async with self.session.get(...) as resp:
            ...
            if resp.status == 429:
                wait = (attempt + 1) * 5
                await asyncio.sleep(wait)
                continue
            if resp.status >= 500:
                ...
    except ...:
        ...
```
**Apply for shipping:** exactly 2 total attempts (1 retry). Retry ONLY network/timeout + retryable HTTP (408/429/5xx). Do NOT retry a valid 200-with-no-delivery (pitfall 5). Use a short deterministic sleep (~250-500ms) that tests can patch (RESEARCH §Retry). Keep the existing `async with self.semaphore` (440) so the retry respects concurrency.

**Concurrency seam** (821-822): `await asyncio.gather(*shipping_tasks)` — keep; each `_fetch_shipping` must swallow its own errors (D-13/D-15).

---

### `backend/api/routes_search.py` (EDIT — route, request-response)

**Analog A — read-only GET route** (`search_products_get`, 214-248) for the new search-config endpoint exposing `DEFAULT_CEP`:
```python
@router.get("", response_model=ComparisonResult, summary="...", description="...")
async def search_products_get(q: str = Query(...), ...): ...
```
Copy this decorator/signature shape. New endpoint (e.g. `@router.get("/config")`) returns `{ "default_cep": settings.DEFAULT_CEP }` (config.py:128). Read-only, no secrets (RESEARCH §Security).

**Analog B — serialization** (190-204): `ComparisonResult(...)` built from `engine_factory.search_all_brands(...)`; history persists `result.model_dump(mode="json")["results"]`. `shipping_options` flows automatically via Pydantic once added to the model — verify the contract test, do not hand-serialize.

**CEP validation pattern to reuse** (67-71 / 225): `pattern=r"^\d{5}-?\d{3}$"` then `zipcode.replace("-", "")` (166, 229). Send CEP only in JSON body, never interpolated into a URL (RESEARCH §Security).

---

### `backend/tests/test_vtex_shipping.py` (NEW — pure unit tests)

**Analog:** the pure-assertion style in `test_vtex_api_client.py:158-194` (build a body dict, call, assert on numeric/status). No HTTP, no fakes needed — these test pure functions directly.

**Required cases (RESEARCH §Required deterministic):** 2 delivery + 1 free pickup → only 2 delivery; `3990`/`1990` → ordered `19.90`,`39.90`; free + paid → free first, `is_free_shipping=True`; `5bd`/`2d`/`12h`/`30m` → each unit preserved; malformed + valid → valid survives. Keep prices under the R$1,000 unit-regression threshold.

---

### `backend/tests/test_search_shipping_contract.py` (NEW — fake-session characterization)

**Analog — exact copy of the fake-session pattern** (`test_vtex_api_client.py:128-154`):
```python
class _FakeResp:
    def __init__(self, status, json_data): self.status = status; self._json = json_data
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False
    async def json(self): return self._json

class _FakeSession:
    def __init__(self, resp): self._resp = resp
    def post(self, url, json=None, timeout=None): return self._resp

def _client_with_response(status, json_data):
    client = VtexApiClient(brand_name="Aramis")
    client.session = _FakeSession(_FakeResp(status, json_data))
    return client
```
**Drive async via `asyncio.run(...)`** (no pytest-asyncio configured — see file header note + 171).

**Required cases:** request payload carries selected SKU+seller; timeout-then-success = exactly 2 calls, no error state; timeout twice = product kept with temporary-unavailable; 200 pickup-only = `Entrega indisponível para este CEP`, no retry; sibling isolation (one quote fails, others fine). For multi-attempt fakes, extend `_FakeSession.post` to return a sequence/raise on first call. Patch the retry sleep.

---

### `frontend/src/api/client.ts` (EDIT — client, request-response)

**Analog — static method pattern** (`static search`, 83-88):
```ts
static search(payload: { ...; zipcode?: string; include_shipping?: boolean }, signal?: AbortSignal) {
  return this.request<any>('/search', { method: 'POST', body: JSON.stringify(payload) }, signal);
}
```
**Add:** `static getSearchConfig()` → `this.request<any>('/search/config')` (mirrors `getBrands`/`getHistoryList` GET style at 42-43, 90-91). Core `request` already injects `X-API-Key` (12-17) and throws on `!response.ok` (32-34) — reuse, do not add bespoke fetch.

---

### `frontend/src/stores/searchStore.ts` (EDIT — store, event-driven)

**Analog:** `SearchSlice` + `setSearch` (15-27, 72-99). The store is intentionally module-scoped, non-persistent (D-06 — comment at 66-71). CEP already lives at `search.zipcode` (19, 77).

**Add (pitfall 8 / D-04/D-06):** a one-time init flag (e.g. `cepInitialized: boolean`) so a late `getSearchConfig` response never overwrites a user-edited CEP. Initialize `zipcode` from config exactly once; subsequent user edits via `setSearch` win. Follow the existing `set((s) => ({ search: { ...s.search, ...patch } }))` immutable-patch shape (95-96).

---

### `frontend/src/App.tsx` (EDIT — component, request-response)

**Analog A — current single-shipping render** (1349-1357) → expand to a list:
```tsx
{p.shipping && (
  <div className="product-meta" style={{ ... color: p.shipping.status === 'Grátis' ? '#10b981' : 'inherit' }}>
    <Package size={14} />
    <span>{p.shipping.status === 'Grátis' ? 'Frete Grátis' : (p.shipping.price ? `Frete: R$ ${p.shipping.price.toFixed(2)}` : p.shipping.status)}
          {p.shipping.estimated_delivery_days ? ` (${p.shipping.estimated_delivery_days} dias)` : ''}</span>
  </div>
)}
```
**Evolve to:** map over `p.shipping_options` in price order; for each show price + the parsed display text ("Até X dias úteis", not generic "X dias"). Free option first with "Frete Grátis" highlight (D-11/D-12). **Legacy fallback (pitfall 6 / case 9):** if `shipping_options` absent/empty, fall back to the legacy single `p.shipping` block above so old history renders. Keep product price (1339-1343) and freight visually separate — no landed-price sum on this surface (D-08).

**Analog B — CEP input + submit gating** (1204-1223, 1155-1156): masking already produces `00000-000`. Today shipping is sent only when 8 digits (1155-1156). **Change (D-04/D-05):** field starts pre-filled from `getSearchConfig` (visible, editable); if user edits to an invalid/incomplete CEP, BLOCK submit/export with a clear error rather than silently searching without freight or resetting the default. With a valid CEP, always send `include_shipping` (D-07).

---

### `frontend/src/App.css` (EDIT — styles)

**Analog:** existing `.product-meta` / `.price-*` classes used at App.tsx:1345-1357. Add classes for the options list (free-shipping highlight, stacked rows) following the existing color tokens (`#10b981` for free, `var(--text-muted)`, `var(--border)`).

---

## Shared Patterns

### Cents → Reais conversion (D-02)
**Source:** `vtex_api_scraper.py:449` (`price / 100`)
**Apply to:** the new pure parser. Free = `0.0`; not-calculated = `None`. Use `is None` checks, never truthiness.

### Bounded retry, semaphore-bound
**Source:** `vtex_api_scraper.py:228-282` (`_request_json` loop, `asyncio.sleep`, `self.semaphore` at 440)
**Apply to:** `_fetch_shipping`. 2 total attempts, retryable transport only, patchable sleep, inside the semaphore.

### Fake async session (zero-network tests)
**Source:** `test_vtex_api_client.py:128-154` (`_FakeResp`/`_FakeSession`/`_client_with_response`), driven by `asyncio.run`
**Apply to:** both new test files (extend for multi-call/raise sequences).

### CEP validation + JSON-only transport
**Source:** `routes_search.py:67-71` (`pattern=r"^\d{5}-?\d{3}$"`), `:166`/`:229` (`replace("-", "")`)
**Apply to:** new config/search paths. Never interpolate CEP into URLs; never log full CEP/payload (RESEARCH §Security).

### Additive Pydantic field + model_validator
**Source:** `models.py:41-42` (`default_factory`), `:120-133` (`@model_validator(mode="after")`)
**Apply to:** `shipping_options` and any derived primary fields. Keep `landed_price` validator intact.

### Frontend immutable store patch + identity guard
**Source:** `searchStore.ts:95-96` (`{ ...s.search, ...patch }`), `:120`/`:129` (stale-request guard)
**Apply to:** CEP init flag and any new option-related state.

## No Analog Found

None. Every file maps to an existing in-repo pattern.

## Metadata

**Analog search scope:** `backend/services/`, `backend/core/`, `backend/api/`, `backend/tests/`, `frontend/src/`
**Files scanned:** vtex_api_scraper.py, models.py, routes_search.py, config.py, test_vtex_api_client.py, App.tsx, searchStore.ts, client.ts
**Pattern extraction date:** 2026-06-25
