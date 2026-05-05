import asyncio
import logging
from typing import Optional
from core.models import RawProductBronze
from services.vtex_api_scraper import VtexApiClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ScraperReserva")

async def scrape_competitor_product(
    product_url: str, brand_name: str
) -> Optional[RawProductBronze]:
    """Extrai os dados de um produto da Reserva delegando para o VtexApiClient."""
    try:
        logger.info(f"Iniciando extração via API-First para: {product_url}")
        async with VtexApiClient(brand_name) as client:
            product_data = await client.get_product_by_url(product_url)
            
            if product_data:
                logger.info("Extração concluída com sucesso via API.")
            else:
                logger.warning("Falha ao extrair dados via API.")
                
            return product_data
    except Exception as e:
        logger.error(f"Erro ao extrair produto via API: {e}")
        return None

async def main():
    # Testando a Polo da Reserva
    url_teste = "https://www.usereserva.com/polo-risca-tech-0097130-195/p"
    logger.info("Iniciando rotina de scraping do produto teste...")
    resultado = await scrape_competitor_product(url_teste, "Reserva (Azzas 2154)")

    if resultado:
        print("\n--- Dado Bruto Capturado (Camada Bronze) ---")
        print(resultado.model_dump_json(indent=2))
    else:
        logger.error("\nFalha na extração.")

if __name__ == "__main__":
    asyncio.run(main())
