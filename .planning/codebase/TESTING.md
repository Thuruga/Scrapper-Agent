# Testing Strategy

## Manual Verification
- **Job Cancellation**: Iniciar varredura e cancelar via dashboard. Verificar se a tarefa no backend encerra instantaneamente.
- **Excel Performance**: Iniciar extração de >1000 produtos e navegar no dashboard. A interface não deve sofrer lentidão ao final da extração.
- **WAF Bypass**: Validar se o motor Shopify/VTEX aciona o Playwright após detecção de 403.

## Automated Verification
- **Static Analysis**: TypeScript linting e Mypy (opcional) para Python.
- **Data Integrity**: Cada extração passa por validação automática via Pydantic. Falhas são logadas com detalhes do motivo (ex: "Preço zerado").

## Stability Checks
- **WebSocket Auth**: Tentar conectar no socket de logs sem token (deve ser rejeitado).
- **Port Management**: Verificar se o sistema encerra processos órfãos que travam a porta 8000.
