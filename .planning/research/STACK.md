# Stack Research — v4.0 New-Feature Stack

**Researched:** 2026-06-26 (inline; subagents rate-limited → library versions from training knowledge, verify with Context7 before pinning).
**Existing stack (do not re-add):** Python/asyncio, FastAPI, Pydantic v2, Playwright, curl_cffi, aiohttp, React/Vite/TypeScript, zustand, CLIP (torch), openpyxl (xlsx).

## Guiding principle
**Most of v4.0 needs NO new dependencies** — it extends existing engines, services, and Pydantic models. New deps should be the exception and justified.

## By category

### A. Attribute parity — **no new deps**
Pure Python normalization/alias mapping over existing `specifications` bag. Optionally `rapidfuzz` (fast fuzzy matching) if attribute-key aliasing needs fuzzy resolution — only if exact/alias maps prove insufficient.

### B. Coverage
- **Zara/Inditex:** no new dep — reuse Playwright (browser-rendered) + existing engine pattern. Inditex has a public product API surface reachable via the site; validate via spike. No SDK exists; don't add one.
- **Hugo Boss / Lacoste:** no new deps (config/mapping only).

### C. UX — **no new backend deps**
URL-only onboarding reuses `detect_engine`. Frontend: existing React/zustand; responsiveness uses existing CSS approach. SKU pattern = a regex (stdlib).

### D. Shipping
- **Correios:** no official free REST API since the legacy SOAP/`ViaCEP` split. `ViaCEP` (free, no key) resolves CEP→address only (useful for the multi-regional matrix region labels), not freight price. Freight pricing comes from each **merchant's own checkout/shipping endpoint** (the existing VTEX approach) — generalize that, don't add a Correios SDK.
- **Mercado Livre:** has a shipping-calculator via its public item/shipping endpoints — use `aiohttp`, no SDK.
- **No new dep required**; optionally `brazilcep`/`pycep-correios` only if we want a tidy CEP-validation/lookup helper for the matrix (small, pure-Python). Prefer ViaCEP over a dependency.

### E. Intelligence
- **MAP:** no new dep — comparison logic + JSON rules.
- **Promotions/payment seals:** no new dep — per-engine parsing + existing `nlp_service` for normalization.
- **Stock rupture / cart probe:** no new dep — reuse engine HTTP/session layer; guard with throttling.
- **Reviews:** no new dep — `review_service` exists.
- **Assortment + analytical persistence:** **SQLite via stdlib `sqlite3`** (zero new dependency) for counts/time-series. If richer querying is wanted later, consider `duckdb` — but start with stdlib.

## What NOT to add
- No Correios SOAP SDK, no paid freight APIs.
- No new scraping framework (Scrapy etc.) — the hybrid Playwright/curl_cffi/aiohttp engine is sufficient.
- No external DB server (Postgres) — SQLite suffices for this single-node tool.
- No Inditex/ML/Amazon vendor SDKs — public endpoints via aiohttp/Playwright.

## Candidate new deps (only if justified during planning)
| Package | Purpose | Verdict |
|---|---|---|
| `rapidfuzz` | fuzzy attribute-key aliasing (A) | Only if exact+alias maps insufficient |
| `brazilcep` / `pycep-correios` | CEP validation/lookup for matrix (D) | Prefer ViaCEP HTTP; add only for convenience |
| stdlib `sqlite3` | analytical persistence (E5, series) | Recommended, zero-dep |

> Verify any pinned version with Context7 when the relevant phase is planned.
