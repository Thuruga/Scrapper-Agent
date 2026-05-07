# Coding Conventions

**Analysis Date:** 2026-05-07

## Naming Patterns

**Files:**
- `snake_case.py` for all Python source files (`brand_service.py`, `vtex_search.py`).
- `camelCase.ts/tsx` for React source files.
- `index.html` for the main frontend entry point (legacy).

**Functions:**
- `snake_case` for all Python functions (`load_monitors`, `save_mappings`).
- `camelCase` for frontend JavaScript/TypeScript functions.
- `handleEventName` for frontend event handlers.

**Variables:**
- `snake_case` for variables and parameters in Python.
- `UPPER_SNAKE_CASE` for global constants and settings (`MAX_RETRIES`, `DEFAULT_USER_AGENTS`).
- `camelCase` for variables in frontend code.

**Types:**
- `PascalCase` for Pydantic models and classes (`Brand`, `PriceMonitorConfig`).
- Type hints are required for all Python function signatures.

## Code Style

**Formatting:**
- PEP 8 compliance for Python (implied).
- 4-space indentation for Python.
- Docstrings (triple double quotes) for modules and complex functions.

**Linting:**
- Pydantic for runtime type validation and data integrity.

## Import Organization (Python)

**Order:**
1. Standard library imports (`os`, `sys`, `json`, `asyncio`).
2. Third-party package imports (`fastapi`, `pydantic`, `aiohttp`).
3. Local application imports (`from config import settings`, `from core.models import Product`).

**Grouping:**
- Blank line between standard, third-party, and local groups.
- Absolute imports preferred over relative imports.

## Error Handling

**Patterns:**
- `try/except` blocks at service and API boundaries.
- Catching specific exceptions where possible (`json.JSONDecodeError`, `ValidationError`).
- Raising `HTTPException` from API routes with descriptive error messages.
- Use of `return_exceptions=True` in `asyncio.gather` for parallel tasks.

**Error Types:**
- Critical failures (e.g., storage corruption) should be logged as `ERROR`.
- Transient failures (e.g., scraper timeout) should be handled with retries or logged as `WARNING`.

## Logging

**Framework:**
- Standard Python `logging` module.
- Configured in `app.py` for console output.

**Patterns:**
- `logger.info("Message")` for significant state changes and job starts.
- `logger.error("Error context", exc_info=True)` for exceptions.
- `logger.warning("Message")` for non-critical issues (e.g., search found no results).

## Comments

**When to Comment:**
- Header comments (docstrings) for all `.py` files explaining purpose.
- Section dividers in large files (`# --- Rotas ---`).
- Explaining complex logic or anti-bot evasion strategies.

**Format:**
- `#` for inline and block comments.
- `"""Docstrings"""` for functions and classes.

## Function Design

**Size:**
- Services tend to have medium-sized functions (20-100 lines).
- Business logic is concentrated in Services, keeping API controllers thin.

**Parameters:**
- Explicit type hints for all parameters.
- Heavy use of Pydantic models for complex parameter sets.

---

*Convention analysis: 2026-05-07*
*Update when patterns change*
