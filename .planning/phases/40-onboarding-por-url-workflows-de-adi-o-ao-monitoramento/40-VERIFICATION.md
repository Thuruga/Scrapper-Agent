---
phase: 40-onboarding-por-url-workflows-de-adi-o-ao-monitoramento
verified: 2026-06-30T12:00:00Z
status: passed
human_verification_completed: true
human_verification_completed_by: arthur.correia
human_verification_note: "All 3 UX flows were verified live by the operator during the Plan 40-05 human-verify checkpoint in the execution session — UX-04 and UX-05 approved as built; UX-03 reworked (URL-identify moved into the monitor flow, brand-add-by-URL form removed) and re-approved. The human_verification items below are retained for the record; they were satisfied at execution time."
score: 14/14
overrides_applied: 1
overrides:
  - must_have: "Pasting a URL in onboarding calls POST /brands/identify and shows a pre-filled, editable confirmation form (name + engine override) before saving (UX-03, D-01/D-02/D-03)"
    reason: "Per operator instruction during Plan 05 human-verify checkpoint, the UX-03 onboarding was redirected: the URL-identify now lives in the MonitorPage 'Monitorar Novo Produto' form (paste product URL → POST /brands/identify → resolve registered brand by normalized-domain match → addToMonitor). The standalone brand-add-by-URL GlassCard (with editable confirmation form + engine override + saveBrand) was intentionally removed from SettingsPage. The backend POST /brands/identify endpoint (engine detection + name inference + SSRF guard, dry-run, no persistence) still exists and is exercised. Domain-match auto-starts the monitor; no-match reveals a manual brand-select fallback. The confirm-with-engine-override path was removed because the operator's intent is monitoring a product, not onboarding a new brand."
    accepted_by: "arthur.correia"
    accepted_at: "2026-06-30T12:00:00Z"
human_verification:
  - test: "UX-03 (Flow 1): Open the app, go to the Monitores tab, find the 'Monitorar Novo Produto' card. Paste a product URL whose domain matches a registered brand (e.g. a product from https://www.hugoboss.com.br). Submit. Confirm: a green toast 'Adicionado ao monitoramento', a 'Marca identificada: <brand_name>' line appears, the product shows in the monitor list, and the URL field clears. Submit the same URL again. Confirm an info toast 'Produto ja esta em monitoramento' and no duplicate entry is created."
    expected: "Brand auto-resolved by domain match; monitor starts via addToMonitor; dedup toast on second submit; no 'Adicionar Marca por URL' form visible on the Marcas/Settings tab."
    why_human: "Requires a running backend + frontend; domain-match resolution and toast behavior cannot be confirmed by static grep or TypeScript compilation alone."
  - test: "UX-03 (Flow 1 fallback): Paste a product URL whose domain is NOT a registered brand. Submit. Confirm: no monitor is started, a non-blocking info message appears ('Nao identificamos uma marca cadastrada para este dominio. Selecione a marca manualmente.'), and the hidden 'Marca Concorrente' select is revealed. Pick a brand and submit. Confirm the monitor starts with the appropriate status toast."
    expected: "Manual fallback revealed on domain-miss; form is never a dead end; monitor starts when brand is manually selected."
    why_human: "Requires runtime interaction with a running app."
  - test: "UX-04 (Flow 2): Run a comparative search (SearchPage), find a product card, click the Plus 'Adicionar ao monitoramento' button. Confirm a success toast and the product appears once in price monitors. Click the same button again on the same product. Confirm an info toast 'Produto ja esta em monitoramento' and no duplicate is created. Repeat from the SKU search (CrossMarketplacePage) and from the category-monitor products modal (MonitoredCategoriesPage). All three surfaces must dedup to the same monitor list."
    expected: "Plus button visible on all 3 surfaces; status-aware toasts (already_active / reactivated / created); no duplicates."
    why_human: "Requires visual inspection of the running app across three separate pages."
  - test: "UX-05 (Flow 3): Open Settings tab. Confirm Mercado Livre, Netshoes, and Amazon each show an activate/deactivate Power toggle (previously hidden by the VIRTUAL guard). The inactive-row visual (opacity 0.55 + 'Inativa' badge) works for marketplaces too. Deactivate one marketplace, run a cross-marketplace search, confirm that marketplace is absent from results. Reactivate it, confirm it returns."
    expected: "Marketplace toggles render without a VIRTUAL guard; deactivation excludes the marketplace from the next cross-marketplace search without a server restart."
    why_human: "Requires visual interaction with the settings page and a live cross-marketplace search to confirm per-request enforcement."
