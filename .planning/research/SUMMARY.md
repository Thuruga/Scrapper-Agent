# Project Research Summary

**Project:** Intelligence Scraper — v4.0 Paridade de Dados, Cobertura Total de Frete & Inteligência Competitiva
**Date:** 2026-06-26
**Method:** Inline synthesis (research subagents rate-limited until 2:10pm BRT). Grounded in the codebase + v4.0 spec. See STACK / FEATURES / ARCHITECTURE / PITFALLS.

## One-paragraph synthesis
v4.0 is mostly an **extension milestone**: the existing multi-engine architecture (BaseScraper + EngineFactory + detect_engine), Pydantic schema (`RawProductBronze` with a `specifications` attribute bag + `ShippingInfo`), and services (`review_service`, `price_monitor_service`, `category_monitor_service`, `vtex_shipping`) already provide the primitives. The work is to (A) **normalize attribute extraction** so all brands reach data parity, (B) **close coverage gaps** (Hugo Boss category, add Zara, remove Lacoste), (C) ship a batch of **UX fixes** to monitoring/search, (D) **generalize shipping** beyond VTEX (other engines, marketplaces, multi-regional CEP matrix), and (E) add **competitive-intelligence layers** (MAP violations, promo/payment seals, stock rupture, reinforced reviews, assortment analysis).

## Stack additions
**Near-zero new dependencies.** Build on existing Python/Playwright/aiohttp + React/zustand. Recommended additions are minimal: stdlib `sqlite3` for analytical/time-series data (assortment counts, price/stock series, review corpus); ViaCEP (HTTP, no key) for CEP region resolution in the shipping matrix. Optional-only: `rapidfuzz` (fuzzy attribute aliasing), `brazilcep` (CEP convenience). **Do NOT add:** Correios SOAP SDK, paid freight APIs, a new scraping framework, an external DB server, or vendor SDKs.

## Feature table stakes (must-have)
- Unified canonical attribute schema + per-engine extractor parity (A).
- Hugo Boss category scan/monitor fixed; Lacoste removed from searches (B).
- UX: promo value in monitoring list, auto-trigger category monitor, history to top-right, SKU pattern + inline CEP, responsiveness, add-to-monitoring, marketplace toggles (C).
- Shipping for non-VTEX brands + a shipping abstraction; Buckman shipping gap closed (D).
- Reviews (ratings + comments) reinforced across all brands (E).

## Differentiators
- URL-only brand onboarding (auto-detect brand/engine) (C).
- Shipping for marketplaces + Multi-Regional CEP matrix (D).
- MAP violation detection + offending seller; promo/payment-seal extraction; stock rupture (% + depth); assortment analysis cron (E).

## Watch out for (top pitfalls)
- **Anti-bot amplification:** shipping matrix + cart probes + assortment cron multiply request volume — shared throttle/identity budget, never concurrent on one host.
- **Zara/Inditex:** spike-gate before building the engine (GO/NO-GO on public product+price extraction).
- **Lossy normalization:** canonical attributes are additive; never overwrite raw `specifications`.
- **JSON persistence races:** move analytical/series data to SQLite; keep JSON for config with atomic writes.
- **MAP false positives & cart-999 caps:** compare the correct price field; label stock depth as an estimate.
- **VTEX shipping regression:** D-03 — VTEX stays on `VtexApiClient`; the abstraction wraps, not replaces.

## Recommended build order (dependency-aware)
1. **Foundations:** attribute-parity normalization (A) + a throttle/persistence (SQLite) base.
2. **UX quick wins** (C — promo, history, SKU/CEP, auto-trigger, responsiveness, marketplace toggles).
3. **Coverage** (B — Hugo Boss category fix; Lacoste removal; Zara behind a spike).
4. **Onboarding + add-to-monitoring** (C).
5. **Shipping** (D — abstraction → non-VTEX → marketplaces → multi-regional matrix).
6. **Intelligence** (E — MAP, promos, reviews, stock rupture; assortment last, depends on A + persistence).

> When subagents are available again, this inline research can be re-validated with Context7/web for exact library versions and Inditex/marketplace endpoint specifics.
