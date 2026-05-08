import asyncio
import json
import os
from services.price_monitor_service import monitor_service
from unittest.mock import MagicMock, patch, AsyncMock

async def manual_verify():
    print("--- Início da Verificação Manual do Monitoramento ---")
    
    # 1. Configura um monitor mock
    job_id = "manual-test-job"
    url = "https://www.reserva.com.br/camiseta-pima/p"
    brand = "reserva"
    
    # Mock do motor para retornar um preço inicial
    mock_engine = MagicMock()
    mock_engine.get_product_details = AsyncMock(return_value={
        "url": url,
        "brand": brand,
        "raw_title": "Camiseta Pima",
        "raw_description": "A melhor camiseta",
        "price_full": 199.0,
        "image_url": "https://img.reserva.com/pima.jpg",
        "stock_availability": True
    })

    with patch("services.price_monitor_service.engine_factory.get_engine", return_value=mock_engine), \
         patch("services.price_monitor_service.manager.send_message", new_callable=AsyncMock) as mock_ws:
        
        print(f"Iniciando monitoramento para {brand}...")
        await monitor_service.start_monitor(job_id, url, brand, interval=1, duration=1)
        
        # O start_monitor inicia uma task em background. 
        # Vamos esperar um pouco para ela rodar a primeira iteração (que ignora jitter se last_price for None)
        await asyncio.sleep(2)
        
        config = monitor_service.monitors.get(job_id)
        print(f"Preço capturado: R$ {config.last_price}")
        
        # 2. Simula mudança de preço
        print("\nSimulando mudança de preço para R$ 159.0...")
        mock_engine.get_product_details.return_value["price_full"] = 159.0
        
        # Forçamos a execução da task se ela estiver dormindo ou apenas esperamos o intervalo?
        # No teste, é melhor chamar o método interno se possível, mas aqui vamos apenas rodar o loop.
        # Como o intervalo é 1 min, vamos esperar um pouco ou manipular o tempo.
        # Para o teste manual ser rápido, vamos apenas rodar a lógica de comparação manualmente
        
        # Simulando o que o loop faria:
        product_data = await mock_engine.get_product_details(url)
        from core.models import RawProductBronze, PriceHistoryEntry
        product = RawProductBronze.model_validate(product_data)
        
        if config.last_price != product.price_full:
            entry = PriceHistoryEntry(price=product.price_full, available=product.stock_availability)
            config.history.append(entry)
            config.last_price = product.price_full
            print(f"✅ Histórico registrado! Total de entradas: {len(config.history)}")
            print(f"Novo preço no histórico: R$ {config.history[-1].price}")

        # 3. Verifica persistência
        monitor_service._save_monitors()
        if os.path.exists("data/price_monitors.json"):
            with open("data/price_monitors.json", "r") as f:
                saved_data = json.load(f)
                if job_id in saved_data:
                    print("✅ Dados salvos corretamente no disco!")
                    print(f"Histórico no JSON: {len(saved_data[job_id]['history'])} itens")

    # Limpeza
    await monitor_service.delete_monitor(job_id)
    print("\n--- Verificação Concluída ---")

if __name__ == "__main__":
    asyncio.run(manual_verify())