---

# Phase 40: Onboarding por URL + Workflows de Adicao ao Monitoramento — Verification Report

**Phase Goal:** Um operador cadastra uma nova marca colando apenas a URL — o sistema detecta o engine e infere o nome para confirmacao — e consegue adicionar qualquer produto ao monitoramento diretamente das telas de busca comparativa, busca por SKU e monitor de categoria; os marketplaces virtuais tem toggles de ativar/desativar respeitados pelo servico de busca cruzada.

**Verified:** 2026-06-30T12:00:00Z
**Status:** passed (human verification completed live by operator at execution time)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | normalize_url drops utm_*/gclid/fbclid, keeps SKU query, lowercases host, strips www, forces https, no trailing slash | VERIFIED | `url_utils.py` stdlib-only implementation confirmed; `normalize_url('https://www.example.com/p?utm_source=x&skuId=123')` returns `'https://example.com/p?skuId=123'` (runtime confirmed); 11 unit tests in `test_url_utils.py` all pass |
| 2 | POST /brands/identify is a dry-run: returns engine + inferred_name + domain and NEVER persists to brands.json | VERIFIED | `identify_brand` in `routes_brands.py` confirmed no call to `brand_service.add_brand`; `test_identify_returns_engine_and_name` asserts `mock_add.assert_not_called()` and passes |
| 3 | detect_engine reuses home HTML for name inference (no second HTTP request, D-01) | VERIFIED | `detect_engine` returns `tuple[str, str|None]`; `identify_brand` calls `engine, home_html = await detect_engine(domain)` then passes `home_html` to `infer_brand_name` — single fetch |
| 4 | infer_brand_name resolves name by precedence JSON-LD/OG/title/domain fallback (D-01) | VERIFIED | Implementation in `routes_brands.py` confirmed; all 4 cases covered by `test_infer_brand_name` (JSON-LD, OG site_name, title, domain fallback); passes |
| 5 | engine='unknown' from identify returns a warning and does NOT block onboarding (D-03) | VERIFIED | `identify_brand` sets `warning` string when `engine == "unknown"` and returns `IdentifyResponse` without raising; not an HTTPException |
| 6 | identify rejects non-http(s) schemes and RFC1918/private-IP hosts (SSRF, ASVS V5) | VERIFIED | ipaddress-based guard in `identify_brand`; `test_identify_rejects_ssrf` passes for file://, ftp://, javascript:, 192.168.x.x, 10.0.0.1, 172.16.0.1, localhost, 127.0.0.1 |
| 7 | list_brands no longer runtime-injects marketplaces (D-10) | VERIFIED | `list_brands()` body is `return brand_service.list_brands()`; grep for `brands.append` in `routes_brands.py` returns 0 matches |
| 8 | start_monitor on an already-active normalized url+brand is a no-op returning status 'already_active' (D-09) | VERIFIED | Dedup scan at top of `start_monitor` in `price_monitor_service.py`; `test_dedup_active` passes |
| 9 | start_monitor on a stopped normalized url+brand reactivates and returns 'reactivated' (D-09) | VERIFIED | `resume_monitor` branch in dedup scan; `test_dedup_reactivate` passes |
| 10 | POST /monitor/start surfaces the status so the UI can toast the right message | VERIFIED | `routes_product.py` unpacks `config, status = await monitor_service.start_monitor(...)`; returns `{"job_id": config.job_id, "status": status, "config": config.model_dump()}` |
| 11 | mercado_livre / netshoes / amazon are real entries in brands.json with is_active (D-10) | VERIFIED | brands.json confirmed: all three entries with correct brand_keys, engines (mercadolivre/netshoes/amazon), is_active=true; `test_marketplaces_in_brands_json` passes |
| 12 | Toggling a marketplace via PATCH /brands/{key}/active is respected by cross_marketplace_service on the NEXT search (D-11) | VERIFIED | `_active_engines()` reads `brand_service.list_brands(active_only=True)` per-request; `test_inactive_marketplace_excluded` passes; `factory.search_all_brands` has no hardcoded extend |
| 13 | frontend/src/api/client.ts contains identifyBrand() and addToMonitor() client methods | VERIFIED | Both methods confirmed in `client.ts`: `identifyBrand` POSTs to `/brands/identify`; `addToMonitor` POSTs to `/monitor/start` with interval=10, duration=24; TypeScript compiles clean |
| 14 | Pasting a URL in onboarding calls POST /brands/identify and shows feedback before starting monitor (UX-03, operator-approved redirect) | PASSED (override) | Override: UX-03 redirected by operator to MonitorPage identify-first flow. `App.tsx` calls `ApiClient.identifyBrand(url)` in the "Monitorar Novo Produto" form; resolves brand by normalized-domain match; starts monitor via `addToMonitor`; shows "Marca identificada: <brand_name>" or reveals manual fallback select. No standalone brand-add-by-URL form in SettingsPage (confirmed: `ApiClient.saveBrand` has 0 call sites in App.tsx). Backend `POST /brands/identify` still exercised. Accepted by arthur.correia on 2026-06-30 |

