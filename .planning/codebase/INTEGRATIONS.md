# Integrations: Intelligence Scraper

## External Platforms

### 1. VTEX (Enterprise E-commerce)
- **Catalog API**: `pub/category/tree` for discovery.
- **Search API**: `pub/products/search` for data extraction.
- **Cross-Selling API**: For discovering color families and variant relationships.
- **Intelligence**: Fuzzy matching for category mapping.

### 2. Shopify (SaaS E-commerce)
- **JSON API**: `collections.json` and `products.json` endpoints.
- **Search Suggest**: Intelligent search endpoint for auto-complete and discovery.

### 3. Review Providers
- **Trustvox**: Widget API integration (`/widget/root`) for ratings and review counts.
- **VTEX Native Reviews**: REST API (`/reviews-and-ratings/api/rating/`) for native platform ratings.

## Output Formats
- **Excel (.xlsx)**: Formatted reports via Pandas with JSON specification expansion and parallel processing.
