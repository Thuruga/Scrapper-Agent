# Integrations

## External Services
- **E-commerce APIs**: VTEX (API v1) e Shopify (Admin API/JSON endpoints).
- **Proxies**: Integração com serviços de proxy rotativo via `IdentityManager`.

## Browser Automation
- **Playwright**: Utilizado como mecanismo de bypass de última instância.
  - Driver: Chromium (Headless).
  - User-Agents: Dinâmicos para emulação de dispositivos reais.

## Security & Auth
- **JWT Standard**: Assinatura de tokens via algoritmo HS256.
- **Bcrypt**: Hashing de senhas para persistência segura.

## Data Formats
- **Input**: JSON (API responses).
- **Output**: XLSX (Pandas ExcelWriter) para relatórios de negócio.
