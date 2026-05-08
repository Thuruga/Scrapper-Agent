# Testing State

## Automated Tests
- **Current Coverage**: Low. Most testing is performed via ad-hoc scripts in the `scratch/` directory.
- **Tools**: The project setup supports `pytest` for backend testing and Vitest (implied by Vite) for frontend testing, but no comprehensive test suites are currently implemented.
- **Scratch Scripts**:
  - `test_autonomous_mapping.py`: Tests for category mapping logic.
  - `test_category_matching.py`: Specific tests for category matching heuristics.
  - `test_foxton_fix.py`: Regression test for the Foxton brand search.

## Manual Verification
- **API Testing**: Performed via the FastAPI Swagger UI (`/docs`).
- **Dashboard Testing**: Manual end-to-end testing of the React frontend by triggering scans and searches.
- **Excel Verification**: Manual inspection of generated Excel reports for data accuracy and formatting.

## Proposed Strategy
- **Unit Tests**: Implement unit tests for core logic (category resolver, scraper factory).
- **Integration Tests**: Test the full scraping pipeline with mock API responses.
- **UI Tests**: Implement Playwright tests for the frontend dashboard to ensure key flows (login, brand registration, search) remain functional.