**Score:** 14/14 truths verified (includes 1 override)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/services/url_utils.py` | normalize_url() stdlib-only dedup normalizer (D-08) | VERIFIED | Exists; `def normalize_url` present; `_TRACKING_PARAMS` frozenset; uses literal `"www."` prefix strip (not lstrip); stdlib-only (`from urllib.parse import`) |
| `backend/api/routes_brands.py` | POST /brands/identify dry-run + infer_brand_name + detect_engine tuple | VERIFIED | `identify_brand` handler, `infer_brand_name`, `IdentifyRequest`/`IdentifyResponse` models, `detect_engine` returning tuple on all paths |
| `backend/services/price_monitor_service.py` | dedup scan in start_monitor returning (config, status) | VERIFIED | Contains `already_active`, `reactivated`, `created`; `from services.url_utils import normalize_url` present |
| `backend/api/routes_product.py` | POST /monitor/start unpacks (config, status) and returns status | VERIFIED | `config, status = await monitor_service.start_monitor(...)`; response dict includes `status` |
| `backend/data/brands.json` | real marketplace brand entries with is_active | VERIFIED | mercado_livre (engine: mercadolivre), netshoes (engine: netshoes), amazon (engine: amazon) — all is_active: true |
| `backend/services/cross_marketplace_service.py` | _active_engines() per-request filter + _by_display lookup | VERIFIED | `_active_engines()` reads `list_brands(active_only=True)` per-request; `_by_display` map used in `_enrich_pdp_and_shipping`; `self.engines` removed |
| `frontend/src/api/client.ts` | identifyBrand() and addToMonitor() client methods | VERIFIED | Both static methods confirmed; correct endpoints and type signatures |
| `frontend/src/App.tsx` | handleAddToMonitor on 3 surfaces + identify-first monitor flow + marketplace toggles | VERIFIED | `handleAddToMonitor` present on SearchPage, CrossMarketplacePage, MonitoredCategoriesPage; `ApiClient.identifyBrand` called in MonitorPage; VIRTUAL guard absent; CategoryPage + BannersPage filters preserved |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `routes_brands.py::identify_brand` | `detect_engine + infer_brand_name` | `engine, home_html = await detect_engine(domain)` | WIRED | Confirmed in `identify_brand` body; tuple unpack present |
| `routes_brands.py::identify_brand` | SSRF validation | scheme + ipaddress guard before fetch | WIRED | Scheme check + `ipaddress.ip_address(host).is_private/is_loopback/is_link_local/is_reserved` |
| `price_monitor_service.py::start_monitor` | `url_utils.py::normalize_url` | `from services.url_utils import normalize_url` (lazy import inside method) | WIRED | Import at line 52; `normalize_url(config.url)` comparison at line 55 |
| `routes_product.py::start_monitoring` | `monitor_service.start_monitor` | `config, status = await monitor_service.start_monitor(...)` | WIRED | Line 31 in `routes_product.py`; response includes `status` field |
| `cross_marketplace_service.py::_fetch_all_engines` | `_active_engines()` | per-request engine selection | WIRED | `_active_engines().items()` at line 353 |
| `cross_marketplace_service.py::_enrich_pdp_and_shipping` | `self._by_display[plat]` | display-name lookup preserved | WIRED | `if plat in self._by_display: engine = self._by_display[plat]` at lines 483-484 |
| `factory.search_all_brands` | `list_brands(active_only=True)` | no hardcoded marketplace extend | WIRED | `target_brands = [b.brand_key for b in brand_service.list_brands(active_only=True)]`; grep for `extend.*mercado_livre` returns 0 matches |
| `App.tsx onboarding form` | `ApiClient.identifyBrand` | identify-first monitor flow | WIRED | `identifyBrand(url)` call in `handleSubmit` of MonitorPage; domain-match drives `addToMonitor` |
| `App.tsx product cards (3 surfaces)` | `ApiClient.addToMonitor` | `handleAddToMonitor(url, brand)` | WIRED | 3 distinct call sites (lines ~1792, ~2367, ~2859); all with `e.preventDefault() + e.stopPropagation()` |
| `App.tsx SettingsPage` | `ApiClient.setBrandActive` | Power toggle for all brands including marketplaces | WIRED | `handleToggleActive` calls `setBrandActive`; no VIRTUAL guard; renders for mercado_livre/netshoes/amazon |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `identify_brand` (routes_brands.py) | `engine, home_html` | `detect_engine(domain)` — live HTTP probe | Yes — live network fetch (or SSRF-rejected 400) | FLOWING |
| `start_monitor` (price_monitor_service.py) | `norm_url` | `normalize_url(url)` — pure stdlib function | Yes — deterministic transformation | FLOWING |
| `_active_engines()` (cross_marketplace_service.py) | `active_brands` | `brand_service.list_brands(active_only=True)` — reads `brands.json` | Yes — reads real file; `test_inactive_marketplace_excluded` verified | FLOWING |
| `App.tsx MonitorPage` | `identified.domain` | `ApiClient.identifyBrand(url)` → `POST /brands/identify` | Yes — calls real endpoint | FLOWING |
| `App.tsx handleAddToMonitor` | `result.status` | `ApiClient.addToMonitor(url, brand)` → `POST /monitor/start` | Yes — calls real endpoint with dedup status | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| normalize_url drops tracking params, keeps SKU | `python -c "from services.url_utils import normalize_url; print(normalize_url('https://www.example.com/p?utm_source=x&skuId=123'))"` | `https://example.com/p?skuId=123` | PASS |
| infer_brand_name domain fallback | `python -c "from api.routes_brands import infer_brand_name; print(infer_brand_name(None,'hugoboss.com.br'))"` | `Hugoboss` (matches test assertion: `"hugoboss" in result.lower()`) | PASS |
| brands.json marketplace keys present | `python -c "import json; d=json.load(open('data/brands.json',encoding='utf-8')); print([k in d for k in ['mercado_livre','netshoes','amazon']])"` | `[True, True, True]` | PASS |
| Full backend test suite | `cd backend && python -m pytest tests/ -q` | 347 passed in 14.24s | PASS |
| Frontend TypeScript compilation | `cd frontend && npx tsc --noEmit` | No errors (no output) | PASS |
| Frontend production build | `cd frontend && npm run build` | built in 1.10s | PASS |

