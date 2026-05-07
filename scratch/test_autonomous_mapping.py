import asyncio
import os
import json
from services.brand_service import brand_service
from core.models import DynamicBrandCreate

async def test_autonomous_mapping():
    print("Testing Autonomous Mapping Trigger...")
    
    # Simula cadastro de uma nova marca (ex: Reserva, mas com chave nova para não conflitar)
    brand_key = "reserva_test"
    brand_data = DynamicBrandCreate(
        brand_key=brand_key,
        brand_name="Reserva Test",
        domain="www.usereserva.com"
    )
    
    print(f"Adding brand {brand_key}...")
    brand_service.add_brand(brand_data)
    
    print("Waiting for background discovery (5s)...")
    await asyncio.sleep(5)
    
    updated_brand = brand_service.get_brand(brand_key)
    if updated_brand and updated_brand.mappings:
        print(f"\n[SUCCESS] Found {len(updated_brand.mappings)} mappings for {brand_key}:")
        for m in updated_brand.mappings:
            print(f"  - {m.canonical_slug}: {m.vtex_fq_path} ({m.label})")
    else:
        print(f"\n[FAILURE] No mappings found for {brand_key}. Check logs.")

    # Cleanup
    brand_service.delete_brand(brand_key)

if __name__ == "__main__":
    # Precisamos garantir que o brand_service use o arquivo de teste ou limpe depois
    asyncio.run(test_autonomous_mapping())
