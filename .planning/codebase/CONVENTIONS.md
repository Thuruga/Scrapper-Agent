# Coding Conventions

## Python (Backend)
- **Style Guide**: Adheres to PEP 8 standards for naming and formatting.
- **Typing**: Strict use of Python type hints for all function signatures and variable declarations.
- **Documentation**: All modules, classes, and major functions must have descriptive docstrings (Google/Sphinx style).
- **Asynchronous Programming**: Use `async/await` for all I/O-bound operations (API calls, file access, scraping).
- **Data Validation**: Utilize Pydantic models for all data ingestion and API responses to ensure type safety.
- **Error Handling**: Use try-except blocks with specific exceptions and log errors using the standard `logging` library.
- **API Design**: Organize routes using FastAPI `APIRouter` with clear prefixes and tags.
- **Variable Naming**: Use `snake_case` for variables and functions, and `PascalCase` for classes and models.

## TypeScript/React (Frontend)
- **Components**: Functional components with hooks.
- **Types**: Define interfaces or types for all component props and API responses.
- **Styling**: Use utility-first CSS with Tailwind CSS.
- **State Management**: React State/Context or lightweight libraries if needed.
- **File Naming**: Use `PascalCase` for component files (e.g., `Button.tsx`) and `camelCase` for utilities.

## General
- **Version Control**: Atomic commits with descriptive messages.
- **Configuration**: Sensitive data and environment-specific settings are stored in `.env` files and managed via `pydantic-settings`.