---

### Probe Execution

Step 7c: SKIPPED — no `scripts/*/tests/probe-*.sh` files declared or found for Phase 40.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| UX-03 | Plans 40-01, 40-02, 40-05 | Operador cadastra uma marca colando apenas a URL; sistema detecta brand + engine e apresenta para confirmacao antes de salvar | SATISFIED (with operator-approved deviation) | Backend: `POST /brands/identify` (dry-run, SSRF-guarded, engine detection + name inference) verified. Frontend: identify-first monitor flow per operator redirect — `identifyBrand` called in MonitorPage, domain-match resolves registered brand, `addToMonitor` starts monitor; manual-select fallback when no domain match. Standalone brand-add-by-URL form intentionally removed. |
| UX-04 | Plans 40-01, 40-03, 40-05 | Operador adiciona produto ao monitoramento direto da busca comparativa, busca por SKU e monitor de categoria; criacao idempotente por url+marca | SATISFIED | Backend: dedup by `normalize_url(url) + brand.lower()` in `start_monitor`; `POST /monitor/start` returns `status` field; `test_dedup_active` and `test_dedup_reactivate` pass. Frontend: `handleAddToMonitor` on all 3 surfaces; status-aware toasts. Automated checks pass; UI behavior needs human verification. |
| UX-05 | Plans 40-04, 40-05 | Toggles de ativar/desativar disponiveis para marketplaces virtuais, respeitados pelo cross_marketplace_service | SATISFIED | Backend: marketplaces are real brands.json entries; `_active_engines()` per-request; factory no hardcoded extend; `test_inactive_marketplace_excluded` passes. Frontend: VIRTUAL guard removed from SettingsPage; Power toggle renders for all brands. UI toggle behavior needs human verification. |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | No TBD/FIXME/XXX debt markers found in any modified file. No placeholder returns. No hardcoded empty arrays used in render paths. |

