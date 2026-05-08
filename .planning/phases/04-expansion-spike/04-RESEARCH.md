# Research: Phase 04 - Expansion Spike (Shopify)

**Brand:** Ricardo Almeida
**Platform:** Shopify
**Status:** ✅ Validated

## Site Structure Analysis
- **Domain:** `https://www.ricardoalmeida.com.br/`
- **Engine Markers:** Shopify specific markers in HTML and `X-Shopify-Stage` headers.

## Data Extraction Strategy

### 1. Collection Discovery (Intelligent Discovery)
- **Endpoint:** `https://www.ricardoalmeida.com.br/collections.json?page={n}`
- **Format:** JSON array.
- **Key Fields:**
    - `title`: For fuzzy matching (e.g., "Camisas", "Sapatos").
    - `handle`: For building product URLs (`/collections/{handle}/products.json`).
    - `products_count`: To ignore empty collections.
- **Pagination:** 30 items per page.

### 2. Product Extraction (Scraping)
- **Endpoint:** `https://www.ricardoalmeida.com.br/collections/{handle}/products.json?page={n}&limit=250`
- **Format:** Shopify Standard Products JSON.
- **Key Fields Mapping to RawProductBronze:**
    - `title` -> `raw_title`
    - `handle` -> `url` (formatted as `/products/{handle}`)
    - `images[0].src` -> `image_url`
    - `variants[0].price` -> `price_full`
    - `variants[0].compare_at_price` -> `price_old` (if exists)
    - `variants` -> `available_sizes` (mapped from variant titles)
    - `options` -> `available_colors` (if one of the options is Color)

## WAF & Protection
- **Detection:** Ricardo Almeida is behind Cloudflare.
- **Access Test:** `curl_cffi` (impersonate chrome) successfully accessed the JSON endpoints without challenge during research.
- **Fallback:** If challenged, the system must use **Playwright** as defined in `04-CONTEXT.md`.

## Implementation Path
1. Update `BaseEngine` with a generic `get_catalog()` method.
2. Implement `ShopifyEngine` using `collections.json`.
3. Update `EngineFactory` to route brands based on the new `engine` field in `brands.json`.
