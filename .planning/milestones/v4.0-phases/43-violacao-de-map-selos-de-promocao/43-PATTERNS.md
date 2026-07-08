# Phase 43: Violacao de MAP & Selos de Promocao - Pattern Map

**Mapped:** 2026-07-04  
**Files analyzed:** 10  
**Analogs found:** 9 / 10 (the only new ground is the specific MAP/promotion domain, not the implementation patterns)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/services/map_rules_service.py` (NEW) | service (JSON config) | file I/O | `backend/services/brand_service.py` | exact |
| `backend/services/map_evaluator_service.py` (NEW) | service (pure business rules) | transform | `backend/services/stock_summary_service.py` | exact |
| `backend/services/promotion_parser.py` (NEW) | service (pure parser) | transform | `backend/services/engines/seller_extraction.py` | exact |
| `backend/core/models.py` (MOD) | contract | request/response/storage | itself | exact |
| `backend/api/routes_map_rules.py` (NEW) | route/controller | request-response | `backend/api/routes_brands.py` | exact |
| `backend/api/__init__.py` (MOD) | router aggregation | request-response | itself | exact |
| `backend/api/routes_search.py` (MOD) | search/export transport | request-response/export | itself | exact |
| `backend/services/product_contract.py` (MOD) | export transform | transform/export | itself | exact |
| `frontend/src/api/client.ts` (MOD) | typed client | request-response | existing brand CRUD methods | exact |
| `frontend/src/App.tsx` (MOD) | settings + result UI | request-response | `SettingsPage` + search result cards | exact |

## Pattern Assignments

### `backend/services/map_rules_service.py`

**Analog:** `backend/services/brand_service.py`

**Why:** same local JSON persistence model, same need for atomic replace, same `Path(...)/data` storage convention, same validate-on-read philosophy.

**Pattern to reuse:**
- module-level `DATA_DIR`
- `_ensure_data_dir()`
- `_load_from_json()`
- `_save_to_json()` via temp file + replace
- service singleton export

### `backend/services/promotion_parser.py`

**Analog:** `backend/services/engines/seller_extraction.py`

**Why:** pure parsing module, no network I/O, compact helper functions, conservative fallback behavior.

**Pattern to reuse:**
- tiny pure helpers (`_normalize`, regex functions)
- parser returns structured minimal payload or `None` / empty list
- no side effects or logging-heavy code

### `backend/services/map_evaluator_service.py`

**Analogs:** `backend/services/stock_summary_service.py` + `backend/core/models.py`

**Why:** deterministic business logic over product-like input with explicit states/defaults.

**Pattern to reuse:**
- product-like input accepted as dict/model
- literal state semantics instead of inference-by-absence
- pure functions that are easy to test in isolation

### `backend/api/routes_map_rules.py`

**Analog:** `backend/api/routes_brands.py`

**Why:** operator CRUD endpoints over JSON-backed configuration, light validation, simple request/response models, no background task complexity.

**Pattern to reuse:**
- local Pydantic request/response models in the route file
- call service, return serialized model
- `HTTPException` for invalid/missing rule IDs

### `backend/api/routes_search.py`

**Analogs:** itself + `routes_monitor.py`

**Why:** this file already owns search response normalization and export; additive MAP/promotion fields should be stitched in here rather than creating a parallel search route.

**Pattern to reuse:**
- helper functions for merged/export payloads
- additive request/response models with safe defaults
- export fidelity tests that monkeypatch engines and inspect the resulting DataFrame

### `frontend/src/App.tsx`

**Analogs:** `SettingsPage`, search product cards, cross-marketplace cards, existing modal patterns

**Why:** Phase 43 needs both operator management and result visualization, and those already exist as reusable UI idioms in one file.

**Pattern to reuse:**
- `GlassCard` block in `SettingsPage`
- modal overlay + content + close button structure
- lightweight badges like `badge-discount` / `monitor-badge`
- `toast.error(...)` / `toast.success(...)` for CRUD feedback

## Concrete Pattern Recommendations

### Recommendation 1: Use additive top-level result fields

Avoid nesting all MAP info under one opaque dict when the frontend and export need simple access. Prefer:

```text
promotions: []
map_violation: false
map_price_floor: null
map_rule_scope: null
map_infractor: null
```

This mirrors existing additive response fields such as `shipping_price`, `is_free_shipping`, `reviews_state`.

### Recommendation 2: Keep raw promotion harvesting separate from normalization

Engine files should ideally contribute raw strings or cheap hints; `promotion_parser.py` should own the regex/type normalization. This keeps engine edits shallow and testable.

### Recommendation 3: CRUD routes should not know precedence logic

`routes_map_rules.py` should create/update/list/delete rules only. Rule selection precedence belongs in `map_evaluator_service.py` / `map_rules_service.py`.

### Recommendation 4: Frontend management belongs in Settings, not Search

The operator edits rules occasionally; the search screen is for reading results. Reusing `SettingsPage` avoids crowding the main search flow.
