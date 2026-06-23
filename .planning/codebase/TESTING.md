---
last_mapped_commit: unknown
---

# 🧪 Testing

**Date:** 2026-06-08

## Framework
- **Backend**: Uses `pytest` (inferred from `.pytest_cache`).
- **Scripts**: Various manual scratch scripts exist to test specific functionalities directly (e.g., `test_redis.py`, `test_redis2.py`, `test_monitor.py`).

## Test Structure
- Tests are located in the `tests/` directory.
- Root test scripts serve as manual verifications for integration logic, particularly for image matching or pub/sub capabilities.

## Patterns
- Relies heavily on checking outputs of image matching algorithms and basic monitors.
- Mocking is likely used for external APIs to prevent tests from being blocked by CAPTCHAs or hitting rate limits.
