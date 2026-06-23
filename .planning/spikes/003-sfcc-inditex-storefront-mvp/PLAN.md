# MVP Test Plan: SFCC / Inditex Storefront Scraping

## Scope
Build only an isolated feasibility test under `.planning/spikes/003-sfcc-inditex-storefront-mvp/`.

The test bench must not connect to the main scraper architecture. It must not import production engines or change registered brands.

## Targets
- Hugo Boss US: SFCC/SFRA candidate.
- Lacoste US: SFCC/SFCC-adjacent candidate.
- Zara BR: Inditex IOP candidate.

## Acceptance Criteria
1. The experiment runs from the repo root with a single Python command.
2. The experiment writes `REPORT.md` and `report.json` inside the spike directory.
3. The experiment uses public storefront URLs only: homepage and robots.
4. The experiment records HTTP status, declared sitemaps, sensitive disallow patterns, platform signals, and link hints.
5. The experiment never calls checkout, cart, account, wishlist, availability, internal app, mobile, or API-authenticated endpoints.
6. The result includes a recommendation for each platform path: continue, continue-limited, or stop.

## Validation Matrix
| Question | Evidence | Pass Condition |
|---|---|---|
| Is SFCC feasible without API? | robots/homepage signals plus public product/category hints | At least one SFCC target exposes enough public navigation or sitemap evidence |
| Is Inditex feasible without API? | robots/homepage signals plus public links | Only public pages are needed; no blocked `/shop/` or internal endpoint dependency |
| Can this stay isolated? | files touched | Only `.planning/spikes/003-*` and manifest are changed |
| Is compliance risk bounded? | report flags | blocked/protected paths are treated as stop signs |

## Follow-Up If Validated
Create a separate production phase later with a narrow scope:

1. `SfccPublicStorefrontEngine` first, behind an explicit `engine="sfcc_public"` config.
2. Product detail extraction from public HTML/JSON-LD.
3. Category discovery from public sitemap/navigation only.
4. `InditexPublicProductProbe` only if the spike finds an allowed public path.

## Follow-Up If Invalidated
Keep these platforms out of main onboarding. Add a future requirement for authorized feeds/API access or manual URL monitoring only.
