# Milestones

## v2.0 Cobertura de Concorrentes & Confiabilidade (Shipped: 2026-06-23)

**Phases completed:** 4 phases, 13 plans, 6 tasks

**Key accomplishments:**

- RED test scaffolds for COMP-02 (detect_engine unknown/Wake) and MGMT-01 (list_brands active_only + set_active) using asyncio.run + unittest.mock aiohttp context managers.
- Hardened `detect_engine` with `fbitsstatic.net` Wake probe before VTEX HTML check, `return "unknown"` fallback for all inconclusive probes, and `create_brand` auto-deactivates unknown-engine brands via `set_active`.
- Service-layer chokepoint `list_brands(active_only=False)` + idempotent `set_active` flag setter with dual-backend persistence via existing `_save`.
- PATCH endpoint for idempotent brand activation/deactivation wired to `brand_service.set_active`, plus `active_only=True` chokepoint adoption at all five consumer call sites.
- 1. [Scope] Tasks 1 and 2 implemented in a single write
- POST /search now persists type='search' history with inner-list results and raw query using create_job/update_job, mirroring the cross-marketplace pattern with two mandatory deviations (Resolution A).
- Wire `PATCH /brands/{key}/active` endpoint to SettingsPage via new `ApiClient.setBrandActive`, adding per-row Power toggle and "Inativa" badge with opacity dimming, guarded off for virtual marketplaces.
- Task 1 — App-level preloadedJobId state + handleReopen + renderTab propagation (SC#2)
- Added 10-line useEffect cleanup to CategoryPage that nulls onmessage before closing wsRef.current on unmount, preventing setState calls in unmounted component when user switches tabs mid-scrape.
- SearchPage e CrossMarketplacePage migradas de useState local para zustand module-scoped store; estado de busca sobrevive ao unmount; build verde. UAT comportamental (4 critérios + regressão D-11) PENDENTE — deferred pelo usuário.

---
