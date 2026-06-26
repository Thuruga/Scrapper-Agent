# Features Research — v4.0 (Paridade de Dados, Frete Total & Inteligência Competitiva)

**Researched:** 2026-06-26
**Method:** Inline (research subagents rate-limited until 2:10pm BRT). Grounded in codebase (`backend/core/models.py`, `backend/services/*`, `backend/api/*`), the v4.0 spec, and competitive-intelligence domain knowledge.
**Scope note:** Most v4.0 features extend existing primitives — few net-new dependencies. Categories map to the 5 PROJECT.md milestone categories (A–E).

---

## A. Paridade de Dados de Marca

**Problem (from spec):** Levi's, Calvin Klein, Zapalla, Austral, Track & Field, Richards, Hugo Boss return a *different/sparser* attribute set than the reference brands. Marketplace-sourced brands return attribute "soup" (`Cor2`, `Corte`, `ModeloMKTP`, `meli_title`, `Style Dafiti`…), while brand-site (VTEX) extraction yields a clean curated set (`Composição`, `Cor`, `Tipo`, `Matéria-Prima`…). Goal: every brand yields the **same normalized attribute schema**.

| Capability | Type | Complexity | Notes |
|---|---|---|---|
| Unified canonical attribute vocabulary | Table stakes | M | Shared keys (`composition`, `color`, `material`, `fit`, `gender`, `age_group`, `sleeve`, `collection`…). `RawProductBronze.specifications: Dict[str,str]` already exists as the bag. |
| Per-engine extractor completeness audit | Table stakes | M | Each engine (VTEX/Wake/SFCC/marketplace) must populate the canonical fields it can. Audit which of the 7 brands miss which fields and why. |
| Attribute-name normalization/aliasing | Table stakes | M | Map source keys → canonical keys (`Cor2`→`color`, `Corte`/`Fit`→`fit`). Locale + casing tolerant. |
| Attribute coverage report (per brand, % filled) | Differentiator | S | Observability so parity is measurable, not vibes. |

**Anti-features:** Don't fabricate values to "fill" fields (honest nulls > fake parity). Don't hard-code one brand's schema as master — derive a shared canonical vocabulary.

---

## B. Cobertura de Marcas

| Capability | Type | Complexity | Notes |
|---|---|---|---|
| Fix Hugo Boss category scan + monitoring | Table stakes | M | Hugo Boss is **VTEX** (corrected empirically in v3.0). Needs VTEX category de/para (`category_mapping`) like other VTEX brands — search works, category scan doesn't because mappings are missing. |
| Add Zara (Inditex) | Differentiator | L | Zara public pages loaded under stealth in v3.0 recheck (HTTP 200). No engine exists. Inditex is a distinct platform — needs an engine + `detect_engine` label, or a browser-rendered extractor. Highest-risk item here. |
| Remove Lacoste from searches | Table stakes | S | Lacoste stays dormant (Akamai IP-reputation). Ensure it never appears as a selectable search target across all surfaces. |

**Anti-features:** Don't attempt Lacoste anti-bot bypass (out of scope). Don't build Zara checkout/shipping this milestone — catalog + price first.

---

## C. UX de Monitoramento & Busca

| Capability | Type | Complexity | Notes |
|---|---|---|---|
| URL-only brand onboarding | Differentiator | M | Paste a URL → `detect_engine` + brand-name inference (domain / page title / JSON-LD) auto-fills `DynamicBrandCreate`. Removes the manual "brand then URL" step. |
| Inline "add to monitoring" action | Table stakes | M | From comparative search, SKU search, and category monitor → create a `PriceMonitorConfig`. Backend route + frontend button + dedup. |
| Promo value in monitoring list | Table stakes | S | List hides the promo price; surface `price_discount` alongside `price_full`. |
| Auto-trigger category monitor on selection | Table stakes | S | Selecting a category immediately runs the first scan and shows products. |
| Responsiveness fixes (monitor + category scan) | Table stakes | M | Layout breaks on smaller viewports — frontend CSS/layout. |
| History panel → top-right corner | Table stakes | S | Relocate search history (comparative + SKU) to top-right. |
| SKU search: enforce pattern + CEP inline | Table stakes | S | Accept only the SKU pattern (e.g. `ML.05.0326046`); CEP on the same line as SKU (match comparative layout). |
| Activate/deactivate toggles for marketplaces | Differentiator | S | Extend brand active-toggle to virtual marketplaces (ML/Netshoes/Amazon), which currently hide the toggle (no backend brand record — needs a representation). |

