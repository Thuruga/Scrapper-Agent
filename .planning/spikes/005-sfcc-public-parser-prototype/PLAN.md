# MVP Test Plan: SFCC Public Parser Prototype

## Scope
Create an isolated parser prototype that consumes small offline observations from Spike 004 and emits `RawProductBronze`-like dictionaries.

## Inputs
- `fixtures.json`
  - Hugo Boss category `ProductGroup`.
  - Hugo Boss product `ProductGroup`.
  - Lacoste category visible card.
  - Lacoste product `Product` + OpenGraph metadata.

## Acceptance Criteria
1. The parser runs from repo root with one Python command.
2. The parser performs no network calls.
3. The parser imports no production code.
4. The parser writes `RESULTS.json` and `REPORT.md`.
5. At least one Hugo Boss product is `bronze_ready`.
6. At least one Lacoste product is `bronze_ready`.
7. Category-card-only records are marked `needs_detail_page` when image or stock data is missing.

## Decision Rule
Proceed to production planning only if:

- JSON-LD/OpenGraph fields can fill required canonical fields.
- Missing data is explicit and recoverable by visiting public PDP pages.
- The future implementation can remain browser-rendered, rate-limited, and isolated behind an explicit engine flag.

## Follow-Up If Validated
Plan a real phase for a guarded `sfcc_public` engine:

1. browser-rendered public page fetcher;
2. parser module based on this spike;
3. per-brand disable switch;
4. conservative rate limits;
5. no checkout/API/private endpoint scope.
