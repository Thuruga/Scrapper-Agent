# Milestones

## v4.0 Paridade de Dados, Cobertura Total de Frete & Inteligência Competitiva (Shipped: 2026-07-08)

**Phases completed:** 9 phases, 32 plans, 48 tasks

**Key accomplishments:**

- Shared canonical product/export contract added with additive alias normalization and pure contract tests.
- Engine and parser parity now flows through the shared contract, with rich sources filling real fields and sparse sources keeping blanks semantics.
- All Excel-producing Phase 37 surfaces now lead with the same canonical English column block.
- Promo-only price changes (price_full unchanged, discount added) now register in price monitor history and the `price_update` WebSocket payload via a new `last_price_discount` delta field on both monitor models.
- Added a 768px breakpoint collapsing `.grid-category` to one column, and a top-right History icon button on both search tabs that toggles the existing `HistoryList` panel with a type-scoped badge count.
- Completed the remaining Phase 38 frontend wave: SKU validation and shared row layout, automatic first category sweep feedback, and promo price rendering in the monitor list.
- Hugo Boss category resolution shipped (7 canonical mappings persisted, resolve + get_canonical green, 318 tests pass); live category monitoring deferred after live probes proved Hugo Boss is a VTEX-IO/Intelligent-Search storefront the legacy scraper can't browse.
- Zara public product+price extraction initially spiked NO-GO (spike 010: 0 products in both rounds, adversarial reprobe hit a hard 403) — **reverted to GO on 2026-07-01** after an operator live retest confirmed real extraction; `ZaraEngine`/`zara_parser.py` were built and are active (`is_active: true`, 7 category mappings, live category scan export confirmed). COMP-07 delivered.
- Pure stdlib `normalize_url` (D-08) + Wave-0 xfail scaffolds for identify (UX-03) and dedup (UX-04) giving Plans 02-03 failing test targets
- `POST /brands/identify` dry-run with SSRF validation, `detect_engine` refactored to `(engine, html)` tuple, and `infer_brand_name` using JSON-LD/OG/title/domain precedence.
- Dedup scan in `start_monitor` using `normalize_url + brand.lower()` returns `(config, status)` in `{created, already_active, reactivated}`, making "Adicionar ao monitoramento" idempotent (D-08/D-09/UX-04).
- Frontend wires UX-03/04/05 — UX-03 reworked to an identify-first monitor flow (paste product URL → auto-identify brand by domain → add to monitor, with manual-select fallback), add-to-monitor Plus button on 3 product surfaces with dedup toasts, and VIRTUAL guard removal for marketplace power toggles.
- resolve_shipping_provider now dispatches Mercado Livre/Amazon/Netshoes to thin BaseShipping adapters that wrap the proven engine scraping logic, add delivery-time extraction, and map Netshoes' Akamai block to an explicit `ShippingState.BLOCKED` instead of a fake free/zero value.
- On-demand `calculate_regional_matrix` orchestrator that resolves the shipping provider once and fetches cost/prazo for 5 curated capital CEPs (throttle + TTL cache + batch isolation), exposed via a new guarded `POST /search/calculate-shipping-matrix` route, with `/calculate-shipping-brand` now documented to cover all 3 marketplace engines.
- Cross-marketplace cards now render marketplace delivery-time and a "Bloqueado (anti-bot)" state without a fake spinner-then-nothing, plus an always-visible "Matriz Regional" button opening a 5-region "Frete por região" modal — backed by a live-verification fix that correctly parses Mercado Livre's real absolute-date delivery-time field instead of the RESEARCH.md-assumed relative shape.
- Additive Phase 44 contracts plus deterministic stock rupture math and JSON scan summary helpers
- Shared STOCK-01 rupture summaries wired into scheduled monitors and manual category scan jobs
- Controlled stock-depth probes for one persisted monitor scan product with VTEX provider isolation and explicit non-false states
- Provider-audited, page-limited review comments for persisted monitor scan products without making normal search heavy
- React monitor product modal now exposes persisted rupture summaries plus explicit one-product stock-depth and review comment actions
- JSON-backed sortiment contracts, separate seeded registry, and immutable snapshot manifest helpers for Phase 45
- Guarded sortiment snapshot execution, dedicated API routes, and an independent APScheduler job for latest-versus-previous dashboard payloads
- Dedicated sortiment dashboard page with typed client contracts, explicit baseline handling, and backend-driven delta/distribution visuals

---

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
