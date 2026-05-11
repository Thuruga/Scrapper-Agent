# Conventions

## Coding Standards
- **Python**: PEP 8, Type Hints obrigatórios em novos módulos.
- **Async**: Uso extensivo de `async/await`. Evitar `time.sleep` (usar `asyncio.sleep`).

## Architectural Patterns
- **Streaming Extraction**: Todos os métodos de extração em massa devem ser `AsyncGenerators` (`async def ... yield ...`).
- **Singleton Browser**: O `BrowserManager` deve ser o único ponto de acesso para instâncias do Playwright.
- **Dependency Injection**: Uso de `Depends` do FastAPI para Auth e recursos compartilhados.

## Frontend
- **State Management**: React Hooks (useState, useEffect, useRef).
- **Communication**: Centralizada na classe `ApiClient`.
- **CSS**: Escopo global via `App.css` usando variáveis CSS (`:root`).

## Logging
- Prefixos consistentes: `[ANTIBOT]`, `[PLAYWRIGHT]`, `[STREAM]`, `[AUTH]`.