**Anti-features:** Validate the SKU field against the strict pattern. Never create duplicate monitors silently.

---

## D. Frete (Cobertura Total)

| Capability | Type | Complexity | Notes |
|---|---|---|---|
| Shipping abstraction beyond VTEX | Table stakes | L | Shipping today lives in `vtex_shipping.py` (VTEX-only). Generalize to per-engine/per-marketplace strategy. Buckman (VTEX) shipping reportedly missing — verify mapping. |
| Shipping for non-VTEX brands (Wake/SFCC/Shopify) | Table stakes | L | Each engine needs its own path (Wake freight API; Shopify AJAX cart; SFCC dormant). Some may only support "calculated at checkout". |
| Shipping for marketplaces (ML/Netshoes/Amazon) | Differentiator | L | Endpoints differ; ML has a shipping calculator API; Amazon/Netshoes typically need cart/page extraction. |
| Multi-Regional shipping matrix | Differentiator | L | Shipping to representative CEPs across Brazil's 5 regions (N/NE/CO/SE/S). Fan-out per product — request-volume + anti-bot sensitive. |

**Anti-features:** Don't fan out the matrix on every search (opt-in / on-demand / batched). Don't route VTEX shipping through a generic hook (D-03: VTEX stays on `VtexApiClient`).

---

## E. Inteligência Competitiva (novas features)

| Capability | Type | Complexity | Notes |
|---|---|---|---|
| MAP violation detection | Differentiator | M | Per-product/brand/category floor price; flag listings priced below it + surface the **offending seller**. New field + comparison at result time + violations view. |
| Payment conditions + promo badges | Differentiator | M | Extract seals ("Leve 3 pague 2", "15% OFF no Pix", installments). Free-text/locale-heavy — per-engine parsers → structured `promotions` field. |
| Stock rupture (% out-of-stock + depth) | Differentiator | L | In category scan: % of a brand's products out of stock; **stock depth** via cart probe (request 999 units, capture allowed max). Anti-bot/side-effect sensitive. |
| Reviews (ratings + comments) reinforced | Table stakes | M | `review_service.py` already exists — extend/reinforce per-brand extraction and coverage. |
| Assortment analysis (cron by attributes) | Differentiator | L | Scheduled full-category scrape → count by attribute (polos by color/fabric) to find catalog gaps. Depends on Category A parity + persistence for counts. |

**Anti-features:** Don't run the cart-999 probe at search time (controlled category scans only). Don't treat the assortment cron as real-time. MAP must compare the correct (advertised) price field.

---

## Cross-Cutting Observations

- **Dependency spine:** A (attribute parity) is foundational for E5 (assortment) and improves E1/E2. A shipping abstraction (D) is foundational for all shipping items. Both come early.
- **Persistence:** Current persistence is JSON files in `backend/data/`. Assortment counts, MAP rules, multi-regional matrices, and review corpora may strain JSON (concurrency, size). Evaluate SQLite — see ARCHITECTURE.md.
- **Anti-bot amplification:** D (matrix), E3 (cart probes), E5 (full-catalog cron) multiply request volume. Throttling/identity rotation designed in, not bolted on.
- **Reuse:** `review_service.py`, `price_monitor_service.py`, `category_monitor_service.py`, `vtex_shipping.py`, `orchestrator*.py`, `relevance_gates.py`, `nlp_service.py`.
