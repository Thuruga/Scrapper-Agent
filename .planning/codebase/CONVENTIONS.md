# Conventions

## Coding Standards
- **Python**: PEP 8 rigoroso. Type Hints são obrigatórios em todas as funções.
- **Async First**: Bloquear o loop de eventos é proibido. Operações de CPU/IO pesadas devem usar `asyncio.to_thread`.
- **Cancellation**: Todo processo longo deve aceitar um `cancel_event: asyncio.Event` e checar periodicamente via `.is_set()`.

## Architectural Patterns
- **Engine Factory**: Instanciação de motores deve ser feita via `engine_factory`.
- **Streaming**: Métodos de extração devem ser `AsyncGenerators`.
- **Quality Gates**: Nenhum dado é salvo sem passar pela validação Pydantic no `BaseEngine`.
- **WebSocket Feedback**: Logs estruturados via dicionários enviados em tempo real.

## Frontend
- **Functional Components**: Uso exclusivo de React Hooks.
- **Type Safety**: Interfaces TypeScript devem espelhar os modelos Pydantic do backend.
- **Visuals**: CSS puro com variáveis `:root` para tema dark/glassmorphism.

## Error Handling
- **Graceful Failures**: Usar logs `[WARNING]` para itens descartados por qualidade, reservando `[ERROR]` para falhas de infraestrutura.
- **Bypass Logic**: Fallback automático entre clientes HTTP e Playwright.
