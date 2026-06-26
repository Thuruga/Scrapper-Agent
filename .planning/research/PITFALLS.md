# Pitfalls Research — v4.0

**Researched:** 2026-06-26 (inline; subagents rate-limited). Specific to adding these features to THIS system (Python + Playwright/curl_cffi/aiohttp + React, JSON persistence, anti-bot-sensitive).

## A. Attribute parity
- **Lossy normalization:** aliasing `Cor2`/`Corte`/`Fit` → canonical can collapse distinct attributes. *Prevention:* keep raw `specifications` untouched; normalization produces an additive canonical view, never overwrites source.
- **Schema over-fit to one brand:** treating the reference brand's fields as the master. *Prevention:* derive a shared canonical vocabulary; allow per-brand extras.
- **Silent field drops:** an engine that simply doesn't extract a field looks identical to "field absent at source". *Prevention:* coverage report distinguishing "not extracted" vs "not present".

## B. Coverage
- **Zara/Inditex anti-bot + platform quirks:** Inditex pages are JS-heavy and geofenced (BR store path); naive HTTP returns shells. *Prevention:* spike first (validate product+price publicly under stealth) with explicit GO/NO-GO before building the engine. Don't commit the engine before the spike passes.
- **Hugo Boss category mapping drift:** category scan breaks when VTEX category paths/pagination change. *Prevention:* derive mappings from the canonical source (mirror the existing VALID_SLUGS-from-RAW pattern), add a mapping-freshness check.
- **Lacoste leak:** removing from search must cover every surface (comparative selector, SKU, category, scheduler, export). *Prevention:* enforce at the single `list_brands(active_only=True)` chokepoint; add a regression test.

## C. UX
- **detect_engine misidentification on onboarding:** ambiguous domains, www/non-www (e.g. `hugoboss.com.br` doesn't resolve; needs `www.`), anti-bot returning `unknown`. *Prevention:* show the inferred engine/brand for operator confirmation before saving; allow manual override (fields already exist).
- **Duplicate monitors:** "add to monitoring" from multiple surfaces creates dupes. *Prevention:* dedup by (url, brand); idempotent create.
- **Promo not refreshing:** showing a stale `price_discount`. *Prevention:* persist promo in each history entry, render the latest.

## D. Shipping
- **Per-product shipping calls slow scans / trip rate limits.** *Prevention:* batch + throttle; never call shipping inline during a full category scan unless explicitly requested.
- **Cart-probe side effects:** adding to cart creates real sessions/cookies, may pollute identity or be flagged. *Prevention:* isolated ephemeral sessions, cleanup, throttle, only in controlled scans.
- **Multi-regional matrix fan-out amplifies volume × anti-bot risk:** N products × M CEPs. *Prevention:* opt-in/on-demand, cap M (curated key CEPs), cache by (sku, cep), spread over time.
- **CEP edge cases:** PO-box/remote CEPs with no delivery, invalid CEPs. *Prevention:* validate via ViaCEP, handle "no service" gracefully.
- **VTEX regression:** routing VTEX through a new generic hook. *Prevention:* honor D-03 — VTEX stays on `VtexApiClient`; abstraction wraps, doesn't replace.

## E. Intelligence
- **MAP false positives:** comparing the wrong price field (full vs advertised/discount). *Prevention:* define which field MAP compares; test against known violations.
- **Promo-badge brittleness:** free-text seals, locale, per-engine markup. *Prevention:* per-engine parsers + a normalization step; store raw + parsed; degrade to raw when unparseable.
- **Cart-999 misleading caps:** site may cap silently or return a soft limit ≠ real stock. *Prevention:* treat depth as "max purchasable observed", label as estimate, don't equate with inventory.
- **Reviews pagination/dedup/locale:** infinite scroll, duplicated reviews, provider differences (Trustvox/VTEX native). *Prevention:* page bounds, dedup keys, per-provider extractors (`review_provider` field already exists).
- **Assortment cron load:** full-catalog scrape is expensive, can trigger IP bans, and partial failures corrupt counts. *Prevention:* incremental/resumable scans, store per-run snapshots (don't mutate in place), throttle, run off-peak; depends on reliable Category A attributes.

## Cross-cutting
- **Anti-bot amplification:** D-matrix + E3-probes + E5-cron together multiply requests dramatically. *Prevention:* a shared throttle/identity-rotation budget; never run them concurrently against the same host.
- **JSON persistence concurrency/corruption:** more writers (cron + scheduler + monitors) racing on JSON files. *Prevention:* move analytical/series data to SQLite; keep JSON for config with atomic writes.
- **Scheduler overload:** assortment cron + 10-min monitor + matrix jobs contending. *Prevention:* stagger schedules, bound concurrency, observable job queue.
- **Data fidelity over coverage:** honest nulls and labeled estimates beat fabricated completeness — core value of the product.

## Phase mapping (where to address)
- Parity pitfalls → Category A phases. Anti-bot/persistence → designed into D and E phases. Zara → spike-gated B phase. Lacoste leak → B regression. Cross-cutting throttle/SQLite → an early foundational phase before D/E.
