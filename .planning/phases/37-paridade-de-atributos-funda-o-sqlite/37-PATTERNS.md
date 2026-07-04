# Phase 37: Paridade de Atributos & Fundaçao SQLite - Pattern Map

**Mapped:** 2026-07-03  
**Files analyzed:** 12  
**Analogs found:** 12 / 12

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/core/models.py` | model | request-response | `backend/core/models.py` | exact |
| `backend/services/product_contract.py` | service | transform | `backend/services/stock_summary_service.py` + `backend/services/shipping/base.py` | role-match |
| `backend/services/vtex_api_scraper.py` | engine mapper | transform | `backend/services/vtex_api_scraper.py` | exact |
| `backend/services/shopify_api_client.py` | engine mapper | transform | `backend/services/shopify_api_client.py` | exact |
| `backend/services/engines/wake_engine.py` | engine mapper | transform | `backend/services/engines/wake_engine.py` | exact |
| `backend/services/engines/sfcc_parser.py` | parser | transform | `backend/services/engines/sfcc_parser.py` | exact |
| `backend/services/engines/zara_parser.py` | parser | transform | `backend/services/engines/zara_parser.py` | exact |
| `backend/services/engines/amazon_engine.py` | engine mapper | transform | `backend/services/engines/amazon_engine.py` | exact |
| `backend/services/engines/mercado_livre_engine.py` | engine mapper | transform | `backend/services/engines/mercado_livre_engine.py` | exact |
| `backend/services/engines/netshoes_engine.py` | engine mapper | transform | `backend/services/engines/netshoes_engine.py` | exact |
| `backend/api/routes_search.py`, `backend/services/orchestrator.py`, `backend/services/orchestrator_multi.py` | export surfaces | file-I/O | same files | exact |
| `backend/tests/test_product_contract.py`, `test_phase37_engine_contract.py`, `test_export_search_contract.py` | tests | transform/request-response | `test_stock_summary_service.py`, `test_search_shipping_contract.py`, `test_vtex_api_client.py` | role-match |

## Pattern Assignments

### `backend/core/models.py`

**Analog:** `backend/core/models.py`

Use the existing additive optional-field pattern:

```python
composition: Optional[str] = None
available_colors: List[str] = Field(default_factory=list)
available_sizes: List[str] = Field(default_factory=list)
rating: Optional[float] = None
review_count: Optional[int] = None
```

**Apply to Phase 37:** add `product_code: Optional[str] = None` to `RawProductBronze` with a safe default only. Avoid renaming existing `raw_title` / `raw_description` model fields.

---

### `backend/services/product_contract.py`

**Analogs:** `backend/services/stock_summary_service.py`, `backend/services/shipping/base.py`

Use a small pure-function service with constants plus deterministic row-building. The closest house style is:

- state/value helpers in `shipping/base.py`
- pure transform helpers in `stock_summary_service.py`

**Apply to Phase 37:**

- fixed ordered tuple/list of canonical columns
- pure alias normalization over `specifications`
- pure projector from `RawProductBronze`-like dict/object to export row
- no I/O and no network

---

### Engine/Parser Files

**Analog:** each current engine/parser file itself

The codebase already prefers engine-local mapping into `RawProductBronze`-compatible dicts rather than a large centralized parser switch.

**Apply to Phase 37:**

- keep per-engine extraction local
- lift only aliasing/projection rules into the shared helper
- when a source exposes a visible commercial code or better category/composition signal, populate it in the engine/parser where it is naturally available

---

### Export Surfaces

**Analogs:** `backend/api/routes_search.py`, `backend/services/orchestrator.py`, `backend/services/orchestrator_multi.py`

Current shared pattern:

```python
df = pd.DataFrame(data)
for col in ["available_colors", "available_sizes"]:
    ...
if "specifications" in df.columns:
    specs_df = df["specifications"].apply(pd.Series)
    df = pd.concat([df.drop("specifications", axis=1), specs_df], axis=1)
```

**Apply to Phase 37:** replace this copy-pasted flattening with one shared canonical projection helper so all exports lead with the same contract columns.

---

### Tests

**Analogs:** `backend/tests/test_stock_summary_service.py`, `backend/tests/test_search_shipping_contract.py`, `backend/tests/test_vtex_api_client.py`

Use three test layers:

- pure unit tests for the canonical projector
- characterization tests for engine/parsers
- export contract tests for DataFrame column order and blanks semantics

## Shared Patterns

### Pure Projector

The preferred phase seam is a pure projector, not route-local pandas logic:

```python
row = build_canonical_product_row(product_like)
```

This keeps behavior testable without Excel I/O.

### Additive Alias Mapping

Mirror the additive philosophy already documented in project state:

```python
normalized = dict(raw_specifications)
normalized["composition"] = ...
```

Never delete or rewrite the raw key when adding a canonical alias.

### Safe Field Fallbacks

Follow current model behavior:

- `product_name` <- `raw_title`
- `product_description` <- `raw_description`
- `product_code` <- visible code only, else `None`

### No New Transport Surface

Phase 37 does not need a new endpoint, route, or UI control. Prefer internal helpers consumed by existing exports and engine mappers.

## No Analog Found

| File | Reason |
|------|--------|
| none | Every planned file has an existing house-style analog. |

## Metadata

**Analog search scope:** `backend/core`, `backend/services`, `backend/services/engines`, `backend/api`, `backend/tests`  
**Pattern extraction date:** 2026-07-03
