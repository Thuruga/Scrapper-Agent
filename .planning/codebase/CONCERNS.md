# Concerns: Intelligence Scraper

## Technical Risks

### 1. Advanced Anti-Bot Mechanisms
Platforms like VTEX (especially with Cloudflare/WAF) are increasingly aggressive. While `curl_cffi` provides a strong baseline, complex interactions may require a headless browser fallback (Playwright) with stealth plugins.

### 2. Event Loop Performance
Large-scale extractions (>10,000 SKUs) can lead to event loop saturation. Although `run_in_executor` is utilized for heavy lifting, the overhead of context switching and memory allocation in Pandas requires constant monitoring.

### 3. Memory Footprint
Accumulating large datasets in memory before Excel generation poses a risk for very high-volume scans. A transition to streaming persistence or a temporary database (SQLite) for "Bronze" data is recommended.

## Maintenance Concerns
- **API Fragility**: Direct reliance on private VTEX/Shopify JSON endpoints is efficient but susceptible to breaking changes without notice.
- **Engine Divergence**: As more platforms are added, maintaining parity across all `BaseEngine` implementations becomes a significant testing burden.
- **Category Drift**: Fuzzy matching is powerful but requires periodic tuning of thresholds as product nomenclature evolves.

## High-Priority Technical Debt
- **Authentication**: The system currently lacks a robust auth layer for the admin dashboard.
- **Data Persistence**: Migration from local JSON to a structured database (SQLite) for better integrity and querying.
- **Test Coverage**: Lack of automated unit and integration tests for core extraction logic.
