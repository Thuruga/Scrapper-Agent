# Codebase Concerns

**Analysis Date:** 2026-05-07

## Tech Debt

**File-based persistence as primary DB:**
- Issue: Using JSON files in `data/` for everything (brands, monitors, mappings).
- Files: `services/brand_service.py`, `services/price_monitor_service.py`.
- Why: Simple to set up, no external database dependency.
- Impact: Potential race conditions during concurrent writes, no transactional integrity, performance degrades as file size grows.
- Fix approach: Migrate to SQLite or a proper document database (e.g., MongoDB/PostgreSQL).

**Monolithic scraping logic:**
- Issue: `services/vtex_api_scraper.py` is very large (~36k bytes) and handles multiple responsibilities (catalog, search, product extraction).
- Why: Organic growth as more features were added to the VTEX integration.
- Impact: Hard to maintain, difficult to test in isolation, high risk of regression when changing one part of the flow.
- Fix approach: Refactor into smaller, specialized modules (e.g., `vtex/catalog_manager.py`, `vtex/search_engine.py`, `vtex/product_extractor.py`).

## Known Bugs

**Event loop issues on Windows:**
- Symptoms: `asyncio` operations might hang or crash if the wrong event loop policy is used.
- Trigger: Running on Windows without the `WindowsProactorEventLoopPolicy`.
- File: `app.py` (line 22-23).
- Workaround: Explicitly set the policy at the top level of `app.py`.
- Root cause: Default selector-based loop on Windows has limitations with subprocesses and sockets.

## Security Considerations

**Hardcoded API Key:**
- Risk: `SCRAPER_API_KEY` has a default value `dev-key-123` in `config.py`.
- Current mitigation: Can be overridden by `.env`.
- Recommendations: Ensure `.env` is always used in production and the default is removed or changed to a random string.

**CORS "allow-all":**
- Risk: `allow_origins=["*"]` in `app.py` allows any domain to access the API.
- Current mitigation: None.
- Recommendations: Restrict to specific frontend domains in production.

## Performance Bottlenecks

**Serial category scanning:**
- Problem: Large category trees take a long time to scan.
- Cause: Synchronous or semi-sequential processing of deep category hierarchies.
- Improvement path: Implement worker-based parallelization for category branches.

## Fragile Areas

**Anti-bot evasion:**
- Why fragile: Site owners (VTEX brands) constantly update their WAF/anti-bot rules.
- Common failures: HTTP 403/401 errors, CAPTCHA blocks.
- Safe modification: Update `identity.py` and `config.py` with fresh User-Agents and rotating proxies.

## Scaling Limits

**Local Storage:**
- Current capacity: Limited by disk space and OS file handling.
- Limit: Performance likely degrades after 1,000+ monitored products or 100+ brands due to JSON parsing overhead.

## Missing Critical Features

**Automated Testing Suite:**
- Problem: No unit or integration tests for core scraping and processing logic.
- Impact: Regressions are only caught during manual testing or after deployment.

**Background Job Management:**
- Problem: `core/job_manager.py` appears to be a basic in-memory tracker.
- Impact: Jobs are lost if the server restarts.

## Test Coverage Gaps

**Scraper logic:**
- What's not tested: Extraction accuracy for different brand layouts.
- Priority: High.

---

*Concerns audit: 2026-05-07*
*Update as issues are fixed or new ones discovered*