---

### Human Verification Required

#### 1. UX-03 — Identify-First Monitor Flow (happy path + fallback)

**Test:** Open the app in a browser with backend running. Go to the "Monitores" tab. In the "Monitorar Novo Produto" card, paste a product URL whose domain matches a registered brand (e.g. `https://www.hugoboss.com.br/some-product`). Submit ("Identificar e Monitorar"). Then submit the same URL again.

**Expected:** First submit: green toast "Adicionado ao monitoramento", a "Marca identificada: Hugo Boss" confirmation line appears, product is in the monitor list, URL field clears. Second submit: info toast "Produto ja esta em monitoramento", no duplicate entry. The "Adicionar Marca por URL" card must NOT be present on the Marcas/Settings tab.

**Why human:** Requires a running backend and frontend; domain-match resolution, toast display, monitor list update, and dedup behavior cannot be confirmed by static analysis or compilation checks alone.

---

#### 2. UX-03 — Manual Fallback (no registered brand for domain)

**Test:** In "Monitorar Novo Produto", paste a product URL whose domain is NOT a registered brand (e.g. a URL from a non-registered site). Submit.

**Expected:** No monitor is started. A non-blocking info message appears: "Nao identificamos uma marca cadastrada para este dominio. Selecione a marca manualmente." The "Marca Concorrente" select is revealed. Operator picks a brand and submits. Monitor starts with the appropriate status toast. Form is never a dead end.

**Why human:** Requires runtime interaction; the manual fallback path is conditional on no domain match, which depends on the runtime brands.json state.

---

#### 3. UX-04 — Add-to-Monitor on All 3 Surfaces with Dedup

**Test:** Run a comparative search (SearchPage). Click the Plus "Adicionar ao monitoramento" button on a product card. Confirm a success toast and the product appears once in price monitors. Click the same button again. Confirm an info toast "Produto ja esta em monitoramento" and no duplicate. Repeat from the SKU search (CrossMarketplacePage) and from the category-monitor products modal (MonitoredCategoriesPage).

**Expected:** Plus button visible and functional on all 3 surfaces; status-aware toasts on all surfaces; all 3 surfaces dedup to the same price-monitor list.

**Why human:** Cross-surface visual inspection required; toast behavior and monitor list state require a running app.

---

#### 4. UX-05 — Marketplace Toggles and Per-Request Enforcement

**Test:** Open the Settings tab. Confirm that Mercado Livre, Netshoes, and Amazon each show a Power toggle (not hidden). The inactive-row visual (opacity 0.55 + "Inativa" badge) works for marketplaces when deactivated. Deactivate one marketplace. Run a cross-marketplace search. Confirm that marketplace is absent from results. Reactivate it. Confirm it returns.

**Expected:** Marketplace toggles render without restriction; deactivation excludes the marketplace from the very next cross-marketplace search without a server restart; reactivation immediately restores it.

**Why human:** Visual confirmation of toggle rendering and live search behavior requires a running app.

---

### Gaps Summary

No technical gaps. All backend behaviors are implemented, tested (347 tests pass), and wired. All frontend behaviors compile and build. The only open items are the 4 human-verification tests above, which are UI/runtime behaviors that cannot be confirmed by static analysis.

The operator-approved UX-03 deviation (redirect to identify-first monitor flow) is documented in the override above and matches the implementation in `App.tsx`. The backend `POST /brands/identify` endpoint still exists and is exercised by the frontend.

---

_Verified: 2026-06-30T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
