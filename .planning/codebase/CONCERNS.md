# Project Concerns & Technical Debt

## Resolved / Improved (Phase 4)
- [x] **Anti-Bot Resilience**: Implementado fallback Playwright.
- [x] **Memory Saturation**: Pipeline convertido para `AsyncGenerator` (Streaming).
- [x] **Insecure Dashboard**: Adicionada autenticação JWT.

## High Priority
- **Rate Limiting**: O endpoint de login está vulnerável a brute-force. Recomendo adicionar `slowapi`.
- **Incremental Excel Writing**: Embora o pipeline seja streaming, o orquestrador ainda acumula produtos em uma lista antes de gerar o Excel final. Necessário migrar para `pd.ExcelWriter` incremental para volumes >50k SKUs.

## Medium Priority
- **Proxy Rotation Strategy**: Atualmente usa um proxy por requisição. Falta uma lógica de "Sticky Session" para fluxos que exigem múltiplas chamadas seguidas.
- **Error Granularity**: Algumas falhas de rede são capturadas genericamente como Exception. Melhorar o tratamento de `aiohttp` vs `curl_cffi` errors.

## Maintenance
- **Playwright Updates**: Manter drivers de navegador atualizados para evitar detecção por impressões digitais obsoletas.
- **Token Rotation**: Implementar Refresh Tokens para evitar logouts frequentes dos usuários.
