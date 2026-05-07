# Testing Patterns

**Analysis Date:** 2026-05-07

## Test Framework

**Current Status:**
- No automated test suite (runner or assertion library) detected in the project root.
- Testing is currently performed via **manual execution** and **scratch scripts**.

**Run Commands:**
```bash
python app.py                                     # Manual integration testing via UI/API
python scratch/test_foxton_fix.py                 # Example of a one-off scratch test script
```

## Test File Organization

**Location:**
- Ad-hoc scripts are placed in the `scratch/` directory.
- No formal `tests/` directory exists.

**Naming:**
- `test_*.py` for scratch scripts in `scratch/`.

## Test Structure

**Scratch Scripts:**
```python
# Example from scratch/test_foxton_fix.py
async def test():
    # setup
    # execute function
    # print results/assert
    pass

if __name__ == "__main__":
    asyncio.run(test())
```

## Mocking

**Framework:**
- No mocking framework used.
- Tests typically run against live or local development environments.

**What to Mock (Future):**
- VTEX APIs (using `unittest.mock` or `pytest-mock`).
- Browser interactions in Playwright scrapers.

## Fixtures and Factories

**Test Data:**
- Real product data and brand configurations from `data/brands.json` are used for testing.
- Temporary Excel files are generated during execution for manual verification.

## Coverage

**Requirements:**
- No formal coverage tracking or requirements.

## Test Types

**Manual Integration:**
- Validating the React frontend against the FastAPI backend locally.
- Verifying scraper output by checking generated `.xlsx` or `.json` files.

**Ad-hoc Scraper Testing:**
- Running specific scraper modules directly to verify extraction logic.

---

*Testing analysis: 2026-05-07*
*Update when a formal test framework (e.g., pytest) is introduced*
