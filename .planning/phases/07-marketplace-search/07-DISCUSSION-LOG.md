# Phase 7 Discussion Log

## Discussed Areas

### 1. Architecture for Marketplaces
- **User Selection**: Camada dinâmica global (MarketplaceEngine)
- **Notes**: Não devem ser fixos no brands.json, pois precisamos de mapear múltiplos Sellers e lógicas de Buy Box para controlo de revendedores e políticas de preços (MAP).

### 2. Performance vs Detalhe (Sizes & Colors)
- **User Selection**: Abordagem Híbrida (Two-Tier)
- **Notes**: Endpoint `/search` para velocidade extrema. Extração profunda (cores/tamanhos) será assíncrona, adicionada ao Supabase via background jobs apenas quando efetivamente monitorado.

### 3. Netshoes Scraping Approach
- **User Selection**: Resiliência em Cascata
- **Notes**: `curl_cffi` com TLS Fingerprinting primeiro. Playwright como fallback final (--single-process, --disable-gpu) para economizar RAM no Render.
