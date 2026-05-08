# Integrations: Intelligence Scraper

## External Platforms

### 1. VTEX (Enterprise E-commerce)
- **Catalog API**: `pub/category/tree` para descoberta.
- **Search API**: `pub/products/search` para extração de dados.
- **Cross-Selling API**: Para descoberta de famílias de cores.

### 2. Shopify (SaaS E-commerce)
- **JSON API**: `collections.json` e `products.json`.
- **Search Suggest**: Endpoint de busca inteligente para auto-complete.

### 3. Trustvox (Reviews)
- Integração via API de widgets para coletar ratings e contagem de reviews.

## Output Formats
- **Excel (.xlsx)**: Relatórios formatados via Pandas com expansão de especificações JSON.
