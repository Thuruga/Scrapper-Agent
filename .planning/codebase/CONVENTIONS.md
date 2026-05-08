# Conventions: Intelligence Scraper

## Python Coding Standards
- **Asynchronous First**: All I/O operations MUST be `async` using `aiohttp` or `playwright`.
- **Typing**: Strict usage of Python Type Hints and Pydantic models for data structures.
- **Naming**: `snake_case` for variables/functions, `PascalCase` for classes, and `UPPER_CASE` for constants.
- **Error Handling**: Comprehensive try-except blocks with detailed logging using module-named loggers.

## Architectural Patterns
- **Engine Pattern**: Platform-specific logic is encapsulated in subclasses of `BaseEngine`.
- **Factory Pattern**: Centralized instance resolution via `factory.py` to ensure scalability.
- **Service Layer**: Business logic is separated into specialized services (Orchestrators, Intelligence, Monitors).
- **Session Lifecycle**: Global session management via `SessionManager` singleton to optimize connection overhead.

## Frontend Standards
- **Component Architecture**: Functional components with Hooks and strict TypeScript typing.
- **UI Consistency**: Use of `tailwind-merge` and `clsx` for dynamic styling and design consistency.
- **Real-time Feedback**: Global logs and progress tracking via persistent WebSockets.
- **Animations**: Framer Motion for micro-interactions and layout transitions.

## Data Standards
- **Layered Data**: Raw data (Bronze) is validated and transformed into structured models (Silver/Gold) before persistence or export.
