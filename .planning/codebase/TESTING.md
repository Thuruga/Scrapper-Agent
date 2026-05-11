# Testing Strategy

## Manual Verification
- **Anti-Bot Bypass**: Verificar se o Playwright é acionado após 403 em sites com Cloudflare.
- **Auth Flow**: Validar redirecionamento para Login e persistência do Token no LocalStorage.
- **Streaming Perf**: Monitorar uso de memória no Gerenciador de Tarefas durante extrações >2000 produtos.

## Automated Tests
- **Backend (Pytest)**:
  - `tests/test_auth.py`: Validação de tokens e proteção de rotas.
  - `tests/test_streaming.py`: Verificar se os generators retornam os dados esperados.
- **Frontend**: Validação de tipos via TypeScript Linting.

## Quality Gates
- **Pydantic**: Validação de esquema para cada produto extraído antes do salvamento final.
- **Logs**: Auditoria de logs para identificar falhas de fallback.
