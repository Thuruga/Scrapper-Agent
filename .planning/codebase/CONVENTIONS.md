# Conventions: Intelligence Scraper

## Python Coding Standards
- **Asynchronous First**: Toda a IO deve ser `async` usando `aiohttp`.
- **Typing**: Uso rigoroso de Type Hints e modelos Pydantic.
- **Naming**: `snake_case` para variáveis/funções, `PascalCase` para classes.
- **Error Handling**: Try-Except com logs detalhados (Logger name = Module name).

## Architectural Patterns
- **Engine Pattern**: Funcionalidades específicas de plataforma residem em subclasses de `BaseEngine`.
- **Factory Pattern**: Centralização da criação de instâncias via `factory.py`.
- **Orchestration**: Separação entre "como extrair" (Engine) e "o que fazer com os dados" (Orchestrator).

## Frontend Standards
- **React Components**: Funcionais com Hooks.
- **TypeScript**: No `any`, interfaces claras para props e estados.
- **State Management**: React State local + WebSockets para logs globais.
