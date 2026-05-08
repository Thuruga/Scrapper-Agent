# Integrations

## Internal Integrations
- **Scraper Factory**: Centralizes the creation of brand-specific scrapers.
- **Brand Service**: Manages brand registration and domain mapping.
- **Category Intelligence/Mapping**: Logic for resolving search queries to VTEX category paths and mapping category trees.
- **Price Monitor Service**: Background service for tracking price changes over time.
- **WebSocket Service**: Real-time communication for category scanning and job progress updates.

## External Integrations
- **VTEX Intelligent Search API**: Primary endpoint for product discovery and search.
- **VTEX Catalog System API**: Used for retrieving category trees and detailed product information.
- **VTEX Cross-Selling API**: Used for discovering product families (e.g., same model in different colors).
- **Brand Websites**: Direct scraping (when API fallbacks are needed) using Playwright or Curl-cffi.
- **Review Services**: Integrated via `review_service.py` (e.g., Yourviews or internal review systems depending on the brand).

## Data Export
- **Excel**: Integrated via Pandas and Openpyxl for generating downloadable reports.
