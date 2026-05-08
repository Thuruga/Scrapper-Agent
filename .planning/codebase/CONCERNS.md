# Concerns: Intelligence Scraper

## Technical Risks

### 1. Cloudflare / WAF
Sites como Ricardo Almeida e Hering podem endurecer a segurança. Atualmente usamos `curl_cffi` e User-Agents reais, mas um fallback via Playwright/Stealth pode ser necessário em breve.

### 2. Event Loop Blocking
Operações pesadas no Pandas podem bloquear o loop principal se o volume de dados crescer muito (ex: > 10.000 skus). Implementamos `run_in_executor`, mas o monitoramento de performance é vital.

### 3. Memória
O armazenamento de produtos em memória antes de salvar o Excel pode ser um problema para varreduras gigantescas. Considerar streaming direto para disco ou banco de dados.

## Maintenance Concerns
- **Engine Evolution**: Mudanças profundas na API da VTEX podem quebrar o `VtexApiClient`.
- **Shopify JSON Changes**: A Shopify costuma ser estável, mas mudanças no formato das Collections exigirão ajustes no mapper.

## Future Tech Debt
- Migrar de JSON para SQLite para gerenciar marcas e monitores com maior integridade.
- Implementar testes unitários para os Engines.
