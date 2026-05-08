# Testing: Intelligence Scraper

## Methodology
The project currently relies on **Experiential Testing** using "scratch" scripts for rapid feature validation and regression checks.

## Test Directory (`scratch/`)
- **`verify_engine_abstraction.py`**: Validates the engine factory and platform-specific implementations.
- **`test_category_matching.py`**: Tests the accuracy of the Fuzzy Matching algorithm.
- **`check_buckman.py`**: Rapid diagnostic script for platform verification.

## Manual Verification Flow
1. **Bootstrap**: Run `app.py` to start the backend services.
2. **UI Access**: Navigate to the local React frontend.
3. **End-to-End Flow**:
   - Perform Category Discovery.
   - Select and Map categories.
   - Execute a Scan/Extraction job.
   - Monitor real-time logs via WebSocket.
   - Verify Excel export integrity.

## Future Testing Roadmap
- **`pytest` Migration**: Implementation of `pytest` for all Engines using `pytest-asyncio`.
- **API Mocking**: Establish stable CI/CD by mocking external platform APIs.
- **Frontend Testing**: Introduce Vitest and React Testing Library for component validation.
