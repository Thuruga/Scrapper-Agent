# Technical Concerns

## Architecture & Scalability
- **Data Persistence**: Currently relies on local JSON and Excel files. As the data grows (more brands, products, and price history), this will become a performance bottleneck and harder to query/manage. A proper database (e.g., PostgreSQL or MongoDB) is recommended.
- **Transition State**: There is both a root-level `index.html` (legacy) and a `frontend/` directory (modern React). This dual existence can lead to confusion and maintenance overhead.
- **Service Orchestration**: `orchestrator_multi.py` and `orchestrator.py` seem to have overlapping responsibilities. Consolidation could simplify the logic.

## Reliability & Quality
- **Test Coverage**: Extremely low. Critical logic for category mapping and scraping depends on ad-hoc verification, making it prone to regressions.
- **API Dependencies**: The system is heavily coupled to VTEX API structures. While fallbacks exist, major changes to VTEX's "Intelligent Search" could require significant refactoring.
- **Rate Limiting**: While there is a semaphore and basic retry logic, there is no centralized rate-limiting management across multiple scraping jobs, which could lead to IP bans or 429 errors from brands.

## Security
- **Authentication**: Basic auth is implemented, but there is no session management or more robust OAuth/JWT implementation for the dashboard.
- **Input Validation**: While Pydantic is used for models, direct user input in search queries or brand registration needs to be strictly sanitized to prevent potential injection or path traversal (though less likely in this stack).

## Maintenance
- **Documentation**: Codebase mapping is a good start, but in-code documentation (inline comments) varies in quality.
- **Dependency Management**: `requirements.txt` is basic; using a more robust tool like `poetry` or `pip-compile` could help manage sub-dependencies and security patches.
