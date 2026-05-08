import asyncio
from services.engines.vtex_engine import VTEXEngine
from core.models import RawProductBronze

async def manual_verify():
    print("--- Início da Verificação Manual de Qualidade ---")
    
    # Simula o motor VTEX
    engine = VTEXEngine(brand_key="reserva")
    
    # Mock de resultados "sujos" que viriam do scraper
    dirty_results = [
        RawProductBronze(
            url="https://reserva.com/p1",
            brand="Reserva",
            raw_title="Camiseta OK",
            raw_description="Boa",
            price_full=159.0,
            image_url="https://img.reserva.com/1.jpg"
        ),
        # Preço Zero (deve ser barrado)
        {
            "url": "https://reserva.com/p2",
            "brand": "Reserva",
            "raw_title": "Camiseta Grátis (Erro)",
            "raw_description": "Erro no preço",
            "price_full": 0.0,
            "image_url": "https://img.reserva.com/2.jpg"
        },
        # Sem Imagem (deve ser barrado)
        {
            "url": "https://reserva.com/p3",
            "brand": "Reserva",
            "raw_title": "Camiseta Fantasma",
            "raw_description": "Sem imagem",
            "price_full": 89.0,
            "image_url": ""
        }
    ]
    
    def log_cb(payload):
        print(f"[LOG] {payload.get('message')}")

    print("\nExecutando Quality Gate...")
    filtered = engine.validate_and_filter(dirty_results, log_callback=log_cb)
    
    print(f"\nResultados Finais: {len(filtered)} de {len(dirty_results)}")
    for p in filtered:
        print(f"✅ Mantido: {p['raw_title']} - R$ {p['price_full']}")

if __name__ == "__main__":
    asyncio.run(manual_verify())
