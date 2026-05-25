# Phase 7 Context: Marketplace and Web Search Integration

## Domain
Expand comparative search to include Netshoes and Mercado Livre, extracting prices, sizes, and colors.

## Decisions

### 1. Architecture for Marketplaces
- **Decision**: Criar uma camada dinâmica global (`MarketplaceEngine`). Não devem ser fixos no `brands.json`.
- **Reasoning**: Necessidade de mapear múltiplos Sellers e as lógicas de Buy Box para controle de revendedores e políticas de preços (MAP). Tratados como meta-motores independentes das marcas próprias.

### 2. Performance vs Detail (Sizes & Colors)
- **Decision**: Abordagem Híbrida (Two-Tier).
- **Reasoning**: O endpoint `/search` deve ser otimizado para velocidade extrema, retornando apenas os dados disponíveis na listagem inicial. A extração profunda de grades (cores/tamanhos) será feita de forma **assíncrona** por background jobs que persistirão no Supabase *apenas* quando o produto for efetivamente monitorado.

### 3. Netshoes Scraping Approach
- **Decision**: Resiliência em Cascata.
- **Reasoning**: Para economizar memória RAM no Render, o primeiro ataque será via HTTP mascarado (`curl_cffi` com TLS Fingerprinting). O Playwright atuará unicamente como fallback final se o primeiro ataque falhar, devendo rodar com máxima restrição de memória (`--single-process`, `--disable-gpu`).

## Canonical Refs
- `data/brands.json` (apenas para não alterar marcas nativas).
- `core/models.py` (SearchProductResult e RawProductBronze).
- `services/engines/factory.py`.
